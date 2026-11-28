"""Phrase <-> source-line matching for extract_phrases_multi.py (pure functions, no I/O)."""
import re
import unicodedata

_ZH_DROP = re.compile(r"[\s，。！？、,.!?…\"'“”‘’]")

def norm(s, zh, language=None):
    """zh: drop spaces and punctuation. Other: lowercase, curly -> straight apostrophe,
    every other non [a-z0-9'] char becomes a space, runs of spaces collapse to one."""
    s = s or ""
    if language == "ja":
        return "".join(ch for ch in unicodedata.normalize("NFKC", s)
                       if not ch.isspace() and not unicodedata.category(ch).startswith("P"))
    if language == "fr":
        folded = unicodedata.normalize("NFKD", s.casefold())
        s = "".join(ch for ch in folded if not unicodedata.category(ch).startswith("M")).replace("œ", "oe").replace("æ", "ae")
    if zh: return _ZH_DROP.sub("", s)
    s = s.lower().replace("\u2019", "'").replace("\u2018", "'")
    if language == "fr":
        s = s.replace("'", " ")
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9' ]", " ", s)).strip()

def matches(key, line_norm, zh):
    """key and line_norm are norm() outputs. zh: substring. Other: whole words only
    ("go" must not match inside "ago" or "go's")."""
    if not key or not line_norm: return False
    if zh: return key in line_norm
    return re.search(r"(?<![a-z0-9'])" + re.escape(key) + r"(?![a-z0-9'])", line_norm) is not None
