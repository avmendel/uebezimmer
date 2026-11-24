"""Hörgang: Audio-Lektionen für Gehörtraining unterwegs.
Erzeugt MP3-Lektionen (Musik synthetisch, Ansagen per Piper, englisch)."""
import numpy as np, wave, io, os, random, json, subprocess, sys
from piper import PiperVoice

SR = 22050
VOICE = PiperVoice.load(os.path.join(os.path.dirname(__file__), "voices/voice-en-us-lessac-medium/en-us-lessac-medium.onnx"))
CACHE = {}
BPM = 100
TARGET = float(os.environ.get("HG_MIN", "12")) * 60
BEAT = 60 / BPM

def speak(text):
    if text not in CACHE:
        buf = io.BytesIO()
        with wave.open(buf, "wb") as w:
            VOICE.synthesize_wav(text, w)
        buf.seek(0)
        with wave.open(buf) as r:
            sr = r.getframerate(); a = np.frombuffer(r.readframes(r.getnframes()), dtype=np.int16).astype(np.float32) / 32768
        if sr != SR:
            a = np.interp(np.arange(0, len(a), sr / SR), np.arange(len(a)), a)
        CACHE[text] = a * 0.9
    return CACHE[text]

def f(m): return 440 * 2 ** ((m - 69) / 12)

def tone(m, dur, vel=0.6):
    n = int(SR * (dur + 0.35)); t = np.arange(n) / SR; out = np.zeros(n, np.float32)
    fr = f(m)
    for k in range(1, 9):
        fk = fr * k * (1 + 0.0004 * k * k)
        if fk > SR / 2.2: break
        out += (1 / k ** 1.3) * np.sin(2 * np.pi * fk * t) * np.exp(-t * (1.2 + 0.9 * k) * (1 + (m - 60) / 60))
    env = np.minimum(1, t / 0.005)
    rel = np.ones(n); r0 = int(SR * dur); rel[r0:] = np.exp(-(t[r0:] - dur) / 0.08)
    return (out * env * rel * vel * 0.35).astype(np.float32)

def mix(parts):
    """parts: list of (start_seconds, array)"""
    end = max(s + len(a) / SR for s, a in parts) if parts else 0
    out = np.zeros(int(end * SR) + 1, np.float32)
    for s, a in parts:
        i = int(s * SR); out[i:i + len(a)] += a
    return out

def chord(notes, dur, vel=0.45): return mix([(0, tone(n, dur, vel)) for n in notes])
def sil(s): return np.zeros(int(SR * s), np.float32)

class Track:
    def __init__(self): self.parts = []; self.t = 0.0
    def add(self, a, gap=0.0):
        self.parts.append((self.t, a)); self.t += len(a) / SR + gap
    def say(self, text, gap=0.35): self.add(speak(text), gap)
    def pause(self, s): self.t += s
    def render(self): return mix(self.parts)

# ---------- Musik ----------
MAJ = [0, 2, 4, 5, 7, 9, 11]
SYL = {0: "do", 1: "di", 2: "re", 3: "me", 4: "mi", 5: "fa", 6: "fi", 7: "so", 8: "le", 9: "la", 10: "te", 11: "ti"}
KEYS = {"C": 60, "D flat": 61, "D": 62, "E flat": 63, "E": 64, "F": 65, "G flat": 66, "G": 67, "A flat": 68, "A": 57, "B flat": 58, "B": 59}

def triad(root, q="maj"):
    return [root, root + (4 if q == "maj" else 3), root + 7]

def cadence(tonic):
    """I – IV – V7 – I, enge Lage um die Tonika, Bass darunter"""
    b = tonic - 12
    seq = [([b, tonic + 4, tonic + 7, tonic + 12]), ([b + 5, tonic + 5, tonic + 9, tonic + 12]),
           ([b + 7 - 12, tonic + 5, tonic + 7, tonic + 11]), ([b, tonic + 4, tonic + 7, tonic + 12])]
    return mix([(i * 2 * BEAT * 0.8, chord(c, 2 * BEAT * 0.8 - 0.05)) for i, c in enumerate(seq)])

def key_name(rng):
    k = rng.choice(list(KEYS)); return k, KEYS[k]

# ---------- Übungsarten ----------
def ex_degrees(T, rng, lvl, n=10):
    pools = {1: [0, 4, 7], 2: [0, 2, 4, 5, 7], 3: MAJ, 4: MAJ, 5: MAJ + [6, 10], 6: MAJ + [6, 10, 3, 8, 1]}
    pool = pools[min(lvl, 6)]; wait = max(2.0, 3.5 - 0.3 * lvl)
    k, tonic = key_name(rng)
    T.say("Scale degrees. Key of %s." % k); T.add(cadence(tonic), 0.8)
    for i in range(n):
        d = rng.choice(pool); octv = rng.choice([0, 0, -12, 12]) if lvl >= 4 else 0
        m = tonic + d + octv
        if m > 81: m -= 12
        T.add(tone(m, 1.0), wait); T.say(SYL[d], 0.9)
        if i % 4 == 3 and i < n - 1: T.add(chord([tonic - 12, tonic + 4, tonic + 7], 1.2, 0.35), 0.8)

def ex_hold(T, rng, lvl, n=4):
    k, tonic = key_name(rng)
    T.say("Hold do. Key of %s. After the distraction, sing do." % k); T.add(cadence(tonic), 0.8)
    for i in range(n):
        ln = 3 + lvl + rng.randint(0, 2)
        pool = MAJ if lvl < 4 else MAJ + [1, 3, 6, 8, 10]
        mel = [tonic + rng.choice(pool) + rng.choice([0, 0, -12, 12]) for _ in range(ln)]
        mel = [m if m < 80 else m - 12 for m in mel]
        T.add(mix([(j * BEAT * 0.75, tone(m, BEAT * 0.7)) for j, m in enumerate(mel)]), 0.6)
        T.say("Sing do.", max(2.0, 3.5 - 0.3 * lvl)); T.add(tone(tonic, 1.3), 1.2)

def ex_melody(T, rng, lvl, n=6):
    k, tonic = key_name(rng)
    T.say("Melodies. Key of %s. Say the syllables." % k); T.add(cadence(tonic), 0.8)
    for i in range(n):
        ln = min(3 + (lvl + 1) // 2, 7); cur = rng.choice([0, 2, 4, 7])
        ds = [cur]; idx = MAJ.index(cur)
        for _ in range(ln - 1):
            step = rng.choice([-1, 1, 1, -1] + ([-2, 2] if lvl >= 2 else []) + ([-3, 3, 4, -4] if lvl >= 4 else []))
            idx = max(-3, min(9, idx + step)); ds.append(MAJ[idx % 7] + 12 * (idx // 7))
        mel = [tonic + d for d in ds]
        rhythm = [1] * ln if lvl < 3 else [rng.choice([.5, 1, 1, 1.5]) for _ in range(ln)]
        def play():
            parts, t = [], 0
            for m, r in zip(mel, rhythm): parts.append((t, tone(m, r * BEAT * 0.9))); t += r * BEAT
            return mix(parts)
        T.add(play(), max(1.5, ln * 0.7)); T.say(", ".join(SYL[d % 12] for d in ds), 0.5); T.add(play(), 1.2)

ROMAN = {0: ("one", "maj"), 2: ("two", "min"), 4: ("three", "min"), 5: ("four", "maj"), 7: ("five", "maj"), 9: ("six", "min")}
def ex_bass(T, rng, lvl, n=5):
    pools = {1: [0, 5, 7], 2: [0, 5, 7, 9], 3: [0, 2, 5, 7, 9], 4: [0, 2, 4, 5, 7, 9]}
    pool = pools[min(lvl, 4)]
    k, tonic = key_name(rng)
    T.say("Bass line. Key of %s. Name the chords." % k); T.add(cadence(tonic), 0.8)
    for i in range(n):
        prog = [0] + [rng.choice(pool) for _ in range(2 if lvl < 3 else 3)]
        if lvl >= 2: prog[-1] = rng.choice([7, 0, 5])
        parts = []
        for j, d in enumerate(prog):
            nm, q = ROMAN[d]; r = tonic + d - 24 if tonic + d - 24 >= 36 else tonic + d - 12
            up = [x if x >= tonic - 2 else x + 12 for x in triad(tonic + d, q)]
            parts.append((j * 2 * BEAT, chord([r] + up, 2 * BEAT - 0.08)))
        T.add(mix(parts), max(2.0, 1.0 * len(prog)))
        T.say(", ".join(ROMAN[d][0] for d in prog), 0.9)

AL = [("C minor seven", 48, [3, 10]), ("F seven", 41, [4, 10]), ("B flat major seven", 46, [4, 11]), ("E flat major seven", 51, [4, 11]),
      ("A half diminished", 45, [3, 10]), ("D seven", 50, [4, 10]), ("G minor six", 43, [3, 9]), ("G minor six", 43, [3, 9])]
def al_chord(i, dur):
    nm, r, iv = AL[i]; top = [r + 12 + x for x in iv]
    return chord([r] + [x if x > r + 12 else x + 12 for x in top] + [r + 19], dur)

def ex_autumn(T, rng, lvl):
    bar = 4 * BEAT
    if lvl == 1:
        T.say("Autumn Leaves, A section. Listen and follow the chords.")
        for i in range(8):
            T.add(speak(AL[i][0]), 0.1); T.add(al_chord(i, bar - 0.1), 0.2)
        T.say("Once more, without names.", 0.5)
        T.add(mix([(i * bar, al_chord(i, bar - 0.1)) for i in range(8)]), 1.0)
    else:
        T.say("Autumn Leaves, A section. Say the next chord before you hear it.")
        T.add(al_chord(0, bar - 0.1), 0.3); T.say(AL[0][0], 0.4)
        for i in range(1, 8):
            if AL[i][0] == AL[i - 1][0]: continue
            T.pause(max(1.5, 3.2 - 0.4 * lvl)); T.say(AL[i][0], 0.2); T.add(al_chord(i, bar - 0.1), 0.3)
        if lvl >= 3:
            T.say("Now the whole A section. Sing the top note of each chord.", 0.5)
            T.add(mix([(i * bar, al_chord(i, bar - 0.1)) for i in range(8)]), 1.0)

# ---------- Lektionsplan ----------
def plan(n):
    """Lektion n (1-basiert): Liste (Übung, Stufe). Start passend zum Stand vom 22.11. (do finden Stufe 5, Melodien Stufe 4),
    alle 3–4 Lektionen eine Stufe höher; Autumn Leaves jede zweite Lektion."""
    L = lambda start, step: max(1, min(6, start + (n - 1) // step))
    items = [("hold", L(2, 4)), ("degrees", L(3, 3)), ("melody", L(2, 4)), ("bass", L(1, 4))]
    if n % 2 == 0: items.append(("autumn", min(4, 1 + (n - 2) // 4)))
    rng = random.Random(n)
    if len(items) > 4: items.pop(rng.randrange(0, 4))
    rng.shuffle(items)
    return items

def lesson(n, out_dir):
    rng = random.Random(1000 + n); T = Track()
    T.say("Ear walk, lesson %d." % n, 0.8)
    P = plan(n); r = 0
    while T.t < TARGET - 60:
        for ex, lvl in P:
            if T.t >= TARGET - 60: break
            if ex == "autumn" and r > 0: continue
            if ex == "degrees": ex_degrees(T, rng, lvl)
            elif ex == "hold": ex_hold(T, rng, lvl)
            elif ex == "melody": ex_melody(T, rng, lvl)
            elif ex == "bass": ex_bass(T, rng, lvl)
            elif ex == "autumn": ex_autumn(T, rng, lvl)
            T.pause(1.5)
        r += 1
    T.say("End of lesson %d. Well done." % n, 1.0)
    a = T.render(); a = a / max(1e-6, np.abs(a).max()) * 0.89
    wav = os.path.join(out_dir, "tmp.wav")
    with wave.open(wav, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR); w.writeframes((a * 32767).astype(np.int16).tobytes())
    mp3 = os.path.join(out_dir, "hoergang-%02d.mp3" % n)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", wav, "-ac", "1", "-b:a", "48k", "-id3v2_version", "3",
                    "-metadata", "title=Hörgang %d" % n, "-metadata", "album=Hörgang", "-metadata", "artist=Übezimmer", "-metadata", "track=%d" % n, mp3], check=True)
    os.remove(wav)
    return mp3, len(a) / SR, plan(n)

if __name__ == "__main__":
    out = sys.argv[1]; a, b = int(sys.argv[2]), int(sys.argv[3]); os.makedirs(out, exist_ok=True)
    meta = {}
    for n in range(a, b + 1):
        p, d, pl = lesson(n, out); meta[n] = {"file": os.path.basename(p), "sec": round(d), "plan": pl}
        print(n, round(d / 60, 1), "min", pl, flush=True)
    json.dump(meta, open(os.path.join(out, "meta-%d-%d.json" % (a, b)), "w"))
