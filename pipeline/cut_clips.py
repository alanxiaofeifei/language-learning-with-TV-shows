"""Cut original-audio clips for phrase cards and keep only clips Whisper can hear.
Usage: python pipeline/cut_clips.py PHRASES.json LINES.json AUDIO OUTDIR [--threads 4]
Clip = whole subtitle line (pad 0.3s / 0.5s) when <= 6s, else the phrase's word span. Writes OUTDIR/<id>.mp3
and updates PHRASES.json in place with clip / clipScore / clipHeard (unverified clips are deleted)."""
import argparse, json, os, re, subprocess, sys, unicodedata
import numpy as np

PAD_BEFORE, PAD_AFTER, MAX_LEN = 300, 500, 6000

def norm_syllables(text):
    t = unicodedata.normalize("NFD", text.lower())
    t = "".join(c for c in t if unicodedata.category(c) != "Mn").replace("đ", "d")
    t = re.sub(r"[^a-z0-9 ]", " ", t)
    out = []
    for w in t.split():
        w = re.sub(r"^(gi|r|d)", "z", w); w = re.sub(r"^x", "s", w); w = re.sub(r"^tr", "ch", w)
        out.append(w)
    return out

def score(expected, heard):
    exp, got = norm_syllables(expected), norm_syllables(heard)
    if not exp: return 0.0
    pool = list(got); hit = 0
    for s in exp:
        if s in pool: pool.remove(s); hit += 1
    return hit / len(exp)

def decode(path, start_ms, end_ms):
    raw = subprocess.run(["ffmpeg", "-loglevel", "error", "-ss", f"{start_ms/1000:.3f}", "-to", f"{end_ms/1000:.3f}", "-i", path,
                          "-f", "s16le", "-ac", "1", "-ar", "16000", "-"], capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.int16).astype(np.float32) / 32768

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("phrases"); ap.add_argument("lines"); ap.add_argument("audio"); ap.add_argument("outdir")
    ap.add_argument("--threads", type=int, default=4); ap.add_argument("--min-score", type=float, default=0.6); a = ap.parse_args()
    from faster_whisper import WhisperModel
    model = WhisperModel("large-v3-turbo", device="cpu", compute_type="int8", cpu_threads=a.threads)
    phrases = json.load(open(a.phrases, encoding="utf-8")); lines = json.load(open(a.lines, encoding="utf-8"))
    os.makedirs(a.outdir, exist_ok=True); ok = 0
    for p in phrases:
        L = lines[p["line"]]
        s, e = L["startMs"] - PAD_BEFORE + 150, L["endMs"] + PAD_AFTER   # startMs already has 150ms lead
        if e - s > MAX_LEN:
            e = s + MAX_LEN
        segs, _ = model.transcribe(decode(a.audio, s, e), language="vi", beam_size=5, condition_on_previous_text=False, vad_filter=False)
        heard = " ".join(x.text.strip() for x in segs)
        sc = score(p["phrase"], heard)
        out = os.path.join(a.outdir, p["id"] + ".mp3")
        p.update(clipScore=round(sc, 2), clipHeard=heard[:200])
        if sc >= a.min_score:
            subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-ss", f"{s/1000:.3f}", "-to", f"{e/1000:.3f}", "-i", a.audio,
                            "-ac", "1", "-ar", "24000", "-b:a", "48k", "-af", "loudnorm=I=-18:TP=-2,afade=t=in:d=0.05", out], check=True)
            p.update(clip=os.path.basename(out), clipStartMs=s, clipEndMs=e); ok += 1
        else:
            p.pop("clip", None)
            if os.path.exists(out): os.remove(out)
    json.dump(phrases, open(a.phrases, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"{ok}/{len(phrases)} clips verified", file=sys.stderr)

if __name__ == "__main__": main()
