"""lines.json -> daily-life phrase cards (LLM picks; tones + readings by rule).
Usage: python pipeline/extract_phrases.py LINES.json VIDEO_ID PART OUT.json [--n 15]"""
import argparse, json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from llm import chat_json, USED
from tones import tone_marks
from reading import reading

SYS = """你是给零基础中文母语者教北越（河内）口语的老师。学习者在海防的台资工厂上班，周末要吃饭、买东西、逛街、打车。
从字幕行里挑出最值得学的日常口语，优先级：food（吃饭点菜）> shopping（买东西、讲价、付钱）> work（职场、同事、上下级、请假、加班、开会）> survival（问路、交通、求助、身体不适、时间数字）> social（寒暄、道谢、道歉、客气话、称呼）> feeling（情绪、劝说、日常回应）。
要求：短、高频、离开剧情也能直接用；避开粗口、人名、剧情专有内容；同一句不要重复挑。
每条输出：idx（字幕行编号）、phrase（从该行原文截取、可单独使用的越南语块，2–8 音节，保持原拼写和声调）、zh（中文意思）、en（英文 gloss）、
category（food/shopping/work/survival/social/feeling 之一）、usage（一句中文：什么场合怎么用，可给一个替换说法）、level（1=第一周就要会，2=第一个月，3=之后）。
只输出 JSON {"phrases":[...]}。"""

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("lines"); ap.add_argument("video"); ap.add_argument("part", type=int); ap.add_argument("out")
    ap.add_argument("--n", type=int, default=15); a = ap.parse_args()
    lines = json.load(open(a.lines, encoding="utf-8"))
    text = "\n".join(f"{i}: {L['vi']} = {L['zh']}" for i, L in enumerate(lines))
    got = chat_json(SYS, f"挑 {a.n} 条：\n" + text, temperature=0.3)["phrases"]
    out, seen = [], set()
    for p in got:
        try: i = int(p["idx"])
        except (KeyError, ValueError, TypeError): continue
        if not (0 <= i < len(lines)) or not p.get("phrase"): continue
        key = p["phrase"].lower().strip(" .,!?")
        if key in seen: continue
        seen.add(key); L = lines[i]; sec = max(0, L["startMs"] // 1000 - 2)
        out.append({"id": f"p{a.part:02d}-{len(out)+1:02d}", "part": a.part, "line": i, "phrase": p["phrase"].strip(), "zh": p.get("zh", ""), "en": p.get("en", ""),
                    "category": p.get("category", "feeling"), "usage": p.get("usage", ""), "level": int(p.get("level", 2) or 2),
                    "tones": tone_marks(p["phrase"]), "reading": reading(p["phrase"]),
                    "lineVi": L["vi"], "lineZh": L["zh"], "startMs": L["startMs"], "endMs": L["endMs"],
                    "youtube": f"https://www.youtube.com/watch?v={a.video}&t={sec}s"})
    json.dump(out, open(a.out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(len(out), "phrases", sorted(USED), file=sys.stderr)

if __name__ == "__main__": main()
