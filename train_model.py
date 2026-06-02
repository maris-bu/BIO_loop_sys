import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, accuracy_score
import joblib

print("Izvelku datus un būvēju modeli...")

# 1. DATU IELĀDE (Ieliekam kolonnu nosaukumus, jo tavā CSV to pirmajā rindā nav)
kolonnas = ['Laiks', 'BPM', 'RR', 'RMSSD', 'Target_BPM']

try:
    df_miers = pd.read_csv('miers.csv', names=kolonnas, header=None)
    df_stress = pd.read_csv('stress.csv', names=kolonnas, header=None)
except FileNotFoundError:
    print("Kļūda: Nevaru atrast miers.csv vai stress.csv failus!")
    exit()

# 2. DATU TĪRĪŠANA UN SAGATAVOŠANA
# Izmetam nulles (kad josta nevarēja aprēķināt starpību) 
# Izmetam rādījumus virs 150ms, kas ir kustību artefakti no pietupieniem
df_miers = df_miers[(df_miers['RMSSD'] > 0) & (df_miers['RMSSD'] < 150)].copy()
df_stress = df_stress[(df_stress['RMSSD'] > 0) & (df_stress['RMSSD'] < 150)].copy()

# Pievienojam marķierus (Labels), kas ir mūsu "Pareizās atbildes" modelim
df_miers['Label'] = 0   # 0 = Miers / Dīvāna klaiņošana
df_stress['Label'] = 1  # 1 = Stress / Fizisks fokuss

# Apvienojam visu vienā lielā tabulā
df_all = pd.concat([df_miers, df_stress], ignore_index=True)

# 3. IZDZALAM DATUS (Features vs Target)
# Izmantosim tikai Pulsu un RMSSD lēmuma pieņemšanai
X = df_all[['BPM', 'RMSSD']]
y = df_all['Label']

# Sadalām datus: 80% treniņam, 20% eksāmenam (testēšanai)
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

# 4. MODEĻA TRENĒŠANA (Random Forest)
model = RandomForestClassifier(n_estimators=100, max_depth=5, random_state=42)
model.fit(X_train, y_train)

# 5. MODEĻA PĀRBAUDE UN REZULTĀTI
y_pred = model.predict(X_test)
accuracy = accuracy_score(y_test, y_pred)
importance = model.feature_importances_

print("-" * 40)
print(f"Iztīrīto datu rindu skaits: {len(df_all)}")
print(f"Modeļa precizitāte: {accuracy * 100:.1f}%")
print("Kas modelim šķita svarīgāks stāvokļa noteikšanā?")
print(f" -> Pulss (BPM): {importance[0] * 100:.1f}%")
print(f" -> Variabilitāte (RMSSD): {importance[1] * 100:.1f}%")
print("-" * 40)

# 6. SAGLABĀŠANA NĀKOTNEI
filename = 'stresa_modelis.joblib'
joblib.dump(model, filename)
print(f"✅ Modelis veiksmīgi saglabāts kā '{filename}'!")
print("Tagad to var integrēt galvenajā reāllaika skriptā.")