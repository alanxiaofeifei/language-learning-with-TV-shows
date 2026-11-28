"""Fetch English SRTs and episode titles from TVsubtitles into a local workdir."""

import argparse
from html import unescape
import io
from pathlib import Path
import re
import sys
import tempfile
import time
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen
from zipfile import BadZipFile, ZipFile

from common import load, save

BASE = "https://www.tvsubtitles.net/"
USER_AGENT = "Mozilla/5.0 (compatible; TVStudySubtitleFetcher/1.0)"
RETRY_STATUS = {408, 429, 500, 502, 503, 504}
SUBTITLE_LINK = r"""href\s*=\s*["']/?(subtitle-\d+\.html)["']"""
ENGLISH_FLAG = r"""\balt\s*=\s*["']en["']"""


def parse_season(html, code_prefix=""):
    """Yield each episode's metadata and its English subtitle or listing link."""
    for row in re.findall(r"<tr\b[^>]*>(.*?)</tr\s*>", html, re.I | re.S):
        number = re.search(r"<td\b[^>]*>\s*(\d+)x(\d+)\s*</td>", row, re.I)
        if not number:
            continue
        season, episode = map(int, number.groups())
        code = f"{code_prefix}S{season:02d}E{episode:02d}"
        bold = re.search(r"<b\b[^>]*>(.*?)</b>", row, re.I | re.S)
        title = unescape(re.sub(r"<[^>]*>", "", bold[1])).strip() if bold else code
        direct = re.search(SUBTITLE_LINK + r"[^>]*>\s*<img\b[^>]*" + ENGLISH_FLAG, row, re.I)
        listing = re.search(r"""href\s*=\s*["']/?(episode-\d+-en\.html)["']""", row, re.I)
        link = direct or listing
        yield {"code": code, "title": title}, link[1] if link else None


def parse_subtitle_listing(html):
    """Return the first English subtitle link from an English-filtered listing."""
    match = re.search(
        SUBTITLE_LINK + r"""[^>]*>\s*<div\b[^>]*\btitle\s*=\s*["']Download English subtitles["']""",
        html,
        re.I,
    )
    return match[1] if match else None


def parse_archive_path(html):
    """Reassemble the split download path without executing page JavaScript."""
    parts = dict(re.findall(r"""\bvar\s+s(\d+)\s*=\s*['"]([^'"]*)['"]""", html))
    path = unescape("".join(parts[str(n)] for n in sorted(map(int, parts))))
    if not re.fullmatch(r"files/[^/\\?#]+\.zip", path, re.I):
        raise ValueError("download page has no recognized ZIP path")
    return path


class Client:
    def get(self, path, referer=None):
        headers = {"User-Agent": USER_AGENT}
        if referer:
            headers["Referer"] = BASE + referer
        request = Request(BASE + quote(path, safe="/%"), headers=headers)
        for attempt in range(3):
            # Delay before each request, including retries.
            time.sleep(3 * 2**attempt)
            try:
                with urlopen(request, timeout=60) as response:
                    return response.read()
            except HTTPError as exc:
                if attempt == 2 or exc.code not in RETRY_STATUS:
                    raise
            except (URLError, TimeoutError):
                if attempt == 2:
                    raise

    def html(self, path):
        return self.get(path).decode("utf-8", errors="replace")


def download_srt(client, subtitle, output):
    download = subtitle.replace("subtitle-", "download-", 1)
    archive = parse_archive_path(client.html(download))
    with ZipFile(io.BytesIO(client.get(archive, referer=subtitle))) as zipped:
        member = next(
            (item for item in zipped.infolist() if not item.is_dir() and item.filename.lower().endswith(".srt")),
            None,
        )
        if member is None:
            raise ValueError("ZIP has no SRT")
        data = zipped.read(member)
    temp_path = None
    try:
        with tempfile.NamedTemporaryFile(dir=output.parent, delete=False) as tmp:
            temp_path = Path(tmp.name)
            tmp.write(data)
        temp_path.replace(output)
    finally:
        if temp_path is not None:
            temp_path.unlink(missing_ok=True)


def fetch(show_id, workdir, seasons, code_prefix=""):
    client = Client()
    srt_dir = workdir / "srt"
    srt_dir.mkdir(parents=True, exist_ok=True)
    meta_path = str(workdir / "episodes.json")
    episodes = {ep["code"]: ep for ep in load(meta_path, [])}
    failed = False
    for season in seasons:
        page = f"tvshow-{show_id}-{season}.html"
        try:
            rows = list(parse_season(client.html(page), code_prefix))
            if not rows:
                raise ValueError("season page has no episode rows")
        except (URLError, TimeoutError, ValueError) as exc:
            print(f"Season {season}: {exc}", file=sys.stderr)
            failed = True
            continue
        for episode, link in rows:
            code = episode["code"]
            episodes[code] = episode
            output = srt_dir / f"{code}.en.srt"
            if output.exists():
                continue
            try:
                if link and link.startswith("episode-"):
                    link = parse_subtitle_listing(client.html(link))
                if not link:
                    print(f"{code}: no English subtitle", file=sys.stderr)
                    continue
                download_srt(client, link, output)
                print(f"{code}: saved English SRT", flush=True)
            except (URLError, TimeoutError, BadZipFile, ValueError) as exc:
                print(f"{code}: {exc}", file=sys.stderr)
                failed = True
        save(meta_path, [episodes[code] for code in sorted(episodes)])
    return int(failed)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("show_id", type=int, help="numeric TVsubtitles show ID")
    parser.add_argument("workdir", type=Path)
    parser.add_argument("--seasons", default="1", help="comma-separated season numbers (default: 1)")
    parser.add_argument("--code-prefix", default="", help="optional uppercase prefix prepended to episode codes and SRT filenames")
    args = parser.parse_args()
    if args.show_id < 1:
        parser.error("show ID must be positive")
    if not re.fullmatch(r"\d{1,2}(?:\s*,\s*\d{1,2})*", args.seasons.strip()):
        parser.error("--seasons must be a comma-separated list of season numbers")
    if not re.fullmatch(r"[A-Za-z0-9_-]*", args.code_prefix):
        parser.error("--code-prefix accepts only ASCII letters, numbers, underscores and hyphens")
    seasons = dict.fromkeys(map(int, args.seasons.split(",")))
    return fetch(args.show_id, args.workdir, seasons, args.code_prefix.upper())


if __name__ == "__main__":
    sys.exit(main())
