"""Fetch completed Addic7ed SRTs into WORKDIR/srt and episode titles into episodes.json."""

import argparse
from html.parser import HTMLParser
from pathlib import Path
import re
import sys
from tempfile import NamedTemporaryFile
import time
from urllib.error import HTTPError, URLError
from urllib.parse import quote, unquote, urlsplit
from urllib.request import Request, urlopen

from common import load, save
from fetch_tvsubtitles import RETRY_STATUS, USER_AGENT
from ingest_srt import TS

BASE = "https://www.addic7ed.com"
LANGUAGES = {"en": "English", "fr": "French", "ja": "Japanese"}
LANGUAGE_NAMES = {name.casefold(): code for code, name in LANGUAGES.items()}


class EpisodePage(HTMLParser):
    def __init__(self, html, season_path):
        super().__init__()
        self.season_path = season_path
        self.episodes = {}
        self.containers = []
        self.blocks = []
        self.option = None
        self.episode_select = False
        self.feed(html)

    def episode_link(self, value):
        url = urlsplit(value)
        path = unquote(url.path)
        if url.netloc and url.netloc != urlsplit(BASE).netloc:
            return
        if path.startswith(self.season_path + "/"):
            number, _, title = path[len(self.season_path) + 1:].partition("/")
            if number.isdecimal() and title:
                self.episodes[int(number)] = (path, title.replace("_", " "))

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "select":
            self.episode_select = any("episode" in value or value == "qsep"
                                      for value in ((attrs.get(k) or "").lower() for k in ("name", "id")))
        if tag == "option" and self.episode_select:
            self.option = (attrs.get("value") or "", [])
        if tag in ("table", "tr"):
            self.containers.append({"tag": tag, "text": [], "links": [], "has_blocks": False})
        if tag in ("a", "option"):
            value = attrs.get("href" if tag == "a" else "value") or ""
            self.episode_link(value)
            if re.fullmatch(r"/original/[^\s?#]+", value):
                for block in self.containers:
                    block["links"].append(value)

    def handle_data(self, data):
        if self.option is not None:
            self.option[1].append(data)
        if data.strip():
            for block in self.containers:
                block["text"].append(data.strip())

    def handle_endtag(self, tag):
        if tag == "select":
            self.episode_select = False
        if tag == "option" and self.option is not None:
            value, parts = self.option
            self.option = None
            if value.isdecimal() and int(value) not in self.episodes:
                title = re.sub(r"^\s*\d+\s*[-.]\s*", "", "".join(parts)).strip()
                if title:
                    self.episodes[int(value)] = (f"{self.season_path}/{value}/{title.replace(' ', '_')}", title)
        if not self.containers or tag != self.containers[-1]["tag"]:
            return
        block = self.containers.pop()
        if block["has_blocks"] or block.get("has_language_rows"):
            return
        text = {part.casefold() for part in block["text"]}
        languages = text & LANGUAGE_NAMES.keys()
        if len(languages) == 1 and "completed" in text and block["links"]:
            self.blocks.append((LANGUAGE_NAMES[languages.pop()], block["links"][0]))
            for parent in self.containers:
                parent["has_blocks"] = True
        elif tag == "tr" and self.containers and languages and text & {"completed", "in progress"}:
            # A language row with its own status cannot borrow another row's link.
            for parent in self.containers:
                parent["has_language_rows"] = True

    def subtitle(self, language):
        return next((link for code, link in self.blocks if code == language), None)


def get(path, referer):
    request = Request(BASE + quote(path, safe="/%"), headers={
        "User-Agent": USER_AGENT,
        "Referer": BASE + quote(referer, safe="/%"),
    })
    for attempt in range(3):
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


def fetch(slug, season, language, workdir):
    season_path = f"/serie/{slug}/{season}"
    first_path = f"{season_path}/1"
    first = EpisodePage(get(first_path, season_path).decode("utf-8", "replace"), season_path)
    if not first.episodes:
        raise ValueError("episode page has no season navigation")
    srt_dir = workdir / "srt"
    srt_dir.mkdir(parents=True, exist_ok=True)
    meta_path = str(workdir / "episodes.json")
    episodes = {ep["code"]: ep for ep in load(meta_path, [])}
    failed = False
    for number, (path, title) in sorted(first.episodes.items()):
        code = f"S{season:02d}E{number:02d}"
        output = srt_dir / f"{code}.{language}.srt"
        episodes[code] = {"code": code, "title": title}
        if output.exists():
            continue
        try:
            page = first if number == 1 else EpisodePage(get(path, first_path).decode("utf-8", "replace"), season_path)
            link = page.subtitle(language)
            if link is None:
                raise ValueError(f"no completed {LANGUAGES[language]} original subtitle")
            data = get(link, path)
            if not any(TS.search(line.decode("ascii", "ignore")) for line in data.splitlines()):
                raise ValueError("download has no SRT timestamps")
            with NamedTemporaryFile(dir=srt_dir, delete=False) as tmp:
                temp_path = Path(tmp.name)
                try:
                    tmp.write(data)
                    tmp.close()
                    temp_path.replace(output)
                finally:
                    temp_path.unlink(missing_ok=True)
        except (URLError, TimeoutError, ValueError) as exc:
            print(f"{code}: {exc}", file=sys.stderr)
            failed = True
    save(meta_path, [episodes[code] for code in sorted(episodes)])
    return int(failed)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("show_slug")
    parser.add_argument("season", type=int)
    parser.add_argument("lang", choices=LANGUAGES)
    parser.add_argument("workdir", type=Path)
    args = parser.parse_args()
    if args.season < 1 or not re.fullmatch(r"[\w.-][\w. '&()-]*", args.show_slug) or args.show_slug in (".", ".."):
        parser.error("provide a show slug and a positive season number")
    try:
        return fetch(args.show_slug, args.season, args.lang, args.workdir)
    except (URLError, TimeoutError, ValueError) as exc:
        parser.exit(1, f"{exc}\n")


if __name__ == "__main__":
    sys.exit(main())
