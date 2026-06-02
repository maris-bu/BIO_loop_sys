import numpy as np

def calculate_rmssd(rr_buffer):
    if len(rr_buffer) < 2: return 0
    diff_rr = np.diff(rr_buffer)
    # Filter out artifacts > 150ms
    diff_rr_filtered = diff_rr[np.abs(diff_rr) <= 150] 
    if len(diff_rr_filtered) < 2: return 0
    return np.sqrt(np.mean(np.square(diff_rr_filtered)))