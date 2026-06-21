"""Nevori launcher.

Running ``python main.py`` starts the complete local web app. The original
hardware pipeline remains available with ``python main.py --hardware``.
"""
from __future__ import annotations

import argparse
import asyncio
import multiprocessing as mp


def run_hardware() -> None:
    from core.ai_brain import QLearningAudioAgent, StressClassifier
    from core.audio_engine import audio_process
    from core.ble_receiver import ble_receiver
    from core.utils import calculate_rmssd

    mp.freeze_support()
    print("\n" + "=" * 42)
    print("  NEVORI HARDWARE BIOFEEDBACK")
    print("=" * 42)
    user_name = input("Your name: ").strip().replace(" ", "_").lower() or "default"
    input("Press Enter when your heart-rate device is ready...")

    shared_freq = mp.Value("d", 10.0)
    shared_tempo = mp.Value("d", 1.0)
    audio_process_handle = mp.Process(target=audio_process, args=(shared_freq, shared_tempo), daemon=True)
    audio_process_handle.start()

    classifier = StressClassifier(model_path="stresa_modelis.joblib")
    agent = QLearningAudioAgent(user_name=user_name)
    agent.load_model()
    try:
        asyncio.run(ble_receiver(user_name, shared_freq, shared_tempo, classifier, agent, calculate_rmssd))
    except KeyboardInterrupt:
        print("\nStopping Nevori...")
    finally:
        agent.save_model()
        if audio_process_handle.is_alive():
            audio_process_handle.terminate()
            audio_process_handle.join()


def main() -> None:
    parser = argparse.ArgumentParser(description="Nevori bio-adaptive recovery app")
    parser.add_argument("--hardware", action="store_true", help="run the original BLE and native-audio pipeline")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()
    if args.hardware:
        run_hardware()
    else:
        from app_server import run_server
        run_server(args.host, args.port)


if __name__ == "__main__":
    main()
