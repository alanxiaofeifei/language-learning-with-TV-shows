"""Assemble one show's generated data into site/private/shows/<SHOW_ID>/ (git-ignored, behind Access).

Usage: python pipeline/multi/build_show_data.py SHOW_ID WORKDIR
Output: index.json (episodes + all phrase cards), eps/<CODE>.json (lines), srt/*.srt, audio/<CODE>/*.mp3.
youtube-official: zh+vi and zh+en SRT per episode (timing = the official YouTube upload).
text-only: en+zh and en+vi SRT (timing approximate). Rebuilds the show folder from scratch each run.
"""
import json, os, shutil, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import ROOT, cfg, episodes, gen_dir, load, save, write_srt

def main():
    if len(sys.argv) != 3: sys.exit(__doc__)
    show, work = sys.argv[1], sys.argv[2]
    c = cfg(show); gen = gen_dir(work)
    out = os.path.join(ROOT, "site", "private", "shows", show)
    base = f"/private/shows/{show}"
    shutil.rmtree(out, ignore_errors=True)
    for sub in ("eps", "srt", "audio"): os.makedirs(os.path.join(out, sub))
    eps_out, phrases, n_lines = [], [], 0
    for ep in episodes(show, work):
        code = ep["code"]
        lines = load(os.path.join(gen, code + ".lines.json"))
        if not lines: continue
        keep = ["i", "start", "end"] + [k for k in c["langs"] if any(L.get(k) for L in lines)]
        slim = [{k: L[k] for k in keep if L.get(k) not in (None, "")} for L in lines]
        save(os.path.join(out, "eps", code + ".json"), {"code": code, "n": ep["n"], "langs": keep[3:], "lines": slim}, compact=True)
        n_lines += len(lines)
        srts = []
        stem = f"{c['srtPrefix']}_{code}" + (f"_{ep['youtubeId']}" if ep.get("youtubeId") else "")
        t = c["target"]
        pairs = [("zh", "vi"), ("zh", "en")] if t == "zh" else [("en", "zh"), ("en", "vi")]
        for a, b in pairs:
            if not any(L.get(b) for L in lines): continue
            name = f"{stem}.{a}-{b}.srt"
            write_srt(os.path.join(out, "srt", name), [(L["start"], L["end"], [L.get(a, ""), L.get(b, "")]) for L in lines])
            srts.append({"langs": [a, b], "href": f"{base}/srt/{name}"})
        for p in load(os.path.join(gen, code + ".phrases.json"), []) or []:
            p = dict(p); clip = p.pop("clip", None); p["clip"] = None
            p["ep"] = ep["n"]
            if clip:
                src = os.path.join(gen, "clips", code, clip)
                if os.path.exists(src):
                    os.makedirs(os.path.join(out, "audio", code), exist_ok=True)
                    shutil.copy(src, os.path.join(out, "audio", code, clip))
                    p["clip"] = f"{base}/audio/{code}/{clip}"
            L = lines[p["line"]] if 0 <= p.get("line", -1) < len(lines) else {}
            p["lineText"] = {k: L[k] for k in c["langs"] if L.get(k)}
            phrases.append(p)
        rec = {"n": ep["n"], "code": code, "lines": len(lines), "phrases": sum(1 for p in phrases if p["code"] == code), "srt": srts,
               "file": f"{base}/eps/{code}.json"}
        for k in ("youtubeId", "duration", "title"):
            if ep.get(k): rec[k] = ep[k]
        eps_out.append(rec)
    save(os.path.join(out, "index.json"), {"show": show, "source": c["source"], "target": c["target"], "langs": c["langs"],
                                           "episodes": eps_out, "phrases": phrases}, compact=True)
    stats = {"show": show, "episodes": len(eps_out), "lines": n_lines, "phrases": len(phrases),
             "clips": sum(1 for p in phrases if p["clip"]), "srt": sum(len(e["srt"]) for e in eps_out)}
    save(os.path.join(gen, "build_stats.json"), stats)
    print(json.dumps(stats))

if __name__ == "__main__": main()
