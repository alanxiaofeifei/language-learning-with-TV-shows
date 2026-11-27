"""Rule-based Chinese-friendly reading for Northern (Hà Nội) Vietnamese.
Output is pinyin-like (consonants read as in Hanyu Pinyin) + tone arrow, e.g. "Không sao đâu" -> "không→hôngm— sao→sao— đâu→dơu—".
Legend lives in site/guide.html; keep the two in sync."""
import re, unicodedata
from tones import tone

ARROW = {"ngang": "—", "huyền": "↘", "sắc": "↗", "hỏi": "↘↗", "ngã": "↗'", "nặng": "↓."}
ONSETS = [("ngh", "ng"), ("ng", "ng"), ("nh", "ni"), ("gh", "g"), ("gi", "z"), ("kh", "h"), ("ch", "j"), ("tr", "j"),
          ("th", "t"), ("ph", "f"), ("qu", "gu"), ("b", "b"), ("c", "g"), ("k", "g"), ("d", "z"), ("đ", "d"), ("g", "g"),
          ("h", "h"), ("l", "l"), ("m", "m"), ("n", "n"), ("p", "b"), ("r", "z"), ("s", "s"), ("t", "d"), ("v", "v"), ("x", "s")]
VOWEL = {"a": "a", "ă": "a", "â": "ơ", "e": "e", "ê": "ê", "i": "i", "y": "i", "o": "o", "ô": "ô", "ơ": "ơ", "u": "u", "ư": "ư"}
# codas after back-rounded vowels close the lips in Hà Nội: ông -> ôngm, óc -> ốcp
def strip_tone(s):
    out = []
    for ch in unicodedata.normalize("NFD", s):
        if ch in "\u0300\u0301\u0309\u0303\u0323": continue
        out.append(ch)
    return unicodedata.normalize("NFC", "".join(out))

def syllable(raw):
    low = strip_tone(raw.lower())
    if not re.fullmatch(r"[a-zđăâêôơư]+", low): return raw
    onset, rest = "", low
    if low in ("gi", "gin", "gim", "git", "gip"):          # gì, gìn, gìm: gi + vowel i
        return "z" + low[1:]
    for o, rep in ONSETS:
        if low.startswith(o) and len(low) > len(o):
            if o == "gi" and low[2:3] in ("", ) : break
            onset, rest = rep, low[len(o):]; break
    if low.startswith("gi") and onset == "z" and not rest: rest = "i"
    m = re.fullmatch(r"([aăâeêioôơuưy]+)(ch|nh|ng|c|m|n|p|t)?", rest)
    if not m: return onset + rest
    nuc, coda = m.group(1), m.group(2) or ""
    nucr = "".join(VOWEL.get(c, c) for c in nuc)
    if coda == "nh": coda = "ing" if nucr[-1] in "aeê" else "ng"
    elif coda == "ch": coda = "ik" if nucr[-1] in "aeê" else "k"
    elif coda == "c": coda = "k"
    if coda in ("ng", "k") and nucr[-1] in "oôu" and len(nucr) == 1: coda += "m" if coda == "ng" else "p"
    if onset == "ni" and nucr.startswith("i"): onset = "n"
    return onset + nucr + coda

def reading(text):
    out = []
    for w in text.split():
        core = w.strip(".,!?…\"“”:;()")
        if not core: continue
        out.append(syllable(core) + ARROW[tone(core)])
    return " ".join(out)

if __name__ == "__main__":
    import sys
    for t in sys.argv[1:] or ["Không sao đâu", "Còn gì nữa không", "Em xin lỗi ạ", "Bao nhiêu tiền", "Cho tôi một cốc cà phê", "Người Trung Quốc", "Rất vui được gặp anh", "Tăng ca", "Nghỉ phép", "Học tiếng Việt"]:
        print(t, "=>", reading(t))
