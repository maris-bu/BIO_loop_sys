import asyncio
import multiprocessing as mp
import numpy as np
import csv
from datetime import datetime
import joblib
import pandas as pd
import random
import warnings

# Izslēdzam brīdinājumus par Pandas datu rāmjiem, lai netrokšņo terminālī
warnings.filterwarnings("ignore", category=UserWarning)

# --- 1. AUDIO PROCESS ---
def audio_process(shared_freq, shared_tempo):
    import sounddevice as sd 
    
    SAMPLE_RATE = 44100
    BASE_FREQ = 110.0 
    VOLUME = 0.8  # <--- Skaļums nomainīts uz 0.8 pēc tava pieprasījuma
    
    phase_l, phase_r, phase_iso, phase_tempo = 0.0, 0.0, 0.0, 0.0

    def callback(outdata, frames, time_info, status):
        nonlocal phase_l, phase_r, phase_iso, phase_tempo
        
        target_hz = float(shared_freq.value)
        tempo_hz = float(shared_tempo.value)
        
        t = np.arange(frames) / SAMPLE_RATE
        
        # Fiksētie fāzes aprēķini (novērš sprakšķus un aizturi)
        out_l = np.sin(phase_l + 2 * np.pi * BASE_FREQ * t)
        phase_l = (phase_l + 2 * np.pi * BASE_FREQ * frames / SAMPLE_RATE) % (2 * np.pi)
        
        out_r = np.sin(phase_r + 2 * np.pi * (BASE_FREQ + target_hz) * t)
        phase_r = (phase_r + 2 * np.pi * (BASE_FREQ + target_hz) * frames / SAMPLE_RATE) % (2 * np.pi)
        
        iso_env = 0.5 * (1.0 + np.sin(phase_iso + 2 * np.pi * target_hz * t))
        phase_iso = (phase_iso + 2 * np.pi * target_hz * frames / SAMPLE_RATE) % (2 * np.pi)
        
        tempo_env = 0.7 + 0.3 * np.sin(phase_tempo + 2 * np.pi * tempo_hz * t)
        phase_tempo = (phase_tempo + 2 * np.pi * tempo_hz * frames / SAMPLE_RATE) % (2 * np.pi)
        
        outdata[:, 0] = out_l * iso_env * tempo_env * VOLUME
        outdata[:, 1] = out_r * iso_env * tempo_env * VOLUME

    stream = sd.OutputStream(channels=2, callback=callback, samplerate=SAMPLE_RATE, blocksize=0)
    stream.start()
    
    import time
    while True:
        time.sleep(1)

# --- 2. Q-LEARNING AĢENTS ---
class QLearningAudioAgent:
    def __init__(self):
        # Iespējamās darbības (Audio frekvences: Theta, Alpha, Beta)
        self.actions = [6.0, 10.0, 14.0]
        self.q_table = {
            0: [0.0, 0.0, 0.0], # Stāvoklis 0: Miers
            1: [0.0, 0.0, 0.0]  # Stāvoklis 1: Stress
        }
        self.learning_rate = 0.1
        self.discount_factor = 0.9
        self.epsilon = 0.2 # 20% laika viņš eksperimentēs
        
        self.last_state = None
        self.last_action_idx = None
    
    def choose_action(self, state):
        if random.uniform(0, 1) < self.epsilon:
            action_idx = random.randint(0, 2)
            msg = "(Eksperiments)"
        else:
            action_idx = np.argmax(self.q_table[state])
            msg = "(Gudrā izvēle)"
            
        self.last_state = state
        self.last_action_idx = action_idx
        return self.actions[action_idx], msg

    def update_q_table(self, reward):
        if self.last_state is not None and self.last_action_idx is not None:
            old_value = self.q_table[self.last_state][self.last_action_idx]
            new_value = old_value + self.learning_rate * (reward - old_value)
            self.q_table[self.last_state][self.last_action_idx] = new_value

# --- 3. BLUETOOTH UN ML LOGIKA ---
MAC_ADDRESS = "C6:3E:75:B3:A5:EB"
HR_MEASUREMENT_UUID = "00002a37-0000-1000-8000-00805f9b34fb"

def calculate_rmssd(rr_buffer):
    if len(rr_buffer) < 2: return 0
    return np.sqrt(np.mean(np.square(np.diff(rr_buffer))))

async def ble_main(shared_freq, shared_tempo):
    from bleak import BleakClient, BleakScanner
    
    # 1. Ielādējam ML modeli
    try:
        classifier = joblib.load('stresa_modelis.joblib')
        print("🧠 ML Modelis 'stresa_modelis.joblib' ielādēts veiksmīgi!")
    except:
        print("❌ Nevaru atrast stresa_modelis.joblib. Pārliecinies, ka tas atrodas šajā mapē.")
        return

    ai_agent = QLearningAudioAgent()

    rr_history = [] 
    last_rmssd = 0
    decision_counter = 0

    def notification_handler(sender, data):
        nonlocal last_rmssd, rr_history, decision_counter
        
        flags = data[0]
        hr_format = flags & 0x01
        rr_present = (flags & 0x10) >> 4
        current_offset = 1
        
        if hr_format == 0:
            hr = data[current_offset]; current_offset += 1
        else:
            hr = int.from_bytes(data[current_offset:current_offset+2], byteorder='little'); current_offset += 2

        if rr_present:
            while current_offset < len(data):
                rr_raw = int.from_bytes(data[current_offset:current_offset+2], byteorder='little')
                rr_history.append( int((rr_raw / 1024.0) * 1000.0) )
                if len(rr_history) > 20: rr_history.pop(0)
                current_offset += 2

        current_rmssd = calculate_rmssd(rr_history)
        
        # Q-Learning atalgojums
        reward = 0
        if current_rmssd > last_rmssd + 0.5: reward = 1.0   
        elif current_rmssd < last_rmssd - 0.5: reward = -1.0 
        ai_agent.update_q_table(reward)
        last_rmssd = current_rmssd

        # ML Klasifikācija
        if current_rmssd > 0:
            features = pd.DataFrame([[hr, current_rmssd]], columns=['BPM', 'RMSSD'])
            predicted_state = classifier.predict(features)[0] 
        else:
            predicted_state = 0
            
        state_text = "STRESS" if predicted_state == 1 else "MIERS "

        decision_counter += 1
        
       # =========================================================
        # REĀLLAIKA DRUKA (DEMO REŽĪMS)
        # =========================================================
        print(f"Sitiens [{decision_counter:2d}/10] | BPM: {hr:3d} | RMSSD: {current_rmssd:5.1f}ms | AI klasifikators: {state_text}")

       # =========================================================
        # Q-LEARNING EPOHA (DEMO REŽĪMS): Reizi 10 sitienos
        # =========================================================
        if decision_counter >= 10:
            chosen_freq, tactic = ai_agent.choose_action(predicted_state)
            shared_freq.value = chosen_freq
            decision_counter = 0
            
            target_bpm = max(55, hr - 5)
            shared_tempo.value = target_bpm / 60.0 

            print("\n" + "═"*60)
            print(f" 🤖 Q-AĢENTA LĒMUMS: Pārslēdzu uz {chosen_freq}Hz {tactic}")
            print("═"*60 + "\n")

    device = await BleakScanner.find_device_by_address(MAC_ADDRESS, timeout=10.0)
    if not device: 
        print("❌ Neizdevās atrast jostu. Pārbaudi savienojumu vai samitrini kontaktus.")
        return

    try:
        async with BleakClient(device, timeout=15.0) as client:
            print("\n🚀 HIBRĪDA SISTĒMA ONLINE: Datu plūsma sākta!")
            await client.start_notify(HR_MEASUREMENT_UUID, notification_handler)
            await asyncio.sleep(3600) # <--- Lūk, šeit bija pazudusi iekava un skaitlis!
    except Exception as e:
        print(f"Savienojuma kļūda: {repr(e)}")

# --- 4. STARTA PUNKTS ---
if __name__ == "__main__":
    mp.freeze_support() 
    print("\n" + "═"*40)
    print("  AI BIOFEEDBACK SISTĒMA (HIBRĪDS)")
    print("═"*40)
    
    while True:
        cmd = input("Nospied 'S' un Enter, lai sāktu: ").strip().upper()
        if cmd == 'S': break

    shared_freq = mp.Value('d', 10.0)
    shared_tempo = mp.Value('d', 1.0) 
    
    audio_p = mp.Process(target=audio_process, args=(shared_freq, shared_tempo), daemon=True)
    audio_p.start()
    
    try:
        asyncio.run(ble_main(shared_freq, shared_tempo))
    except KeyboardInterrupt:
        print("\nSistēma apturēta.")