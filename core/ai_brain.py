import numpy as np
import random
import joblib
import pandas as pd
import warnings

# Izslēdzam brīdinājumus par Pandas datu rāmjiem, lai netrokšņo terminālī
warnings.filterwarnings("ignore", category=UserWarning)

class QLearningAudioAgent:
    def __init__(self):
        self.actions = [6.0, 10.0, 14.0]
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

class StressClassifier:
    def __init__(self, model_path='stresa_modelis.joblib'):
        try:
            self.model = joblib.load(model_path)
            print(f"🧠 ML Model \'{model_path}\' ielādēts veiksmīgi!")
        except FileNotFoundError:
            print(f"❌ Nevaru atrast {model_path}. Pārliecinies, ka tas atrodas pareizajā mapē.")
            self.model = None

    def predict(self, hr, rmssd):
        if self.model is None: 
            return 0 # Default to 'MIERS' if model not loaded
        features = pd.DataFrame([[hr, rmssd]], columns=['BPM', 'RMSSD'])
        return self.model.predict(features)[0]