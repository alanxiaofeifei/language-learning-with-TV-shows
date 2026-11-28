"""Fetch original-language SRTs for a text-only show from SubDL into WORKDIR/srt.

Usage: SUBDL_API_KEY=... python pipeline/multi/fetch_subdl.py SHOW_ID WORKDIR [--lang ES] [--dry-run]

Show config (pipeline/multi/common.py): subdlTmdbId, subdlSeasons, optional seasonEpisodes {season: count}.
The API key is read only from the SUBDL_API_KEY environment variable. It is never printed, logged or stored:
every error message is redacted and every URL the API returns has its query string stripped before use.

Per (season, episode): episode-level subtitles first, then season-pack unpack_files, in API order. Only .srt,
no hearing-impaired files (hi flag, *hi.srt, *.hi.*, spaHi, SDH). A file is accepted only if it parses to
>= MIN_CUES cues and reads as the requested language (stopword ratio >= MIN_RATIO over >= MIN_WORDS words,
and clearly more Spanish than Italian/Portuguese markers). Rejected files fall through to the next candidate.

Writes WORKDIR/srt/SxxEyy.<lang>.srt, WORKDIR/subdl-manifest.json {code: {release, file, season_pack}} and
WORKDIR/subdl-rejected.json (download paths that failed validation, so later runs never re-download them;
delete it to retry). Existing SRTs are never re-downloaded; seasons that are already complete make no API
call. Stops before MAX_DOWNLOADS downloads (anonymous limit is 300/day/IP). Prints one JSON summary line.
"""
import argparse, io, json, os, re, sys, time
from dataclasses import dataclass
from urllib.error import HTTPError
from urllib.parse import urlencode, urlsplit
from urllib.request import Request, urlopen
from zipfile import BadZipFile, ZipFile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import cfg, load, save
from ingest_srt import TS

API = "https://api.subdl.com/api/v1/subtitles"
DL = "https://dl.subdl.com"
USER_AGENT = "curl/8.5.0"          # SubDL answers 403 to Python's default User-Agent
MAX_DOWNLOADS = 250
MAX_API_REQUESTS = 1900            # free plan: 2,000/day
MAX_PAGES = 10
MIN_CUES, MIN_WORDS, MIN_RATIO = 150, 200, 0.12
RETRY_STATUS = {500, 502, 503, 504}

STOPWORDS = {
    "es": frozenset("""el la de que y en los las un una es por con para no se lo del al me te mi su qué yo tú tu
        pero como más este esta eso esto ya muy está hay le les nos sí bien aquí ahora todo nada algo""".split()),
}
# Frequent Italian / Portuguese words that are not Spanish words (mislabeled packs exist upstream).
FOREIGN_MARKERS = {
    "es": frozenset("""il di che non è gli della sono questo perché anche ho hai sei cosa più così
        não você isso uma eu ele com em muito obrigado""".split()),
}
WORD = re.compile(r"[^\W\d_]+")
PATH = re.compile(r"/[A-Za-z0-9_.\-/]+")
EPISODE_IN_NAME = (re.compile(r"[Ss](\d{1,2})[ ._-]?[Ee](\d{1,3})"), re.compile(r"(?<!\d)(\d{1,2})x(\d{2,3})(?!\d)"))


class SubdlError(Exception):
    """Network/API failure; the message is already redacted."""


class DownloadLimit(SubdlError):
    """Stopped before exceeding MAX_DOWNLOADS."""


def redact(text, key):
    text = str(text)
    if key:
        text = text.replace(key, "[REDACTED]")
    return re.sub(r"(api_key=)[^&\s'\"]*", r"\1[REDACTED]", text, flags=re.I)


def clean_path(url):
    """Path of a SubDL download URL without host, query or fragment (the query may carry the API key)."""
    path = urlsplit(str(url or "")).path
    if not path.startswith("/"):
        path = "/" + path
    return path if PATH.fullmatch(path) and ".." not in path else None


def is_hi(name):
    n = str(name or "")
    return bool(re.search(r"hi\.srt$", n, re.I) or re.search(r"\.hi\.", n, re.I)
                or re.search(r"spahi", n, re.I) or re.search(r"(?:^|[^a-z])sdh(?:[^a-z]|$)", n, re.I))


def as_int(v):
    try:
        return int(v)
    except (TypeError, ValueError):
        return None


def truthy(v):
    return v is True or (isinstance(v, (int, float)) and v != 0) or str(v).lower() in ("true", "1", "yes")


def episode_from_name(name):
    for pattern in EPISODE_IN_NAME:
        m = pattern.search(str(name or ""))
        if m:
            return int(m[1]), int(m[2])
    return None, None


def http_get(url, headers):
    with urlopen(Request(url, headers=headers), timeout=60) as response:
        return response.read()


def decode(raw):
    for enc in ("utf-8-sig", "cp1252", "latin-1"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue


def cue_texts(text):
    out = []
    for block in re.split(r"\n\s*\n", text.replace("\r\n", "\n").replace("\r", "\n")):
        rows = [r for r in block.strip().split("\n") if r.strip()]
        k = next((j for j, r in enumerate(rows) if TS.search(r)), None)
        if k is None:
            continue
        body = " ".join(re.sub(r"<[^>]+>|\{\\[^}]*\}", "", r) for r in rows[k + 1:]).strip()
        if body:
            out.append(body)
    return out


def validate(text, lang):
    """(ok, reason). Language check only where we have a stopword list; cue count always."""
    cues = cue_texts(text or "")
    if len(cues) < MIN_CUES:
        return False, f"only {len(cues)} cues"
    stop = STOPWORDS.get(lang)
    if stop is None:
        return True, "ok"
    words = [w.casefold() for w in WORD.findall(" ".join(cues))]
    if len(words) < MIN_WORDS:
        return False, f"only {len(words)} words"
    ratio = sum(w in stop for w in words) / len(words)
    foreign = sum(w in FOREIGN_MARKERS.get(lang, ()) for w in words) / len(words)
    if ratio < MIN_RATIO:
        return False, f"stopword ratio {ratio:.2f} < {MIN_RATIO}"
    if foreign * 2 >= ratio:
        return False, f"looks like another language (markers {foreign:.2f} vs {ratio:.2f})"
    return True, "ok"


@dataclass(frozen=True)
class Candidate:
    path: str            # download path on dl.subdl.com, no query
    release: str
    name: str            # file name hint ("" = take matching members of a zip)
    season_pack: bool
    episode: int
    season: int


def candidates(subtitles, season, episode, lang):
    """Download candidates for one episode: episode-level subtitles first, then season packs, API order each."""
    lang = lang.upper()
    direct, packs = [], []
    for sub in subtitles or []:
        if not isinstance(sub, dict) or truthy(sub.get("hi")):
            continue
        s = as_int(sub.get("season"))
        if s not in (None, season):
            continue
        release = str(sub.get("release_name") or sub.get("name") or "")
        ep = as_int(sub.get("episode"))
        pack = truthy(sub.get("full_season")) or not ep
        if not pack and ep != episode:
            continue
        files = [f for f in sub.get("unpack_files") or [] if isinstance(f, dict)]
        bucket = packs if pack else direct
        if files:
            for f in files:
                name = str(f.get("name") or "")
                if str(f.get("format") or name.rsplit(".", 1)[-1]).lower() != "srt" or truthy(f.get("hi")) or is_hi(name):
                    continue
                if f.get("language") and str(f["language"]).upper() != lang:
                    continue
                fs, fe = episode_from_name(name)
                fe = as_int(f.get("episode")) or fe
                if (fs not in (None, season)) or (fe != episode if pack else fe not in (None, episode)):
                    continue
                path = clean_path(f.get("url"))
                if path:
                    bucket.append(Candidate(path, release, name, pack, episode, season))
        else:
            path = clean_path(sub.get("url"))
            if path:
                bucket.append(Candidate(path, release, "", pack, episode, season))
    return direct + packs


class Client:
    def __init__(self, key, get=http_get, sleep=time.sleep, max_downloads=MAX_DOWNLOADS):
        if not key:
            raise SubdlError("SUBDL_API_KEY is not set")
        self.key, self.get, self.sleep, self.max_downloads = key, get, sleep, max_downloads
        self.downloads = self.requests = 0
        self.cache = {}

    def _fetch(self, url, headers):
        for attempt in range(3):
            try:
                return self.get(url, headers)
            except HTTPError as exc:
                code = exc.code
                if attempt == 2 or code not in RETRY_STATUS:
                    raise SubdlError(redact(f"HTTP {code} for {urlsplit(url).netloc}", self.key)) from None
            except Exception as exc:  # URLError, timeouts, stub errors: never let the raw URL escape
                if attempt == 2:
                    raise SubdlError(redact(f"{type(exc).__name__}: {exc}", self.key)) from None
            self.sleep(2 * 2 ** attempt)

    def subtitles(self, tmdb_id, season, lang):
        out, page, pages = [], 1, 1
        while page <= min(pages, MAX_PAGES):
            if self.requests >= MAX_API_REQUESTS:
                raise SubdlError("API request budget reached")
            params = {"api_key": self.key, "tmdb_id": tmdb_id, "type": "tv", "season_number": season,
                      "languages": lang, "subs_per_page": 30, "unpack": 1}
            if page > 1:
                params["page"] = page
            self.requests += 1
            raw = self._fetch(f"{API}?{urlencode(params)}", {"User-Agent": USER_AGENT, "Accept": "application/json"})
            try:
                data = json.loads(raw.decode("utf-8"))
            except (UnicodeDecodeError, ValueError):
                raise SubdlError("API returned non-JSON") from None
            if not isinstance(data, dict) or not data.get("status"):
                msg = data.get("error") or data.get("message") if isinstance(data, dict) else None
                raise SubdlError(redact(f"API error: {msg or 'status false'}", self.key))
            out += [s for s in data.get("subtitles") or [] if isinstance(s, dict)]
            pages = as_int(data.get("totalPages")) or 1
            page += 1
        return out

    def download(self, path):
        if path in self.cache:
            return self.cache[path]
        if self.downloads >= self.max_downloads:
            raise DownloadLimit(f"stopped before {self.max_downloads} downloads")
        self.downloads += 1
        data = self._fetch(DL + path, {"User-Agent": USER_AGENT})
        self.cache[path] = data
        return data


def members(data, cand):
    """[(key, name, raw)] SRT files in a download: the file itself, or matching non-HI .srt members of a zip."""
    if not data.startswith(b"PK"):
        return [(cand.path, cand.name or os.path.basename(cand.path), data)]
    try:
        z = ZipFile(io.BytesIO(data))
    except BadZipFile:
        return []
    out = []
    for info in z.infolist():
        name = os.path.basename(info.filename)
        if info.is_dir() or not name.lower().endswith(".srt") or is_hi(name):
            continue
        s, e = episode_from_name(name)
        if s not in (None, cand.season) or (e != cand.episode if cand.season_pack else e not in (None, cand.episode)):
            continue
        out.append((f"{cand.path}!{name}", name, z.read(info)))
    return out


def select_episode(client, subs, season, episode, lang, rejected, log=print):
    """(candidate, file name, text) for the first valid file, or None. Adds failures to `rejected`."""
    for cand in candidates(subs, season, episode, lang):
        if cand.path in rejected:
            continue
        data = client.download(cand.path)
        found = members(data, cand)
        # A season-pack zip serves other episodes too: only reject the per-episode member keys.
        whole = not (cand.season_pack and data.startswith(b"PK"))
        if not found:
            if whole:
                rejected.add(cand.path)
            continue
        for key, name, raw in found:
            if key in rejected:
                continue
            text = decode(raw)
            ok, why = validate(text, lang.lower())
            if ok:
                return cand, name, text
            rejected.add(key)
            log(f"S{season:02d}E{episode:02d}: skip {redact(name, client.key)} ({why})", file=sys.stderr)
        if whole and all(key in rejected for key, _, _ in found):
            rejected.add(cand.path)
    return None


def write_text(path, text):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8", newline="") as f:
        f.write(text)
    os.replace(tmp, path)


def fetch(show_id, work, lang="ES", dry_run=False, client=None, log=print):
    c = cfg(show_id)
    if not c.get("subdlTmdbId") or not c.get("subdlSeasons"):
        raise SubdlError(f"{show_id} has no subdlTmdbId / subdlSeasons")
    suffix = lang.lower()
    srt_dir = os.path.join(work, "srt")
    os.makedirs(srt_dir, exist_ok=True)
    manifest_p, rejected_p = os.path.join(work, "subdl-manifest.json"), os.path.join(work, "subdl-rejected.json")
    manifest = load(manifest_p, {}) or {}
    rejected = set(load(rejected_p, []) or [])
    counts = {int(k): int(v) for k, v in (c.get("seasonEpisodes") or {}).items()}
    exists = lambda code: os.path.isfile(os.path.join(srt_dir, f"{code}.{suffix}.srt"))
    summary, errors, stopped = {}, [], False
    for season in c["subdlSeasons"]:
        expected = set(range(1, counts[season] + 1)) if counts.get(season) else set()
        subs = []
        if not (expected and all(exists(f"S{season:02d}E{e:02d}") for e in expected)) and not stopped:
            if client is None:
                client = Client(os.environ.get("SUBDL_API_KEY", ""))
            try:
                subs = client.subtitles(c["subdlTmdbId"], season, lang)
            except SubdlError as exc:
                errors.append(f"S{season:02d}: {exc}")
        seen = {as_int(s.get("episode")) for s in subs if not truthy(s.get("full_season"))}
        seen |= {as_int(f.get("episode")) or episode_from_name(f.get("name"))[1]
                 for s in subs for f in (s.get("unpack_files") or []) if isinstance(f, dict)}
        targets = sorted(e for e in (expected | seen) if isinstance(e, int) and e > 0)
        for ep in targets:
            code = f"S{season:02d}E{ep:02d}"
            if exists(code) or stopped:
                continue
            if dry_run:
                first = next(iter(candidates(subs, season, ep, lang)), None)
                log(f"{code}: " + (f"would try {first.name or first.path} ({'pack' if first.season_pack else 'episode'})"
                                   if first else "no candidate"), file=sys.stderr)
                continue
            try:
                got = select_episode(client, subs, season, ep, lang, rejected, log)
            except DownloadLimit as exc:
                errors.append(str(exc)); stopped = True; continue
            except SubdlError as exc:
                errors.append(f"{code}: {exc}"); continue
            finally:
                save(rejected_p, sorted(rejected))
            if not got:
                continue
            cand, name, text = got
            write_text(os.path.join(srt_dir, f"{code}.{suffix}.srt"), text)
            manifest[code] = {"release": redact(cand.release, client.key), "file": redact(name, client.key),
                              "season_pack": cand.season_pack}
            save(manifest_p, dict(sorted(manifest.items())))
            log(f"{code}: {name}", file=sys.stderr)
        found = [e for e in targets if exists(f"S{season:02d}E{e:02d}")]
        summary[f"S{season:02d}"] = {"found": [f"E{e:02d}" for e in found],
                                     "missing": [f"E{e:02d}" for e in targets if e not in found]}
    result = {"show": show_id, "lang": suffix, "seasons": summary, "downloads": client.downloads if client else 0,
              "apiRequests": client.requests if client else 0, "limitReached": stopped, "errors": errors}
    if dry_run:
        result["dryRun"] = True
    key = client.key if client else os.environ.get("SUBDL_API_KEY", "")
    log(redact(json.dumps(result, ensure_ascii=False), key))
    return result


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("show"); ap.add_argument("work")
    ap.add_argument("--lang", default="ES", help="SubDL language code (default ES)")
    ap.add_argument("--dry-run", action="store_true", help="query the API and list candidates; no downloads")
    a = ap.parse_args()
    if not re.fullmatch(r"[A-Za-z]{2}(?:[_-][A-Za-z]{2})?", a.lang):
        ap.error("--lang must be a SubDL language code such as ES")
    if not os.environ.get("SUBDL_API_KEY"):
        sys.exit("SUBDL_API_KEY is not set (the key is read from the environment only)")
    try:
        result = fetch(a.show, a.work, a.lang.upper(), a.dry_run)
    except SubdlError as exc:
        sys.exit(f"fetch_subdl: {exc}")
    missing = any(s["missing"] for s in result["seasons"].values())
    return 1 if (result["errors"] or (missing and not a.dry_run)) else 0


if __name__ == "__main__":
    sys.exit(main())
