"""Pick ~15 useful phrases per episode with level + bilingual (zh/vi) explanations.

Usage: python pipeline/multi/extract_phrases_multi.py SHOW_ID WORKDIR [--only EP01] [--n 15] [--force]
Writes gen/<CODE>.phrases.json. Skips episodes that already have one unless --force.
Phrases must occur in their source line (else re-located in nearby lines, else dropped).
zh shows get pypinyin readings by rule; levels are HSK bands (HSK1..HSK6, HSK7-9) JLPT (N5..N1), or CEFR (A1..C2).
"""
import argparse, json, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import cfg, episodes, select, gen_dir, save, load
from llm import chat_json, USED
from textmatch import norm, matches

LEVELS = {"JLPT": ["N5", "N4", "N3", "N2", "N1"], "HSK": ["HSK1", "HSK2", "HSK3", "HSK4", "HSK5", "HSK6", "HSK7-9"], "CEFR": ["A1", "A2", "B1", "B2", "C1", "C2"]}

def system(c, n):
    reading = ""
    example = "中文或英文"
    if c["target"] == "zh":
        what = ("从中文字幕里挑出最值得学的词语、固定搭配、口语句式或成语（2–12 个汉字，从原句里原样截取）。"
                "level 用新 HSK 等级：HSK1…HSK6 或 HSK7-9（取该表达整体的难度）。优先 HSK4 以上、考试和日常都常用的；避开人名和剧情专有词。")
        meaning = '"meaning_vi":"越南语意思","meaning_en":"English gloss"'
    elif c["target"] in ("ja", "fr"):
        japanese = c["target"] == "ja"
        example = "日语" if japanese else "法语"
        level = "JLPT：N5/N4/N3/N2/N1" if japanese else "CEFR：A1/A2/B1/B2/C1/C2"
        what = (f"从{example}字幕里原样截取实用的日常口语表达、固定搭配或句式。"
                f"level 用 {level}，按整个表达的难度分级。避开人名和剧情专有词。")
        meaning = '"meaning_zh":"中文意思","meaning_vi":"越南语意思"'
        if japanese:
            reading = '"reading":"短语在原句中的读法，使用平假名",'
    else:
        what = ("从英文字幕里挑出最值得学的口语表达、短语动词、习语或句式（1–8 个词，从原句里原样截取）。"
                "level 用 CEFR：A2/B1/B2/C1/C2。优先地道、高频、能离开剧情直接用的；粗口、人名、剧情专有内容不要。")
        meaning = '"meaning_zh":"中文意思","meaning_vi":"越南语意思"'
    return (f"你是语言老师。{c['audience']}\n{what}\n挑 {n} 条，按出现顺序，不要重复。每条输出："
            f'{{"idx":字幕行号,"phrase":"原文片段","level":"…",{meaning},{reading}'
            '"explain_vi":"越南语讲解：意思、语气、和近义说法的区别（1–2 句）","explain_zh":"中文讲解（1 句）",'
            f'"usage_vi":"越南语：什么场合用 + 一个自编新例句（附{example}原文）","usage_zh":"中文：什么场合用 + 一个自编新例句"}}。'
            '例句必须自编，不能抄剧中台词。只输出 JSON {"phrases":[...]}。')

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("show"); ap.add_argument("work")
    ap.add_argument("--only"); ap.add_argument("--n", type=int, default=15); ap.add_argument("--force", action="store_true"); a = ap.parse_args()
    c = cfg(a.show); src = c["target"]; zh = src == "zh"; gen = gen_dir(a.work); total = 0; run_used = set()
    substring = src in ("zh", "ja")
    if zh:
        from ingest_youtube_json3 import pinyin
    for ep in select(episodes(a.show, a.work), a.only):
        out = os.path.join(gen, ep["code"] + ".phrases.json")
        if os.path.exists(out) and not a.force: continue
        lines = load(os.path.join(gen, ep["code"] + ".lines.json"))
        if not lines: continue
        usable = [L for L in lines if L.get(src) and not re.fullmatch(r"\[.*\]", L[src])]
        user = f"《{c['title']['zh']}》{ep['code']} 字幕：\n" + "\n".join(f"{L['i']}: {L[src]}" for L in usable)
        USED.clear()                      # meta records only this episode's providers
        got = chat_json(system(c, a.n), user, temperature=0.3).get("phrases", [])
        run_used |= USED
        by_i = {L["i"]: L for L in lines}; res, seen = [], set()
        for p in got:
            phrase = (p.get("phrase") or "").strip().strip("，。,.!?！？")
            if not phrase: continue
            try: i = int(p.get("idx"))
            except (TypeError, ValueError): i = -1
            key = norm(phrase, zh, src)
            if not key or key in seen: continue
            cand = [i] + [j for d in range(1, 4) for j in (i - d, i + d)]
            hit = next((j for j in cand if j in by_i and matches(key, norm(by_i[j].get(src), zh, src), substring)), None)
            if hit is None:
                hit = next((L["i"] for L in usable if matches(key, norm(L[src], zh, src), substring)), None)
            if hit is None: print("drop (not in source)", ep["code"], phrase, file=sys.stderr); continue
            seen.add(key); L = by_i[hit]
            lv = str(p.get("level", "")).upper().replace(" ", "")
            lv = next((x for x in LEVELS[c["level"]] if x.upper() == lv), None) or ("HSK7-9" if zh and lv.startswith("HSK7") else None)
            card = {"id": f"{ep['code'].lower()}-{len(res) + 1:02d}", "ep": ep["n"], "code": ep["code"], "line": hit,
                    "start": L["start"], "end": L["end"], "phrase": phrase, "level": lv,
                    "explain_zh": (p.get("explain_zh") or "").strip(), "explain_vi": (p.get("explain_vi") or "").strip(),
                    "usage_zh": (p.get("usage_zh") or "").strip(), "usage_vi": (p.get("usage_vi") or "").strip()}
            for k in ("meaning_zh", "meaning_vi", "meaning_en"):
                if p.get(k): card[k] = str(p[k]).strip()
            if zh: card["py"] = pinyin(phrase)
            if src == "ja" and isinstance(p.get("reading"), str):
                card["reading"] = p["reading"].strip()
            res.append(card)
        save(out, res); total += len(res)
        meta_p = os.path.join(gen, ep["code"] + ".meta.json"); meta = load(meta_p, {}) or {}
        meta["phrases"] = sorted(USED); save(meta_p, meta)
        print(f"{ep['code']}: {len(res)} phrases", file=sys.stderr)
    print(json.dumps({"phrases": total, "providers": sorted(run_used)}))

if __name__ == "__main__": main()
