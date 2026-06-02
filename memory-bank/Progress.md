Tehniskā Atmiņas Karte (Technical Memory Map)

Statuss: Prototips (Proof of Concept - Hackathon MVP līmenī)
Vide: Python 3.x, Visual Studio Code
Aparatūra: BLE sirds ritma josta (Hammerhead / Polar H10)

1. SISTĒMAS ARHITEKTŪRA (HIBRĪDAIS MODELIS)

Sistēma darbojas reāllaika asinhronā ciklā, apvienojot aparatūras ievadi, mašīnmācīšanos un audio ģenerēšanu:

Datu iegūšana (Sense): bleak nolasa BLE R-R intervālus. Tiek uzturēts 20 sitienu slīdošais logs (rolling window).

Filtrēšana: Ekstrēmi lēcieni (>150ms starpība) tiek ignorēti, lai novērstu sensora atvienošanās radītos artefaktus. Tiek aprēķināts RMSSD.

1. Slānis (Analyze): RandomForestClassifier nosaka bāzes stāvokli (0 = Miers, 1 = Stress), izmantojot 66.9% svaru BPM un 33.1% svaru RMSSD.

2. Slānis (Adapt): QLearningAudioAgent izmanto Epsilon-Greedy (20% eksperimentē), lai izvēlētos rīcību (6Hz, 10Hz, 14Hz). Atlīdzība (Reward) tiek dota, ja RMSSD pieaug.

Audio (Respond): Tīri sinusoīdu viļņi (Binaural Beats + Isochronic Tones) tiek atskaņoti reāllaikā izolētā procesā, novēršot skaņas aizkaves.

2. KODA BĀZES STĀVOKLIS (VS Code Pārskats)

hackathon_mvp.py (Galvenais dzinējs): Aktīvais, strādājošais MVP skripts. Izmanto multiprocessing audio atdalīšanai no BLE plūsmas. Satur Q-Learning aģenta un BLE loģiku. Piezīme: Šobrīd epoha iestatīta uz 10 pukstiem demo nolūkiem.

train_model.py: Skripts, kas ielādē miers.csv un stress.csv, iztīra datus un apmāca Random Forest modeli. Rezultātu saglabā kā stresa_modelis.joblib.

audio_test.py: Laboratorijas skripts tīru binaurālo ritmu ģenerēšanas testēšanai (numpy + sounddevice).

main_ble.py: Sandbox skripts tīrai BLE datu nolasīšanai un izpratnei.

main.py & libusb-1.0.dll: (Novecojis/Arhīvs) Iepriekšējie mēģinājumi savienoties caur ANT+ protokolu.

stresa_modelis.joblib: Apmācītais Random Forest modelis (Gatavs lietošanai reāllaikā).

3. KRITISKIE INŽENIERIJAS LĒMUMI (Kāpēc darām tā?)

BLE pārākums pār ANT+: ANT+ prasīja specifiskus draiverus un USB "dongles", kas radīja konfliktus (openant). BLE ir stabili iebūvēts OS līmenī.

Multiprocessing audio izvadei: Python Global Interpreter Lock (GIL) dēļ, asinhronais kods joprojām var radīt skaņas kropļojumus ("sprakšķus"). Audio palaišana ar multiprocessing.Process nodrošina nepārtrauktu plūsmu. Fāzes tiek kalkulētas nepārtraukti, lai frekvenču maiņas (no 10Hz uz 6Hz) notiktu gludi.

Kustību artefaktu ignorēšana: Bez >150ms filtra sistēma reģistrētu zaudētu kontaktu kā "izcili augstu HRV/RMSSD", tādējādi izjaucot Q-Learning atlīdzības sistēmu.

60 Sitienu Epoha (FFR likums): Zinātniski pamatots atklājums. Ātrāka frekvenču maiņa rada Orienting Response (stresu). AI aģents nedrīkst mainīt stāvokli pārāk ātri.

4. ATTĪSTĪBAS BACKLOGS (Ko darīt tālāk koda līmenī)

Refaktorēšana (Modulārā arhitektūra):

Sadalīt lielo hackathon_mvp.py atsevišķos moduļos: core/audio_engine.py, core/ble_receiver.py, core/ai_brain.py. Šādi mēs sagatavosimies nākotnes sistēmas uzturēšanai.

Ražošanas (Production) Epohas ieviešana:

Koda loģikā nomainīt demonstrācijas epohu (decision_counter >= 10) uz zinātniski validēto 60 pukstu epohu.

Uzlabota Q-Table un Modelis:

Q-Learning algoritma uzlabošana (nākotnē pāreja uz PPO/Stable Baselines3).

Random Forest modeļa pārtrenēšana uz industriāli atzītām datubāzēm (WESAD, PhysioNet).

Validācijas Datu vākšana:

Pievienot datu saglabāšanas loģiku (log failus), kas automātiski pieraksta katras sesijas rezultātus vēlākai analīzei un pētījumiem.

COMPLETED:
- [x] Refactor `hackathon_mvp.py` into a modular architecture.
- [x] Add Dual BLE Support (Polar H10 + Hammerhead).
- [x] Implement the Scientific Epoch (60 beats).
- [x] Polar H10 BLE integration working and streaming data.
- [x] Implement real-time RMSSD trend display in terminal.
- [x] Implement session summary on shutdown.
- [x] Implement Q-table persistence (saving/loading).
- [x] Implement automated CSV data logging for Q-Agent interactions and session summaries.
- [x] Implement multi-user profile system with dynamic file naming for Q-table and data logs.
- [x] Update Q-Agent\'s action space to use Vibroacoustic Therapy (VAT) tones.
