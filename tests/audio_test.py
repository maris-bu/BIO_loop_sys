import numpy as np
import sounddevice as sd
import time

def play_binaural_beat(base_freq, beat_freq, duration=5, sample_rate=44100):
    print(f"Spēlēju binaurālo ritmu: {beat_freq} Hz (Pamata frekvence: {base_freq} Hz)")
    
    # Izveidojam laika asi
    t = np.linspace(0, duration, int(sample_rate * duration), endpoint=False)
    
    # Kreisā auss: Tīra pamata frekvence (piemēram, 200 Hz)
    left_channel = np.sin(2 * np.pi * base_freq * t)
    
    # Labā auss: Pamata frekvence + ritms (piemēram, 210 Hz)
    right_channel = np.sin(2 * np.pi * (base_freq + beat_freq) * t)
    
    # Saliekam abus kanālus kopā stereo signālā
    stereo_signal = np.vstack((left_channel, right_channel)).T
    
    # Pārvēršam datus formātā, ko saprot skaņas karte
    stereo_signal = np.float32(stereo_signal)
    
    # Atskaņojam
    sd.play(stereo_signal, sample_rate)
    sd.wait() # Pagaidām, kamēr skaņa beidz skanēt

if __name__ == "__main__":
    print("Sagatavojies - skaņa skanēs 5 sekundes.")
    time.sleep(1)
    
    # 200 Hz pamats, 10 Hz ritms (Alfa viļņi - relaksācijai)
    play_binaural_beat(base_freq=200, beat_freq=10, duration=5)