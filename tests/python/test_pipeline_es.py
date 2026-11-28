"""Spanish (Mexican / Latin-American) text-only shows: cleanup, matching, prompts and build exports."""

from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "pipeline" / "multi"))
import build_show_data
import extract_phrases_multi
import ingest_srt
from common import cfg, episodes, load, save
from extract_phrases_multi import LEVELS, system as phrase_prompt
from textmatch import matches, norm
from translate_lines import system as translation_prompt

SHOWS = ("club-de-cuervos", "la-casa-de-las-flores")


def es(s):
    return norm(s, False, "es")


class SpanishShows(unittest.TestCase):
    def test_config(self):
        for show in SHOWS:
            c = cfg(show)
            self.assertEqual((c["source"], c["target"], c["level"]), ("text-only", "es", "CEFR"))
            self.assertEqual(c["langs"], ["es", "zh"])
            self.assertEqual(c["translate"], ["zh"])
            self.assertEqual(c["explainLangs"], ["zh"])
            self.assertIn("es", c["title"])
            self.assertIn("güey", c["audience"])
        self.assertEqual(cfg("club-de-cuervos")["srtPrefix"], "ClubDeCuervos")
        self.assertEqual(cfg("la-casa-de-las-flores")["srtPrefix"], "LaCasaDeLasFlores")

    def test_cleanup(self):
        clean = lambda s: ingest_srt.clean_text(s, "es")
        self.assertEqual(clean("[música]"), "")
        self.assertEqual(clean("(risas)"), "")
        self.assertEqual(clean("- [suspira]"), "")
        self.assertEqual(clean("♪ La la la ♪"), "")
        self.assertEqual(clean("- (risas) ¿Qué onda?"), "- ¿Qué onda?")
        self.assertEqual(clean("MARÍA: ¡Ahorita voy!"), "¡Ahorita voy!")
        self.assertEqual(clean("- DON PEPE: Sí, claro."), "- Sí, claro.")
        self.assertEqual(clean("<i>¿Neta?</i>"), "¿Neta?")
        self.assertEqual(clean("Son las 3: ya vámonos."), "Son las 3: ya vámonos.")
        self.assertEqual(clean("OK, ¿y tú?"), "OK, ¿y tú?")
        # French behaviour is unchanged: parentheses are kept there.
        self.assertEqual(ingest_srt.clean_text("(rires) Bon.", "fr"), "(rires) Bon.")

    def test_matching_keeps_n_tilde(self):
        self.assertTrue(matches(es("qué onda"), es("¿QUE ONDA, güey?"), False))
        self.assertTrue(matches(es("no manches"), es("¡No manches!"), False))
        self.assertTrue(matches(es("guey"), es("¿Qué onda, güey?"), False))
        self.assertTrue(matches(es("año"), es("Feliz AÑO nuevo"), False))
        self.assertFalse(matches(es("año"), es("el ano"), False))
        self.assertFalse(matches(es("ano"), es("Feliz año"), False))
        self.assertFalse(matches(es("mano"), es("hermano"), False))
        self.assertEqual(es("«¿Señor?»"), "señor")

    def test_prompts(self):
        for show in SHOWS:
            c = cfg(show)
            self.assertIn("把每行拉美西班牙语（墨西哥）字幕译成", translation_prompt(c, c["translate"]))
            prompt = phrase_prompt(c, 15)
            self.assertIn("CEFR", prompt)
            self.assertIn("西班牙语", prompt)
            self.assertNotIn('"reading"', prompt)
            for field in ("meaning", "explain", "usage"):
                self.assertIn(f'"{field}_zh"', prompt)
                self.assertNotIn(f'"{field}_vi"', prompt)
        self.assertEqual(LEVELS["CEFR"], ["A1", "A2", "B1", "B2", "C1", "C2"])

    def test_phrase_extraction_uses_whole_words(self):
        lines = [{"i": 0, "start": 0, "end": 1000, "es": "Mi hermano llegó ahorita."}]
        phrases = [{"idx": 0, "phrase": "mano", "level": "A1"}, {"idx": 0, "phrase": "ahorita", "level": "a2", "meaning_zh": "马上"}]
        with TemporaryDirectory() as tmp:
            gen = Path(tmp) / "gen"
            save(str(gen / "S01E01.lines.json"), lines)
            with patch.object(sys, "argv", ["extract_phrases_multi.py", "la-casa-de-las-flores", tmp]), \
                 patch.object(extract_phrases_multi, "episodes", return_value=[{"n": 1, "code": "S01E01"}]), \
                 patch.object(extract_phrases_multi, "chat_json", return_value={"phrases": phrases}):
                extract_phrases_multi.main()
            card, = load(str(gen / "S01E01.phrases.json"))
        self.assertEqual((card["phrase"], card["level"], card["meaning_zh"]), ("ahorita", "A2", "马上"))
        self.assertNotIn("reading", card)
        self.assertNotIn("explain_vi", card)

    def test_ingest_and_build_exports_es_zh_only(self):
        srt = ("1\r\n00:00:01,000 --> 00:00:02,500\r\n[música]\r\n\r\n"
               "2\r\n00:00:03,000 --> 00:00:04,000\r\nPACO: ¿Qué onda?\r\n- (risas) ¡Órale!\r\n")
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            work = root / "work"
            (work / "srt").mkdir(parents=True)
            (work / "srt/S04E01.es.srt").write_bytes(srt.encode("cp1252"))
            (work / "srt/S04E02.en.srt").touch()
            show = "club-de-cuervos"
            self.assertEqual([e["code"] for e in episodes(show, str(work))], ["S04E01"])
            with patch.object(sys, "argv", ["ingest_srt.py", show, str(work)]):
                ingest_srt.main()
            generated = work / "gen/S04E01.lines.json"
            line, = load(str(generated))
            self.assertEqual(line["es"], "¿Qué onda? - ¡Órale!")
            self.assertEqual((line["start"], line["end"]), (3000, 4000))
            line.update(zh="怎么样？哇！", vi="Synthetic legacy translation")
            save(str(generated), [line])
            save(str(work / "gen/S04E01.phrases.json"), [{"code": "S04E01", "line": 0, "phrase": "qué onda",
                                                         "meaning_zh": "怎么样", "meaning_vi": "legacy", "explain_vi": "legacy"}])
            with patch.object(build_show_data, "ROOT", str(root)), patch.object(sys, "argv", ["build_show_data.py", show, str(work)]):
                build_show_data.main()
            out = root / "site/private/shows" / show
            episode, index = load(str(out / "eps/S04E01.json")), load(str(out / "index.json"))
            self.assertEqual(episode["langs"], ["es", "zh"])
            self.assertNotIn("vi", episode["lines"][0])
            self.assertNotIn("meaning_vi", index["phrases"][0])
            self.assertNotIn("explain_vi", index["phrases"][0])
            self.assertEqual(index["target"], "es")
            data = (out / "srt/ClubDeCuervos_S04E01.es-zh.srt").read_bytes().decode("utf-8-sig")
            self.assertEqual(data.splitlines()[2:4], [line["es"], line["zh"]])
            self.assertEqual(sorted(p.name for p in (out / "srt").iterdir()), ["ClubDeCuervos_S04E01.es-zh.srt"])

    def test_episodes_ignore_srts_outside_configured_seasons(self):
        """Leftover SRTs (another season, E13 of a 12-episode season) never shift the public numbering."""
        with TemporaryDirectory() as tmp:
            work = Path(tmp)
            (work / "srt").mkdir()
            for code in ("S01E01", "S04E00", "S04E01", "S04E12", "S04E13"):
                (work / f"srt/{code}.es.srt").touch()
            save(str(work / "episodes.json"), [{"code": "S04E14", "title": "x"}, {"code": "S04E12", "title": "Final"}])
            eps = episodes("club-de-cuervos", str(work))
            self.assertEqual([(e["n"], e["code"]) for e in eps], [(1, "S04E01"), (2, "S04E12")])
            self.assertEqual(eps[1]["title"], "Final")
            with patch.dict(cfg("club-de-cuervos"), {"seasonEpisodes": {"4": 13}}):   # JSON-style string keys
                self.assertEqual([e["code"] for e in episodes("club-de-cuervos", str(work))],
                                 ["S04E01", "S04E12", "S04E13"])
            with patch.dict(cfg("club-de-cuervos"), {"seasonEpisodes": {}}):          # no count: every SRT
                self.assertEqual(len(episodes("club-de-cuervos", str(work))), 5)


if __name__ == "__main__":
    unittest.main()
