"""Shared config + helpers for the multi-show pipeline (pipeline/multi/*).

WORKDIR layout (outside Git, e.g. /workspace/tvshows-work/multi/dtt):
  youtube-official: playlist.tsv (idx, youtubeId, durationSec), subs/<id>.{zh-Hans,vi,en}.json3, audio/<id>.m4a
  text-only:        srt/SxxEyy.<target>.srt, episodes.json (optional titles)
  gen/<CODE>.lines.json, gen/<CODE>.phrases.json, gen/<CODE>.meta.json, gen/clips/<CODE>/*.mp3
"""
import glob, json, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.dirname(HERE))          # pipeline/ (llm.py)

SHOWS = {
    "dou-ting-hao": {
        "source": "youtube-official",
        "target": "zh",                       # language being learned
        "langs": ["zh", "py", "vi", "en"],    # line fields available in the reader
        "translate": [],                      # official tracks already cover zh/vi/en
        "level": "HSK",                       # HSK 1-6 / 7-9
        "title": {"zh": "都挺好", "en": "All is Well"},
        "srtPrefix": "DouTingHao",
        "audience": "学习者是越南语母语者，中文已有工作水平，正在备考 HSK。越南语解释最重要，要准确、自然（北越用语）；中文解释可以很短。",
    },
    "friends": {
        "source": "text-only",
        "target": "en",
        "langs": ["en", "zh", "vi"],
        "translate": ["zh", "vi"],
        "level": "CEFR",
        "title": {"zh": "老友记", "en": "Friends"},
        "srtPrefix": "Friends",
        "audience": "学习者一位是中文母语者（英语中上），另一位是越南语母语者。中文解释和越南语解释都要写好，各自用自然的母语。",
    },
    "seinfeld": {
        "source": "text-only",
        "tvsubtitlesId": 89,
        "target": "en",
        "langs": ["en", "zh", "vi"],
        "translate": ["zh", "vi"],
        "level": "CEFR",
        "title": {"zh": "宋飞正传", "en": "Seinfeld"},
        "srtPrefix": "Seinfeld",
        "audience": "学习者一位是中文母语者（英语中上），另一位是越南语母语者。中文解释和越南语解释都要写好，各自用自然的母语。",
    },
    "silicon-valley": {
        "source": "text-only",
        "tvsubtitlesId": 1465,
        "target": "en",
        "langs": ["en", "zh", "vi"],
        "translate": ["zh", "vi"],
        "level": "CEFR",
        "title": {"zh": "硅谷", "en": "Silicon Valley"},
        "srtPrefix": "SiliconValley",
        "audience": "学习者一位是中文母语者（英语中上），另一位是越南语母语者。中文解释和越南语解释都要写好，各自用自然的母语。重点关注现代科技和创业公司常用的英语词汇。",
    },
    "desperate-housewives": {
        "source": "text-only",
        "tvsubtitlesId": 29,
        "target": "en",
        "langs": ["en", "zh", "vi"],
        "translate": ["zh", "vi"],
        "level": "CEFR",
        "title": {"zh": "绝望主妇", "en": "Desperate Housewives"},
        "srtPrefix": "DesperateHousewives",
        "audience": "学习者一位是中文母语者（英语中上），另一位是越南语母语者。中文解释和越南语解释都要写好，各自用自然的母语。",
    },
    "nigeru-wa-haji": {
        "source": "text-only",
        "target": "ja",
        "langs": ["ja", "reading", "zh", "vi"],
        "translate": ["zh", "vi"],
        "level": "JLPT",
        "title": {"zh": "逃避虽可耻但有用", "ja": "逃げるは恥だが役に立つ"},
        "srtPrefix": "Nigeru",
        "audience": "Alan 的母语是中文，Linh 的母语是越南语。用自然的中文和北越越南语讲解现代日常日语，按 JLPT 分级。",
    },
    "lupin": {
        "source": "text-only",
        "target": "fr",
        "langs": ["fr", "zh", "vi"],
        "translate": ["zh", "vi"],
        "level": "CEFR",
        "title": {"zh": "亚森·罗宾", "fr": "Lupin"},
        "srtPrefix": "Lupin",
        "audience": "用自然的中文和北越越南语讲解法国法语，按 CEFR 分级。先打好法国法语基础，魁北克法语差异以后补充。",
    },
}

def cfg(show_id):
    if show_id not in SHOWS:
        sys.exit(f"unknown show {show_id}; known: {', '.join(SHOWS)}")
    return SHOWS[show_id]

def gen_dir(work):
    d = os.path.join(work, "gen"); os.makedirs(d, exist_ok=True); return d

def episodes(show_id, work):
    """[{n, code, youtubeId?, duration?, title?, srt?}] for whatever exists in WORKDIR."""
    c = cfg(show_id); out = []
    if c["source"] == "youtube-official":
        with open(os.path.join(work, "playlist.tsv"), encoding="utf-8") as f:
            for row in f:
                parts = row.rstrip("\n").split("\t")
                if len(parts) < 2 or not parts[0].strip().isdigit(): continue
                n = int(parts[0]); vid = parts[1].strip()
                dur = int(parts[2]) if len(parts) > 2 and parts[2].strip().isdigit() else None
                out.append({"n": n, "code": f"EP{n:02d}", "youtubeId": vid, "duration": dur})
    else:
        target = c["target"]
        titles = {e["code"]: e.get("title", "") for e in load(os.path.join(work, "episodes.json"), [])}
        srt_dir = os.path.join(work, "srt")
        codes = sorted(set(titles) | {
            os.path.basename(path).split(".")[0]
            for path in glob.glob(os.path.join(srt_dir, f"S??E??.{target}.srt"))
        })
        for code in codes:
            srt = os.path.join(srt_dir, f"{code}.{target}.srt")
            if os.path.isfile(srt):
                out.append({"n": len(out) + 1, "code": code, "title": titles.get(code, ""), "srt": srt})
    return out

def select(eps, only):
    """--only EP01,EP02 or S01E01 or 1-2 (by n)."""
    if not only: return eps
    want = set()
    for tok in only.split(","):
        tok = tok.strip()
        m = re.fullmatch(r"(\d+)-(\d+)", tok)
        if m: want |= {e["code"] for e in eps if int(m[1]) <= e["n"] <= int(m[2])}
        else: want.add(tok.upper())
    return [e for e in eps if e["code"] in want]

def load(path, default=None):
    if not os.path.exists(path): return default
    with open(path, encoding="utf-8") as f: return json.load(f)

def save(path, obj, compact=False):
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        if compact: json.dump(obj, f, ensure_ascii=False, separators=(",", ":"))
        else: json.dump(obj, f, ensure_ascii=False, indent=1)
    os.replace(tmp, path)

JUNK = " \t\r\n,，、;；:：.。·…-–—"
def clean(text):
    """Collapse whitespace; drop stray leading/trailing punctuation (keep ?! and closing quotes)."""
    t = re.sub(r"\s+", " ", (text or "").replace("​", "")).strip()
    t = t.lstrip(JUNK)
    t = t.rstrip(" \t,，、;；:：")
    return t.strip()

def srt_ts(ms):
    ms = max(0, int(ms)); h, ms = divmod(ms, 3600000); m, ms = divmod(ms, 60000); s, ms = divmod(ms, 1000)
    return f"{h:02}:{m:02}:{s:02},{ms:03}"

def write_srt(path, cues):
    """cues: [(start_ms, end_ms, [text lines])]; empty texts skipped. UTF-8 BOM + CRLF for VLC on Windows."""
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    n = 0
    with open(path, "w", encoding="utf-8-sig", newline="\r\n") as f:
        for s, e, texts in cues:
            texts = [t for t in texts if t]
            if not texts: continue
            n += 1
            f.write(f"{n}\n{srt_ts(s)} --> {srt_ts(e)}\n" + "\n".join(texts) + "\n\n")
    return n
