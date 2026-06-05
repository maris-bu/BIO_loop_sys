import multiprocessing as mp

SAMPLE_RATE = 44100
BASE_FREQ = 110.0
VOLUME = 4

def audio_process(shared_freq, shared_tempo):
    import numpy as np
    import sounddevice as sd 
    
    phase_l, phase_r, phase_iso, phase_tempo = 0.0, 0.0, 0.0, 0.0

    def callback(outdata, frames, time_info, status):
        nonlocal phase_l, phase_r, phase_iso, phase_tempo
        
        target_hz = float(shared_freq.value)
        tempo_hz = float(shared_tempo.value)
        
        t = np.arange(frames) / SAMPLE_RATE
        
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