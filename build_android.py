"""Rulat in CI dupa `npx cap add android`: adauga permisiunile, sunetul de alarma si iconita de notificare.
Cu --extras adauga si: widget, scurtatura, deep link si pluginul OfflineSpeech (descarcare romana offline)."""
import math, pathlib, re, struct, sys, wave

main = pathlib.Path("android/app/src/main")
manifest = main / "AndroidManifest.xml"
if not manifest.exists():
    sys.exit("Nu gasesc " + str(manifest))

s = manifest.read_text(encoding="utf8")

perms = [
    '<uses-permission android:name="android.permission.RECORD_AUDIO" />',
    # dictarea fara internet: pluginul de voce verifica daca exista internet (vezi patch-ul de mai jos)
    '<uses-permission android:name="android.permission.ACCESS_NETWORK_STATE" />',
    '<uses-permission android:name="android.permission.POST_NOTIFICATIONS" />',
    '<uses-permission android:name="android.permission.USE_EXACT_ALARM" />',
    '<uses-permission android:name="android.permission.SCHEDULE_EXACT_ALARM" android:maxSdkVersion="32" />',
    '<uses-permission android:name="android.permission.VIBRATE" />',
    '<uses-permission android:name="android.permission.WAKE_LOCK" />',
    '<uses-permission android:name="android.permission.RECEIVE_BOOT_COMPLETED" />',
    # Google Calendar prin calendarul telefonului (pluginul @ebarooni/capacitor-calendar)
    '<uses-permission android:name="android.permission.READ_CALENDAR" />',
    '<uses-permission android:name="android.permission.WRITE_CALENDAR" />',
    # agenda telefonului pentru comenzile WhatsApp (pluginul @capacitor-community/contacts cere ambele; Planner doar citeste)
    '<uses-permission android:name="android.permission.READ_CONTACTS" />',
    '<uses-permission android:name="android.permission.WRITE_CONTACTS" />',
    # copia automata in Documents/Secretara pe Android 10 si mai vechi (pe 11+ nu e nevoie)
    '<uses-permission android:name="android.permission.WRITE_EXTERNAL_STORAGE" android:maxSdkVersion="29" />',
]
queries = ('<queries><intent><action android:name="android.speech.RecognitionService" /></intent></queries>')

block = ""
for p in perms:
    name = p.split('android:name="')[1].split('"')[0]
    if name not in s:
        block += "    " + p + "\n"
if "android.speech.RecognitionService" not in s:
    block += "    " + queries + "\n"
# vocea telefonului (pluginul text-to-speech): pe Android 11+ aplicatia trebuie sa poata vedea motorul TTS
if "android.intent.action.TTS_SERVICE" not in s:
    block += '    <queries><intent><action android:name="android.intent.action.TTS_SERVICE" /></intent></queries>\n'

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

# ---------- semnatura FIXA: APK-ul se semneaza mereu cu debug.keystore din repo ----------
# Fara asta, Gradle poate folosi o cheie temporara (alta la fiecare build) si telefonul refuza update-ul
# („App not installed”). Daca debug.keystore lipseste, oprim build-ul.
ks = pathlib.Path("debug.keystore")
if not ks.exists():
    sys.exit("EROARE: debug.keystore lipseste din radacina repo-ului. Fara el APK-ul nu se poate instala peste cel existent.")
gradle = pathlib.Path("android/app/build.gradle")
if not gradle.exists():
    sys.exit("Nu gasesc " + str(gradle))
g = gradle.read_text(encoding="utf8")
if "secretara-semnatura" not in g:
    sign = (
        "android {\n"
        "    // secretara-semnatura: aceeasi cheie la fiecare build = update fara pierderea datelor\n"
        "    signingConfigs {\n"
        "        debug {\n"
        "            storeFile rootProject.file('../debug.keystore')\n"
        "            storePassword 'android'\n"
        "            keyAlias 'androiddebugkey'\n"
        "            keyPassword 'android'\n"
        "        }\n"
        "    }\n"
    )
    if not re.search(r"^android\s*\{", g, re.M):
        sys.exit("build.gradle fara blocul android {")
    g = re.sub(r"^android\s*\{\n?", sign, g, count=1, flags=re.M)
    gradle.write_text(g, encoding="utf8")
print("build_android.py: semnatura fixa din debug.keystore")

# ---------- sunete (aceleasi formule ca sndSample() din index.html, pentru previzualizare) ----------
# al_<sunet>_<5|15|30>.wav pentru alarme, mem_<sunet>.wav pentru memento-uri, alarm.wav = vechiul canal (compatibilitate)
TAU = 2 * math.pi
S = math.sin

def seg(x):
    return min(1.0, x * 12, (1 - x) * 12)

def sample(kind, t):
    if kind == "clasic":
        ph = t % 1.0
        if ph < 0.15: f, a0, a1 = 880, 0.0, 0.15
        elif 0.25 <= ph < 0.40: f, a0, a1 = 1175, 0.25, 0.40
        elif 0.50 <= ph < 0.65: f, a0, a1 = 880, 0.50, 0.65
        else: return 0.0
        return 0.7 * seg((ph - a0) / (a1 - a0)) * S(TAU * f * t)
    if kind == "digital":
        ph = t % 1.0
        for k in range(4):
            s = k * 0.12
            if s <= ph < s + 0.07:
                x = (ph - s) / 0.07
                return 0.6 * min(1.0, x * 10, (1 - x) * 10) * S(TAU * 1500 * t)
        return 0.0
    if kind == "clopotel":
        ph = t % 1.6
        v = 0.0
        for s, f in ((0, 880), (0.45, 660)):
            if ph >= s:
                d = ph - s
                v += min(1.0, d * 200) * math.exp(-d * 4) * (S(TAU * f * t) + 0.35 * S(TAU * 2 * f * t))
        return 0.45 * v
    if kind == "sirena":
        return 0.55 * S(TAU * (975 * t - (325 / TAU) * S(TAU * t)))
    if kind == "bland":
        ph = t % 2.0
        v = 0.0
        for s, f in ((0, 523), (0.5, 659), (1.0, 784)):
            if s <= ph < s + 0.5:
                v = S(math.pi * (ph - s) / 0.5) * S(TAU * f * t)
        return min(0.8, 0.25 + 0.055 * t) * v
    if kind == "ding":
        v = 0.0
        for s, f in ((0, 988), (0.15, 1319)):
            if t >= s:
                d = t - s
                v += min(1.0, d * 200) * math.exp(-d * 6) * (S(TAU * f * t) + 0.3 * S(TAU * 2 * f * t))
        return 0.4 * v
    if kind == "bip":
        for s in (0, 0.18):
            if s <= t < s + 0.1:
                x = (t - s) / 0.1
                return 0.6 * min(1.0, x * 10, (1 - x) * 10) * S(TAU * 1000 * t)
        return 0.0
    return 0.0

def write_wav(path, sr, vals):
    n = len(vals)
    fade = int(sr * 0.05)
    frames = bytearray()
    for i, v in enumerate(vals):
        if i > n - fade:
            v *= (n - i) / fade
        v = max(-1.0, min(1.0, v))
        frames += struct.pack("<h", int(v * 32767))
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr); w.writeframes(bytes(frames))

raw = main / "res" / "raw"
raw.mkdir(parents=True, exist_ok=True)
# 8 kHz: fisiere mici; toate frecventele folosite sunt sub 4 kHz, deci sunetul ramane curat
SR = 8000
for kind in ("clasic", "digital", "clopotel", "sirena", "bland"):
    full = [sample(kind, i / SR) for i in range(SR * 30)]
    for secs in (5, 15, 30):
        write_wav(raw / f"al_{kind}_{secs}.wav", SR, full[: SR * secs])
write_wav(raw / "mem_ding.wav", SR, [sample("ding", i / SR) for i in range(int(SR * 1.2))])
write_wav(raw / "mem_bip.wav", SR, [sample("bip", i / SR) for i in range(int(SR * 0.5))])
# vechiul canal „alarms_v1” foloseste alarm.wav: il pastram pentru alarmele programate cu versiunea veche
write_wav(raw / "alarm.wav", 11025, [sample("clasic", i / 11025) for i in range(11025 * 15)])

# iconita mica de notificare (clopotel alb)
dr = main / "res" / "drawable"
dr.mkdir(parents=True, exist_ok=True)
(dr / "ic_stat_icon.xml").write_text('''<vector xmlns:android="http://schemas.android.com/apk/res/android"
    android:width="24dp" android:height="24dp" android:viewportWidth="24" android:viewportHeight="24">
  <path android:fillColor="#FFFFFFFF"
      android:pathData="M12,22c1.1,0 2,-0.9 2,-2h-4c0,1.1 0.89,2 2,2zM18,16v-5c0,-3.07 -1.64,-5.64 -4.5,-6.32V4c0,-0.83 -0.67,-1.5 -1.5,-1.5s-1.5,0.67 -1.5,1.5v0.68C7.63,5.36 6,7.92 6,11v5l-2,2v1h16v-1l-2,-2z"/>
</vector>
''', encoding="utf8")
print("build_android.py: manifest, sunete (5 alarme x 3 durate + 2 memento) si icon adaugate")

# ---------- pluginul de voce (@capacitor-community/speech-recognition 7.0.1): 2 imbunatatiri ----------
# 1) fara internet cere recunoasterea pe telefon (EXTRA_PREFER_OFFLINE) -> merge cu pachetul de romana offline
# 2) erorile recunoasterii (fara internet, fara limba offline, ocupat etc.) ajung in aplicatie ca listeningState "error"
#    (pluginul original le pierdea dupa pornire, iar aplicatia afisa "Ascult..." fara sa auda nimic)
srj = list(pathlib.Path("node_modules/@capacitor-community/speech-recognition/android").glob("**/SpeechRecognition.java"))
if not srj:
    print("::warning::Nu gasesc SpeechRecognition.java - dictarea fara internet NU e activata")
else:
    j = srj[0].read_text(encoding="utf8")
    if "secretara-offline" not in j:
        a1 = 'intent.putExtra("android.speech.extra.DICTATION_MODE", partialResults);'
        p1 = a1 + '''
        // secretara-offline: fara internet cerem recunoasterea pe telefon (pachetul de limba descarcat)
        try {
            android.net.ConnectivityManager cm = (android.net.ConnectivityManager) bridge.getContext().getSystemService(android.content.Context.CONNECTIVITY_SERVICE);
            android.net.NetworkCapabilities nc = cm != null ? cm.getNetworkCapabilities(cm.getActiveNetwork()) : null;
            boolean online = nc != null && nc.hasCapability(android.net.NetworkCapabilities.NET_CAPABILITY_INTERNET)
                && nc.hasCapability(android.net.NetworkCapabilities.NET_CAPABILITY_VALIDATED);
            if (!online) intent.putExtra(RecognizerIntent.EXTRA_PREFER_OFFLINE, true);
        } catch (Exception ignored) {}'''
        a2 = "String errorMssg = getErrorText(error);"
        p2 = a2 + '''
            // secretara-offline: trimitem eroarea si catre aplicatie
            try {
                JSObject ev = new JSObject();
                ev.put("status", "error");
                ev.put("code", error);
                ev.put("message", errorMssg);
                SpeechRecognition.this.notifyListeners(LISTENING_EVENT, ev);
            } catch (Exception ignored) {}'''
        ok1, ok2 = a1 in j, a2 in j
        j = j.replace(a1, p1, 1).replace(a2, p2, 1)
        srj[0].write_text(j, encoding="utf8")
        print("build_android.py: plugin voce - offline " + ("OK" if ok1 else "NEGASIT") + ", erori " + ("OK" if ok2 else "NEGASIT"))
        if not (ok1 and ok2):
            print("::warning::Patch-ul pluginului de voce nu s-a aplicat complet (alta versiune a pluginului?)")

if not EXTRAS:
    sys.exit(0)

acts = list(main.glob("java/**/MainActivity.java"))
if not acts:
    sys.exit("Nu gasesc MainActivity.java")
pkg = re.search(r"package\s+([\w.]+);", acts[0].read_text(encoding="utf8")).group(1)
src = acts[0].parent

# ---------- widget ----------
(src / "DictateWidget.java").write_text("""package __PKG__;

import android.app.PendingIntent;
import android.appwidget.AppWidgetManager;
import android.appwidget.AppWidgetProvider;
import android.content.Context;
import android.content.Intent;
import android.net.Uri;
import android.widget.RemoteViews;

public class DictateWidget extends AppWidgetProvider {
    @Override
    public void onUpdate(Context ctx, AppWidgetManager mgr, int[] ids) {
        for (int id : ids) {
            Intent i = new Intent(Intent.ACTION_VIEW, Uri.parse("secretara://dictate"));
            i.setPackage(ctx.getPackageName());
            i.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK | Intent.FLAG_ACTIVITY_SINGLE_TOP);
            PendingIntent pi = PendingIntent.getActivity(ctx, 0, i, PendingIntent.FLAG_UPDATE_CURRENT | PendingIntent.FLAG_IMMUTABLE);
            RemoteViews v = new RemoteViews(ctx.getPackageName(), R.layout.widget_dictate);
            v.setOnClickPendingIntent(R.id.widget_root, pi);
            mgr.updateAppWidget(id, v);
        }
    }
}
""".replace("__PKG__", pkg), encoding="utf8")

# ---------- plugin OfflineSpeech: verifica / descarca pachetul offline de romana (Android 13+) ----------
(src / "OfflineSpeechPlugin.java").write_text("""package __PKG__;

import android.annotation.TargetApi;
import android.content.ComponentName;
import android.content.Intent;
import android.os.Build;
import android.os.Handler;
import android.os.Looper;
import android.speech.ModelDownloadListener;
import android.speech.RecognitionSupport;
import android.speech.RecognitionSupportCallback;
import android.speech.RecognizerIntent;
import android.speech.SpeechRecognizer;
import com.getcapacitor.JSObject;
import com.getcapacitor.Plugin;
import com.getcapacitor.PluginCall;
import com.getcapacitor.PluginMethod;
import com.getcapacitor.annotation.CapacitorPlugin;
import java.util.List;

@CapacitorPlugin(name = "OfflineSpeech")
public class OfflineSpeechPlugin extends Plugin {

    private static boolean has(List<String> langs, String lang) {
        if (langs == null) return false;
        String full = lang.toLowerCase();
        String base = full.split("-")[0];
        for (String l : langs) {
            if (l == null) continue;
            String x = l.toLowerCase().replace('_', '-');
            if (x.equals(full) || x.equals(base) || x.startsWith(base + "-")) return true;
        }
        return false;
    }

    private static String msg(Exception e) {
        return e.getMessage() != null ? e.getMessage() : e.toString();
    }

    private Intent recIntent(String lang) {
        Intent i = new Intent(RecognizerIntent.ACTION_RECOGNIZE_SPEECH);
        i.putExtra(RecognizerIntent.EXTRA_LANGUAGE_MODEL, RecognizerIntent.LANGUAGE_MODEL_FREE_FORM);
        i.putExtra(RecognizerIntent.EXTRA_LANGUAGE, lang);
        return i;
    }

    private void emitProgress(int percent) {
        JSObject o = new JSObject();
        o.put("progress", percent);
        notifyListeners("downloadProgress", o);
    }

    @PluginMethod
    public void status(final PluginCall call) {
        final String lang = call.getString("language", "ro-RO");
        final JSObject r = new JSObject();
        r.put("sdk", Build.VERSION.SDK_INT);
        if (Build.VERSION.SDK_INT < 33) {
            r.put("supported", false);
            call.resolve(r);
            return;
        }
        new Handler(Looper.getMainLooper()).post(() -> status33(call, lang, r));
    }

    @TargetApi(33)
    private void status33(final PluginCall call, final String lang, final JSObject r) {
        try {
            if (!SpeechRecognizer.isOnDeviceRecognitionAvailable(getContext())) {
                r.put("supported", false);
                call.resolve(r);
                return;
            }
            final SpeechRecognizer sr = SpeechRecognizer.createOnDeviceSpeechRecognizer(getContext());
            sr.checkRecognitionSupport(recIntent(lang), getContext().getMainExecutor(), new RecognitionSupportCallback() {
                @Override
                public void onSupportResult(RecognitionSupport s) {
                    r.put("supported", true);
                    r.put("installed", has(s.getInstalledOnDeviceLanguages(), lang));
                    r.put("pending", has(s.getPendingOnDeviceLanguages(), lang));
                    r.put("available", has(s.getSupportedOnDeviceLanguages(), lang));
                    List<String> sup = s.getSupportedOnDeviceLanguages();
                    if (sup != null) r.put("langs", String.join(", ", sup));
                    sr.destroy();
                    call.resolve(r);
                }

                @Override
                public void onError(int error) {
                    r.put("supported", true);
                    r.put("error", error);
                    sr.destroy();
                    call.resolve(r);
                }
            });
        } catch (Exception e) {
            call.reject(msg(e));
        }
    }

    // deschide descarcarea limbilor offline din aplicatia Google (sau setarile de intrare vocala)
    @PluginMethod
    public void openSettings(final PluginCall call) {
        Intent[] list = {
            new Intent().setComponent(new ComponentName("com.google.android.googlequicksearchbox",
                "com.google.android.voicesearch.greco3.languagepack.InstallActivity")),
            new Intent("android.settings.VOICE_INPUT_SETTINGS"),
            new Intent(android.provider.Settings.ACTION_SETTINGS)
        };
        String[] names = {"google", "voice_input", "settings"};
        for (int k = 0; k < list.length; k++) {
            try {
                Intent i = list[k];
                i.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
                getContext().startActivity(i);
                JSObject o = new JSObject();
                o.put("opened", names[k]);
                call.resolve(o);
                return;
            } catch (Exception e) {
                // incercam urmatoarea varianta
            }
        }
        call.reject("Nu am putut deschide setarile");
    }

    @PluginMethod
    public void download(final PluginCall call) {
        final String lang = call.getString("language", "ro-RO");
        if (Build.VERSION.SDK_INT < 33) {
            call.reject("Necesita Android 13 sau mai nou");
            return;
        }
        new Handler(Looper.getMainLooper()).post(() -> download33(call, lang));
    }

    @TargetApi(33)
    private void download33(final PluginCall call, final String lang) {
        try {
            if (!SpeechRecognizer.isOnDeviceRecognitionAvailable(getContext())) {
                call.reject("Telefonul nu are recunoastere vocala pe dispozitiv");
                return;
            }
            final SpeechRecognizer sr = SpeechRecognizer.createOnDeviceSpeechRecognizer(getContext());
            if (Build.VERSION.SDK_INT >= 34) {
                download34(call, lang, sr);
                return;
            }
            sr.triggerModelDownload(recIntent(lang));
            new Handler(Looper.getMainLooper()).postDelayed(sr::destroy, 15000);
            JSObject o = new JSObject();
            o.put("result", "started");
            call.resolve(o);
        } catch (Exception e) {
            call.reject(msg(e));
        }
    }

    @TargetApi(34)
    private void download34(final PluginCall call, final String lang, final SpeechRecognizer sr) {
        final boolean[] done = {false};
        sr.triggerModelDownload(recIntent(lang), getContext().getMainExecutor(), new ModelDownloadListener() {
            @Override
            public void onProgress(int completedPercent) {
                emitProgress(completedPercent);
            }

            @Override
            public void onSuccess() {
                finish("installed");
            }

            @Override
            public void onScheduled() {
                finish("scheduled");
            }

            @Override
            public void onError(int error) {
                finish("error:" + error);
            }

            private void finish(String res) {
                if (done[0]) return;
                done[0] = true;
                JSObject o = new JSObject();
                o.put("result", res);
                call.resolve(o);
                sr.destroy();
            }
        });
    }
}
""".replace("__PKG__", pkg), encoding="utf8")

# ---------- MainActivity: inregistreaza pluginul propriu ----------
acts[0].write_text("""package __PKG__;

import android.os.Bundle;
import com.getcapacitor.BridgeActivity;

public class MainActivity extends BridgeActivity {
    @Override
    public void onCreate(Bundle savedInstanceState) {
        registerPlugin(OfflineSpeechPlugin.class);
        super.onCreate(savedInstanceState);
    }
}
""".replace("__PKG__", pkg), encoding="utf8")

# ---------- resurse widget + scurtatura ----------
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
(main / "res/xml/shortcuts.xml").write_text('''<?xml version="1.0" encoding="utf-8"?>
<shortcuts xmlns:android="http://schemas.android.com/apk/res/android">
    <shortcut android:shortcutId="dictate" android:enabled="true" android:icon="@mipmap/ic_launcher"
        android:shortcutShortLabel="@string/sc_dictate" android:shortcutLongLabel="@string/sc_dictate_long">
        <intent android:action="android.intent.action.VIEW" android:data="secretara://dictate"
            android:targetPackage="__PKG__" android:targetClass="__PKG__.MainActivity" />
    </shortcut>
</shortcuts>
'''.replace("__PKG__", pkg), encoding="utf8")
print("build_android.py: widget, scurtatura si plugin OfflineSpeech adaugate (" + pkg + ")")
