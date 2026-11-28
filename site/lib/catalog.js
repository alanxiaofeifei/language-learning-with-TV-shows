// Public catalog: languages and shows. Adding a language later means one
// entry here, optional show records, and (when a show exists) private data
// under site/private/. Coming-soon languages have no shows and no content.

export const LANGUAGES = [
  {
    id: "vi",
    nameZh: "越南语",
    nameVi: "Tiếng Việt",
    nameNative: "Tiếng Việt",
    variant: "北越 · 河内口音",
    variantVi: "Miền Bắc · giọng Hà Nội",
    status: "ready",
    shows: ["ve-nha-di-con"],
    planned: [{ track: "long", title: "Gạo nếp gạo tẻ", noteZh: "长期加选：南越口音", noteVi: "Bổ sung dài hạn: giọng miền Nam" }],
  },
  {
    id: "zh",
    nameZh: "中文",
    nameVi: "Tiếng Trung",
    nameNative: "简体中文",
    variant: "中国大陆为主，含台湾模块",
    variantVi: "Chủ yếu Trung Quốc đại lục, có học phần Đài Loan",
    status: "ready",
    shows: ["dou-ting-hao"],
    planned: [
      { track: "long", title: "欢乐颂 1", noteZh: "长期第二部：都市职场", noteVi: "Dài hạn phần 2: công sở đô thị" },
      { track: "long", title: "我们与恶的距离", noteZh: "长期台湾模块：台湾用语与繁体", noteVi: "Học phần Đài Loan: từ ngữ Đài Loan, chữ phồn thể" },
    ],
  },
  {
    id: "en",
    nameZh: "英语",
    nameVi: "Tiếng Anh",
    nameNative: "English",
    variant: "美式英语",
    variantVi: "Tiếng Anh Mỹ",
    status: "ready",
    shows: ["friends", "seinfeld", "silicon-valley", "desperate-housewives"],
    planned: [],
  },
  {
    id: "fr",
    nameZh: "法语",
    nameVi: "Tiếng Pháp",
    nameNative: "Français",
    variant: "加拿大法语",
    variantVi: "Tiếng Pháp Canada",
    status: "coming",
    shows: [],
    planned: [
      { track: "short", title: "Lupin", noteZh: "法国法语打底", noteVi: "Nền tảng tiếng Pháp chuẩn" },
      { track: "long", title: "魁北克剧待定", titleVi: "Phim Québec (chưa chọn)", noteZh: "加拿大法语", noteVi: "Tiếng Pháp Canada" },
    ],
  },
  {
    id: "ja",
    nameZh: "日语",
    nameVi: "Tiếng Nhật",
    nameNative: "日本語",
    variant: "东京标准音",
    variantVi: "Giọng chuẩn Tokyo",
    status: "coming",
    shows: [],
    planned: [{ track: "short", title: "逃げるは恥だが役に立つ", noteZh: "第一部", noteVi: "Phim đầu tiên" }],
  },
  {
    id: "es",
    nameZh: "西班牙语",
    nameVi: "Tiếng Tây Ban Nha",
    nameNative: "Español",
    variant: "美式 / 拉美西班牙语",
    variantVi: "Tây Ban Nha Mỹ Latinh",
    status: "coming",
    shows: [],
    planned: [
      { track: "short", title: "Club de Cuervos", noteZh: "短期版", noteVi: "Lộ trình ngắn" },
      { track: "long", title: "La casa de las flores", noteZh: "长期版", noteVi: "Lộ trình dài" },
    ],
  },
  {
    id: "yue",
    nameZh: "粤语",
    nameVi: "Tiếng Quảng Đông",
    nameNative: "粵語",
    variant: "香港广东话",
    variantVi: "Tiếng Quảng Đông Hồng Kông",
    status: "coming",
    shows: [],
    planned: [{ track: "short", title: "愛·回家之開心速遞", noteZh: "第一部", noteVi: "Phim đầu tiên" }],
  },
];

// kind "vn" = the original Vietnamese app (data under /private/data); kind "multi" = generic show
// built by pipeline/multi (private data under /private/shows/<id>/, public episode list under /shows/<id>/).
export const SHOWS = {
  "ve-nha-di-con": {
    id: "ve-nha-di-con",
    kind: "vn",
    language: "vi",
    titleNative: "Về nhà đi con",
    titleZh: "回家吧，孩子",
    mark: "Về",
    dataBase: "/private/data",
    parts: 82,
    tracks: ["short", "long"],
  },
  "dou-ting-hao": {
    id: "dou-ting-hao",
    kind: "multi",
    language: "zh",
    source: "youtube-official",
    titleNative: "都挺好",
    titleZh: "都挺好",
    titleVi: "Tất cả đều ổn",
    titleEn: "All is Well",
    mark: "都",
    year: "2019",
    channel: "正午阳光官方频道",
    channelVi: "Daylight Entertainment (正午阳光)",
    playlist: "PL2Vcf2jYz5dfh5rHzOEok_gDLJf39MhuO",
    dataBase: showDataBase("dou-ting-hao"),
    publicBase: "/shows/dou-ting-hao",
    episodes: 46,
    langs: ["zh", "py", "vi", "en"],
    levels: "HSK",
    tracks: ["short", "long"],
  },
  friends: {
    id: "friends",
    kind: "multi",
    language: "en",
    source: "text-only",
    titleNative: "Friends",
    titleZh: "老友记",
    titleVi: "Những người bạn",
    titleEn: "Friends",
    mark: "F",
    year: "1994–1996 · S01–S02",
    dataBase: showDataBase("friends"),
    publicBase: "/shows/friends",
    episodes: 48,
    langs: ["en", "zh", "vi"],
    levels: "CEFR",
    tracks: ["short", "long"],
    watch: { name: "HBO Max", url: "https://www.hbomax.com/" },
  },
  "seinfeld": {
    id: "seinfeld",
    kind: "multi",
    language: "en",
    source: "text-only",
    titleNative: "Seinfeld",
    titleZh: "宋飞正传",
    titleVi: "Seinfeld",
    titleEn: "Seinfeld",
    mark: "S",
    year: "1990–1993 · S01–S02",
    dataBase: showDataBase("seinfeld"),
    publicBase: "/shows/seinfeld",
    episodes: 17,
    langs: ["en", "zh", "vi"],
    levels: "CEFR",
    tracks: ["short", "long"],
    watch: null,
  },
  "silicon-valley": {
    id: "silicon-valley",
    kind: "multi",
    language: "en",
    source: "text-only",
    titleNative: "Silicon Valley",
    titleZh: "硅谷",
    titleVi: "Thung lũng Silicon",
    titleEn: "Silicon Valley",
    mark: "SV",
    year: "2014 · S01",
    dataBase: showDataBase("silicon-valley"),
    publicBase: "/shows/silicon-valley",
    episodes: 8,
    langs: ["en", "zh", "vi"],
    levels: "CEFR",
    tracks: ["short", "long"],
    watch: null,
  },
  "desperate-housewives": {
    id: "desperate-housewives",
    kind: "multi",
    language: "en",
    source: "text-only",
    titleNative: "Desperate Housewives",
    titleZh: "绝望主妇",
    titleVi: "Desperate Housewives",
    titleEn: "Desperate Housewives",
    mark: "DH",
    year: "2004–2005 · S01",
    dataBase: showDataBase("desperate-housewives"),
    publicBase: "/shows/desperate-housewives",
    episodes: 23,
    langs: ["en", "zh", "vi"],
    levels: "CEFR",
    tracks: ["short", "long"],
    watch: null,
  },
};

export function showDataBase(showId) {
  return `/private/shows/${showId}`;
}

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
    case "ep": return `${base}/ep/${parts.ep}`;
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
  [new RegExp(`^#/(${LANG})/(${SHOW})/ep/(\\d+)$`), (m) => ({ page: "ep", lang: m[1], show: m[2], ep: +m[3] })],
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

export function isMultiShow(showId) {
  return SHOWS[showId]?.kind === "multi";
}

export function isComingLanguage(langId) {
  const lang = languageById(langId);
  return !lang || lang.status === "coming";
}
