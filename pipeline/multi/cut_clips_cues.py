"""Original-audio clip per phrase from its source cue span (youtube-official shows with audio only).

Usage: python pipeline/multi/cut_clips_cues.py SHOW_ID WORKDIR [--only EP01] [--force]
Span = cue start - 0.25 s .. cue end + 0.4 s, capped at 7 s; mono 64 kbps mp3 at
gen/clips/<CODE>/<phraseId>.mp3. Sets phrase["clip"] = file name. Skips missing audio and existing clips.
"""
import argparse, json, os, subprocess, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import cfg, episodes, select, gen_dir, save, load

PRE, POST, CAP = 0.25, 0.4, 7.0

def cut(audio, start_ms, end_ms, out):
    s = max(0.0, start_ms / 1000 - PRE)
    dur = min(CAP, end_ms / 1000 + POST - s)
    tmp = out + ".part.mp3"
    subprocess.run(["ffmpeg", "-nostdin", "-loglevel", "error", "-y", "-ss", f"{s:.3f}", "-i", audio, "-t", f"{dur:.3f}",
                    "-vn", "-ac", "1", "-ar", "44100", "-b:a", "64k", tmp], check=True)
    os.replace(tmp, out)

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("show"); ap.add_argument("work")
    ap.add_argument("--only"); ap.add_argument("--force", action="store_true"); a = ap.parse_args()
    c = cfg(a.show)
    if c["source"] != "youtube-official": print(json.dumps({"note": "text-only show: no clips"})); return
    gen = gen_dir(a.work); made = kept = no_audio = 0
    for ep in select(episodes(a.show, a.work), a.only):
        ph_p = os.path.join(gen, ep["code"] + ".phrases.json"); phrases = load(ph_p)
        if not phrases: continue
        audio = os.path.join(a.work, "audio", ep["youtubeId"] + ".m4a")
        if not os.path.exists(audio): no_audio += 1; print("no audio yet", ep["code"], file=sys.stderr); continue
        d = os.path.join(gen, "clips", ep["code"]); os.makedirs(d, exist_ok=True)
        for p in phrases:
            name = p["id"] + ".mp3"; out = os.path.join(d, name)
            if os.path.exists(out) and not a.force: p["clip"] = name; kept += 1; continue
            try: cut(audio, p["start"], p["end"], out); p["clip"] = name; made += 1
            except subprocess.CalledProcessError as e: print("ffmpeg failed", ep["code"], p["id"], e.returncode, file=sys.stderr)
        save(ph_p, phrases)
    print(json.dumps({"made": made, "kept": kept, "episodesWithoutAudio": no_audio}))

if __name__ == "__main__": main()
