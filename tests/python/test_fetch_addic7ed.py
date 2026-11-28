"""Offline fixtures for Addic7ed navigation, subtitle selection and downloads."""

from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import MagicMock, patch
from urllib.error import HTTPError

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "pipeline" / "multi"))
import fetch_addic7ed as fetcher

SEASON = "/serie/Example/1"
NAVIGATION = f"""
<select name="episode">
  <option value="{SEASON}/1/First_Episode">First Episode</option>
  <option value="2">2 - Next Episode</option>
</select>
"""
ENGLISH = '<table><tr><td>English</td><td>Completed</td><td><a href="/original/en">Original</a></td></tr></table>'
IN_PROGRESS = '<table><tr><td>French</td><td>In progress</td><td><a href="/original/draft">Original</a></td></tr></table>'
FRENCH = '''
<table>
  <tr><td>French</td></tr>
  <tr><td><table><tr><td>Completed</td>
    <td><a href="/updated/42">Updated</a><a href="/original/fr-first">Original</a></td>
  </tr></table></td></tr>
</table>
<table><tr><td>French</td><td>Completed</td><td><a href="/original/fr-second">Original</a></td></tr></table>
'''
SRT = b"1\r\n00:00:00,000 --> 00:00:01,000\r\nSynthetic fixture.\r\n"


class Addic7ed(unittest.TestCase):
    def test_language_status_and_document_order(self):
        page = fetcher.EpisodePage(f"<table><tr><td>{ENGLISH}{IN_PROGRESS}{FRENCH}</td></tr></table>", SEASON)
        self.assertEqual(page.subtitle("fr"), "/original/fr-first")
        self.assertEqual(page.subtitle("en"), "/original/en")
        self.assertIsNone(page.subtitle("ja"))
        self.assertIsNone(fetcher.EpisodePage(IN_PROGRESS, SEASON).subtitle("fr"))

    def test_fetch_is_idempotent_and_keeps_episode_titles(self):
        path1 = f"{SEASON}/1"
        path2 = f"{SEASON}/2/Next_Episode"
        fixtures = {
            path1: (NAVIGATION + ENGLISH + IN_PROGRESS + FRENCH).encode(),
            path2: FRENCH.encode(),
            "/original/fr-first": SRT,
        }
        with TemporaryDirectory() as tmp, patch.object(fetcher, "get", side_effect=lambda path, _: fixtures[path]) as get:
            work = Path(tmp)
            self.assertEqual(fetcher.fetch("Example", 1, "fr", work), 0)
            for number in (1, 2):
                self.assertEqual((work / "srt" / f"S01E{number:02}.fr.srt").read_bytes(), SRT)
            self.assertEqual(fetcher.load(work / "episodes.json"), [
                {"code": "S01E01", "title": "First Episode"},
                {"code": "S01E02", "title": "Next Episode"},
            ])
            get.assert_any_call("/original/fr-first", path2)
            get.reset_mock()
            self.assertEqual(fetcher.fetch("Example", 1, "fr", work), 0)
            get.assert_called_once_with(path1, SEASON)

    def test_request_headers_and_retry_delays(self):
        response = MagicMock()
        response.__enter__.return_value.read.return_value = SRT
        error = HTTPError(fetcher.BASE, 503, "fixture", {}, None)
        with patch.object(fetcher.time, "sleep") as sleep, patch.object(fetcher, "urlopen", side_effect=[error, response]) as open_url:
            self.assertEqual(fetcher.get("/original/fr-first", SEASON), SRT)
        request = open_url.call_args.args[0]
        self.assertEqual(request.full_url, fetcher.BASE + "/original/fr-first")
        self.assertEqual(request.get_header("Referer"), fetcher.BASE + SEASON)
        self.assertTrue(request.get_header("User-agent"))
        self.assertEqual([call.args[0] for call in sleep.call_args_list], [3, 6])
