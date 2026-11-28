"""Fetch original-language SRTs for a text-only show from SubDL into WORKDIR/srt.

Usage: SUBDL_API_KEY=... python pipeline/multi/fetch_subdl.py SHOW_ID WORKDIR [--lang ES] [--dry-run]

Show config (pipeline/multi/common.py): subdlTmdbId, subdlSeasons, optional seasonEpisodes {season: count}.
A configured count is authoritative (S04 with 12 episodes never gains an E13 from upstream metadata); seasons
without a count use the episodes the API lists. Only --lang ES is supported (it is the only language we can
validate). The API key is read only from the SUBDL_API_KEY environment variable. It is never printed, logged
or stored: every URL the API returns has its query string stripped before use, every upstream name (release,
file, archive member) is redacted and reduced to safe characters before it is printed or stored, and archive
errors are reported without member names.

Per (season, episode): episode-level subtitles first, then season-pack unpack_files, in API order. Only .srt,
no hearing-impaired files (hi flag, *hi.srt, *.hi.*, spaHi, SDH). A raw (non-zip) download is accepted only
when the metadata names an eligible .srt for that exact episode; a season-pack zip must contain a member named
for that episode. A file is accepted only if it parses to >= MIN_CUES cues and reads as the requested language
(stopword ratio >= MIN_RATIO over >= MIN_WORDS words, and clearly more Spanish than Italian/Portuguese markers).
A raw body also needs a file name (metadata name or URL basename) ending in .srt, and EVERY SxxEyy / NxNN marker
in the metadata name and in the URL basename (unless it names an archive) must be the requested episode
(S04E01.S04E02.srt, S04E01E02.srt, or a name S04E01.srt served from .../S04E02.srt never serve E01). Missing (404/410), oversized or unreadable files fall through to the next
candidate; quota/auth failures (401/403/429) and the request/download budgets stop the run. Redirects are never
followed automatically: each hop is charged to the same budget as the request, at most MAX_REDIRECTS hops are
taken, redirect bodies are never read, and only https targets on *.subdl.com are followed.

Writes WORKDIR/srt/SxxEyy.<lang>.srt (LF line endings, CR-only files normalised), WORKDIR/subdl-manifest.json
{code: {release, file, season_pack}} and WORKDIR/subdl-rejected.json: opaque ids (sha256 of language, path and
member) for files that failed on their own content (missing, too large, unreadable, not the language), for
(language, path, season, episode) when a download was inspected for that episode and gave nothing (a file named
for another episode is rejected only for this episode, never path-wide), and for paths known to serve a raw
(non-zip) body, so later runs never re-download them; delete it to retry. A cache from an older version (plain paths) is
rewritten as opaque ids as soon as it is loaded. Existing SRTs are never re-downloaded; seasons that
are already complete make no API call. Both budgets are charged before every HTTP attempt, retries included:
stops before MAX_DOWNLOADS downloads (anonymous limit is 300/day/IP) and MAX_API_REQUESTS API requests.
Responses are capped at MAX_BODY_BYTES, subtitle files / archive members at MAX_MEMBER_BYTES (a member's declared
size is checked before it is opened, and only stored/deflated members are read), and only a few
season packs are kept in memory (PACK_CACHE_ITEMS / PACK_CACHE_BYTES). Prints one JSON summary line.
"""
import argparse, hashlib, io, json, os, re, sys, time
from collections import OrderedDict
from dataclasses import dataclass
from urllib.error import HTTPError
from urllib.parse import urlencode, urljoin, urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener
from zipfile import ZIP_DEFLATED, ZIP_STORED, ZipFile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import cfg, load, save
from ingest_srt import TS

API = "https://api.subdl.com/api/v1/subtitles"
DL = "https://dl.subdl.com"
USER_AGENT = "curl/8.5.0"          # SubDL answers 403 to Python's default User-Agent
MAX_DOWNLOADS = 250
MAX_API_REQUESTS = 1900            # free plan: 2,000/day
MAX_PAGES = 10
MAX_REDIRECTS = 3                  # hops per request, each charged to the request's budget
REDIRECT_HOST_SUFFIX = ".subdl.com"
ZIP_METHODS = {ZIP_STORED, ZIP_DEFLATED}   # bzip2 / lzma members could expand past the cap inside zipfile
MAX_BODY_BYTES = 20 * 1024 * 1024  # any single HTTP response (download or API page)
MAX_MEMBER_BYTES = 5 * 1024 * 1024 # a raw subtitle file or one decompressed archive member
PACK_CACHE_ITEMS, PACK_CACHE_BYTES = 4, 60 * 1024 * 1024
MIN_CUES, MIN_WORDS, MIN_RATIO = 150, 200, 0.12
RETRY_STATUS = {500, 502, 503, 504}
MISSING_STATUS = {404, 410}        # this file is gone: try the next candidate
STOP_STATUS = {401, 403, 429}      # quota / auth: every further request would fail too

STOPWORDS = {
    "es": frozenset("""el la de que y en los las un una es por con para no se lo del al me te mi su qué yo tú tu
        pero como más este esta eso esto ya muy está hay le les nos sí bien aquí ahora todo nada algo""".split()),
}
SUPPORTED_LANGS = sorted(k.upper() for k in STOPWORDS)
# Frequent Italian / Portuguese words that are not Spanish words (mislabeled packs exist upstream).
FOREIGN_MARKERS = {
    "es": frozenset("""il di che non è gli della sono questo perché anche ho hai sei cosa più così
        não você isso uma eu ele com em muito obrigado""".split()),
}
WORD = re.compile(r"[^\W\d_]+")
PATH = re.compile(r"/[A-Za-z0-9_.\-/]+")
UNSAFE = re.compile(r"[^\w .,'+()\[\]&-]")
SECRET_PARAM = re.compile(r"((?:api[_-]?key|apikey|key|token|access_token|signature|sig|secret|password)\s*[=:])[^&\s'\"]*", re.I)
# SxxEyy (with E-continuations: S04E01E02, S04E01-E02) and NxNN episode markers in a file name.
SXXEYY = re.compile(r"[Ss](\d{1,2})[ ._-]?[Ee](\d{1,3})((?:[ ._-]?[Ee]\d{1,3})*)")
NXNN = re.compile(r"(?<!\d)(\d{1,2})x(\d{2,3})(?!\d)")
ARCHIVE_EXT = (".zip", ".rar", ".7z")


class SubdlError(Exception):
    """Network/API failure; the message is already redacted and holds no upstream file names."""


class Stop(SubdlError):
    """Stop the whole run: a budget is used up or the service refuses every request (quota/auth)."""


class DownloadLimit(Stop):
    """Stopped before exceeding the download budget."""


class RequestLimit(Stop):
    """Stopped before exceeding the API request budget."""


class CandidateError(SubdlError):
    """This one file is unusable (missing upstream, too large): try the next candidate."""


class TooLarge(Exception):
    """A response or archive member is over its byte cap."""


class Redirect(Exception):
    """A 3xx response (never followed by urllib). str() holds no URL: the target may echo the key."""

    def __init__(self, code, location):
        super().__init__(f"HTTP {code} redirect")
        self.code, self.location = code, str(location or "")


class NoRedirect(HTTPRedirectHandler):
    """Turn every redirect into Redirect without reading the body; Client._fetch decides whether to follow."""

    def http_error_302(self, req, fp, code, msg, headers):
        location = headers.get("Location") or headers.get("URI") or ""
        if fp is not None:
            fp.close()
        raise Redirect(code, location)

    http_error_301 = http_error_303 = http_error_307 = http_error_308 = http_error_302


_OPENER = build_opener(NoRedirect)


def urlopen(req, timeout):
    return _OPENER.open(req, timeout=timeout)


def redirect_target(current, location):
    """Absolute https URL on *.subdl.com for a Location header, else CandidateError (target never shown)."""
    try:
        target = urljoin(current, location)
        parts = urlsplit(target)
        host, port = (parts.hostname or "").lower(), parts.port
    except ValueError:
        raise CandidateError("redirect to an invalid URL") from None
    if (parts.scheme != "https" or not host.endswith(REDIRECT_HOST_SUFFIX) or port not in (None, 443)
            or parts.username is not None or parts.password is not None):
        raise CandidateError("redirect to a disallowed host")
    return target


def redact(text, key):
    text = str(text)
    if key:
        text = text.replace(key, "[REDACTED]")
    return re.sub(r"(api_key=)[^&\s'\"]*", r"\1[REDACTED]", text, flags=re.I)


def safe_name(text, key, limit=160):
    """Upstream release/file/member name made safe to print or store: key and secret-looking parameters
    redacted, then reduced to word characters and a few punctuation marks, and truncated."""
    text = SECRET_PARAM.sub(r"\1[REDACTED]", redact(text, key))
    text = UNSAFE.sub("_", text).strip()
    return (text[:limit] + "…" if len(text) > limit else text) or "?"


def opaque_id(*parts):
    """Stable id for subdl-rejected.json that never stores upstream paths or names."""
    return "sha256:" + hashlib.sha256("\0".join(map(str, parts)).encode("utf-8")).hexdigest()[:32]


def file_id(lang, path, member=""):
    return opaque_id("file", lang.lower(), path, member)


def exhausted_id(lang, path, season, episode):
    """This download was inspected for this one episode and gave nothing (other episodes may still use it)."""
    return opaque_id("exhausted", lang.lower(), path, int(season), int(episode))


def raw_body_id(lang, path):
    """This path serves a raw (non-zip) body: only a candidate allowed to use a raw body needs to download it."""
    return opaque_id("raw", lang.lower(), path)


def load_rejected(path, lang):
    """Opaque ids; entries from older versions ("/path" or "/path!member") are converted on load, and the
    file is rewritten at once (atomically) so no plain upstream path stays on disk, even if nothing is fetched."""
    raw, out = load(path, []) or [], set()
    for entry in raw:
        entry = str(entry)
        if entry.startswith("sha256:"):
            out.add(entry)
        elif entry.startswith("/"):
            p, _, member = entry.partition("!")
            out.add(file_id(lang, p, member))
    if not isinstance(raw, list) or raw != sorted(out):
        if os.path.exists(path):
            save(path, sorted(out))
    return out


def clean_path(url):
    """Path of a SubDL download URL without host, query or fragment (the query may carry the API key).
    None for a URL urllib cannot parse (the error text would echo it, so it is dropped silently)."""
    try:
        path = urlsplit(str(url or "")).path
    except ValueError:
        return None
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


def episode_markers(name):
    """Every (season, episode) marker in a file name, in order: S04E01.S04E02.srt -> [(4, 1), (4, 2)],
    S04E01E02.srt -> [(4, 1), (4, 2)], 4x01.srt -> [(4, 1)]."""
    name, out = str(name or ""), []
    for m in SXXEYY.finditer(name):
        s = int(m[1])
        out.append((s, int(m[2])))
        out += [(s, int(e)) for e in re.findall(r"\d+", m[3] or "")]
    out += [(int(m[1]), int(m[2])) for m in NXNN.finditer(name)]
    return out


def episode_from_name(name):
    marks = episode_markers(name)
    return marks[0] if marks else (None, None)


def url_name(path):
    """Basename of a download path whose episode markers count, or "" for an archive (it may name a range)."""
    base = os.path.basename(str(path or ""))
    return "" if base.lower().endswith(ARCHIVE_EXT) else base


def markers_match(season, episode, *names):
    """True if every episode marker in every name is this exact episode (no marker at all also passes)."""
    return all(m == (season, episode) for n in names for m in episode_markers(n))


def raw_name_ok(name, season, episode, *others):
    """A raw (non-zip) body may stand for this episode only under a non-HI .srt name, and only if every episode
    marker in that name and in the other names (URL basename) is this exact episode (S04E02.srt never serves E01)."""
    name = str(name or "")
    return (name.lower().endswith(".srt") and not any(is_hi(n) for n in (name, *others))
            and markers_match(season, episode, name, *others))


def http_get(url, headers, limit=MAX_BODY_BYTES):
    with urlopen(Request(url, headers=headers), timeout=60) as response:
        length = as_int(response.headers.get("Content-Length"))
        if length is not None and length > limit:
            raise TooLarge()
        data = response.read(limit + 1)
    if len(data) > limit:
        raise TooLarge()
    return data


def decode(raw):
    for enc in ("utf-8-sig", "cp1252", "latin-1"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue


def normalize_newlines(text):
    """CRLF and CR-only (old Mac) line endings -> LF, so validation and ingest_srt see the same cues."""
    return text.replace("\r\n", "\n").replace("\r", "\n")


def cue_texts(text):
    out = []
    for block in re.split(r"\n\s*\n", normalize_newlines(text)):
        rows = [r for r in block.strip().split("\n") if r.strip()]
        k = next((j for j, r in enumerate(rows) if TS.search(r)), None)
        if k is None:
            continue
        body = " ".join(re.sub(r"<[^>]+>|\{\\[^}]*\}", "", r) for r in rows[k + 1:]).strip()
        if body:
            out.append(body)
    return out


def validate(text, lang):
    """(ok, reason): cue count and a stopword language check; languages without a stopword list fail."""
    stop = STOPWORDS.get(lang)
    if stop is None:
        return False, "no validator for this language"
    cues = cue_texts(text or "")
    if len(cues) < MIN_CUES:
        return False, f"only {len(cues)} cues"
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
    name: str            # file name from metadata ("" = none: take matching members of a zip)
    season_pack: bool
    episode: int
    season: int
    raw_ok: bool = False # metadata names an eligible .srt for this exact episode: a non-zip body may be used


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
                me = as_int(f.get("episode"))
                path = clean_path(f.get("url"))
                if not path:
                    continue
                base = url_name(path)
                # Every marker in the name and the URL basename, and the metadata, must agree when present;
                # a pack file needs at least one of them to name this episode.
                if not markers_match(season, episode, name, base) or me not in (None, episode):
                    continue
                if pack and me != episode and not (episode_markers(name) or episode_markers(base)):
                    continue
                bucket.append(Candidate(path, release, name, pack, episode, season,
                                        raw_ok=raw_name_ok(name, season, episode, base)))
        else:
            path = clean_path(sub.get("url"))
            if path:
                raw_ok = not pack and raw_name_ok(os.path.basename(path), season, episode)
                bucket.append(Candidate(path, release, "", pack, episode, season, raw_ok=raw_ok))
    return direct + packs


class Client:
    def __init__(self, key, get=http_get, sleep=time.sleep, max_downloads=MAX_DOWNLOADS,
                 max_requests=MAX_API_REQUESTS, max_bytes=MAX_BODY_BYTES):
        if not key:
            raise SubdlError("SUBDL_API_KEY is not set")
        self.key, self.get, self.sleep = key, get, sleep
        self.max_downloads, self.max_requests, self.max_bytes = max_downloads, max_requests, max_bytes
        self.downloads = self.requests = 0
        self.cache, self.cache_bytes = OrderedDict(), 0   # small LRU of season-pack zips

    def _charge_request(self):
        if self.requests >= self.max_requests:
            raise RequestLimit(f"stopped before {self.max_requests} API requests")
        self.requests += 1

    def _charge_download(self):
        if self.downloads >= self.max_downloads:
            raise DownloadLimit(f"stopped before {self.max_downloads} downloads")
        self.downloads += 1

    def _fetch(self, url, headers, charge):
        """GET with up to 3 attempts; `charge` runs before every attempt and every redirect hop (budgets count
        real requests). Redirects: at most MAX_REDIRECTS hops, https *.subdl.com targets only."""
        host = urlsplit(url).netloc
        for attempt in range(3):
            current = url
            try:
                for hop in range(MAX_REDIRECTS + 1):
                    charge()
                    try:
                        data = self.get(current, headers)
                        break
                    except Redirect as r:
                        location = r.location
                    if hop == MAX_REDIRECTS:
                        raise CandidateError(f"more than {MAX_REDIRECTS} redirects from {host}")
                    current = redirect_target(current, location)
            except SubdlError:      # budgets, refused redirects: never retried
                raise
            except HTTPError as exc:
                code = exc.code
                if code in MISSING_STATUS:
                    raise CandidateError(f"HTTP {code} from {host}") from None
                if code in STOP_STATUS:
                    raise Stop(f"HTTP {code} from {host}") from None
                if attempt == 2 or code not in RETRY_STATUS:
                    raise SubdlError(f"HTTP {code} from {host}") from None
            except TooLarge:
                raise CandidateError(f"response over {self.max_bytes // 2**20} MB") from None
            except Exception as exc:  # URLError, timeouts, stub errors: never let the raw URL escape
                if attempt == 2:
                    msg = str(exc).replace(current, host).replace(url, host)
                    raise SubdlError(redact(f"{type(exc).__name__}: {msg}", self.key)) from None
            else:
                if len(data) > self.max_bytes:
                    raise CandidateError(f"response over {self.max_bytes // 2**20} MB")
                return data
            self.sleep(2 * 2 ** attempt)

    def subtitles(self, tmdb_id, season, lang):
        out, page, pages = [], 1, 1
        while page <= min(pages, MAX_PAGES):
            params = {"api_key": self.key, "tmdb_id": tmdb_id, "type": "tv", "season_number": season,
                      "languages": lang, "subs_per_page": 30, "unpack": 1}
            if page > 1:
                params["page"] = page
            raw = self._fetch(f"{API}?{urlencode(params)}", {"User-Agent": USER_AGENT, "Accept": "application/json"},
                              self._charge_request)
            try:
                data = json.loads(raw.decode("utf-8"))
            except (UnicodeDecodeError, ValueError):
                raise SubdlError("API returned non-JSON") from None
            if not isinstance(data, dict) or not data.get("status"):
                msg = data.get("error") or data.get("message") if isinstance(data, dict) else None
                raise SubdlError("API error: " + (safe_name(msg, self.key, 200) if msg else "status false"))
            out += [s for s in data.get("subtitles") or [] if isinstance(s, dict)]
            pages = as_int(data.get("totalPages")) or 1
            page += 1
        return out

    def download(self, path, keep=False):
        """Body of a download path. keep=True: a season pack other episodes will reuse (kept in a small LRU)."""
        if path in self.cache:
            self.cache.move_to_end(path)
            return self.cache[path]
        data = self._fetch(DL + path, {"User-Agent": USER_AGENT}, self._charge_download)
        if keep and len(data) <= PACK_CACHE_BYTES:
            self.cache[path] = data
            self.cache_bytes += len(data)
            while len(self.cache) > PACK_CACHE_ITEMS or self.cache_bytes > PACK_CACHE_BYTES:
                _, old = self.cache.popitem(last=False)
                self.cache_bytes -= len(old)
        return data


class Unreadable(Exception):
    """The archive itself cannot be opened (no member names in the message)."""


class Unsupported(Exception):
    """An archive member compressed with a method we do not read (only stored / deflate)."""


def read_capped(z, info):
    """Member bytes; the declared size and compression method are checked before the member is opened."""
    if info.file_size > MAX_MEMBER_BYTES:
        raise TooLarge()
    if info.compress_type not in ZIP_METHODS:
        raise Unsupported()
    with z.open(info) as f:
        raw = f.read(MAX_MEMBER_BYTES + 1)
    if len(raw) > MAX_MEMBER_BYTES:
        raise TooLarge()
    return raw


def members(data, cand):
    """Yield (member name, reader) for SRT files in a download that may belong to this episode, one at a time.

    A raw (non-zip) body is the file itself, used only when the metadata names an eligible .srt for this
    episode (member name ""). A zip yields non-HI .srt members; a season pack needs the episode in the name."""
    if not data.startswith(b"PK"):
        if cand.raw_ok:
            def raw():
                if len(data) > MAX_MEMBER_BYTES:
                    raise TooLarge()
                return data
            yield "", raw
        return
    try:
        z = ZipFile(io.BytesIO(data))
        infos = z.infolist()
    except Exception:
        raise Unreadable() from None
    for info in infos:
        name = os.path.basename(info.filename)
        if info.is_dir() or not name.lower().endswith(".srt") or is_hi(name):
            continue
        marks = episode_markers(name)
        if not markers_match(cand.season, cand.episode, name) or (cand.season_pack and not marks):
            continue
        yield name, (lambda info=info: read_capped(z, info))


def skip_candidate(cand, lang, rejected):
    """True if `rejected` already rules this candidate out for its episode (no download needed)."""
    return bool({file_id(lang, cand.path), exhausted_id(lang, cand.path, cand.season, cand.episode)} & rejected
                or (not cand.raw_ok and raw_body_id(lang, cand.path) in rejected))


def select_episode(client, subs, season, episode, lang, rejected, log=print):
    """(candidate, file name, text) for the first valid file, or None.

    Adds opaque ids to `rejected`: files that failed on their own content (whole download or archive member),
    paths that serve a raw body, and an exhausted (lang, path, season, episode) id for a download inspected for
    this episode without result. Episode mismatches are only ever recorded for this episode, so a file named for
    E02 that E01's metadata pointed at is still tried for E02."""
    code, key = f"S{season:02d}E{episode:02d}", client.key
    for cand in candidates(subs, season, episode, lang):
        whole, done = file_id(lang, cand.path), exhausted_id(lang, cand.path, season, episode)
        if skip_candidate(cand, lang, rejected):
            if done not in rejected and whole not in rejected:
                rejected.add(done)   # known raw body this candidate may not use
            continue
        label = safe_name(cand.name or cand.release or cand.path, key)
        reusable = cand.season_pack and not cand.name
        try:
            data = client.download(cand.path, keep=reusable)
        except CandidateError as exc:
            rejected.add(whole)
            log(f"{code}: skip {label} ({exc})", file=sys.stderr)
            continue
        if not data.startswith(b"PK"):
            rejected.add(raw_body_id(lang, cand.path))
            if not cand.raw_ok:
                rejected.add(done)
                log(f"{code}: skip {label} (raw file not named for this episode)", file=sys.stderr)
                continue
        tried = 0
        try:
            for name, read in members(data, cand):
                mid = file_id(lang, cand.path, name)
                if mid in rejected:
                    continue
                tried += 1
                try:
                    raw = read()
                except TooLarge:
                    why = f"over {MAX_MEMBER_BYTES // 2**20} MB"
                except Unsupported:
                    why = "unsupported compression"
                except Exception:   # bad CRC, truncated, encrypted, unsupported compression...
                    why = "unreadable archive member"
                else:
                    text = normalize_newlines(decode(raw) or "")
                    ok, why = validate(text, lang.lower())
                    if ok:
                        return cand, name or cand.name or os.path.basename(cand.path), text
                rejected.add(mid)
                log(f"{code}: skip {safe_name(name, key) if name else label} ({why})", file=sys.stderr)
        except Unreadable:
            rejected.add(whole)
            log(f"{code}: skip {label} (unreadable archive)", file=sys.stderr)
            continue
        if not tried:
            log(f"{code}: no eligible .srt for this episode in {label}", file=sys.stderr)
        # Content failures are already recorded per member; the download may still serve other episodes.
        rejected.add(done)
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
    lang = lang.upper()
    if lang not in SUPPORTED_LANGS:
        raise SubdlError(f"unsupported language (supported: {', '.join(SUPPORTED_LANGS)})")
    suffix = lang.lower()
    srt_dir = os.path.join(work, "srt")
    os.makedirs(srt_dir, exist_ok=True)
    manifest_p, rejected_p = os.path.join(work, "subdl-manifest.json"), os.path.join(work, "subdl-rejected.json")
    manifest = load(manifest_p, {}) or {}
    rejected = load_rejected(rejected_p, lang)
    counts = {int(k): int(v) for k, v in (c.get("seasonEpisodes") or {}).items()}
    exists = lambda code: os.path.isfile(os.path.join(srt_dir, f"{code}.{suffix}.srt"))
    summary, errors, stopped = {}, [], False
    for season in c["subdlSeasons"]:
        expected = list(range(1, counts[season] + 1)) if counts.get(season) else []
        subs = []
        if not (expected and all(exists(f"S{season:02d}E{e:02d}") for e in expected)) and not stopped:
            if client is None:
                client = Client(os.environ.get("SUBDL_API_KEY", ""))
            try:
                subs = client.subtitles(c["subdlTmdbId"], season, lang)
            except Stop as exc:
                errors.append(f"S{season:02d}: {exc}"); stopped = True
            except SubdlError as exc:
                errors.append(f"S{season:02d}: {exc}")
        if expected:   # a configured count is authoritative: upstream metadata cannot add episodes
            targets = expected
        else:
            seen = {as_int(s.get("episode")) for s in subs if not truthy(s.get("full_season"))}
            seen |= {as_int(f.get("episode")) or episode_from_name(f.get("name"))[1]
                     for s in subs for f in (s.get("unpack_files") or []) if isinstance(f, dict)}
            targets = sorted(e for e in seen if isinstance(e, int) and e > 0)
        for ep in targets:
            code = f"S{season:02d}E{ep:02d}"
            if exists(code) or stopped:
                continue
            if dry_run:
                first = next((x for x in candidates(subs, season, ep, lang)
                              if not skip_candidate(x, lang, rejected)), None)
                log(f"{code}: " + (f"would try {safe_name(first.name or first.release or first.path, client.key)} "
                                   f"({'pack' if first.season_pack else 'episode'})" if first else "no candidate"),
                    file=sys.stderr)
                continue
            try:
                got = select_episode(client, subs, season, ep, lang, rejected, log)
            except Stop as exc:
                errors.append(f"{code}: {exc}"); stopped = True; continue
            except SubdlError as exc:
                errors.append(f"{code}: {exc}"); continue
            finally:
                save(rejected_p, sorted(rejected))
            if not got:
                continue
            cand, name, text = got
            write_text(os.path.join(srt_dir, f"{code}.{suffix}.srt"), text)
            manifest[code] = {"release": safe_name(cand.release, client.key), "file": safe_name(name, client.key),
                              "season_pack": cand.season_pack}
            save(manifest_p, dict(sorted(manifest.items())))
            log(f"{code}: {safe_name(name, client.key)}", file=sys.stderr)
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
    ap.add_argument("--lang", default="ES", type=str.upper, choices=SUPPORTED_LANGS,
                    help="SubDL language code; only ES can be validated (default ES)")
    ap.add_argument("--dry-run", action="store_true", help="query the API and list candidates; no downloads")
    a = ap.parse_args()
    if not os.environ.get("SUBDL_API_KEY"):
        sys.exit("SUBDL_API_KEY is not set (the key is read from the environment only)")
    try:
        result = fetch(a.show, a.work, a.lang, a.dry_run)
    except SubdlError as exc:
        sys.exit(f"fetch_subdl: {exc}")
    missing = any(s["missing"] for s in result["seasons"].values())
    return 1 if (result["errors"] or (missing and not a.dry_run)) else 0


if __name__ == "__main__":
    sys.exit(main())
