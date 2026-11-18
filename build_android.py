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

EXTRAS = "--extras" in sys.argv
if EXTRAS:
    # deep link secretara://dictate + scurtatura (apasare lunga pe icoana) in MainActivity
    if 'android:scheme="secretara"' not in s:
        filt = (
            '        <intent-filter>\n'
            '            <action android:name="android.intent.action.VIEW" />\n'
            '            <category android:name="android.intent.category.DEFAULT" />\n'
            '            <category android:name="android.intent.category.BROWSABLE" />\n'
            '            <data android:scheme="secretara" android:host="dictate" />\n'
            '        </intent-filter>\n'
            '        <meta-data android:name="android.app.shortcuts" android:resource="@xml/shortcuts" />\n'
        )
        if "</activity>" not in s:
            sys.exit("Manifest fara </activity>")
        s = s.replace("</activity>", filt + "        </activity>", 1)
    # receiver pentru widget
    if "DictateWidget" not in s:
        rec = (
            '        <receiver android:name=".DictateWidget" android:exported="true">\n'
            '            <intent-filter><action android:name="android.appwidget.action.APPWIDGET_UPDATE" /></intent-filter>\n'
            '            <meta-data android:name="android.appwidget.provider" android:resource="@xml/dictate_widget_info" />\n'
            '        </receiver>\n'
        )
        s = s.replace("</application>", rec + "    </application>", 1)
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

if EXTRAS:
    import re
    acts = list(main.glob("java/**/MainActivity.java"))
    if not acts:
        sys.exit("Nu gasesc MainActivity.java")
    pkg = re.search(r"package\s+([\w.]+);", acts[0].read_text(encoding="utf8")).group(1)
    (acts[0].parent / "DictateWidget.java").write_text(f"""package {pkg};

import android.app.PendingIntent;
import android.appwidget.AppWidgetManager;
import android.appwidget.AppWidgetProvider;
import android.content.Context;
import android.content.Intent;
import android.net.Uri;
import android.widget.RemoteViews;

public class DictateWidget extends AppWidgetProvider {{
    @Override
    public void onUpdate(Context ctx, AppWidgetManager mgr, int[] ids) {{
        for (int id : ids) {{
            Intent i = new Intent(Intent.ACTION_VIEW, Uri.parse("secretara://dictate"));
            i.setPackage(ctx.getPackageName());
            i.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK | Intent.FLAG_ACTIVITY_SINGLE_TOP);
            PendingIntent pi = PendingIntent.getActivity(ctx, 0, i, PendingIntent.FLAG_UPDATE_CURRENT | PendingIntent.FLAG_IMMUTABLE);
            RemoteViews v = new RemoteViews(ctx.getPackageName(), R.layout.widget_dictate);
            v.setOnClickPendingIntent(R.id.widget_root, pi);
            mgr.updateAppWidget(id, v);
        }}
    }}
}}
""", encoding="utf8")
    for d in ("xml", "layout", "values", "drawable"):
        (main / "res" / d).mkdir(parents=True, exist_ok=True)
    (main / "res/xml/dictate_widget_info.xml").write_text('''<?xml version="1.0" encoding="utf-8"?>
<appwidget-provider xmlns:android="http://schemas.android.com/apk/res/android"
    android:minWidth="110dp" android:minHeight="40dp" android:updatePeriodMillis="0"
    android:initialLayout="@layout/widget_dictate" android:resizeMode="horizontal|vertical"
    android:widgetCategory="home_screen" />
''', encoding="utf8")
    (main / "res/layout/widget_dictate.xml").write_text('''<?xml version="1.0" encoding="utf-8"?>
<LinearLayout xmlns:android="http://schemas.android.com/apk/res/android"
    android:id="@+id/widget_root" android:layout_width="match_parent" android:layout_height="match_parent"
    android:gravity="center" android:padding="8dp" android:background="@drawable/widget_bg">
    <TextView android:layout_width="wrap_content" android:layout_height="wrap_content"
        android:text="@string/sc_dictate_widget" android:textColor="#FFFFFF" android:textSize="18sp" android:textStyle="bold" />
</LinearLayout>
''', encoding="utf8")
    (main / "res/drawable/widget_bg.xml").write_text('''<?xml version="1.0" encoding="utf-8"?>
<shape xmlns:android="http://schemas.android.com/apk/res/android" android:shape="rectangle">
    <solid android:color="#4F8CFF" />
    <corners android:radius="18dp" />
</shape>
''', encoding="utf8")
    (main / "res/values/secretara_extras.xml").write_text('''<?xml version="1.0" encoding="utf-8"?>
<resources>
    <string name="sc_dictate">Dictează</string>
    <string name="sc_dictate_long">Dictează un memento</string>
    <string name="sc_dictate_widget">🎤  Dictează</string>
</resources>
''', encoding="utf8")
    (main / "res/xml/shortcuts.xml").write_text(f'''<?xml version="1.0" encoding="utf-8"?>
<shortcuts xmlns:android="http://schemas.android.com/apk/res/android">
    <shortcut android:shortcutId="dictate" android:enabled="true" android:icon="@mipmap/ic_launcher"
        android:shortcutShortLabel="@string/sc_dictate" android:shortcutLongLabel="@string/sc_dictate_long">
        <intent android:action="android.intent.action.VIEW" android:data="secretara://dictate"
            android:targetPackage="{pkg}" android:targetClass="{pkg}.MainActivity" />
    </shortcut>
</shortcuts>
''', encoding="utf8")
    print("build_android.py: widget + scurtatura adaugate (" + pkg + ")")
