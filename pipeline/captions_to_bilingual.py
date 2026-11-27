"""YouTube json3 auto-captions (vi) -> corrected sentence lines + Chinese -> bilingual SRT.

Usage: python pipeline/captions_to_bilingual.py CAPTIONS.vi-orig.json3 OUT_PREFIX [--model deepseek-chat]
Needs DEEPSEEK_API_KEY in env (never logged). Writes OUT_PREFIX.lines.json and OUT_PREFIX.vi-zh.srt.
"""
import argparse, json, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from llm import chat_json, USED

API = "https://api.deepseek.com/chat/completions"
SYSTEM = """你是越南语（北部河内口音）影视字幕编辑兼中文译者。剧名《Về nhà đi con》（回家吧，孩子，VTV 2019）。
河内口音里 d/gi/r 都读 /z/，s/x、tr/ch 不分，所以自动识别常混淆这些字母（如 giỗ 被识别成 dỗ），请按语义改正。
称谓：三姐妹称 ông Sơn 为 bố（爸）；三姐妹的外公外婆（Sơn 的岳父母）出现时，说话人叫 ông/bà，应译“外公/外婆”或按说话人译“爸/妈”（Sơn 对岳父母称 bố/mẹ）；ông Luật、bà Giang 是 Vũ 的父母。
主要人物：ông Sơn（老爸）、Thu Huệ（大女儿）、Anh Thư（二女儿）、Ánh Dương / Dương Xoăn（小女儿，假小子）、Vũ（Thư 的丈夫）、Khải（Huệ 的丈夫）、Bảo（Dương 的青梅竹马）、Quốc（Bảo 的爸爸）、ông Luật、bà Giang、Nhã、Cu Bon。
输入是 YouTube 自动识别的越南语词表，每个词带编号。任务：
1. 按说话人和语义把词切成自然的字幕句，每句不超过约 14 个越南语音节；
2. 改正明显的识别错误（如 gần cũi→gần gũi，đường mặt→đường mật），补上越南语正确的声调和标点，人名首字母大写；不确定时保持原样；
3. 给出自然、口语化的简体中文翻译，保留称谓的亲疏（bố=爸，con=孩子/我(对长辈)，anh/chị/em 按语境译）。
4. 删除 [âm nhạc] 之类的非对白。
只输出 JSON：{"lines":[{"s":起始词编号,"e":结束词编号,"vi":"...","zh":"..."}]}，s/e 必须覆盖输入里的对白词，按顺序，不重叠。"""

def words_from_json3(path):
    d = json.load(open(path, encoding="utf-8"))
    out = []
    for ev in d.get("events", []):
        if "segs" not in ev: continue
        for sg in ev["segs"]:
            w = sg.get("utf8", "").strip()
            if not w or w.startswith("["): continue
            out.append({"t": ev["tStartMs"] + sg.get("tOffsetMs", 0), "w": w, "evEnd": ev["tStartMs"] + ev.get("dDurationMs", 0)})
    return out

def call(model, prompt):
    return chat_json(SYSTEM, prompt)["lines"]

def ts(ms):
    ms = max(0, int(ms)); h, ms = divmod(ms, 3600000); m, ms = divmod(ms, 60000); s, ms = divmod(ms, 1000)
    return f"{h:02}:{m:02}:{s:02},{ms:03}"

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("captions"); ap.add_argument("out"); ap.add_argument("--model", default="deepseek-chat")
    ap.add_argument("--chunk", type=int, default=220)
    ap.add_argument("--reuse", action="store_true", help="re-time from existing OUT.lines.json without calling the LLM"); a = ap.parse_args()
    words = words_from_json3(a.captions)
    lines = []
    if a.reuse:
        lines = [{k: L[k] for k in ("s", "e", "vi", "zh")} for L in json.load(open(a.out + ".lines.json", encoding="utf-8"))]
    for start in ([] if a.reuse else range(0, len(words), a.chunk)):
        seg = words[start:start + a.chunk]
        ctx = "\n".join(f"{L['vi']} = {L['zh']}" for L in lines[-6:])
        prompt = (("上文（仅供参考，不要输出）：\n" + ctx + "\n\n") if ctx else "") + "词表：\n" + " ".join(f"{start + i}:{w['w']}" for i, w in enumerate(seg))
        got = call(a.model, prompt)
        for L in got:
            s, e = int(L["s"]), int(L["e"])
            if not (start <= s <= e < start + len(seg)) or not L.get("vi"): continue
            lines.append({"s": s, "e": e, "vi": L["vi"].strip(), "zh": L.get("zh", "").strip()})
        print(f"chunk {start // a.chunk + 1}/{(len(words) + a.chunk - 1) // a.chunk}: {len(got)} lines", file=sys.stderr)
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    lines.sort(key=lambda x: x["s"])
    for i, L in enumerate(lines):
        L["startMs"] = words[L["s"]]["t"] - 150
        nxt = words[L["e"] + 1]["t"] if L["e"] + 1 < len(words) else words[L["e"]]["t"] + 1500
        end = min(nxt, words[L["e"]]["t"] + 1200)          # last word start + ~1.2s
        if i + 1 < len(lines): end = min(end, words[lines[i + 1]["s"]]["t"] - 180)
        L["endMs"] = max(end, L["startMs"] + 900)
    for a_, b_ in zip(lines, lines[1:]):                 # no overlaps: VLC stacks overlapping cues
        if a_["endMs"] > b_["startMs"] - 40:
            a_["endMs"] = max(a_["startMs"] + 300, b_["startMs"] - 40)
            if a_["endMs"] > b_["startMs"] - 40: b_["startMs"] = a_["endMs"] + 40
    json.dump(lines, open(a.out + ".lines.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    with open(a.out + ".vi-zh.srt", "w", encoding="utf-8-sig", newline="\r\n") as f:
        for i, L in enumerate(lines, 1):
            f.write(f"{i}\n{ts(L['startMs'])} --> {ts(L['endMs'])}\n{L['vi']}\n{L['zh']}\n\n")
    if not a.reuse:
        json.dump({"providers": sorted(USED), "words": len(words), "lines": len(lines)}, open(a.out + ".meta.json", "w"))
    print(len(words), "words ->", len(lines), "lines", sorted(USED), file=sys.stderr)

if __name__ == "__main__":
    main()
