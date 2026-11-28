"""Offline tests for fetch_subdl.py: fixture API responses and a stub downloader (no network)."""

import contextlib
import io
import json
import os
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import MagicMock, patch
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, urlsplit
from zipfile import ZIP_BZIP2, ZipFile, ZipInfo

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "pipeline" / "multi"))
import fetch_subdl
from common import cfg, load

KEY = "TESTKEY-not-a-real-key-123"
AT = "@"   # URL userinfo separator, kept apart so the repo's email scan does not flag the test URLs

# Synthetic text written for these tests (not from any show).
SPANISH = ["¿Qué vas a hacer hoy en la casa?", "No sé, pero ya es muy tarde para eso.",
           "Mi hermano está con los niños en el parque.", "Hay que hablar con ella por la mañana."]
ITALIAN = ["Non so che cosa fare con il mio lavoro.", "Questo è il libro di mia sorella.",
           "Ho detto che sono stanco, perché non dormo.", "Anche lui è più alto di te."]


def srt(lines, cues=160, nl="\r\n"):
    out = []
    for n in range(cues):
        s = n * 2
        out.append(f"{n + 1}{nl}00:{s // 60:02}:{s % 60:02},000 --> 00:{s // 60:02}:{s % 60:02},900{nl}{lines[n % len(lines)]}{nl}")
    return nl.join(out).encode("utf-8-sig")


def corrupt(data, needle=b"casa"):
    """Flip stored bytes of the first zip member that contains `needle` so reading it fails its CRC check."""
    i = data.index(needle)
    return data[:i] + b"cosa" + data[i + 4:]


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
        rejected = load(str(Path(self.work) / "subdl-rejected.json"))
        # The Italian member is rejected on its content; the zip itself only for E01 (it is not an E01-only fact).
        self.assertIn(fetch_subdl.file_id("ES", "/subtitle/20-21.zip", "Show.S01E01.WEB.srt"), rejected)
        self.assertIn(fetch_subdl.exhausted_id("ES", "/subtitle/20-21.zip", 1, 1), rejected)
        self.assertNotIn(fetch_subdl.file_id("ES", "/subtitle/20-21.zip"), rejected)
        self.assertTrue(all(r.startswith("sha256:") for r in rejected))
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
        rejected = load(str(Path(self.work) / "subdl-rejected.json"))
        self.assertNotIn(fetch_subdl.file_id("ES", "/subtitle/2-2.zip"), rejected)
        self.assertIn(fetch_subdl.exhausted_id("ES", "/subtitle/2-2.zip", 4, 3), rejected)
        self.assertNotIn(fetch_subdl.exhausted_id("ES", "/subtitle/2-2.zip", 4, 2), rejected)

        # Second run: the pack was already inspected for E03, so it is not downloaded again.
        stub2 = Stub(api, stub.files)
        with patch.dict(cfg("club-de-cuervos"), {"seasonEpisodes": {4: 3}}):
            result2, _ = self.run_fetch("club-de-cuervos", stub2)
        self.assertEqual(stub2.downloaded(), [])
        self.assertEqual(result2["seasons"]["S04"]["missing"], ["E03"])

    def test_download_limit_stops_before_budget(self):
        subs = [{"release_name": f"E{n}", "season": 4, "episode": n, "url": f"/subtitle/{n}-0.zip"} for n in range(1, 13)]
        stub = Stub({4: {"status": True, "subtitles": subs}},
                    {f"/subtitle/{n}-0.zip": zipped({f"S04E{n:02}.srt": srt(SPANISH)}) for n in range(1, 13)})
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

    def test_upstream_names_are_sanitized_everywhere(self):
        """A credential echoed in upstream release/file/member names never reaches logs, manifest or caches."""
        evil = f"{KEY}.api_key=zzz"
        api = {1: {"status": True, "subtitles": [
            {"release_name": f"Rel.{evil}", "hi": False, "season": 1, "episode": 1, "url": "/subtitle/1-1.zip"},
            {"release_name": f"Pack.{evil}", "hi": False, "full_season": True, "season": 1, "url": "/subtitle/9-9.zip",
             "unpack_files": [unpack(2, f"Show.S01E02.{evil}.srt", "/subtitle/9/2"),
                              unpack(3, f"Show.S01E03.{evil}.srt", "/subtitle/9/3")]},
        ]}}
        e01 = zipped({f"Show.S01E01.{evil}.srt": srt(SPANISH), f"Show.S01E01.{evil}.v2.srt": srt(SPANISH)})
        stub = Stub(api, {"/subtitle/1-1.zip": corrupt(e01), "/subtitle/9/2": srt(ITALIAN), "/subtitle/9/3": srt(SPANISH)})
        logs = []
        log = lambda *a, **k: logs.append(" ".join(map(str, a)))
        with patch.dict(cfg("la-casa-de-las-flores"), {"subdlSeasons": [1], "seasonEpisodes": {1: 3}}):
            fetch_subdl.fetch("la-casa-de-las-flores", self.work, "ES", dry_run=True, client=self.client(stub), log=log)
            result = fetch_subdl.fetch("la-casa-de-las-flores", self.work, "ES", client=self.client(stub), log=log)
        self.assertEqual(result["seasons"]["S01"], {"found": ["E01", "E03"], "missing": ["E02"]})
        joined = "\n".join(logs)
        self.assertIn("would try", joined)                       # dry-run lines
        self.assertIn("unreadable archive member", joined)       # corrupt member, translated
        self.assertIn("S01E02: skip Show.S01E02.[REDACTED]", joined)   # rejected Italian file
        manifest = load(str(Path(self.work) / "subdl-manifest.json"))
        self.assertEqual(manifest["S01E01"]["file"], "Show.S01E01.[REDACTED].api_key_[REDACTED]")
        self.assertEqual(manifest["S01E01"]["release"], "Rel.[REDACTED].api_key_[REDACTED]")
        self.assertEqual(fetch_subdl.safe_name(f"a/b\\c\n{KEY}<x>.srt", KEY), "a_b_c_[REDACTED]_x_.srt")
        rejected = load(str(Path(self.work) / "subdl-rejected.json"))
        self.assertTrue(rejected and all(r.startswith("sha256:") for r in rejected))
        everything = joined + json.dumps(result) + "".join(p.read_text(encoding="utf-8") for p in Path(self.work).glob("*.json"))
        for secret in (KEY, "zzz", "Bad CRC", "Show.S01E01.TESTKEY"):
            self.assertNotIn(secret, everything)

    def test_budgets_are_charged_before_every_attempt(self):
        def unavailable(u, h):
            raise HTTPError(u, 503, "unavailable", {}, None)
        calls = []
        get = lambda u, h: (calls.append(u), unavailable(u, h))
        client = fetch_subdl.Client(KEY, get=get, sleep=lambda s: None, max_downloads=1, max_requests=2)
        with self.assertRaises(fetch_subdl.DownloadLimit):
            client.download("/subtitle/1-1.zip")
        self.assertEqual((len(calls), client.downloads), (1, 1))
        with self.assertRaises(fetch_subdl.RequestLimit):
            client.subtitles(1, 1, "ES")
        self.assertEqual((len(calls), client.requests), (3, 2))
        # Retries count too: a budget of 3 allows exactly one retried download (3 GETs), then nothing more.
        calls.clear()
        client = fetch_subdl.Client(KEY, get=get, sleep=lambda s: None, max_downloads=3)
        with self.assertRaises(fetch_subdl.SubdlError):
            client.download("/subtitle/1-1.zip")
        with self.assertRaises(fetch_subdl.DownloadLimit):
            client.download("/subtitle/2-2.zip")
        self.assertEqual((len(calls), client.downloads), (3, 3))

    def test_missing_or_unreadable_preferred_candidate_falls_through(self):
        def ep(n, url, rel="x"):
            return {"release_name": rel, "hi": False, "season": 4, "episode": n, "url": url}
        api = {4: {"status": True, "subtitles": [
            ep(1, "/subtitle/1-1.zip"), ep(1, "/subtitle/1-2.zip"),       # 404, then valid
            ep(2, "/subtitle/2-1.zip"), ep(2, "/subtitle/2-2.zip"),       # corrupt member, then valid
            ep(3, "/subtitle/3-1.zip"), ep(3, "/subtitle/3-2.zip"),       # not a zip at all, then valid
        ]}}
        good = lambda n: zipped({f"S04E{n:02}.srt": srt(SPANISH)})
        stub = Stub(api, {"/subtitle/1-2.zip": good(1), "/subtitle/2-1.zip": corrupt(good(2)), "/subtitle/2-2.zip": good(2),
                          "/subtitle/3-1.zip": b"PK\x03\x04 truncated", "/subtitle/3-2.zip": good(3)})
        with patch.dict(cfg("club-de-cuervos"), {"seasonEpisodes": {4: 3}}):
            result, logs = self.run_fetch("club-de-cuervos", stub)
        self.assertEqual(result["seasons"]["S04"], {"found": ["E01", "E02", "E03"], "missing": []})
        self.assertEqual(result["errors"], [])
        self.assertFalse(result["limitReached"])
        rejected = load(str(Path(self.work) / "subdl-rejected.json"))
        for path in ("/subtitle/1-1.zip", "/subtitle/3-1.zip"):
            self.assertIn(fetch_subdl.file_id("ES", path), rejected)
        self.assertIn(fetch_subdl.file_id("ES", "/subtitle/2-1.zip", "S04E02.srt"), rejected)

    def test_quota_failure_stops_the_run(self):
        subs = [{"release_name": f"E{n}", "season": 4, "episode": n, "url": f"/subtitle/{n}-0.zip"} for n in range(1, 13)]
        api = {4: {"status": True, "subtitles": subs}}

        def get(u, h):
            if "api.subdl.com" in u:
                return Stub(api, {})(u, h)
            calls.append(u)
            raise HTTPError(u, 429, "too many", {}, None)
        calls = []
        result, _ = self.run_fetch("club-de-cuervos", get)
        self.assertEqual(len(calls), 1)
        self.assertTrue(result["limitReached"])
        self.assertEqual(len(result["seasons"]["S04"]["missing"]), 12)
        self.assertEqual(load(str(Path(self.work) / "subdl-rejected.json")), [])   # not the file's fault

    def test_pack_without_member_for_episode_is_exhausted_not_redownloaded(self):
        api = {4: {"status": True, "subtitles": [
            {"release_name": "Pack", "hi": False, "full_season": True, "season": 4, "url": "/subtitle/2-2.zip"}]}}
        files = {"/subtitle/2-2.zip": zipped({"X.S04E01.srt": srt(SPANISH), "notes.srt": srt(SPANISH)})}
        stub = Stub(api, files)
        with patch.dict(cfg("club-de-cuervos"), {"seasonEpisodes": {4: 2}}):
            result, _ = self.run_fetch("club-de-cuervos", stub)
            self.assertEqual(result["seasons"]["S04"], {"found": ["E01"], "missing": ["E02"]})
            self.assertEqual(stub.downloaded(), ["/subtitle/2-2.zip"])
            stub2 = Stub(api, files)
            self.run_fetch("club-de-cuervos", stub2)
        self.assertEqual(stub2.downloaded(), [])
        self.assertIn(fetch_subdl.exhausted_id("ES", "/subtitle/2-2.zip", 4, 2),
                      load(str(Path(self.work) / "subdl-rejected.json")))

    def test_raw_payload_needs_metadata_for_that_episode(self):
        api = {4: {"status": True, "subtitles": [
            # Undifferentiated season pack whose URL serves one raw SRT: never accepted for any episode.
            {"release_name": "Pack", "hi": False, "full_season": True, "season": 4, "url": "/subtitle/9-9.zip"},
            # Episode-level .zip URL serving a raw body: no metadata names an .srt, so rejected.
            {"release_name": "E1", "hi": False, "season": 4, "episode": 1, "url": "/subtitle/1-1.zip"},
            # Episode-level URL that is itself a non-HI .srt: accepted.
            {"release_name": "E2", "hi": False, "season": 4, "episode": 2, "url": "/subtitle/2-2/S04E02.srt"},
        ]}}
        stub = Stub(api, {"/subtitle/9-9.zip": srt(SPANISH), "/subtitle/1-1.zip": srt(SPANISH),
                          "/subtitle/2-2/S04E02.srt": srt(SPANISH)})
        with patch.dict(cfg("club-de-cuervos"), {"seasonEpisodes": {4: 3}}):
            result, _ = self.run_fetch("club-de-cuervos", stub)
        self.assertEqual(result["seasons"]["S04"], {"found": ["E02"], "missing": ["E01", "E03"]})
        self.assertEqual(stub.downloaded().count("/subtitle/9-9.zip"), 1)
        manifest = load(str(Path(self.work) / "subdl-manifest.json"))
        self.assertEqual(manifest["S04E02"]["file"], "S04E02.srt")

    def test_size_caps_and_bounded_pack_cache(self):
        big = srt(SPANISH, cues=400)
        api = {4: {"status": True, "subtitles": [
            {"release_name": "a", "season": 4, "episode": 1, "url": "/subtitle/1-1.zip"},   # body over the cap
            {"release_name": "b", "season": 4, "episode": 1, "url": "/subtitle/1-2.zip"},   # member over the cap
            {"release_name": "c", "season": 4, "episode": 1, "url": "/subtitle/1-3.zip"},
        ]}}
        stub = Stub(api, {"/subtitle/1-1.zip": b"PK" + b"\0" * 200_000, "/subtitle/1-2.zip": zipped({"a.srt": big}),
                          "/subtitle/1-3.zip": zipped({"c.srt": srt(SPANISH)})})
        with patch.object(fetch_subdl, "MAX_MEMBER_BYTES", len(big) - 1), \
                patch.dict(cfg("club-de-cuervos"), {"seasonEpisodes": {4: 1}}):
            result, logs = self.run_fetch("club-de-cuervos", stub, max_bytes=150_000)
        self.assertEqual(result["seasons"]["S04"]["found"], ["E01"])
        self.assertEqual(load(str(Path(self.work) / "subdl-manifest.json"))["S04E01"]["file"], "c.srt")
        self.assertTrue(any("response over" in line for line in logs))
        self.assertTrue(any("over " in line and "a.srt" in line for line in logs))

        client = self.client(lambda u, h: b"PK" + b"\0" * 10)
        with patch.object(fetch_subdl, "PACK_CACHE_ITEMS", 2):
            for n in range(3):
                client.download(f"/subtitle/{n}.zip", keep=True)
            client.download("/subtitle/x.zip")
        self.assertEqual(list(client.cache), ["/subtitle/1.zip", "/subtitle/2.zip"])

        class Response:
            def __init__(self, body, length=None):
                self.body, self.headers = body, ({"Content-Length": str(length)} if length else {})
            def read(self, n=-1):
                return self.body[:n] if n >= 0 else self.body
            def __enter__(self):
                return self
            def __exit__(self, *a):
                return False
        for resp in (Response(b"x" * 10, length=10**9), Response(b"x" * 101)):
            with patch.object(fetch_subdl, "urlopen", lambda req, timeout: resp):
                with self.assertRaises(fetch_subdl.TooLarge):
                    fetch_subdl.http_get("https://dl.subdl.com/x", {}, limit=100)
        with patch.object(fetch_subdl, "urlopen", lambda req, timeout: Response(b"x" * 100)):
            self.assertEqual(len(fetch_subdl.http_get("https://dl.subdl.com/x", {}, limit=100)), 100)

    def test_configured_episode_count_is_authoritative(self):
        subs = [{"release_name": f"E{n}", "season": 4, "episode": n, "url": f"/subtitle/{n}-0.zip"} for n in (1, 13)]
        subs.append({"release_name": "Pack", "full_season": True, "season": 4, "url": "/subtitle/p.zip",
                     "unpack_files": [unpack(14, "X.S04E14.srt", "/subtitle/p/14")]})
        files = {f"/subtitle/{n}-0.zip": zipped({f"S04E{n:02}.srt": srt(SPANISH)}) for n in (1, 13)}
        stub = Stub({4: {"status": True, "subtitles": subs}}, files)
        result, _ = self.run_fetch("club-de-cuervos", stub)          # seasonEpisodes {4: 12}
        season = result["seasons"]["S04"]
        self.assertEqual(season["found"], ["E01"])
        self.assertEqual(season["missing"], [f"E{n:02}" for n in range(2, 13)])
        self.assertEqual(stub.downloaded(), ["/subtitle/1-0.zip"])
        self.assertFalse((Path(self.work) / "srt" / "S04E13.es.srt").exists())

        # Without a configured count, upstream metadata decides.
        stub = Stub({4: {"status": True, "subtitles": subs}}, files)
        with patch.dict(cfg("club-de-cuervos"), {"seasonEpisodes": {}}):
            result, _ = self.run_fetch("club-de-cuervos", stub)
        self.assertEqual(result["seasons"]["S04"]["found"], ["E01", "E13"])

    def test_unsupported_lang_rejected_at_argument_parsing(self):
        for lang in ("es-la", "IT", "en"):
            with patch.dict(os.environ, {"SUBDL_API_KEY": KEY}), contextlib.redirect_stderr(io.StringIO()) as err, \
                    patch.object(sys, "argv", ["fetch_subdl.py", "club-de-cuervos", self.work, "--lang", lang]):
                with self.assertRaises(SystemExit) as ctx:
                    fetch_subdl.main()
            self.assertEqual(ctx.exception.code, 2, lang)
            self.assertIn("--lang", err.getvalue())
            self.assertNotIn(KEY, err.getvalue())
        with self.assertRaises(fetch_subdl.SubdlError):
            fetch_subdl.fetch("club-de-cuervos", self.work, "ES-LA", client=self.client(Stub({}, {})), log=quiet)
        self.assertFalse(fetch_subdl.validate(srt(ITALIAN).decode("utf-8-sig"), "es-la")[0])

    def test_cr_only_file_is_normalised_and_ingests(self):
        import ingest_srt
        api = {4: {"status": True, "subtitles": [
            {"release_name": "E1", "season": 4, "episode": 1, "url": "/subtitle/1-1.zip"}]}}
        stub = Stub(api, {"/subtitle/1-1.zip": zipped({"S04E01.srt": srt(SPANISH, nl="\r")})})
        with patch.dict(cfg("club-de-cuervos"), {"seasonEpisodes": {4: 1}}):
            result, _ = self.run_fetch("club-de-cuervos", stub)
        self.assertEqual(result["seasons"]["S04"]["found"], ["E01"])
        path = Path(self.work) / "srt" / "S04E01.es.srt"
        self.assertNotIn(b"\r", path.read_bytes())
        cues = ingest_srt.read_srt(str(path), "es")
        self.assertEqual(len(cues), 160)
        self.assertEqual(cues[0]["es"], SPANISH[0])
        raw = Path(self.work) / "cr.srt"
        raw.write_bytes(srt(SPANISH, nl="\r"))
        self.assertEqual(len(ingest_srt.read_srt(str(raw), "es")), 160)   # ingest also accepts CR-only input

    def test_unparseable_url_is_skipped_without_echoing_it(self):
        bad = f"https://{KEY}\u2100x/subtitle/S04E01.srt"     # urlsplit raises ValueError quoting the netloc
        with self.assertRaises(ValueError):
            urlsplit(bad)
        self.assertIsNone(fetch_subdl.clean_path(bad))
        self.assertIsNone(fetch_subdl.clean_path("http://[::1/subtitle/x.zip"))
        api = {4: {"status": True, "subtitles": [
            {"release_name": "Bad", "season": 4, "episode": 1, "url": bad},
            {"release_name": "Pack", "full_season": True, "season": 4, "url": "/subtitle/p.zip",
             "unpack_files": [unpack(1, "S04E01.srt", bad)]},
            {"release_name": "Good", "season": 4, "episode": 1, "url": "/subtitle/1-1.zip"},
        ]}}
        stub = Stub(api, {"/subtitle/1-1.zip": zipped({"S04E01.srt": srt(SPANISH)})})
        with patch.dict(cfg("club-de-cuervos"), {"seasonEpisodes": {4: 1}}), \
                contextlib.redirect_stderr(io.StringIO()) as err:
            result, logs = self.run_fetch("club-de-cuervos", stub)
        self.assertEqual(result["seasons"]["S04"]["found"], ["E01"])
        self.assertEqual(stub.downloaded(), ["/subtitle/1-1.zip"])
        everything = err.getvalue() + "\n".join(logs) + json.dumps(result)
        everything += "".join(p.read_text(encoding="utf-8") for p in Path(self.work).glob("*.json"))
        self.assertNotIn(KEY, everything)

    def test_legacy_rejected_cache_is_migrated_on_load(self):
        srt_dir = Path(self.work) / "srt"
        srt_dir.mkdir()
        for n in range(1, 13):
            (srt_dir / f"S04E{n:02}.es.srt").write_bytes(b"x")
        path = Path(self.work) / "subdl-rejected.json"
        legacy = ["/subtitle/1-1.zip", "/subtitle/2-2.zip!Show.S04E02.srt", fetch_subdl.file_id("ES", "/x")]
        path.write_text(json.dumps(legacy), encoding="utf-8")
        stub = Stub({}, {})
        self.run_fetch("club-de-cuervos", stub)                  # complete season: no request, still migrated
        self.assertEqual(stub.calls, [])
        migrated = load(str(path))
        self.assertEqual(migrated, sorted({fetch_subdl.file_id("ES", "/subtitle/1-1.zip"),
                                           fetch_subdl.file_id("ES", "/subtitle/2-2.zip", "Show.S04E02.srt"),
                                           fetch_subdl.file_id("ES", "/x")}))
        self.assertNotIn("/subtitle", path.read_text(encoding="utf-8"))
        self.assertEqual(sorted(p.name for p in Path(self.work).iterdir()), ["srt", "subdl-rejected.json"])
        mtime = path.stat().st_mtime_ns
        with patch.object(fetch_subdl, "save") as save:          # already migrated: not rewritten
            fetch_subdl.load_rejected(str(path), "ES")
        save.assert_not_called()
        self.assertEqual(path.stat().st_mtime_ns, mtime)
        with patch.object(fetch_subdl, "save") as save:          # no cache yet: nothing written
            self.assertEqual(fetch_subdl.load_rejected(str(Path(self.work) / "none.json"), "ES"), set())
        save.assert_not_called()

    def test_redirects_are_charged_capped_and_restricted_to_subdl(self):
        body = zipped({"S04E01.srt": srt(SPANISH)})

        def server(routes):
            calls = []
            def get(url, headers):
                calls.append(url)
                hop = routes[url]
                if isinstance(hop, bytes):
                    return hop
                raise fetch_subdl.Redirect(302, hop)
            return get, calls

        # Absolute and relative hops on *.subdl.com are followed; every hop is charged.
        get, calls = server({"https://dl.subdl.com/a.zip": "https://cdn.subdl.com/b.zip",
                             "https://cdn.subdl.com/b.zip": "/c.zip", "https://cdn.subdl.com/c.zip": body})
        client = self.client(get)
        self.assertEqual(client.download("/a.zip"), body)
        self.assertEqual((len(calls), client.downloads), (3, 3))

        # A hop past the budget stops the run.
        client = self.client(get, max_downloads=2)
        calls.clear()
        with self.assertRaises(fetch_subdl.DownloadLimit):
            client.download("/a.zip")
        self.assertEqual(len(calls), 2)

        # API redirects are charged to the request budget.
        api = json.dumps({"status": True, "subtitles": []}).encode()
        client = self.client(lambda u, h: api if "api2" in u else (_ for _ in ()).throw(
            fetch_subdl.Redirect(301, "https://api2.subdl.com/v1")))
        self.assertEqual(client.subtitles(1, 4, "ES"), [])
        self.assertEqual((client.requests, client.downloads), (2, 0))

        # At most MAX_REDIRECTS hops.
        loop = {f"https://dl.subdl.com/{n}": f"https://dl.subdl.com/{n + 1}" for n in range(10)}
        get, calls = server(loop)
        client = self.client(get)
        with self.assertRaises(fetch_subdl.CandidateError):
            client._fetch("https://dl.subdl.com/0", {}, client._charge_download)
        self.assertEqual(len(calls), fetch_subdl.MAX_REDIRECTS + 1)

        # Disallowed targets are refused without being requested or echoed.
        for target in (f"http://dl.subdl.com/x?k={KEY}", f"https://evil.example/{KEY}", "https://evilsubdl.com/x",
                       "https://dl.subdl.com.evil.example/x", f"https://dl.subdl.com{AT}evil.example/x",
                       f"https://user{AT}dl.subdl.com/x", "https://dl.subdl.com:8443/x", "ftp://dl.subdl.com/x",
                       f"https://{KEY}\u2100x/", "https://[::1/x"):
            get, calls = server({"https://dl.subdl.com/a.zip": target})
            client = self.client(get)
            with self.assertRaises(fetch_subdl.CandidateError) as ctx:
                client.download("/a.zip")
            self.assertEqual(len(calls), 1, target)
            self.assertNotIn(KEY, str(ctx.exception))
            self.assertNotIn("evil", str(ctx.exception))

        # In a run, a refused redirect falls through to the next candidate.
        api4 = {4: {"status": True, "subtitles": [
            {"release_name": "a", "season": 4, "episode": 1, "url": "/subtitle/1-1.zip"},
            {"release_name": "b", "season": 4, "episode": 1, "url": "/subtitle/1-2.zip"}]}}
        stub = Stub(api4, {"/subtitle/1-2.zip": body})
        def get(u, h):
            if u.endswith("/subtitle/1-1.zip"):
                raise fetch_subdl.Redirect(302, f"https://evil.example/?api_key={KEY}")
            return stub(u, h)
        with patch.dict(cfg("club-de-cuervos"), {"seasonEpisodes": {4: 1}}):
            result, logs = self.run_fetch("club-de-cuervos", get)
        self.assertEqual(result["seasons"]["S04"]["found"], ["E01"])
        self.assertTrue(any("disallowed host" in line for line in logs))
        self.assertNotIn(KEY, "\n".join(logs))
        self.assertNotIn("evil", "\n".join(logs))

    def test_real_opener_never_follows_or_reads_redirects(self):
        handlers = fetch_subdl._OPENER.handlers
        self.assertTrue(any(isinstance(h, fetch_subdl.NoRedirect) for h in handlers))
        self.assertFalse(any(type(h) is fetch_subdl.HTTPRedirectHandler for h in handlers))
        for code in (301, 302, 303, 307, 308):
            fp = MagicMock()
            fp.read.side_effect = AssertionError("redirect body read")
            handler = getattr(fetch_subdl.NoRedirect(), f"http_error_{code}")
            with self.assertRaises(fetch_subdl.Redirect) as ctx:
                handler(None, fp, code, "Found", {"Location": f"https://x.subdl.com/?api_key={KEY}"})
            fp.close.assert_called_once()
            fp.read.assert_not_called()
            self.assertEqual(ctx.exception.location, f"https://x.subdl.com/?api_key={KEY}")
            self.assertNotIn(KEY, str(ctx.exception))
            self.assertNotIn("subdl.com", str(ctx.exception))

    def test_zip_member_size_and_method_checked_before_opening(self):
        z = MagicMock()
        z.open.side_effect = AssertionError("opened")
        big = ZipInfo("S04E01.srt")
        big.file_size = fetch_subdl.MAX_MEMBER_BYTES + 1
        with self.assertRaises(fetch_subdl.TooLarge):
            fetch_subdl.read_capped(z, big)
        bz = ZipInfo("S04E01.srt")
        bz.compress_type, bz.file_size = ZIP_BZIP2, 10
        with self.assertRaises(fetch_subdl.Unsupported):
            fetch_subdl.read_capped(z, bz)
        z.open.assert_not_called()

        buf = io.BytesIO()
        with ZipFile(buf, "w") as zf:
            zf.writestr("S04E01.srt", srt(SPANISH), compress_type=ZIP_BZIP2)
        api = {4: {"status": True, "subtitles": [
            {"release_name": "a", "season": 4, "episode": 1, "url": "/subtitle/1-1.zip"},
            {"release_name": "b", "season": 4, "episode": 1, "url": "/subtitle/1-2.zip"}]}}
        stub = Stub(api, {"/subtitle/1-1.zip": buf.getvalue(), "/subtitle/1-2.zip": zipped({"S04E01.srt": srt(SPANISH)})})
        with patch.dict(cfg("club-de-cuervos"), {"seasonEpisodes": {4: 1}}):
            result, logs = self.run_fetch("club-de-cuervos", stub)
        self.assertEqual(result["seasons"]["S04"]["found"], ["E01"])
        self.assertTrue(any("unsupported compression" in line for line in logs))
        self.assertIn(fetch_subdl.file_id("ES", "/subtitle/1-1.zip", "S04E01.srt"),
                      load(str(Path(self.work) / "subdl-rejected.json")))

    def test_raw_candidate_name_must_match_episode(self):
        client = self.client(lambda u, h: srt(SPANISH))
        # Episode-level URL whose file name names another episode (Codex's offline check).
        sub = {"season": 4, "episode": 1, "url": "/sub/S04E02.srt"}
        self.assertIsNone(fetch_subdl.select_episode(client, [sub], 4, 1, "ES", set(), quiet))
        for url in ("/sub/S03E01.srt", "/sub/2x01.srt", "/sub/S04E01.txt", "/sub/S04E01.hi.srt"):
            sub = {"season": 4, "episode": 1, "url": url}
            self.assertFalse(fetch_subdl.candidates([sub], 4, 1, "ES")[0].raw_ok, url)
        for url in ("/sub/S04E01.srt", "/sub/4x01.srt", "/sub/episode.srt"):
            sub = {"season": 4, "episode": 1, "url": url}
            self.assertTrue(fetch_subdl.candidates([sub], 4, 1, "ES")[0].raw_ok, url)
        self.assertTrue(fetch_subdl.select_episode(client, [{"season": 4, "episode": 1, "url": "/sub/S04E01.srt"}],
                                                   4, 1, "ES", set(), quiet))

        # unpack_files: metadata and name marker must agree, and a raw body needs an .srt name.
        def files(*entries):
            return [{"release_name": "r", "season": 4, "episode": 1, "url": "/subtitle/1.zip", "unpack_files": list(entries)},
                    {"release_name": "p", "season": 4, "full_season": True, "url": "/subtitle/p.zip",
                     "unpack_files": list(entries)}]
        self.assertEqual(fetch_subdl.candidates(files(unpack(1, "X.S04E02.srt", "/subtitle/f/1")), 4, 1, "ES"), [])
        self.assertEqual(fetch_subdl.candidates(files(unpack(2, "X.S04E01.srt", "/subtitle/f/1")), 4, 1, "ES"), [])
        odd = fetch_subdl.candidates(files(unpack(1, "X.S04E01.txt", "/subtitle/f/1", format="srt")), 4, 1, "ES")
        self.assertEqual([c.raw_ok for c in odd], [False, False])
        good = fetch_subdl.candidates(files(unpack(1, "X.S04E01.srt", "/subtitle/f/1")), 4, 1, "ES")
        self.assertEqual([(c.season_pack, c.raw_ok) for c in good], [(False, True), (True, True)])
        self.assertEqual(fetch_subdl.candidates(files(unpack(None, "X.srt", "/subtitle/f/1")), 4, 1, "ES")[0].raw_ok,
                         True)                                     # episode-level, no marker anywhere
        self.assertEqual(len(fetch_subdl.candidates(files(unpack(None, "X.srt", "/subtitle/f/1")), 4, 1, "ES")), 1)
        stub = Stub({}, {"/subtitle/f/1": srt(SPANISH)})
        self.assertIsNone(fetch_subdl.select_episode(self.client(stub), files(unpack(1, "X.S04E01.txt", "/subtitle/f/1",
                                                                                     format="srt")),
                                                     4, 1, "ES", set(), quiet))

    def test_every_episode_marker_in_name_and_url_must_agree(self):
        marks = fetch_subdl.episode_markers
        self.assertEqual(marks("S04E01.S04E02.srt"), [(4, 1), (4, 2)])
        self.assertEqual(marks("Show.S04E01E02.srt"), [(4, 1), (4, 2)])
        self.assertEqual(marks("Show.S04E01-E02.srt"), [(4, 1), (4, 2)])
        self.assertEqual(marks("Show 4x01 S04E01.srt"), [(4, 1), (4, 1)])
        self.assertEqual(marks("Show.S04E01.Episodio.1080p.x264.srt"), [(4, 1)])
        client = self.client(lambda u, h: srt(SPANISH))
        # Codex's checks: two markers in one raw name, and metadata name vs URL basename.
        for url in ("/sub/S04E01.S04E02.srt", "/sub/S04E01E02.srt", "/sub/S04E01.4x02.srt"):
            sub = {"season": 4, "episode": 1, "url": url}
            self.assertFalse(fetch_subdl.candidates([sub], 4, 1, "ES")[0].raw_ok, url)
            self.assertIsNone(fetch_subdl.select_episode(client, [sub], 4, 1, "ES", set(), quiet), url)
        for entry in (unpack(1, "S04E01.srt", "/sub/S04E02.srt"), unpack(1, "S04E01.srt", "/sub/x/S04E01.S04E02.srt"),
                      unpack(1, "S04E01.S04E02.srt", "/sub/f/1"), unpack(None, "S04E02.srt", "/sub/S04E01.srt")):
            for sub in ({"season": 4, "episode": 1, "url": "/subtitle/1.zip", "unpack_files": [entry]},
                        {"season": 4, "full_season": True, "url": "/subtitle/p.zip", "unpack_files": [entry]}):
                self.assertEqual(fetch_subdl.candidates([sub], 4, 1, "ES"), [], entry)
                self.assertIsNone(fetch_subdl.select_episode(client, [sub], 4, 1, "ES", set(), quiet), entry)
        # Agreeing names (or an archive / opaque URL basename) are still accepted.
        for entry in (unpack(1, "S04E01.srt", "/sub/S04E01.srt"), unpack(1, "S04E01.srt", "/sub/f/1"),
                      unpack(1, "S04E01.srt", "/sub/S04E01-E12.zip"), unpack(None, "x.srt", "/sub/S04E01.srt")):
            sub = {"season": 4, "episode": 1, "url": "/subtitle/1.zip", "unpack_files": [entry]}
            self.assertTrue(fetch_subdl.candidates([sub], 4, 1, "ES")[0].raw_ok, entry)
            self.assertTrue(fetch_subdl.select_episode(client, [sub], 4, 1, "ES", set(), quiet), entry)
        # Pack: the URL basename alone may name the episode; a zip member naming two episodes is skipped.
        pack = {"season": 4, "full_season": True, "url": "/subtitle/p.zip",
                "unpack_files": [unpack(None, "x.srt", "/sub/S04E01.srt")]}
        self.assertTrue(fetch_subdl.candidates([pack], 4, 1, "ES")[0].raw_ok)
        both = zipped({"S04E01.S04E02.srt": srt(SPANISH)})
        pack = {"season": 4, "full_season": True, "url": "/subtitle/p.zip"}
        for ep in (1, 2):
            self.assertIsNone(fetch_subdl.select_episode(self.client(lambda u, h: both), [pack], 4, ep, "ES",
                                                         set(), quiet))
        one = zipped({"S04E01.srt": srt(SPANISH), "S04E02.srt": srt(ITALIAN)})
        got = fetch_subdl.select_episode(self.client(lambda u, h: one), [pack], 4, 1, "ES", set(), quiet)
        self.assertEqual(got[1], "S04E01.srt")

    def test_episode_mismatch_rejection_is_scoped_to_that_episode(self):
        shared = "/subtitle/x/S04E02.srt"
        # E01's metadata points at a file named for E02; E02's own entry points at the same file.
        subs = [{"release_name": "E1", "season": 4, "episode": 1, "url": shared},
                {"release_name": "E2", "season": 4, "episode": 2, "url": shared}]
        rejected = set()
        stub = Stub({}, {shared: srt(SPANISH)})
        self.assertIsNone(fetch_subdl.select_episode(self.client(stub), subs, 4, 1, "ES", rejected, quiet))
        self.assertNotIn(fetch_subdl.file_id("ES", shared), rejected)
        self.assertIn(fetch_subdl.exhausted_id("ES", shared, 4, 1), rejected)
        self.assertTrue(fetch_subdl.select_episode(self.client(stub), subs, 4, 2, "ES", rejected, quiet))

        # Through fetch() and the saved cache: E02 is found in the same run and nothing is downloaded again.
        api = {4: {"status": True, "subtitles": subs}}
        stub = Stub(api, {shared: srt(SPANISH)})
        with patch.dict(cfg("club-de-cuervos"), {"seasonEpisodes": {4: 2}}):
            result, _ = self.run_fetch("club-de-cuervos", stub)
            self.assertEqual(result["seasons"]["S04"], {"found": ["E02"], "missing": ["E01"]})
            self.assertEqual(stub.downloaded(), [shared, shared])
            stub2 = Stub(api, stub.files)
            self.run_fetch("club-de-cuervos", stub2)
        self.assertEqual(stub2.downloaded(), [])
        saved = load(str(Path(self.work) / "subdl-rejected.json"))
        self.assertIn(fetch_subdl.exhausted_id("ES", shared, 4, 1), saved)
        self.assertNotIn(fetch_subdl.file_id("ES", shared), saved)

        # A cache from the first run (E01 only) still lets a later run fetch E02 from the same file.
        os.remove(Path(self.work) / "srt" / "S04E02.es.srt")
        stub3 = Stub(api, stub.files)
        with patch.dict(cfg("club-de-cuervos"), {"seasonEpisodes": {4: 2}}):
            result3, _ = self.run_fetch("club-de-cuervos", stub3)
        self.assertEqual(result3["seasons"]["S04"]["found"], ["E02"])
        self.assertEqual(stub3.downloaded(), [shared])

        # Content failures stay path-wide: an Italian raw file is rejected for every episode.
        bad = "/subtitle/y/S04E01.srt"
        rejected = set()
        subs = [{"season": 4, "episode": 1, "url": bad}, {"season": 4, "episode": 2, "url": bad}]
        stub = Stub({}, {bad: srt(ITALIAN)})
        self.assertIsNone(fetch_subdl.select_episode(self.client(stub), subs, 4, 1, "ES", rejected, quiet))
        self.assertIn(fetch_subdl.file_id("ES", bad), rejected)
        self.assertIsNone(fetch_subdl.select_episode(self.client(stub), subs, 4, 2, "ES", rejected, quiet))
        self.assertEqual(stub.downloaded(), [bad])


if __name__ == "__main__":
    unittest.main()
