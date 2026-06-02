

Sākotnējais prototips (main.py) mēģināja izmantot ANT+ protokolu (openant bibliotēka).

Problēma: ANT+ pieprasa specifiskus USB uztvērējus (dongles) un kompleksu libusb draiveru konfigurāciju, kas radīja nestabilitāti un apgrūtināja sistēmas pārnesamību (portability).

Risinājums: Pilnīga pāreja uz BLE (Bluetooth Low Energy), izmantojot Python bleak asinhrono bibliotēku. BLE ir natively atbalstīts visās modernajās operētājsistēmās un nodrošina stabilu reāllaika R-R intervālu plūsmu (ko nodrošina EKG jostas, piem., Polar H10 vai Hammerhead).

Kritisko 60 Pukstu "Epohas" Likums

Sākotnējā iterācijā Q-Learning aģents mainīja audio stimulus pie katrām mikroskopiskām stresa izmaiņām.

Atklājums: Pārāk bieža audio frekvenču maiņa izsauc Orienting Response (Orientēšanās/trauksmes refleksu), kas aktivizē simpātisko nervu sistēmu un pazemina HRV.

Arhitektūras likums: Lai smadzenes spētu sinhronizēties ar jauno ritmu (izveidotos FFR), aģents drīkst veikt izmaiņas tikai pēc 60 sirdspukstu (aptuveni 1 minūtes) epohas. (Piezīme: hackathon_mvp.py demo nolūkos tas īslaicīgi tika samazināts uz 10).

Reāllaika Audio un Fāžu Aprēķini

Lai nodrošinātu efektīvu Binaural Beats un Isochronic Tones iedarbību, skaņai jābūt perfektai, bez kompresijas (MP3 ir aizliegts).

Audio Ģenerēšana: Skaņa tiek ģenerēta reāllaikā ar numpy.sin un sounddevice.

Kropļojumu (Stutter) novēršana: Python GIL (Global Interpreter Lock) var aizkavēt audio ģenerēšanu, kamēr Bluetooth gaida datus vai AI veic aprēķinus. Tāpēc audio dzinējs ir izolēts atsevišķā sistēmas procesā, izmantojot multiprocessing.

Fāžu fiksēšana: Brīdī, kad AI aģents nomaina frekvenci (piem., no 10Hz uz 6Hz), audio vilnis nedrīkst pārtrūkt vai "noklikšķēt". Algoritms nepārtraukti uztur un turpina matemātisko signāla fāzi (phase_l, phase_r, utt.), nodrošinot pilnīgi gludu akustisko pāreju.

4. Datu Filtrēšana (Higiēna)

Kustību artefakti (piemēram, dziļa elpošana vai fiziska kustība) var īslaicīgi atraut sensora kontaktu. Tas rada nereālus R-R lēcienus (piemēram, 1000ms intervāls 500ms vietā), ko matemātika kļūdaini uzskatītu par izcilu HRV.

Filtrs: Visi R-R lēcieni un RMSSD vērtības > 150ms tiek programmatūriski ignorētas kā fiziski artefakti.