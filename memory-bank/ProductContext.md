Projekta Atmiņas Fails (Project Knowledge Base)

Pēdējais atjauninājums: 2026. gada jūnijs

Projekta nosaukums: Neuro-Acoustic Biofeedback System (Darba nosaukums) Autors/Dibinātājs: Māris Bulats (bijušais izturības sportists, maģistrants) ---

1. PROJEKTA IDENTITĀTE UN VĪZIJA

Koncepcija: Slēgta cikla (closed-loop) AI vadīta biofeedback sistēma, kas izmanto reāllaika sirds ritma variabilitātes (HRV) datus, lai ģenerētu personalizētu audio (neiro-akustisko) stimulāciju.

Vērtības piedāvājums (Value Proposition): Esošās viedierīces (Garmin, Whoop) tikai pasīvi mēra nogurumu. Mūsu sistēma to aktīvi labo, fiziski piespiežot Centrālo nervu sistēmu (CNS) pārslēgties no simpātiskā (stresa) uz parasimpātisko (atjaunošanās) stāvokli minūšu laikā.

"Beachhead" (Ieejas) Tirgus: Izturības sportisti (triatlonisti, riteņbraucēji, maratonisti).

Mērogošanas vīzija (The Multi-Billion Pivot): Pēc validācijas sporta tirgū, algoritms tiks pielāgots korporatīvajam wellness, miega traucējumu klīnikām un trauksmes novēršanas (anxiety) tirgum.

2. ZINĀTNISKAIS UN TEHNISKAIS PAMATOJUMS

Problēma ("Stress Bucket"): Cilvēkam ir viena stresa kapacitāte. Smags treniņš un smaga darba diena vienādi pārslogo CNS. Kad CNS ir "izdegusi", smadzenes iesprūst Beta viļņu (13-30 Hz) stāvoklī, un vienkārša "nomierināšanās" nestrādā, jo trūkst kognitīvās enerģijas.

Tehniskā arhitektūra (Targeted Sensory Immersion):

Ievade: EKG krūšu josta (piem., Polar H10, Hammerhead) caur Bluetooth Low Energy (BLE). Nodrošina milisekunžu precizitātes R-R intervālus.

Hibrīda AI Apstrāde:

1. Slānis (Klasifikators): Random Forest modelis, kas atpazīst stāvokli (Miers/Stress), balstoties uz BPM un RMSSD.

2. Slānis (Aģents): Q-Learning aģents. Reward: RMSSD pieaugums (+1). Action: Audio frekvences maiņa.

Izvade: Dinamiski modulēti binaurālie ritmi un izohronie toņi, kas ģenerēti reāllaikā ar fiksētu fāzi (bez MP3 kompresijas zudumiem).

Kritiskais Atklājums (60-beat Epoch): Lai novērstu stresa (Orienting Response) refleksu, stimulus drīkst mainīt ne biežāk kā reizi 60 sirdspukstos.

3. BIZNESA MODELIS UN GO-TO-MARKET

Modelis: Tīrs programmatūras (SaaS) bizness (Hardware-agnostic). Nulle ražošanas izmaksu, 90%+ marža.

Monetizācija: Freemium modelis. Bezmaksas izmēģinājums + Premium abonements (~€15/mēn).

Konkurences priekšrocība: Vienīgais "Aktīvais + Biometriskais" risinājums tirgū (pretstatā pasīvajam Garmin/Oura un subjektīvajam Headspace/Calm).

4. PITCHING STRATĒĢIJA (TRANSLATION FRAMEWORK)

Aspekts

❌ Kā inženieris domā

✅ Kā jāsaka investoram

Problēma

CNS nogurums un iesprūšana Beta viļņos samazina kognitīvo/fizisko veiktspēju.

Tava "cilvēka baterija" ir uz 15%. Miega laika nav.

Risinājums

Hibrīda ML modelis analizē EKG datus un ģenerē binaurālus stimulus parasimpātiskajam tonusam.

"Ātrais lādētājs" nervu sistēmai. Klausās sirdspukstos un piemeklē skaņas, kas piespiež atslābt.

Ieguvums

Statistiski nozīmīgs HF-HRV/RMSSD pieaugums.

Negodīga priekšrocība atlētam. "Sarkanā" diena kļūst "zaļa" 20 minūtēs.

5. NĀKAMIE SOĻI (NEXT STEPS)

Klīnika: Saziņa ar prof. Aināru Stepenu (RSU/RAKUS).

Finansējums: LIAA inkubators un ALTUM inovāciju aizdevums (€250k).

Pētniecība: Testi ar WESAD / SWELL-KW datubāzēm. Laboratorijas validācija ar EEG aparātu.

Izstrāde: Koda refaktorēšana modulārā, objektorientētā Python arhitektūrā (OOP).