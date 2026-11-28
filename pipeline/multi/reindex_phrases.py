"""Re-point phrase cards at re-ingested lines (no LLM).

Usage: python pipeline/multi/reindex_phrases.py SHOW_ID WORKDIR --old-gen DIR [--only S01E01] [--dry-run]
After gen/<CODE>.lines.json is re-ingested (for example after dropping Spanish lyric cues) line indexes `i`
shift. --old-gen holds copies of the pre-ingest gen/<CODE>.lines.json files. For every card in
gen/<CODE>.phrases.json the old line is found by (start, end) (preferring old index `line`); the card keeps
its id and gets the `line` of the new line with the same start, end and target text. Cards whose line no
longer exists (the cue was dropped or its text changed) are dropped and reported on stderr.
Idempotent: a second run finds the same lines and changes nothing. --dry-run writes nothing.
Prints a JSON summary {episode: {kept, dropped}} on stdout.
"""
import argparse, json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import cfg, episodes, select, gen_dir, save, load


def pick(cands, prefer):
    """First candidate, preferring the one whose index is `prefer`."""
    return next((L for L in cands if L.get("i") == prefer), cands[0] if cands else None)


def reindex(phrases, old_lines, new_lines, target):
    """-> (kept cards with updated `line`, [(card, reason)] dropped)."""
    old_by = {}
    for L in old_lines: old_by.setdefault((L["start"], L["end"]), []).append(L)
    new_by = {}
    for L in new_lines: new_by.setdefault((L["start"], L["end"], L.get(target)), []).append(L)
    kept, dropped = [], []
    for p in phrases:
        span = (p.get("start"), p.get("end"))
        olds = sorted(old_by.get(span, []), key=lambda L: L.get("i") != p.get("line"))   # old index first
        if not olds:
            dropped.append((p, "old line not found")); continue
        new = next((n for n in (pick(new_by.get(span + (o.get(target),), []), p.get("line")) for o in olds) if n), None)
        if new is None:
            dropped.append((p, "line dropped or changed")); continue
        kept.append({**p, "line": new["i"]})
    return kept, dropped


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("show"); ap.add_argument("work")
    ap.add_argument("--old-gen", required=True, help="folder with the pre-ingest <CODE>.lines.json copies")
    ap.add_argument("--only"); ap.add_argument("--dry-run", action="store_true"); a = ap.parse_args()
    c = cfg(a.show); target = c["target"]; gen = gen_dir(a.work)
    if os.path.realpath(a.old_gen) == os.path.realpath(gen):
        sys.exit("--old-gen must be a backup folder, not WORKDIR/gen")
    summary = {}
    for ep in select(episodes(a.show, a.work), a.only):
        code = ep["code"]
        p_path = os.path.join(gen, code + ".phrases.json")
        phrases = load(p_path)
        if phrases is None: continue
        old_lines = load(os.path.join(a.old_gen, code + ".lines.json"))
        new_lines = load(os.path.join(gen, code + ".lines.json"))
        if old_lines is None or new_lines is None:
            print(f"{code}: skipped (missing {'old' if old_lines is None else 'new'} lines.json)", file=sys.stderr)
            continue
        kept, dropped = reindex(phrases, old_lines, new_lines, target)
        for p, why in dropped:
            print(f"{code}: drop {p.get('id')} {p.get('phrase')!r} ({why})", file=sys.stderr)
        summary[code] = {"kept": len(kept), "dropped": len(dropped)}
        if not a.dry_run and kept != phrases: save(p_path, kept)
    print(json.dumps(summary, ensure_ascii=False))


if __name__ == "__main__": main()
