"""Phrase <-> source-line matching for extract_phrases_multi.py (pure functions, no I/O)."""
import re

_ZH_DROP = re.compile(r"[\s，。！？、,.!?…\"'“”‘’]")

def norm(s, zh):
    """zh: drop spaces and punctuation. Other: lowercase, curly -> straight apostrophe,
    every other non [a-z0-9'] char becomes a space, runs of spaces collapse to one."""
    s = s or ""
    if zh: return _ZH_DROP.sub("", s)
    s = s.lower().replace("\u2019", "'").replace("\u2018", "'")
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9' ]", " ", s)).strip()

def matches(key, line_norm, zh):
    """key and line_norm are norm() outputs. zh: substring. Other: whole words only
    ("go" must not match inside "ago" or "go's")."""
    if not key or not line_norm: return False
    if zh: return key in line_norm
    return re.search(r"(?<![a-z0-9'])" + re.escape(key) + r"(?![a-z0-9'])", line_norm) is not None
