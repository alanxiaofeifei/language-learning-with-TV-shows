"""Offline tests for fetch_subdl.py: fixture API responses and a stub downloader (no network)."""

import io
import json
import os
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, urlsplit
from zipfile import ZipFile

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "pipeline" / "multi"))
import fetch_subdl
from common import cfg, load

KEY = "TESTKEY-not-a-real-key-123"

# Synthetic text written for these tests (not from any show).
SPANISH = ["¿Qué vas a hacer hoy en la casa?", "No sé, pero ya es muy tarde para eso.",
           "Mi hermano está con los niños en el parque.", "Hay que hablar con ella por la mañana."]
ITALIAN = ["Non so che cosa fare con il mio lavoro.", "Questo è il libro di mia sorella.",
           "Ho detto che sono stanco, perché non dormo.", "Anche lui è più alto di te."]


def srt(lines, cues=160):
    out = []
    for n in range(cues):
        s = n * 2
        out.append(f"{n + 1}\r\n00:{s // 60:02}:{s % 60:02},000 --> 00:{s // 60:02}:{s % 60:02},900\r\n{lines[n % len(lines)]}\r\n")
    return "\r\n".join(out).encode("utf-8-sig")


def zipped(files):
    buf = io.BytesIO()
    with ZipFile(buf, "w") as z:
        for name, data in files.items():
            z.writestr(name, data)
    return buf.getvalue()


class Stub:
    """Stand-in for http_get: serves API pages and download paths, records every call."""

    def __init__(self, api, files):
        self.api, self.files, self.calls = api, files, []

    def __call__(self, url, headers):
        self.calls.append((url, headers))
        parts = urlsplit(url)
        if parts.netloc == "api.subdl.com":
            q = parse_qs(parts.query)
            assert q["api_key"] == [KEY] and q["type"] == ["tv"] and q["unpack"] == ["1"]
            return json.dumps(self.api[int(q["season_number"][0])]).encode()
        assert parts.netloc == "dl.subdl.com" and not parts.query, url
        assert headers["User-Agent"] == "curl/8.5.0"
        if parts.path not in self.files:
            raise HTTPError(url, 404, "not found", {}, None)
        return self.files[parts.path]

    def downloaded(self):
        return [urlsplit(u).path for u, _ in self.calls if "dl.subdl.com" in u]


def quiet(*args, **kwargs):
    pass


def unpack(n, name, path, **extra):
    return {"episode": n, "language": "ES", "format": "srt", "size": 1, "hi": False, "name": name, "url": path, **extra}


class FetchSubdl(unittest.TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.work = self.tmp.name

    def tearDown(self):
        self.tmp.cleanup()

    def client(self, stub, **kw):
        return fetch_subdl.Client(KEY, get=stub, sleep=lambda s: None, **kw)

    def run_fetch(self, show, stub, **kw):
        logs = []
        log = lambda *a, **k: logs.append(" ".join(map(str, a)))
        result = fetch_subdl.fetch(show, self.work, "ES", client=self.client(stub, **kw), log=log)
        return result, logs

    def test_show_config(self):
        cuervos, flores = cfg("club-de-cuervos"), cfg("la-casa-de-las-flores")
        self.assertEqual((cuervos["subdlTmdbId"], cuervos["subdlSeasons"]), (63314, [4]))
        self.assertEqual((flores["subdlTmdbId"], flores["subdlSeasons"]), (80169, [1, 2]))
        self.assertEqual(sum(cuervos["seasonEpisodes"].values()), 12)
        self.assertEqual(sum(flores["seasonEpisodes"].values()), 22)

    def test_validation_rejects_italian_short_and_junk(self):
        self.assertEqual(fetch_subdl.validate(srt(SPANISH).decode("utf-8-sig"), "es"), (True, "ok"))
        self.assertFalse(fetch_subdl.validate(srt(ITALIAN).decode("utf-8-sig"), "es")[0])
        self.assertFalse(fetch_subdl.validate(srt(SPANISH, cues=40).decode("utf-8-sig"), "es")[0])
        self.assertFalse(fetch_subdl.validate("not a subtitle file", "es")[0])
        self.assertEqual(fetch_subdl.decode("año".encode("cp1252")), "año")

    def test_hi_names_and_paths(self):
        for name in ("Show.S01E01.hi.srt", "S01E01.spaHi.srt", "S01E01_HI.srt", "S01E01.SDH.srt"):
            self.assertTrue(fetch_subdl.is_hi(name), name)
        self.assertFalse(fetch_subdl.is_hi("Show.S01E01.WEB.srt"))
        self.assertEqual(fetch_subdl.clean_path(f"/subtitle/1-2.zip?api_key={KEY}&x=1"), "/subtitle/1-2.zip")
        self.assertEqual(fetch_subdl.clean_path("https://dl.subdl.com/subtitle/9/10"), "/subtitle/9/10")
        self.assertIsNone(fetch_subdl.clean_path("/subtitle/../../etc"))

    def test_episode_subs_then_pack_with_italian_mislabel_and_hi_skip(self):
        api = {1: {"status": True, "results": [], "subtitles": [
            # Episode-level HI subtitle for E01: must not even be downloaded.
            {"release_name": "Show.S01E01.HI", "lang": "spanish", "hi": True, "full_season": False,
             "season": 1, "episode": 1, "url": "/subtitle/10-11.zip"},
            # Episode-level E01 whose zip holds Italian text (mislabeled): rejected, falls through to the pack.
            {"release_name": "Show.S01E01.WEB", "lang": "spanish", "hi": False, "full_season": False,
             "season": 1, "episode": 1, "url": f"/subtitle/20-21.zip?api_key={KEY}"},
            {"release_name": "Show.S01.Pack", "lang": "spanish", "hi": False, "full_season": True,
             "season": 1, "episode": None, "url": f"/subtitle/30-31.zip?api_key={KEY}", "unpack_files": [
                 unpack(1, "Show.S01E01.spaHi.srt", f"/subtitle/30/1?api_key={KEY}"),
                 unpack(1, "Show.S01E01.srt", f"https://dl.subdl.com/subtitle/30/2?api_key={KEY}"),
                 unpack(2, "Show.S01E02.ass", "/subtitle/30/3", format="ass"),
                 unpack(2, "Show.S01E02.srt", "/subtitle/30/4"),
                 unpack(3, "Show.S01E03.srt", "/subtitle/30/5"),
             ]},
        ]}}
        stub = Stub(api, {
            "/subtitle/20-21.zip": zipped({"Show.S01E01.WEB.srt": srt(ITALIAN)}),
            "/subtitle/30/2": srt(SPANISH),
            "/subtitle/30/4": srt(SPANISH),
            "/subtitle/30/5": srt(SPANISH, cues=20),       # junk: too few cues
        })
        with patch.dict(cfg("la-casa-de-las-flores"), {"subdlSeasons": [1], "seasonEpisodes": {1: 4}}):
            result, logs = self.run_fetch("la-casa-de-las-flores", stub)
        srt_dir = Path(self.work) / "srt"
        self.assertEqual(sorted(p.name for p in srt_dir.iterdir()), ["S01E01.es.srt", "S01E02.es.srt"])
        self.assertEqual((srt_dir / "S01E01.es.srt").read_bytes().decode("utf-8").lstrip("﻿")[:1], "1")
        self.assertEqual(stub.downloaded(), ["/subtitle/20-21.zip", "/subtitle/30/2", "/subtitle/30/4", "/subtitle/30/5"])
        self.assertEqual(result["seasons"]["S01"], {"found": ["E01", "E02"], "missing": ["E03", "E04"]})
        manifest = load(str(Path(self.work) / "subdl-manifest.json"))
        self.assertEqual(manifest["S01E01"], {"release": "Show.S01.Pack", "file": "Show.S01E01.srt", "season_pack": True})
        self.assertIn("/subtitle/20-21.zip", load(str(Path(self.work) / "subdl-rejected.json")))
        everything = json.dumps(manifest) + json.dumps(result) + "\n".join(logs)
        everything += "".join(p.read_text(encoding="utf-8") for p in Path(self.work).glob("*.json"))
        self.assertNotIn(KEY, everything)
        self.assertNotIn("api_key", everything)

        # Second run: existing SRTs and rejected files are never downloaded again.
        stub2 = Stub(api, stub.files)
        with patch.dict(cfg("la-casa-de-las-flores"), {"subdlSeasons": [1], "seasonEpisodes": {1: 4}}):
            result2, _ = self.run_fetch("la-casa-de-las-flores", stub2)
        self.assertEqual(stub2.downloaded(), [])
        self.assertEqual(result2["seasons"]["S01"]["missing"], ["E03", "E04"])

    def test_complete_season_makes_no_requests(self):
        srt_dir = Path(self.work) / "srt"
        srt_dir.mkdir()
        for n in range(1, 13):
            (srt_dir / f"S04E{n:02}.es.srt").write_bytes(b"x")
        stub = Stub({}, {})
        result, _ = self.run_fetch("club-de-cuervos", stub)
        self.assertEqual(stub.calls, [])
        self.assertEqual(len(result["seasons"]["S04"]["found"]), 12)
        self.assertEqual(result["seasons"]["S04"]["missing"], [])

    def test_episode_zip_and_pack_zip_without_unpack_files(self):
        api = {4: {"status": True, "subtitles": [
            {"release_name": "Ep1", "hi": False, "season": 4, "episode": 1, "url": "/subtitle/1-1.zip"},
            {"release_name": "Pack", "hi": False, "full_season": True, "season": 4, "url": "/subtitle/2-2.zip"},
        ]}}
        stub = Stub(api, {
            "/subtitle/1-1.zip": zipped({"a.hi.srt": srt(SPANISH), "a.srt": srt(SPANISH)}),
            "/subtitle/2-2.zip": zipped({"X.S04E02.srt": srt(SPANISH), "X.S04E03.srt": srt(ITALIAN)}),
        })
        with patch.dict(cfg("club-de-cuervos"), {"seasonEpisodes": {4: 3}}):
            result, _ = self.run_fetch("club-de-cuervos", stub)
        self.assertEqual(result["seasons"]["S04"], {"found": ["E01", "E02"], "missing": ["E03"]})
        self.assertEqual(stub.downloaded(), ["/subtitle/1-1.zip", "/subtitle/2-2.zip"])   # pack zip cached in-run
        manifest = load(str(Path(self.work) / "subdl-manifest.json"))
        self.assertEqual(manifest["S04E01"]["file"], "a.srt")
        self.assertEqual(manifest["S04E02"], {"release": "Pack", "file": "X.S04E02.srt", "season_pack": True})
        self.assertNotIn("/subtitle/2-2.zip", load(str(Path(self.work) / "subdl-rejected.json")))

    def test_download_limit_stops_before_budget(self):
        subs = [{"release_name": f"E{n}", "season": 4, "episode": n, "url": f"/subtitle/{n}-0.zip"} for n in range(1, 13)]
        stub = Stub({4: {"status": True, "subtitles": subs}}, {f"/subtitle/{n}-0.zip": srt(SPANISH) for n in range(1, 13)})
        result, _ = self.run_fetch("club-de-cuervos", stub, max_downloads=3)
        self.assertEqual(len(stub.downloaded()), 3)
        self.assertTrue(result["limitReached"])
        self.assertEqual(result["seasons"]["S04"]["found"], ["E01", "E02", "E03"])
        self.assertEqual(fetch_subdl.MAX_DOWNLOADS, 250)

    def test_key_is_redacted_from_errors(self):
        url = f"https://api.subdl.com/api/v1/subtitles?api_key={KEY}&tmdb_id=1"

        def http_error(u, h):
            raise HTTPError(u, 403, f"Forbidden {u}", {}, None)

        def url_error(u, h):
            raise URLError(f"failed to open {u}")

        for get in (http_error, url_error):
            client = fetch_subdl.Client(KEY, get=get, sleep=lambda s: None)
            with self.assertRaises(fetch_subdl.SubdlError) as ctx:
                client.subtitles(1, 1, "ES")
            self.assertNotIn(KEY, str(ctx.exception))
            self.assertIsNone(ctx.exception.__cause__)
            self.assertTrue(ctx.exception.__suppress_context__)
        bad = fetch_subdl.Client(KEY, get=lambda u, h: json.dumps({"status": False, "error": f"bad key {KEY}"}).encode())
        with self.assertRaises(fetch_subdl.SubdlError) as ctx:
            bad.subtitles(1, 1, "ES")
        self.assertNotIn(KEY, str(ctx.exception))
        self.assertNotIn(KEY, fetch_subdl.redact(url, KEY))
        self.assertNotIn("other-key", fetch_subdl.redact(url.replace(KEY, "other-key"), KEY))
        self.assertIn("api_key=[REDACTED]", fetch_subdl.redact("x?api_key=zzz&y=1", ""))

    def test_errors_recorded_without_key_and_missing_key_rejected(self):
        def boom(u, h):
            raise URLError(f"down {u}")
        result, logs = self.run_fetch("club-de-cuervos", boom)
        self.assertTrue(result["errors"])
        self.assertNotIn(KEY, json.dumps(result) + "\n".join(logs))
        with self.assertRaises(fetch_subdl.SubdlError):
            fetch_subdl.Client("")
        with patch.dict(os.environ, {}, clear=True), patch.object(sys, "argv", ["fetch_subdl.py", "club-de-cuervos", self.work]):
            with self.assertRaises(SystemExit) as ctx:
                fetch_subdl.main()
            self.assertIn("SUBDL_API_KEY", str(ctx.exception.code))

    def test_dry_run_downloads_nothing(self):
        subs = [{"release_name": "E1", "season": 4, "episode": 1, "url": "/subtitle/1-0.zip"}]
        stub = Stub({4: {"status": True, "subtitles": subs}}, {})
        result = fetch_subdl.fetch("club-de-cuervos", self.work, "ES", dry_run=True, client=self.client(stub), log=quiet)
        self.assertEqual(stub.downloaded(), [])
        self.assertTrue(result["dryRun"])
        self.assertEqual(list((Path(self.work) / "srt").iterdir()), [])


if __name__ == "__main__":
    unittest.main()
