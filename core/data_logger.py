import os
import csv
from datetime import datetime

Q_AGENT_DATA_FILE = "data/q_agent_training_data.csv"
SESSION_HISTORY_FILE = "data/session_history.csv"

def _ensure_directory_exists(filepath):
    os.makedirs(os.path.dirname(filepath), exist_ok=True)

def log_q_agent_interaction(timestamp, hr, rmssd, smoothed_rmssd, ai_state, action_freq, reward, next_rmssd):
    _ensure_directory_exists(Q_AGENT_DATA_FILE)
    file_exists = os.path.exists(Q_AGENT_DATA_FILE)
    with open(Q_AGENT_DATA_FILE, 'a', newline='') as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(["Timestamp", "Heart_Rate", "RMSSD", "Smoothed_RMSSD", "AI_State", "Action_Frequency_Hz", "Reward", "Next_RMSSD"])
        writer.writerow([timestamp.isoformat(), hr, rmssd, smoothed_rmssd, ai_state, action_freq, reward, next_rmssd])

def log_session_summary(date, duration_seconds, baseline_rmssd, final_rmssd, delta_rmssd):
    _ensure_directory_exists(SESSION_HISTORY_FILE)
    file_exists = os.path.exists(SESSION_HISTORY_FILE)
    with open(SESSION_HISTORY_FILE, 'a', newline='') as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(["Date", "Duration_Seconds", "Baseline_RMSSD", "Final_RMSSD", "Delta_RMSSD"])
        writer.writerow([date.isoformat(), duration_seconds, baseline_rmssd, final_rmssd, delta_rmssd])