"""Rulat in CI dupa `npx cap add android`: adauga permisiunile, sunetul de alarma si iconita de notificare."""
import math, pathlib, struct, sys, wave

main = pathlib.Path("android/app/src/main")
manifest = main / "AndroidManifest.xml"
if not manifest.exists():
    sys.exit("Nu gasesc " + str(manifest))

s = manifest.read_text(encoding="utf8")

perms = [
    '<uses-permission android:name="android.permission.RECORD_AUDIO" />',
    '<uses-permission android:name="android.permission.POST_NOTIFICATIONS" />',
    '<uses-permission android:name="android.permission.USE_EXACT_ALARM" />',
    '<uses-permission android:name="android.permission.SCHEDULE_EXACT_ALARM" android:maxSdkVersion="32" />',
    '<uses-permission android:name="android.permission.VIBRATE" />',
    '<uses-permission android:name="android.permission.WAKE_LOCK" />',
    '<uses-permission android:name="android.permission.RECEIVE_BOOT_COMPLETED" />',
]
queries = ('<queries><intent><action android:name="android.speech.RecognitionService" /></intent></queries>')

block = ""
for p in perms:
    name = p.split('android:name="')[1].split('"')[0]
    if name not in s:
        block += "    " + p + "\n"
if "android.speech.RecognitionService" not in s:
    block += "    " + queries + "\n"

if "<application" not in s:
    sys.exit("Manifest fara <application>")
s = s.replace("<application", block + "    <application", 1)
manifest.write_text(s, encoding="utf8")

# sunet de alarma: 15 secunde, 3 bipuri pe secunda
raw = main / "res" / "raw"
raw.mkdir(parents=True, exist_ok=True)
sr, secs = 22050, 15
frames = bytearray()
for i in range(sr * secs):
    t = i / sr
    ph = t % 1.0
    if ph < 0.15:   f, a0, a1 = 880, 0.0, 0.15
    elif 0.25 <= ph < 0.40: f, a0, a1 = 1175, 0.25, 0.40
    elif 0.50 <= ph < 0.65: f, a0, a1 = 880, 0.50, 0.65
    else: f = 0; a0 = a1 = 0
    v = 0.0
    if f:
        x = (ph - a0) / (a1 - a0)
        env = min(1.0, x * 12, (1 - x) * 12)
        v = 0.7 * env * math.sin(2 * math.pi * f * t)
    frames += struct.pack("<h", int(v * 32767))
with wave.open(str(raw / "alarm.wav"), "wb") as w:
    w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr); w.writeframes(bytes(frames))

# iconita mica de notificare (clopotel alb)
dr = main / "res" / "drawable"
dr.mkdir(parents=True, exist_ok=True)
(dr / "ic_stat_icon.xml").write_text('''<vector xmlns:android="http://schemas.android.com/apk/res/android"
    android:width="24dp" android:height="24dp" android:viewportWidth="24" android:viewportHeight="24">
  <path android:fillColor="#FFFFFFFF"
      android:pathData="M12,22c1.1,0 2,-0.9 2,-2h-4c0,1.1 0.89,2 2,2zM18,16v-5c0,-3.07 -1.64,-5.64 -4.5,-6.32V4c0,-0.83 -0.67,-1.5 -1.5,-1.5s-1.5,0.67 -1.5,1.5v0.68C7.63,5.36 6,7.92 6,11v5l-2,2v1h16v-1l-2,-2z"/>
</vector>
''', encoding="utf8")
print("build_android.py: manifest, alarm.wav si icon adaugate")
