"""Text-only show: English SRT -> lines per episode.

Usage: python pipeline/multi/ingest_srt.py SHOW_ID WORKDIR [--only S01E01,S01E02] [--force]
Strips HTML/ASS tags and music notes, keeps speaker dashes and [SOUND] cues as-is.
Writes WORKDIR/gen/SxxEyy.lines.json = [{i,start,end,en}] (ms). If the file exists, keeps existing
translations (zh/vi) for lines whose English text is unchanged; skips entirely unless --force.
"""
import argparse, json, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import cfg, episodes, select, gen_dir, save, load

TS = re.compile(r"(\d+):(\d+):(\d+)[,.](\d+)\s*-->\s*(\d+):(\d+):(\d+)[,.](\d+)")

def ms(h, m, s, f): return ((int(h) * 60 + int(m)) * 60 + int(s)) * 1000 + int(f.ljust(3, "0")[:3])

def read_srt(path):
    raw = open(path, "rb").read()
    for enc in ("utf-8-sig", "cp1252", "latin-1"):
        try: text = raw.decode(enc); break
        except UnicodeDecodeError: continue
    blocks = re.split(r"\r?\n\s*\r?\n", text.replace("\r\n", "\n"))
    out = []
    for b in blocks:
        rows = [r for r in b.strip().split("\n") if r.strip()]
        k = next((j for j, r in enumerate(rows) if TS.search(r)), None)
        if k is None: continue
        m = TS.search(rows[k])
        body = [clean_text(r) for r in rows[k + 1:]]
        body = [r for r in body if r]
        if not body: continue
        out.append({"start": ms(*m.groups()[:4]), "end": ms(*m.groups()[4:]), "en": " ".join(body)})
    return out

def clean_text(r):
    r = re.sub(r"<[^>]+>", "", r)           # <i>, <font ...>
    r = re.sub(r"\{\\[^}]*\}", "", r)       # {\an8}
    r = r.replace("♪", "").replace("♫", "").replace("#", "")
    return re.sub(r"\s+", " ", r).strip()

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("show"); ap.add_argument("work")
    ap.add_argument("--only"); ap.add_argument("--force", action="store_true"); a = ap.parse_args()
    c = cfg(a.show)
    if c["source"] != "text-only": sys.exit("ingest_srt is for text-only shows")
    gen = gen_dir(a.work); done = skipped = missing = 0
    for ep in select(episodes(a.show, a.work), a.only):
        out = os.path.join(gen, ep["code"] + ".lines.json")
        if os.path.exists(out) and not a.force: skipped += 1; continue
        if not ep.get("srt"): missing += 1; print("no srt", ep["code"], file=sys.stderr); continue
        old = {L["en"]: L for L in (load(out, []) or [])}
        cues = sorted(read_srt(ep["srt"]), key=lambda x: x["start"])
        lines = []
        for cue in cues:
            L = {"i": len(lines), "start": cue["start"], "end": cue["end"], "en": cue["en"]}
            for k in c["translate"]:
                if old.get(cue["en"], {}).get(k): L[k] = old[cue["en"]][k]
            lines.append(L)
        save(out, lines); done += 1
        print(f"{ep['code']}: {len(lines)} lines", file=sys.stderr)
    print(json.dumps({"written": done, "skipped": skipped, "missing": missing}))

if __name__ == "__main__": main()
