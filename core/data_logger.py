import os
import csv
from datetime import datetime

def _ensure_directory_exists(filepath):
    os.makedirs(os.path.dirname(filepath), exist_ok=True)

def log_q_agent_interaction(user_name, timestamp, hr, rmssd, smoothed_rmssd, ai_state, action_freq, reward, next_rmssd):
    filepath = f"data/{user_name}_q_agent_training_data.csv"
    _ensure_directory_exists(filepath)
    file_exists = os.path.exists(filepath)
    with open(filepath, 'a', newline='') as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(["Timestamp", "Heart_Rate", "RMSSD", "Smoothed_RMSSD", "AI_State", "Action_Frequency_Hz", "Reward", "Next_RMSSD"])
        writer.writerow([timestamp.isoformat(), hr, rmssd, smoothed_rmssd, ai_state, action_freq, reward, next_rmssd])

def log_session_summary(user_name, date, duration_seconds, baseline_rmssd, final_rmssd, delta_rmssd):
    filepath = f"data/{user_name}_session_history.csv"
    _ensure_directory_exists(filepath)
    file_exists = os.path.exists(filepath)
    with open(filepath, 'a', newline='') as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(["Date", "Duration_Seconds", "Baseline_RMSSD", "Final_RMSSD", "Delta_RMSSD"])
        writer.writerow([date.isoformat(), duration_seconds, baseline_rmssd, final_rmssd, delta_rmssd])