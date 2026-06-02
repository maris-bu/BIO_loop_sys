import asyncio
import multiprocessing as mp

from core.audio_engine import audio_process
from core.ai_brain import QLearningAudioAgent, StressClassifier
from core.utils import calculate_rmssd
from core.ble_receiver import ble_receiver

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

    classifier = StressClassifier(model_path='stresa_modelis.joblib')
    ai_agent = QLearningAudioAgent()
    ai_agent.load_model()
    
    try:
        asyncio.run(ble_receiver(shared_freq, shared_tempo, classifier, ai_agent, calculate_rmssd))
    except KeyboardInterrupt:
        print("\nSaņemts apturēšanas signāls (Ctrl+C)...")
    finally:
        ai_agent.save_model()
        print("🧠 Q-Aģenta atmiņa (Q-table) veiksmīgi saglabāta nākamajam seansam!")
        print("Apturu audio dzinēju...")
        if audio_p.is_alive():
            audio_p.terminate()
            audio_p.join()
        print("Sistēma veiksmīgi apturēta.")
