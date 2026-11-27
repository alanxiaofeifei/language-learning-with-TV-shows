// Public catalog: languages and shows. Adding a language later means one
// entry here, optional show records, and (when a show exists) private data
// under site/private/. Coming-soon languages have no shows and no content.

export const LANGUAGES = [
  {
    id: "vi",
    nameZh: "越南语",
    nameNative: "Tiếng Việt",
    variant: "北越 · 河内口音",
    status: "ready",
    shows: ["ve-nha-di-con"],
  },
  {
    id: "en",
    nameZh: "英语",
    nameNative: "English",
    variant: "美式英语",
    status: "coming",
    shows: [],
  },
  {
    id: "fr",
    nameZh: "法语",
    nameNative: "Français",
    variant: "加拿大法语",
    status: "coming",
    shows: [],
  },
  {
    id: "ja",
    nameZh: "日语",
    nameNative: "日本語",
    variant: "东京标准音",
    status: "coming",
    shows: [],
  },
  {
    id: "es",
    nameZh: "西班牙语",
    nameNative: "Español",
    variant: "美式 / 拉美西班牙语",
    status: "coming",
    shows: [],
  },
  {
    id: "yue",
    nameZh: "粤语",
    nameNative: "粵語",
    variant: "香港广东话",
    status: "coming",
    shows: [],
  },
];

export const SHOWS = {
  "ve-nha-di-con": {
    id: "ve-nha-di-con",
    language: "vi",
    titleNative: "Về nhà đi con",
    titleZh: "回家吧，孩子",
    mark: "Về",
    dataBase: "/private/data",
    parts: 82,
    tracks: ["short", "long"],
  },
};

export const TRACKS = {
  short: {
    id: "short",
    nameZh: "短期版",
    lengthZh: "12 周 · 84 天",
    blurb: "把 82 段过一遍：先学生存用语和发音，再用双语字幕看完，适合先尽快开口。",
  },
  long: {
    id: "long",
    nameZh: "长期版",
    lengthZh: "约 5 年 · 260 周",
    blurb: "同一部剧当长期教材：分段精读、语法递进、间隔回看，从站稳脚跟走到工厂职场和接近母语的听力。",
  },
};

export const LANG_IDS = LANGUAGES.map((l) => l.id);
export const DEFAULT_SHOW = "ve-nha-di-con";

export function languageById(id) {
  return LANGUAGES.find((l) => l.id === id) || null;
}

export function showsForLanguage(langId) {
  return (languageById(langId)?.shows || []).map((id) => SHOWS[id]).filter(Boolean);
}

export function href(parts) {
  const { page } = parts;
  if (page === "home" || !page) return "#/";
  if (page === "lang") return `#/lang/${parts.lang}`;
  const base = `#/${parts.lang}/${parts.show}`;
  const track = parts.track;
  switch (page) {
    case "show": return base;
    case "track": return `${base}/${track}`;
    case "day": return `${base}/short/day/${parts.day}`;
    case "plan": return `${base}/${track || "short"}/plan`;
    case "stage": return `${base}/long/stage/${parts.stage}`;
    case "week": return `${base}/long/week/${parts.week}`;
    case "part": return `${base}/part/${parts.part}`;
    case "parts": return `${base}/parts`;
    case "review": return `${base}/review`;
    case "scenes": return parts.cat ? `${base}/scenes/${parts.cat}` : `${base}/scenes`;
    case "search": return parts.q != null && parts.q !== "" ? `${base}/search/${encodeURIComponent(parts.q)}` : `${base}/search`;
    case "vlc": return `${base}/vlc`;
    case "lesson": return `${base}/lesson/${parts.lesson}`;
    default: return "#/";
  }
}

const LANG = LANG_IDS.join("|");
const SHOW = "[a-z0-9-]+";

const NAMED = [
  [new RegExp(`^#?/?$`), () => ({ page: "home" })],
  [new RegExp(`^#/lang/(${LANG})$`), (m) => ({ page: "lang", lang: m[1] })],
  [new RegExp(`^#/(${LANG})/(${SHOW})/short/day/(\\d+)$`), (m) => ({ page: "day", lang: m[1], show: m[2], track: "short", day: +m[3] })],
  [new RegExp(`^#/(${LANG})/(${SHOW})/short/plan$`), (m) => ({ page: "plan", lang: m[1], show: m[2], track: "short" })],
  [new RegExp(`^#/(${LANG})/(${SHOW})/long/plan$`), (m) => ({ page: "plan", lang: m[1], show: m[2], track: "long" })],
  [new RegExp(`^#/(${LANG})/(${SHOW})/long/stage/([a-z0-9-]+)$`), (m) => ({ page: "stage", lang: m[1], show: m[2], track: "long", stage: m[3] })],
  [new RegExp(`^#/(${LANG})/(${SHOW})/long/week/(\\d+)$`), (m) => ({ page: "week", lang: m[1], show: m[2], track: "long", week: +m[3] })],
  [new RegExp(`^#/(${LANG})/(${SHOW})/(short|long)$`), (m) => ({ page: "track", lang: m[1], show: m[2], track: m[3] })],
  [new RegExp(`^#/(${LANG})/(${SHOW})/part/(\\d+)$`), (m) => ({ page: "part", lang: m[1], show: m[2], part: +m[3] })],
  [new RegExp(`^#/(${LANG})/(${SHOW})/parts$`), (m) => ({ page: "parts", lang: m[1], show: m[2] })],
  [new RegExp(`^#/(${LANG})/(${SHOW})/review$`), (m) => ({ page: "review", lang: m[1], show: m[2] })],
  [new RegExp(`^#/(${LANG})/(${SHOW})/scenes(?:/(\\w+))?$`), (m) => ({ page: "scenes", lang: m[1], show: m[2], cat: m[3] || null })],
  [new RegExp(`^#/(${LANG})/(${SHOW})/search(?:/(.*))?$`), (m) => ({ page: "search", lang: m[1], show: m[2], q: m[3] ? safeDecode(m[3]) : "" })],
  [new RegExp(`^#/(${LANG})/(${SHOW})/vlc$`), (m) => ({ page: "vlc", lang: m[1], show: m[2] })],
  [new RegExp(`^#/(${LANG})/(${SHOW})/lesson/(\\w+)$`), (m) => ({ page: "lesson", lang: m[1], show: m[2], lesson: m[3] })],
  [new RegExp(`^#/(${LANG})/(${SHOW})$`), (m) => ({ page: "show", lang: m[1], show: m[2] })],
];

const ALIASES = [
  [/^#\/day\/(\d+)$/, (m) => ({ page: "day", lang: "vi", show: DEFAULT_SHOW, track: "short", day: +m[1], alias: true })],
  [/^#\/plan$/, () => ({ page: "plan", lang: "vi", show: DEFAULT_SHOW, track: "short", alias: true })],
  [/^#\/parts$/, () => ({ page: "parts", lang: "vi", show: DEFAULT_SHOW, alias: true })],
  [/^#\/part\/(\d+)$/, (m) => ({ page: "part", lang: "vi", show: DEFAULT_SHOW, part: +m[1], alias: true })],
  [/^#\/review$/, () => ({ page: "review", lang: "vi", show: DEFAULT_SHOW, alias: true })],
  [/^#\/scenes(?:\/(\w+))?$/, (m) => ({ page: "scenes", lang: "vi", show: DEFAULT_SHOW, cat: m[1] || null, alias: true })],
  [/^#\/search(?:\/(.*))?$/, (m) => ({ page: "search", lang: "vi", show: DEFAULT_SHOW, q: m[1] ? safeDecode(m[1]) : "", alias: true })],
  [/^#\/vlc$/, () => ({ page: "vlc", lang: "vi", show: DEFAULT_SHOW, alias: true })],
  [/^#\/lesson\/(\w+)$/, (m) => ({ page: "lesson", lang: "vi", show: DEFAULT_SHOW, lesson: m[1], alias: true })],
];

export function matchRoute(hash) {
  const h = hash || "#/";
  for (const [re, fn] of NAMED) {
    const m = h.match(re);
    if (m) return validate(fn(m));
  }
  for (const [re, fn] of ALIASES) {
    const m = h.match(re);
    if (m) return validate(fn(m));
  }
  return { page: "notfound", hash: h };
}

export function safeDecode(s) {
  try { return decodeURIComponent(s); }
  catch { return s; }
}

function validate(route) {
  if (route.lang && !languageById(route.lang)) return { page: "notfound" };
  if (route.show) {
    const show = SHOWS[route.show];
    if (!show || show.language !== route.lang) return { page: "notfound" };
    if (route.track && !show.tracks.includes(route.track)) return { page: "notfound" };
  }
  return route;
}

export function isComingLanguage(langId) {
  const lang = languageById(langId);
  return !lang || lang.status === "coming";
}
