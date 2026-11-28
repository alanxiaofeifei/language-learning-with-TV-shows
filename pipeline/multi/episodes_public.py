"""Write the PUBLIC episode list site/shows/<SHOW_ID>/episodes.json (tracked in Git).

Usage: python pipeline/multi/episodes_public.py SHOW_ID WORKDIR
Only public metadata: episode number/code, official YouTube ID + duration, episode title. No subtitle text.
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import ROOT, cfg, episodes, save

def main():
    if len(sys.argv) != 3: sys.exit(__doc__)
    show, work = sys.argv[1], sys.argv[2]; c = cfg(show)
    eps = [{k: e[k] for k in ("n", "code", "youtubeId", "duration", "title") if e.get(k)} for e in episodes(show, work)]
    save(os.path.join(ROOT, "site", "shows", show, "episodes.json"), {"show": show, "source": c["source"], "episodes": eps})
    print(show, len(eps), "episodes")

if __name__ == "__main__": main()
