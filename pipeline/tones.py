"""Deterministic Vietnamese tone tagging from diacritics (Northern/Hà Nội keeps all 6 tones)."""
import unicodedata
TONES = {"\u0300": ("huyền", "低降 ↘ (像普通话轻声往下)"), "\u0301": ("sắc", "高升 ↗ (像普通话二声偏高)"),
         "\u0309": ("hỏi", "低降后微升 ↘↗ (像三声)"), "\u0303": ("ngã", "高升带喉塞 ↗' (嗓子中间一卡)"),
         "\u0323": ("nặng", "低沉短促 ↓. (急降+喉塞)")}
def tone(syllable):
    for ch in unicodedata.normalize("NFD", syllable.lower()):
        if ch in TONES: return TONES[ch][0]
    return "ngang"
def tone_marks(text):
    sym = {"ngang": "—", "huyền": "↘", "sắc": "↗", "hỏi": "↘↗", "ngã": "↗'", "nặng": "↓."}
    words = [w.strip(".,!?…\"“”") for w in text.split()]
    return " ".join(f"{w}({sym[tone(w)]})" for w in words if w)
if __name__ == "__main__":
    import sys; print(tone_marks(" ".join(sys.argv[1:])))
