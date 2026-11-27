"""lines.json -> daily-life phrase cards with timestamps + YouTube jump links (DeepSeek).
Usage: python pipeline/extract_phrases.py LINES.json VIDEO_ID OUT.json [--n 15]"""
import argparse, json, os, sys
sys.path.insert(0, os.path.dirname(__file__))
from captions_to_bilingual import API
from tones import tone_marks
import urllib.request
SYS = """你是给零基础中文母语者教北越（河内）口语的老师。学习者在海防的台企工作，要应付吃饭、买东西、问路、职场寒暄。
从给定字幕行里挑出最值得学的日常口语（短、高频、可直接在生活/工作中用；避开剧情专有、粗口和人名）。
每条输出：idx（字幕行编号）、phrase（句中可单独拿出来用的越南语块，2-8 音节）、zh（意思）、en（英文 gloss）、
reading（给中国人的近似读法，用汉语拼音/汉字近似，并提醒北音：d/gi/r 读 z，tr 读 ch，s 读 x，结尾 c/t/p 不爆破）、
usage（什么场合怎么用，一句话中文）、level（1=第一周就要会，2=第一个月，3=之后）。
只输出 JSON {"phrases":[...]}。"""
def main():
    ap = argparse.ArgumentParser(); ap.add_argument("lines"); ap.add_argument("video"); ap.add_argument("out"); ap.add_argument("--n", type=int, default=15)
    a = ap.parse_args(); lines = json.load(open(a.lines, encoding="utf-8"))
    text = "\n".join(f"{i}: {L['vi']} = {L['zh']}" for i, L in enumerate(lines))
    body = json.dumps({"model": "deepseek-chat", "temperature": 0.3, "response_format": {"type": "json_object"},
        "messages": [{"role": "system", "content": SYS}, {"role": "user", "content": f"挑 {a.n} 条：\n" + text}]}).encode()
    req = urllib.request.Request(API, data=body, headers={"Authorization": "Bearer " + os.environ["DEEPSEEK_API_KEY"], "Content-Type": "application/json", "User-Agent": "tvshows-pipeline/0.1"})
    out = json.loads(json.load(urllib.request.urlopen(req, timeout=300))["choices"][0]["message"]["content"])["phrases"]
    for p in out:
        L = lines[int(p["idx"])]; sec = max(0, L["startMs"] // 1000 - 2)
        p.update(line_vi=L["vi"], line_zh=L["zh"], startMs=L["startMs"], endMs=L["endMs"], tones=tone_marks(p["phrase"]),
                 youtube=f"https://www.youtube.com/watch?v={a.video}&t={sec}s")
    json.dump(out, open(a.out, "w", encoding="utf-8"), ensure_ascii=False, indent=1); print(len(out), "phrases", file=sys.stderr)
if __name__ == "__main__": main()
