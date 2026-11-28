"""Offline tests for TVsubtitles ingestion."""

from contextlib import redirect_stderr, redirect_stdout
from io import BytesIO, StringIO
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import Mock, patch
from urllib.error import HTTPError
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "pipeline" / "multi"))

import fetch_tvsubtitles as fetcher
from common import episodes

SEASON = """
<table>
<tr><td>1x01</td><td><b>First &amp; Second</b></td><td>
  <a href="subtitle-10.html"><img alt="fr"></a>
  <a class="flag" href="/subtitle-11.html"><img src="en.gif" alt="en"></a>
</td></tr>
<tr><td align="center"> 1x02 </td><td><b>Example Listing</b></td><td>
  <a href="episode-12-en.html"><img alt="en"></a>
</td></tr>
<tr><td>1x03</td><td><b>Missing English</b></td><td>
  <a href="subtitle-13.html"><img alt="vi"></a>
</td></tr>
</table>
"""
LISTING = """
<a href="/subtitle-14.html"><div title="Download French subtitles"></div></a>
<a href="/subtitle-15.html"><div class="subtitlen" title="Download English subtitles"></div></a>
"""
DOWNLOAD = """
<script>
var s2 = 'es/example';
var s1 = 'fil';
var s3 = '_en.zip';
document.location = s1+s2+s3;
</script>
"""


class FetchTests(unittest.TestCase):
    def test_season_rows(self):
        self.assertEqual(list(fetcher.parse_season(SEASON, "DEMO-")), [
            ({"code": "DEMO-S01E01", "title": "First & Second"}, "subtitle-11.html"),
            ({"code": "DEMO-S01E02", "title": "Example Listing"}, "episode-12-en.html"),
            ({"code": "DEMO-S01E03", "title": "Missing English"}, None),
        ])

    def test_english_listing(self):
        self.assertEqual(fetcher.parse_subtitle_listing(LISTING), "subtitle-15.html")
        self.assertIsNone(fetcher.parse_subtitle_listing("<p>No results</p>"))

    def test_archive_path(self):
        self.assertEqual(fetcher.parse_archive_path(DOWNLOAD), "files/example_en.zip")
        with self.assertRaises(ValueError):
            fetcher.parse_archive_path("<script>var s1='//elsewhere.invalid/x.zip';</script>")

    def test_fetch_rerun_and_metadata(self):
        archive = BytesIO()
        with ZipFile(archive, "w") as zipped:
            zipped.writestr("nested/example.SRT", b"fixture")
        client = Mock()
        client.html.side_effect = {
            "tvshow-89-1.html": SEASON,
            "episode-12-en.html": LISTING,
            "download-11.html": DOWNLOAD,
            "download-15.html": DOWNLOAD,
        }.__getitem__
        client.get.return_value = archive.getvalue()
        with TemporaryDirectory(dir=ROOT) as folder, patch.object(fetcher, "Client", return_value=client):
            workdir = Path(folder)
            fetcher.save(str(workdir / "episodes.json"), [{"code": "S02E01", "title": "Prior Season"}])
            with redirect_stderr(StringIO()) as log, redirect_stdout(StringIO()):
                self.assertEqual(fetcher.fetch(89, workdir, [1]), 0)
                self.assertEqual(fetcher.fetch(89, workdir, [1]), 0)
            self.assertIn("S01E03: no English subtitle", log.getvalue())
            self.assertEqual(client.get.call_count, 2)
            client.get.assert_called_with("files/example_en.zip", referer="subtitle-15.html")
            self.assertEqual((workdir / "srt/S01E02.en.srt").read_bytes(), b"fixture")
            rows = episodes("seinfeld", workdir)
            self.assertEqual([row["code"] for row in rows], ["S01E01", "S01E02", "S01E03", "S02E01"])
            self.assertIsNone(rows[2]["srt"])

    def test_retry_uses_backoff_and_user_agent(self):
        error = HTTPError(fetcher.BASE, 503, "Unavailable", None, None)
        with patch.object(fetcher.time, "sleep") as sleep, patch.object(
            fetcher, "urlopen", side_effect=[error, BytesIO(b"ok")]
        ) as request:
            self.assertEqual(fetcher.Client().get("files/example title.zip"), b"ok")
        self.assertEqual([call.args[0] for call in sleep.call_args_list], [3, 6])
        self.assertEqual(request.call_args.args[0].full_url, fetcher.BASE + "files/example%20title.zip")
        self.assertEqual(request.call_args.args[0].get_header("User-agent"), fetcher.USER_AGENT)

    def test_forbidden_request_is_not_retried(self):
        error = HTTPError(fetcher.BASE, 403, "Forbidden", None, None)
        with patch.object(fetcher.time, "sleep"), patch.object(fetcher, "urlopen", side_effect=error) as request:
            with self.assertRaises(HTTPError):
                fetcher.Client().get("example.html")
        request.assert_called_once()
