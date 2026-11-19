# Secretara – jurnal de modificări

## v3.1 – 19.11.2026
- **Datele se păstrează la update**: copie automată la fiecare modificare (memoria aplicației + `Documents/Secretara/secretara-autobackup.json`), restaurată singură dacă WebView-ul pornește gol. `build.yml` eșuează dacă lipsește `debug.keystore` (altă semnătură = reinstalare = date pierdute).
- **Dictare reparată**: a doua oprire întârziată nu mai omoară o sesiune nouă; paznic care repornește microfonul blocat; rezultatul final nu se mai pierde / dublează; mesaj „🎙️ Ascult… vorbește” abia când microfonul e gata.
- **Sunete alarmă**: 5 variante (Clasic, Digital, Clopoțel, Sirenă, Blând) × 3 durate (5/15/30 s), cu previzualizare; memento: sunetul telefonului / Ding / Dublu bip. Schimbarea se aplică și pe alarmele deja programate.
- **Confirmare la salvare**: sunet scurt + vibrație (+ voce, opțional) și butoane rapide: +10 min, +1 oră, Mâine, alarmă ↔ memento, Anulează.
- **Ora implicită 10:00** când spui doar ziua („vineri alarmă …”), modificabilă din Setări; avertizare dacă ora ar fi deja trecută.
- **Istoric separat** pe Sarcini / Memento-uri / Alarme, grupat pe zile, cu căutare. Memento-urile bifate nu mai stau tăiate în listă. Alarmele care au sunat și n-au fost bifate trec în Istoric după 12 ore.
- **Calendar**: zilele cu activitate rămân colorate (verde = trecut, albastru = programat) cu ⏰/🔔/✔; ziua aleasă arată și istoricul.
- **Româna offline**: eroarea 12 = limba nu e oferită de modelul offline încorporat (nu e de la Wi-Fi). Mesaje clare pe coduri, reîncercare cu „ro”, buton nou „⚙️ Setări voce Google”.
