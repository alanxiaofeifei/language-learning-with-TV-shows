"""Assemble generated data into site/private/ (git-ignored, deployed behind Cloudflare Access).
Usage: python pipeline/build_site_data.py WORKDIR   (WORKDIR has gen/Pxx.*, gen/clips/Pxx/*.mp3)"""
import json, os, shutil, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
work = sys.argv[1]; gen = os.path.join(work, "gen")
priv = os.path.join(ROOT, "site", "private")
meta = json.load(open(os.path.join(ROOT, "data", "ve-nha-di-con", "parts.json"), encoding="utf-8"))

titles_path = os.path.join(gen, "titles_zh.json")
titles = json.load(open(titles_path, encoding="utf-8")) if os.path.exists(titles_path) else {}
missing = [p for p in meta["parts"] if str(p["part"]) not in titles]
if missing:
    from llm import chat_json
    got = chat_json("把越南电视剧《Về nhà đi con》各段的 YouTube 标题翻译成简洁的中文（去掉夸张大写语气，15 字内）。只输出 JSON {\"titles\":{\"段号\":\"中文\"}}。",
                    "\n".join(f"{p['part']}: {p['title']}" for p in missing))["titles"]
    titles.update({str(k): v for k, v in got.items()})
    json.dump(titles, open(titles_path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

for sub in ("data", "srt", "audio"):
    shutil.rmtree(os.path.join(priv, sub), ignore_errors=True); os.makedirs(os.path.join(priv, sub))
parts, phrases, search, providers = [], [], [], {}
for p in meta["parts"]:
    n = p["part"]; tag = f"P{n:02d}"
    lines_f = os.path.join(gen, tag + ".lines.json")
    if not os.path.exists(lines_f):
        print("missing", tag, file=sys.stderr); continue
    lines = json.load(open(lines_f, encoding="utf-8"))
    m = json.load(open(os.path.join(gen, tag + ".meta.json"))) if os.path.exists(os.path.join(gen, tag + ".meta.json")) else {"providers": ["deepseek"]}
    providers[tag] = m.get("providers") or ["deepseek"]
    srt_name = f"VeNhaDiCon_{tag}_{p['videoId']}.srt"
    shutil.copy(os.path.join(gen, tag + ".vi-zh.srt"), os.path.join(priv, "srt", srt_name))
    json.dump({"part": n, "lines": [{"vi": L["vi"], "zh": L["zh"], "startMs": L["startMs"], "endMs": L["endMs"]} for L in lines]},
              open(os.path.join(priv, "data", tag + ".json"), "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
    search += [[n, L["startMs"], L["vi"], L["zh"]] for L in lines]
    ph_f = os.path.join(gen, tag + ".phrases.json")
    for ph in (json.load(open(ph_f, encoding="utf-8")) if os.path.exists(ph_f) else []):
        clip = None
        if ph.get("clip"):
            src = os.path.join(gen, "clips", tag, ph["clip"])
            if os.path.exists(src):
                os.makedirs(os.path.join(priv, "audio", tag), exist_ok=True)
                shutil.copy(src, os.path.join(priv, "audio", tag, ph["clip"])); clip = f"/private/audio/{tag}/{ph['clip']}"
        phrases.append({k: ph.get(k) for k in ("id", "part", "phrase", "zh", "en", "category", "level", "usage", "tones", "reading", "lineVi", "lineZh", "startMs", "youtube")} | {"clip": clip})
    parts.append({"part": n, "videoId": p["videoId"], "title": p["title"], "titleZh": titles.get(str(n), ""), "duration": p["duration"],
                  "lines": len(lines), "source": "whisper" if p.get("captions") == "none" else "youtube-asr", "srt": f"/private/srt/{srt_name}"})
json.dump({"show": {"vi": "Về nhà đi con", "zh": "回家吧，孩子"}, "parts": parts, "phrases": phrases},
          open(os.path.join(priv, "data", "index.json"), "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
json.dump(search, open(os.path.join(priv, "data", "search.json"), "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
open(os.path.join(priv, "login.html"), "w").write('<!doctype html><meta charset="utf-8"><title>已登录</title><meta http-equiv="refresh" content="0;url=/#/"><a href="/#/">已登录，回到学习页</a>')
open(os.path.join(priv, "index.html"), "w").write('<!doctype html><meta charset="utf-8"><meta http-equiv="refresh" content="0;url=/#/">')
glm = sorted(t for t, v in providers.items() if "glm" in v)
stats = {"parts": len(parts), "lines": len(search), "phrases": len(phrases), "clips": sum(1 for x in phrases if x["clip"]), "glmParts": glm}
json.dump(stats, open(os.path.join(work, "gen", "build_stats.json"), "w"), indent=1)
print(json.dumps(stats))
