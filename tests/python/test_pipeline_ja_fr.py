"""Synthetic text-only inputs and a build redirected to a temporary root."""

from pathlib import Path
import sys
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "pipeline" / "multi"))
import build_show_data
import ingest_srt
from common import cfg, episodes, load, save
from extract_phrases_multi import LEVELS, system as phrase_prompt
from textmatch import matches, norm
from translate_lines import system as translation_prompt


class NewTextShows(unittest.TestCase):
    def test_japanese_ingest_and_chinese_exports(self):
        srt = (
            "1\r\n00:00:00,100 --> 00:00:01,000\r\n"
            "{\\an8}（案内役）今日は晴れです。\r\n\r\n"
            "2\r\n00:00:01,000 --> 00:00:02,000\r\n（…テーマ曲）\r\n"
        )
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            work = root / "work"
            (work / "srt").mkdir(parents=True)
            (work / "srt/S01E01.ja.srt").write_bytes(srt.encode("utf-8-sig"))
            (work / "srt/S01E02.en.srt").touch()
            show = "nigeru-wa-haji"
            self.assertEqual([row["code"] for row in episodes(show, work)], ["S01E01"])
            generated = work / "gen/S01E01.lines.json"
            save(str(generated), [{"i": 0, "start": 100, "end": 1000, "ja": "今日は晴れです。", "zh": "今天是晴天。", "vi": "Hôm nay trời nắng."}])
            kana = SimpleNamespace(convert=lambda text: [{"hira": "きょうははれです。"}])
            with patch.dict(sys.modules, {"pykakasi": SimpleNamespace(kakasi=lambda: kana)}):
                with patch.object(sys, "argv", ["ingest_srt.py", show, str(work), "--force"]):
                    ingest_srt.main()
            line, = load(generated)
            self.assertEqual(line["ja"], "今日は晴れです。")
            self.assertEqual(line["reading"], "きょうははれです。")
            self.assertEqual((line["start"], line["end"]), (100, 1000))
            line["vi"] = "Synthetic legacy translation"
            save(str(generated), [line])
            phrase_path = work / "gen/S01E01.phrases.json"
            phrase = {"code": "S01E01", "line": 0, "meaning_vi": "Legacy gloss", "explain_vi": "Legacy explanation", "usage_vi": "Legacy usage"}
            save(str(phrase_path), [phrase])
            with patch.object(build_show_data, "ROOT", str(root)), patch.object(sys, "argv", ["build_show_data.py", show, str(work)]):
                build_show_data.main()
            output = root / "site/private/shows" / show
            episode = load(output / "eps/S01E01.json")
            index = load(output / "index.json")
            self.assertEqual(episode["langs"], ["ja", "reading", "zh"])
            self.assertEqual(index["langs"], episode["langs"])
            self.assertNotIn("vi", episode["lines"][0])
            self.assertNotIn("vi", index["phrases"][0]["lineText"])
            for field in ("meaning_vi", "explain_vi", "usage_vi"):
                self.assertNotIn(field, index["phrases"][0])
            self.assertEqual(load(generated), [line])
            self.assertEqual(load(phrase_path), [phrase])
            data = (output / "srt/Nigeru_S01E01.ja-zh.srt").read_bytes()
            self.assertEqual(data.decode("utf-8-sig").splitlines()[2:4], [line["ja"], line["zh"]])
            self.assertFalse((output / "srt/Nigeru_S01E01.ja-vi.srt").exists())

    def test_french_cleanup_and_matching(self):
        self.assertEqual(ingest_srt.clean_text("[musique suspense]", "fr"), "")
        self.assertEqual(ingest_srt.clean_text("- [bruit] Ça va ?", "fr"), "- Ça va ?")
        self.assertTrue(matches(norm("Ça va", False, "fr"), norm("CA VA ?", False, "fr"), False))
        self.assertTrue(matches(norm("est-ce que", False, "fr"), norm("Qu’est-ce que c'est ?", False, "fr"), False))
        self.assertFalse(matches(norm("été", False, "fr"), norm("La fête", False, "fr"), False))
        self.assertTrue(matches(norm("そうです", False, "ja"), norm("「そう、です！」", False, "ja"), True))

    def test_translation_and_phrase_prompt_languages(self):
        ja, fr = cfg("nigeru-wa-haji"), cfg("lupin")
        for config, label in ((ja, "日语"), (fr, "法国法语")):
            self.assertEqual(config["translate"], ["zh"])
            self.assertEqual(config["explainLangs"], ["zh"])
            self.assertNotIn("vi", config["langs"])
            for field in ("meaning", "explain", "usage"):
                self.assertIn(f'"{field}_zh"', phrase_prompt(config, 15))
                self.assertNotIn(f'"{field}_vi"', phrase_prompt(config, 15))
            self.assertIn(f"把每行{label}字幕译成", translation_prompt(config, config["translate"]))
        self.assertIn('"reading"', phrase_prompt(ja, 15))
        self.assertEqual(LEVELS[ja["level"]], ["N5", "N4", "N3", "N2", "N1"])
        self.assertNotIn('"reading"', phrase_prompt(fr, 15))
        self.assertIn("CEFR", phrase_prompt(fr, 15))

    def test_existing_shows_keep_vietnamese(self):
        for show in ("dou-ting-hao", "friends", "seinfeld", "silicon-valley", "desperate-housewives"):
            config = cfg(show)
            self.assertEqual(config["translate"], [] if show == "dou-ting-hao" else ["zh", "vi"])
            self.assertEqual(config["explainLangs"], ["zh", "vi"])
            self.assertIn("vi", config["langs"])
            for field in ("meaning", "explain", "usage"):
                self.assertIn(f'"{field}_vi"', phrase_prompt(config, 15))
