import random
import warnings
import pickle
import os

# Izslēdzam brīdinājumus par Pandas datu rāmjiem, lai netrokšņo terminālī
warnings.filterwarnings("ignore", category=UserWarning)

class QLearningAudioAgent:
    def __init__(self, user_name="default", storage_dir="data"):
        self.user_name = user_name
        self.storage_dir = storage_dir
        self.actions = [30, 40, 50, 60, 80]
        self.q_table = {
            0: [0.0, 0.0, 0.0],
            1: [0.0, 0.0, 0.0]
        }
        self.learning_rate = 0.1
        self.discount_factor = 0.9
        self.epsilon = 0.2
        
        self.last_state = None
        self.last_action_idx = None
    
    def choose_action(self, state):
        if random.uniform(0, 1) < self.epsilon:
            action_idx = random.randint(0, 2)
            msg = "(Eksperiments)"
        else:
            action_idx = max(range(len(self.q_table[state])), key=self.q_table[state].__getitem__)
            msg = "(Gudrā izvēle)"
            
        self.last_state = state
        self.last_action_idx = action_idx
        return self.actions[action_idx], msg

    def update_q_table(self, reward):
        if self.last_state is not None and self.last_action_idx is not None:
            old_value = self.q_table[self.last_state][self.last_action_idx]
            new_value = old_value + self.learning_rate * (reward - old_value)
            self.q_table[self.last_state][self.last_action_idx] = new_value

    def save_model(self):
        filepath = os.path.join(self.storage_dir, f"{self.user_name}_q_table.pkl")
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, 'wb') as f:
            pickle.dump(self.q_table, f)

    def load_model(self):
        filepath = os.path.join(self.storage_dir, f"{self.user_name}_q_table.pkl")
        if os.path.exists(filepath):
            with open(filepath, 'rb') as f:
                self.q_table = pickle.load(f)
            print(f"Nevori learning memory loaded for {self.user_name}.")
        else:
            print(f"Starting a new local learning memory for {self.user_name}.")

class StressClassifier:
    def __init__(self, model_path="stresa_modelis.joblib"):
        self.model = None
        try:
            import joblib
            self.model = joblib.load(model_path)
            print("Nevori stress classifier loaded.")
        except (FileNotFoundError, ImportError, ModuleNotFoundError, ValueError):
            print("Nevori is using its built-in HR/HRV stress heuristic.")

    def predict(self, hr, rmssd):
        if self.model is None:
            # Conservative local fallback: elevated HR together with suppressed
            # RMSSD indicates a likely higher-arousal state.
            return int(hr >= 78 and rmssd <= 38)
        try:
            import pandas as pd
            features = pd.DataFrame([[hr, rmssd]], columns=["BPM", "RMSSD"])
            return self.model.predict(features)[0]
        except (ImportError, ModuleNotFoundError):
            return int(hr >= 78 and rmssd <= 38)
