"""Official YouTube subtitle tracks (json3) -> aligned lines per episode.

Usage: python pipeline/multi/ingest_youtube_json3.py SHOW_ID WORKDIR [--only EP01,EP02] [--force]
zh-Hans and vi share cue timing (joined by exact cue start; a vi cue with no exact match is attached
to the line it overlaps most); en has its own timing and is attached the same way. Cues with no
overlap (e.g. title cards) become their own lines. Cues whose text is empty after cleaning are dropped.
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
        if not text: continue
        start = int(ev.get("tStartMs", 0)); end = start + max(0, int(ev.get("dDurationMs", 0)))
        out.append({"start": start, "end": end, "text": text})
    return sorted(out, key=lambda c: (c["start"], c["end"]))

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

def attach(lines, items, key):
    """Append each item's text to lines[*][key] (a list) of the line it overlaps most.
    lines and items sorted by start. Returns the lines plus new single-item lines for non-overlapping items."""
    orphans = []
    j0 = 0
    for e in items:
        if not e["text"]: continue
        best, bo = None, 0
        while j0 < len(lines) and lines[j0]["end"] < e["start"] - 10000: j0 += 1
        for j in range(j0, len(lines)):
            L = lines[j]
            if L["start"] > e["end"]: break
            o = overlap(L, e)
            if o > bo: best, bo = j, o
        if best is None:
            o = {"start": e["start"], "end": e["end"], "zh": "", "vi": [], "en": []}; o[key] = [e["text"]]; orphans.append(o)
        else: lines[best][key].append(e["text"])
    return sorted(lines + orphans, key=lambda L: (L["start"], L["end"]))

def align(zh, vi, en):
    zh = [c for c in zh if c["text"]]; vi = [c for c in vi if c["text"]]; en = [c for c in en if c["text"]]
    if zh:
        vi_by_start = {}
        for k, c in enumerate(vi): vi_by_start.setdefault(c["start"], []).append(k)
        used = set(); lines = []
        for c in zh:
            ks = vi_by_start.get(c["start"], [])
            v = []
            if ks: k = ks.pop(0); used.add(k); v = [vi[k]["text"]]
            lines.append({"start": c["start"], "end": c["end"], "zh": c["text"], "vi": v, "en": []})
        lines = attach(lines, [c for k, c in enumerate(vi) if k not in used], "vi")
    else:                                        # no zh track: fall back to vi timing
        lines = [{"start": c["start"], "end": c["end"], "zh": "", "vi": [c["text"]], "en": []} for c in vi]
    lines = attach(lines, en, "en")
    out = []
    for L in lines:
        if not (L["zh"] or L["vi"] or L["en"]): continue
        out.append({"i": len(out), "start": L["start"], "end": L["end"], "zh": L["zh"], "py": pinyin(L["zh"]),
                    "vi": " ".join(L["vi"]), "en": " ".join(L["en"])})
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
