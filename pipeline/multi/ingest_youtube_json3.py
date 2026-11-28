"""Official YouTube subtitle tracks (json3) -> aligned lines per episode.

Usage: python pipeline/multi/ingest_youtube_json3.py SHOW_ID WORKDIR [--only EP01,EP02] [--force]
zh-Hans and vi share cue timing (joined by cue start); en has its own timing and is attached to the
zh cue it overlaps most (en cues with no overlap, e.g. title cards, become their own lines).
Writes WORKDIR/gen/EPxx.lines.json = [{i,start,end,zh,py,vi,en}] (ms). Skips existing unless --force.
"""
import argparse, json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import cfg, episodes, select, gen_dir, save, clean

try:
    from pypinyin import lazy_pinyin, Style
except ImportError:            # pragma: no cover
    sys.exit("pypinyin missing: use /home/box/venvs/ytdlp/bin/python")

def cues(path):
    if not os.path.exists(path): return []
    d = json.load(open(path, encoding="utf-8"))
    out = []
    for ev in d.get("events", []):
        if "segs" not in ev: continue
        text = clean("".join(s.get("utf8", "") for s in ev["segs"]))
        start = int(ev.get("tStartMs", 0)); end = start + int(ev.get("dDurationMs", 0))
        out.append({"start": start, "end": end, "text": text})
    return out

def pinyin(text):
    if not text: return ""
    toks = lazy_pinyin(text, style=Style.TONE, errors=lambda s: list(s))
    out = " ".join(t for t in toks if t != " ")
    for p in "，。！？、；：,.!?;:”」』)）":
        out = out.replace(" " + p, p)
    for p in "“「『(（":
        out = out.replace(p + " ", p)
    return " ".join(out.split())

def overlap(a, b):
    return max(0, min(a["end"], b["end"]) - max(a["start"], b["start"]))

def align(zh, vi, en):
    vi_by_start = {}
    for c in vi: vi_by_start.setdefault(c["start"], []).append(c["text"])
    lines = []
    for c in zh:
        v = vi_by_start.get(c["start"], [])
        lines.append({"start": c["start"], "end": c["end"], "zh": c["text"], "vi": v.pop(0) if v else "", "en": []})
    if not zh:                                   # no zh track: fall back to vi timing
        lines = [{"start": c["start"], "end": c["end"], "zh": "", "vi": c["text"], "en": []} for c in vi]
    orphans = []
    j0 = 0
    for e in en:
        if not e["text"]: continue
        best, bo = None, 0
        while j0 < len(lines) and lines[j0]["end"] < e["start"] - 10000: j0 += 1
        for j in range(j0, len(lines)):
            L = lines[j]
            if L["start"] > e["end"]: break
            o = overlap(L, e)
            if o > bo: best, bo = j, o
        if best is None: orphans.append({"start": e["start"], "end": e["end"], "zh": "", "vi": "", "en": [e["text"]]})
        else: lines[best]["en"].append(e["text"])
    lines = sorted(lines + orphans, key=lambda L: (L["start"], L["end"]))
    out = []
    for L in lines:
        if not (L["zh"] or L["vi"] or L["en"]): continue
        out.append({"i": len(out), "start": L["start"], "end": L["end"], "zh": L["zh"], "py": pinyin(L["zh"]),
                    "vi": L["vi"], "en": " ".join(L["en"])})
    return out

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("show"); ap.add_argument("work")
    ap.add_argument("--only"); ap.add_argument("--force", action="store_true"); a = ap.parse_args()
    c = cfg(a.show)
    if c["source"] != "youtube-official": sys.exit("ingest_youtube_json3 is for youtube-official shows")
    gen = gen_dir(a.work); done = skipped = missing = 0
    for ep in select(episodes(a.show, a.work), a.only):
        out = os.path.join(gen, ep["code"] + ".lines.json")
        if os.path.exists(out) and not a.force: skipped += 1; continue
        sub = lambda lang: os.path.join(a.work, "subs", f"{ep['youtubeId']}.{lang}.json3")
        zh, vi, en = cues(sub("zh-Hans")), cues(sub("vi")), cues(sub("en"))
        if not zh and not vi:
            missing += 1; print("no subs yet", ep["code"], ep["youtubeId"], file=sys.stderr); continue
        lines = align(zh, vi, en)
        save(out, lines)
        done += 1
        print(f"{ep['code']}: zh={len(zh)} vi={len(vi)} en={len(en)} -> {len(lines)} lines", file=sys.stderr)
    print(json.dumps({"written": done, "skipped": skipped, "missing": missing}))

if __name__ == "__main__": main()
