

Sākotnējais prototips (main.py) mēģināja izmantot ANT+ protokolu (openant bibliotēka).

Problēma: ANT+ pieprasa specifiskus USB uztvērējus (dongles) un kompleksu libusb draiveru konfigurāciju, kas radīja nestabilitāti un apgrūtināja sistēmas pārnesamību (portability).

Risinājums: Pilnīga pāreja uz BLE (Bluetooth Low Energy), izmantojot Python bleak asinhrono bibliotēku. BLE ir natively atbalstīts visās modernajās operētājsistēmās un nodrošina stabilu reāllaika R-R intervālu plūsmu (ko nodrošina EKG jostas, piem., Polar H10 vai Hammerhead). Windows OS "Tap to set up your device" pairing prompt tika atrisināts, izmantojot `BleakClient` ar `winrt={"use_cached_services": False}` konfigurāciju, lai apietu OS piesaistes pieprasījumu.

Kritisko 60 Pukstu "Epohas" Likums

Sākotnējā iterācijā Q-Learning aģents mainīja audio stimulus pie katrām mikroskopiskām stresa izmaiņām.

Atklājums: Pārāk bieža audio frekvenču maiņa izsauc Orienting Response (Orientēšanās/trauksmes refleksu), kas aktivizē simpātisko nervu sistēmu un pazemina HRV.

Arhitektūras likums: Lai smadzenes spētu sinhronizēties ar jauno ritmu (izveidotos FFR), aģents drīkst veikt izmaiņas tikai pēc 60 sirdspukstu (aptuveni 1 minūtes) epohas. (Piezīme: hackathon_mvp.py demo nolūkos tas īslaicīgi tika samazināts uz 10).

Reāllaika Audio un Fāžu Aprēķini

Lai nodrošinātu efektīvu Binaural Beats un Isochronic Tones iedarbību, skaņai jābūt perfektai, bez kompresijas (MP3 ir aizliegts).

Audio Ģenerēšana: Skaņa tiek ģenerēta reāllaikā ar numpy.sin un sounddevice.

Kropļojumu (Stutter) novēršana: Python GIL (Global Interpreter Lock) dēļ, asinhronais kods joprojām var radīt skaņas kropļojumus ("sprakšķus"). Audio palaišana ar multiprocessing.Process nodrošina nepārtrauktu plūsmu. Fāzes tiek kalkulētas nepārtraukti, lai frekvenču maiņas (no 10Hz uz 6Hz) notiktu gludi.

Kustību artefaktu ignorēšana: Bez >150ms filtra sistēma reģistrētu zaudētu kontaktu kā "izcili augstu HRV/RMSSD", tādējādi izjaucot Q-Learning atlīdzības sistēmu.

60 Sitienu Epoha (FFR likums): Zinātniski pamatots atklājums. Ātrāka frekvenču maiņa rada Orienting Response (stresu). AI aģents nedrīkst mainīt stāvokli pārāk ātri.

**Jaunumi (Pēdējās izmaiņas):**

- Real-time RMSSD trend display un sesijas kopsavilkums: Ieviests reāllaika RMSSD izmaiņu attēlojums un sesijas kopsavilkums, kas tiek parādīts pēc programmas apturēšanas (Ctrl+C). Šīs funkcijas sniedz lietotājam precīzu ieskatu par sirds ritma variabilitātes tendencēm gan sesijas laikā, gan kopumā.
- Q-table saglabāšana/ielāde: Q-Learning aģenta Q-tabula tagad tiek automātiski saglabāta failā (piemēram, `data/{user_name}_q_table.pkl`) pēc katras sesijas un ielādēta programmas starta laikā, nodrošinot aģenta mācīšanās nepārtrauktību un individuālu lietotāju profilu atbalstu.
- Automatizēta datu reģistrēšana: Visi Q-Agent mijiedarbības dati (Timestamp, Heart_Rate, RMSSD, Smoothed_RMSSD, AI_State, Action_Frequency_Hz, Reward, Next_RMSSD) tiek saglabāti lietotāja profilam specifiskā failā (piemēram, `data/{user_name}_q_agent_training_data.csv`). Sesijas kopsavilkumi tiek saglabāti `data/{user_name}_session_history.csv` failā, nodrošinot vēsturisko analīzi un pamatu dziļākas mācīšanās modeļiem. Jaunā `core/data_logger.py` arhitektūra nodrošina šo funkcionalitāti.

Daudzlietotāju Arhitektūra un Datu Savienošanas Koncepcija:

* Q-tabulas (.pkl failus) NEKAD nedrīkst matemātiski apvienot vai sapludināt, jo katra cilvēka veģetatīvā nervu sistēma uz audio frekvencēm reaģē unikāli (tas, kas vienu nomierina, otram var izraisīt stresu). Apvienojot Q-tabulas, AI tiktu sabojāts.
* Kolektīvā pētniecība un datu savienošana notiek caur neapstrādātajiem pieredzes datiem (.csv failiem). Dažādu lietotāju CSV faili (State, Action, Reward, Next State) vēlāk tiek apvienoti vienā milzīgā datu masīvā (Master Dataset). Šis kopējais masīvs tiks izmantots, lai nākotnē trenētu vispārīgu neironu tīklu (Deep Q-Network), kas spēj atpazīt universālus cilvēku biometriskos modeļus.

Zinātniskais Pamatojums: Audio Terapijas Modeļi

* **Binaurālie ritmi (Brainwave Entrainment):**
  - Delta (0.5–4 Hz): Dziļa atjaunošanās, parasimpātiskā nervu sistēma.
  - Theta (4–8 Hz): Relaksācija, HRV/RMSSD paaugstināšana.
  - Alpha (8–14 Hz): Viegla atslābināšanās un "plūsmas" (flow) stāvoklis.
* **Vibroakustiskā terapija (VAT) - MŪSU IZVĒLE:**
  - Tīri zemo frekvenču sinusoidālie viļņi (30-120 Hz). 
  - 40 Hz ir "zelta standarts" (MIT pētījumi) neiroiekaisumu mazināšanai. Frekvences zem 40 Hz (piem., 30 Hz) tieši stimulē vagusa nervu.
* **Akustiskā maskēšana (Krāsu trokšņi):**
  - Rozā troksnis (stresa mazināšana), Brūnais troksnis (fokuss, ADHD).
* **Brīdinājums par Pseidoloģiju:** Solfedžo frekvencēm (piem., 432 Hz, 528 Hz) trūkst zinātniska un klīniska pamatojuma, tās sistēmā neizmantojam.
