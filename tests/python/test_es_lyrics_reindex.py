"""Spanish lyric cleanup in ingest_srt and phrase re-indexing after a re-ingest (offline, no LLM)."""

import json
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
import unittest

MULTI = Path(__file__).resolve().parents[2] / "pipeline" / "multi"
sys.path.insert(0, str(MULTI))
import ingest_srt
from common import load, save
from reindex_phrases import reindex

SRT = """1
00:00:01,000 --> 00:00:02,000
<i>♪ No me cuentes cuentos
Que no me la gastas ♪</i>

2
00:00:03,000 --> 00:00:04,000
Esto es por el movimiento
de #Metoo.

3
00:00:05,000 --> 00:00:06,000
# Cuervos campeón #
- ¿Y ahora qué?

4
00:00:07,000 --> 00:00:08,000
- ¿Qué número?
- No. #20

5
00:00:09,000 --> 00:00:10,000
Ya me voy
y no vuelvo ♬

6
00:00:11,000 --> 00:00:12,000
{\\an8}<i>♫</i>

7
00:00:13,000 --> 00:00:14,000
# Smelly cat #
We're #1!
"""

LYRIC_ROWS = ["<i>♪ No me cuentes cuentos", "Que no me la gastas ♪</i>", "hola ♬", "♩", "# Cuervos campeón #", "# a # b #"]


class SpanishLyrics(unittest.TestCase):
    def read(self, target):
        with TemporaryDirectory() as tmp:
            p = Path(tmp) / f"S01E01.{target}.srt"
            p.write_text(SRT, encoding="utf-8")
            return ingest_srt.read_srt(str(p), target)

    def test_es_drops_whole_lyric_cues_and_wrapped_rows(self):
        self.assertEqual([(c["start"], c["es"]) for c in self.read("es")], [
            (3000, "Esto es por el movimiento de #Metoo."),
            (5000, "- ¿Y ahora qué?"),
            (7000, "- ¿Qué número? - No. #20"),
            (13000, "We're #1!"),
        ])

    def test_es_clean_text(self):
        for row in LYRIC_ROWS:
            self.assertEqual(ingest_srt.clean_text(row, "es"), "", row)
        self.assertEqual(ingest_srt.clean_text("de #Metoo.", "es"), "de #Metoo.")
        self.assertEqual(ingest_srt.clean_text("No. #20", "es"), "No. #20")
        self.assertEqual(ingest_srt.clean_text("#", "es"), "")

    def test_other_targets_unchanged(self):
        # Pinned to the behaviour before the Spanish change: notes are stripped, "# ... #" unwrapped.
        expect = [
            (1000, "No me cuentes cuentos Que no me la gastas"),
            (3000, "Esto es por el movimiento de #Metoo."),
            (5000, "Cuervos campeón - ¿Y ahora qué?"),
            (7000, "- ¿Qué número? - No. #20"),
            (9000, "Ya me voy y no vuelvo ♬"),
            (13000, "Smelly cat We're #1!"),
        ]
        for target in ("en", "zh", "fr", "ja"):
            self.assertEqual([(c["start"], c[target]) for c in self.read(target)], expect, target)
        self.assertEqual(ingest_srt.clean_text("hola ♬", "en"), "hola ♬")
        self.assertEqual(ingest_srt.clean_text("# a # b #", "fr"), "a b")


def line(i, start, text):
    return {"i": i, "start": start, "end": start + 900, "es": text, "zh": "译" + text}


OLD = [line(0, 1000, "♪ canción"), line(1, 2000, "Hola, güey."), line(2, 3000, "Otra canción"),
       line(3, 4000, "¿Qué onda?"), line(4, 5000, "Ya me voy.")]
NEW = [line(0, 2000, "Hola, güey."), line(1, 4000, "¿Qué onda?"), line(2, 5000, "Ya me fui.")]


def card(n, old_line):
    L = OLD[old_line]
    return {"id": f"s01e01-{n:02d}", "ep": 1, "code": "S01E01", "line": L["i"], "start": L["start"], "end": L["end"],
            "phrase": L["es"].split()[0], "level": "A1", "explain_zh": "x"}


class Reindex(unittest.TestCase):
    PHRASES = [card(1, 0), card(2, 1), card(3, 3), card(4, 4)]

    def test_reindex_maps_and_drops(self):
        kept, dropped = reindex(self.PHRASES, OLD, NEW, "es")
        self.assertEqual([(p["id"], p["line"]) for p in kept], [("s01e01-02", 0), ("s01e01-03", 1)])
        self.assertEqual([(p["id"], why) for p, why in dropped],
                         [("s01e01-01", "line dropped or changed"), ("s01e01-04", "line dropped or changed")])
        self.assertEqual({k: v for k, v in kept[0].items() if k != "line"},
                         {k: v for k, v in self.PHRASES[1].items() if k != "line"})
        again, dropped2 = reindex(kept, OLD, NEW, "es")      # idempotent
        self.assertEqual((again, dropped2), (kept, []))

    def test_duplicate_spans_prefer_matching_text(self):
        old = [line(0, 1000, "A"), {**line(1, 1000, "B")}]
        new = [{**line(0, 1000, "B")}]
        p = {"id": "x", "line": 1, "start": 1000, "end": 1900}
        kept, _ = reindex([p], old, new, "es")
        self.assertEqual(kept[0]["line"], 0)
        self.assertEqual(reindex(kept, old, new, "es")[0], kept)

    def test_cli(self):
        with TemporaryDirectory() as tmp:
            work = Path(tmp) / "work"; gen = work / "gen"; backup = Path(tmp) / "old-gen"
            (work / "srt").mkdir(parents=True); backup.mkdir()
            (work / "srt" / "S04E01.es.srt").write_text(SRT, encoding="utf-8")
            save(str(backup / "S04E01.lines.json"), OLD)
            save(str(gen / "S04E01.lines.json"), NEW)
            save(str(gen / "S04E01.phrases.json"), self.PHRASES)
            before = (gen / "S04E01.phrases.json").read_bytes()

            def run(*extra):
                r = subprocess.run([sys.executable, "-B", str(MULTI / "reindex_phrases.py"), "club-de-cuervos", str(work),
                                    "--old-gen", str(backup), *extra], capture_output=True, text=True)
                self.assertEqual(r.returncode, 0, r.stderr)
                return json.loads(r.stdout), r.stderr

            summary, err = run("--dry-run")
            self.assertEqual(summary, {"S04E01": {"kept": 2, "dropped": 2}})
            self.assertIn("s01e01-01", err)
            self.assertEqual((gen / "S04E01.phrases.json").read_bytes(), before)
            run()
            self.assertEqual([p["line"] for p in load(str(gen / "S04E01.phrases.json"))], [0, 1])
            after = (gen / "S04E01.phrases.json").read_bytes()
            self.assertEqual(run()[0], {"S04E01": {"kept": 2, "dropped": 0}})
            self.assertEqual((gen / "S04E01.phrases.json").read_bytes(), after)

            r = subprocess.run([sys.executable, "-B", str(MULTI / "reindex_phrases.py"), "club-de-cuervos", str(work),
                                "--old-gen", str(gen)], capture_output=True, text=True)
            self.assertNotEqual(r.returncode, 0)


if __name__ == "__main__":
    unittest.main()
