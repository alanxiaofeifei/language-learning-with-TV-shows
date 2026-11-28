"""Pure-function tests for pipeline/multi (no network, no LLM, no files written).
Run: python3 -B tests/python/test_pipeline_text.py  (npm test runs it via tests/pipeline-python.test.js)."""
import os, sys, unittest
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "pipeline", "multi"))
for extra in filter(None, os.environ.get("PIPELINE_TEST_PATH", "").split(os.pathsep)):
    sys.path.insert(0, extra)

from textmatch import norm, matches


class EnglishMatching(unittest.TestCase):
    def hit(self, phrase, line):
        return matches(norm(phrase, False), norm(line, False), False)

    def test_punctuation_runs_collapse(self):
        self.assertEqual(norm("Wait -- what?", False), "wait what")
        self.assertEqual(norm("Wait... what?", False), "wait what")
        self.assertTrue(self.hit("Wait, what", "Wait -- what?"))
        self.assertTrue(self.hit("Wait, what", "Wait... what?!"))

    def test_word_boundaries(self):
        self.assertFalse(self.hit("go", "That was ages ago."))
        self.assertFalse(self.hit("on", "Ross is gone."))
        self.assertFalse(self.hit("you", "You're kidding."))
        self.assertTrue(self.hit("you", "Are you kidding?"))
        self.assertTrue(self.hit("hang out", "We could hang out later."))
        self.assertFalse(self.hit("hang out", "We could hang outside."))
        self.assertTrue(self.hit("Oh my God", "Oh. My. God!"))

    def test_apostrophes(self):
        self.assertEqual(norm("Don’t", False), "don't")
        self.assertTrue(self.hit("don't", "I don’t know."))
        self.assertTrue(self.hit("we were on a break", "WE WERE ON A BREAK!"))

    def test_empty(self):
        self.assertFalse(matches("", "anything", False))
        self.assertFalse(matches("x", "", False))


class ChineseMatching(unittest.TestCase):
    def test_substring_ignores_punctuation(self):
        self.assertTrue(matches(norm("说到底", True), norm("说到底，这是你家的事。", True), True))
        self.assertTrue(matches(norm("你，别管", True), norm("你别管！", True), True))
        self.assertFalse(matches(norm("不至于", True), norm("至于吗", True), True))


class SrtClean(unittest.TestCase):
    def test_hash(self):
        from ingest_srt import clean_text
        self.assertEqual(clean_text("We're #1!"), "We're #1!")
        self.assertEqual(clean_text("Apt. #20"), "Apt. #20")
        self.assertEqual(clean_text("# Smelly cat, smelly cat #"), "Smelly cat, smelly cat")
        self.assertEqual(clean_text("#Smelly cat#"), "Smelly cat")
        self.assertEqual(clean_text("## la la ##"), "la la")
        self.assertEqual(clean_text("<i>♪ Oh</i> #"), "Oh")
        self.assertEqual(clean_text("#"), "")


class ClipSpan(unittest.TestCase):
    def test_span(self):
        from cut_clips_cues import span, CAP, MIN_DUR
        s, d = span(10_000, 12_000)
        self.assertAlmostEqual(s, 9.75); self.assertAlmostEqual(d, 2.65)
        self.assertEqual(span(10_000, 30_000)[1], CAP)
        self.assertGreaterEqual(span(10_000, 9_000)[1], MIN_DUR)   # end before start
        self.assertGreaterEqual(span(10_000, None)[1], MIN_DUR)
        self.assertEqual(span(100, 200)[0], 0.0)


class YoutubeAlign(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try:
            import pypinyin  # noqa: F401
        except ImportError:
            raise unittest.SkipTest("pypinyin not installed (use /home/box/venvs/ytdlp/bin/python)")
        import ingest_youtube_json3 as m
        cls.m = m

    def cue(self, s, e, text): return {"start": s, "end": e, "text": text}

    def test_vi_exact_then_overlap_and_empty_cues(self):
        zh = [self.cue(0, 1000, "你好"), self.cue(1000, 2000, ""), self.cue(2000, 3000, "再见")]
        vi = [self.cue(0, 1000, "Xin chào"), self.cue(2001, 3000, "Tạm biệt"), self.cue(9000, 9500, "Chỉ có vi")]
        en = [self.cue(1000, 1900, "Hi"), self.cue(2100, 2900, "Bye")]
        out = self.m.align(zh, vi, en)
        # The empty zh cue is gone, so "Hi" (overlapping only it) becomes its own en-only line.
        self.assertEqual([(L["zh"], L["vi"], L["en"]) for L in out], [
            ("你好", "Xin chào", ""),
            ("", "", "Hi"),
            ("再见", "Tạm biệt", "Bye"),          # vi off by 1 ms: attached by overlap, not dropped
            ("", "Chỉ có vi", ""),                # vi with no zh overlap: kept as its own line
        ])
        self.assertEqual([L["i"] for L in out], [0, 1, 2, 3])
        self.assertEqual(set(out[0]), {"i", "start", "end", "zh", "py", "vi", "en"})


if __name__ == "__main__":
    unittest.main()
