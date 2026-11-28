import { WEEKS, buildDays, nextDay } from "./lib/curriculum.js";
import { LESSONS } from "./lib/pron.js";
import { review, queue, today } from "./lib/srs.js";
import {
  LANGUAGES, SHOWS, TRACKS, languageById, showsForLanguage,
  href, matchRoute, isComingLanguage, isMultiShow,
} from "./lib/catalog.js";
import { t, setUiLang, uiLang, UI_LANGS } from "./lib/i18n.js";
import { DEFAULT_ME, effectivePrefs, homeLanguages, fetchMe, loadLocalPrefs, saveLocalPrefs } from "./lib/prefs.js";
import { initMulti, renderMulti } from "./multi.js";
import {
  LONG_STAGES, LONG_TOTAL_WEEKS, WEEK_MODES,
  buildLongWeeks, stageById, nextWeek,
} from "./lib/long-curriculum.js";
import { initMotion, swapMain, paintMain } from "./lib/motion.js";
import { h, fmt, titleEl, progressBar } from "./lib/dom.js";

const KEY = "vndc:v1";
const KEY_LONG = "vndc:long:v1";
const CATS = { food: "吃饭", shopping: "购物", work: "工作", survival: "出行求助", social: "寒暄礼貌", feeling: "情绪回应" };
const DAYS = buildDays();
const LONG_WEEKS = buildLongWeeks();
const main = document.getElementById("main-content");
const navEl = document.getElementById("site-nav");
const brandEl = document.getElementById("site-brand");

let data = null, dataError = null, searchIndex = null, ctx = { lang: "vi", show: "ve-nha-di-con", track: "short" };
const partCache = {};

const state = load();
const longState = loadLong();
function load() {
  try { return { doneDays: [], watched: {}, srs: {}, newToday: { day: 0, n: 0 }, newLimit: 15, track: "short", ...JSON.parse(localStorage.getItem(KEY) || "{}") }; }
  catch { return { doneDays: [], watched: {}, srs: {}, newToday: { day: 0, n: 0 }, newLimit: 15, track: "short" }; }
}
function loadLong() {
  try { return { doneWeeks: [], ...JSON.parse(localStorage.getItem(KEY_LONG) || "{}") }; }
  catch { return { doneWeeks: [] }; }
}
function save() { localStorage.setItem(KEY, JSON.stringify(state)); }
function saveLong() { localStorage.setItem(KEY_LONG, JSON.stringify(longState)); }

const yt = (videoId, ms) => `https://www.youtube.com/watch?v=${videoId}&t=${Math.max(0, Math.floor(ms / 1000) - 2)}s`;
const go = (parts) => href({ lang: ctx.lang, show: ctx.show, track: ctx.track, ...parts });
function weekChipLabel(w) {
  const mode = { deep: "", review: " 复习", rewatch: " 回看", cycle: " 循环" }[w.mode] || "";
  const parts = w.parts.length ? " P" + w.parts.join("+P") : "";
  return `W${w.week}${parts}${mode}`;
}

function dataBase() { return SHOWS[ctx.show]?.dataBase || "/private/data"; }
async function loadData() {
  if (data || dataError) return data;
  try {
    const r = await fetch(`${dataBase()}/index.json`, { credentials: "same-origin", redirect: "manual" });
    if (r.type === "opaqueredirect" || r.status === 0 || r.status === 401 || r.status === 403) throw new Error("login");
    if (!r.ok) throw new Error("http " + r.status);
    data = await r.json();
  } catch (e) { dataError = e.message === "login" ? "login" : "error"; }
  return data;
}
async function loadPart(n) {
  if (!partCache[n]) {
    partCache[n] = fetch(`${dataBase()}/P${String(n).padStart(2, "0")}.json`, { credentials: "same-origin" })
      .then((r) => { if (!r.ok) throw new Error("http " + r.status); return r.json(); })
      .catch((err) => { delete partCache[n]; throw err; });
  }
  return partCache[n];
}
function loginCard() {
  return h("section", { class: "panel login reveal" },
    h("h2", {}, dataError === "login" ? "需要登录" : "数据暂时打不开"),
    h("p", {}, "台词、双语字幕和原声片段只给你本人看（Cloudflare Access，Google 登录）。"),
    h("a", { class: "btn primary", href: "/private/login.html" }, "用 Google 登录"));
}

let currentAudio = null;
function speak(text) {
  const synth = window.speechSynthesis; if (!synth) return false;
  const voice = synth.getVoices().find((v) => v.lang?.toLowerCase().startsWith("vi"));
  if (!voice) return false;
  synth.cancel(); const u = new SpeechSynthesisUtterance(text); u.voice = voice; u.lang = voice.lang; u.rate = 0.8; synth.speak(u); return true;
}
function playButton(p, label = "▶ 原声") {
  if (p.clip) {
    return h("button", { class: "btn play", type: "button", onclick: (e) => {
      e.stopPropagation();
      currentAudio?.pause(); currentAudio = new Audio(p.clip);
      const slow = e.shiftKey || e.currentTarget.dataset.slow === "1"; currentAudio.playbackRate = slow ? 0.75 : 1;
      currentAudio.play();
    } }, label);
  }
  return h("button", { class: "btn play tts", type: "button", title: "没有核实过的原声片段，使用设备的越南语合成音",
    onclick: (e) => { e.stopPropagation(); if (!speak(p.phrase)) alert("这台设备没有越南语语音。可以点「YouTube」听原声。"); } }, "▶ 合成音");
}
function slowButton(p) {
  if (!p.clip) return null;
  return h("button", { class: "btn ghost", type: "button", onclick: (e) => {
    e.stopPropagation(); currentAudio?.pause(); currentAudio = new Audio(p.clip); currentAudio.playbackRate = 0.7; currentAudio.play();
  } }, "慢放");
}

function setFlipped(card, front, back, flipped) {
  card.classList.toggle("is-flipped", flipped);
  front.inert = flipped;
  back.inert = !flipped;
  (flipped ? back : front).querySelector("button, a")?.focus();
}
function phraseCard(p, video) {
  const front = h("div", { class: "face front" },
    h("div", { class: "card-top" }, h("span", { class: "tag " + p.category }, CATS[p.category] || p.category), p.level === 1 ? h("span", { class: "tag lv1" }, "第一周必会") : null),
    h("p", { class: "vi" }, p.phrase),
    h("p", { class: "reading", title: "拼音读法：辅音按汉语拼音读；箭头是声调" }, p.reading),
    h("div", { class: "actions" }, playButton(p), slowButton(p),
      h("button", { class: "btn primary", type: "button", onclick: (e) => { e.stopPropagation(); setFlipped(card, front, back, true); } }, "显示意思")),
    h("p", { class: "flip-hint" }, "先听、先猜，再翻面看中文。"));
  const back = h("div", { class: "face back" },
    h("p", { class: "zh" }, p.zh, p.en ? h("span", { class: "en" }, " · " + p.en) : null),
    p.usage ? h("p", { class: "usage" }, p.usage) : null,
    h("details", { onclick: (e) => e.stopPropagation() }, h("summary", {}, "原句与声调"),
      h("p", { class: "line" }, p.lineVi), h("p", { class: "line zh" }, p.lineZh), h("p", { class: "tones" }, p.tones)),
    h("div", { class: "actions" }, playButton(p),
      h("a", { class: "btn ghost", href: p.youtube || yt(video, p.startMs), target: "_blank", rel: "noopener", onclick: (e) => e.stopPropagation() }, `YouTube ${fmt(p.startMs)}`),
      h("button", { class: "btn", type: "button", onclick: (e) => { e.stopPropagation(); setFlipped(card, front, back, false); } }, "收回")));
  const card = h("article", { class: "flip" }, h("div", { class: "flip-inner" }, front, back));
  back.inert = true;
  return card;
}

function trackSwitch(route) {
  const show = SHOWS[route.show || ctx.show];
  const multi = isMultiShow(show?.id);
  const current = route.track || (multi ? null : state.track) || show?.tracks?.[0] || "short";
  const base = { lang: route.lang || ctx.lang, show: route.show || ctx.show };
  return h("span", { class: "tracks", "aria-label": t("track.label") },
    (show?.tracks || ["short", "long"]).map((id) => h("a", {
      href: href({ page: "track", ...base, track: id }),
      "aria-current": current === id ? "true" : null,
    }, t("track." + id))));
}

function userMenu() {
  const sel = (key, value, label) => h("label", {}, label + " ",
    h("select", { onchange: (e) => { localPrefs[key] = e.target.value; saveLocalPrefs(localPrefs); applyPrefs(); route({ transition: false, preserveScroll: true }); } },
      UI_LANGS.map((l) => h("option", { value: l, selected: l === value }, l === "zh" ? "中文" : "Tiếng Việt"))));
  return h("details", { class: "user-menu" },
    h("summary", { "aria-label": t("menu.ui") }, prefs.name ? t("menu.hello", { name: prefs.name }) : (prefs.uiLang === "vi" ? "VI" : "中")),
    h("div", { class: "user-menu-pop" }, sel("uiLang", prefs.uiLang, t("menu.ui")), sel("explainLang", prefs.explainLang, t("menu.explain"))));
}

function langName(lang) { return uiLang() === "vi" ? (lang.nameVi || lang.nameZh) : lang.nameZh; }
function langVariant(lang) { return uiLang() === "vi" ? (lang.variantVi || lang.variant) : lang.variant; }

function renderShell(route) {
  const onShow = route.page !== "notfound" && route.show && SHOWS[route.show];
  const lang = languageById(route.lang) || (onShow && languageById(SHOWS[route.show].language));
  const multi = onShow && isMultiShow(route.show);
  if (onShow) {
    ctx = { lang: route.lang, show: route.show, track: route.track || (multi ? "short" : state.track) || "short" };
    if (route.track && !multi) { state.track = route.track; save(); }
  }
  document.documentElement.lang = uiLang() === "vi" ? "vi" : "zh-CN";
  navEl.setAttribute("aria-label", t("nav.label"));
  brandEl.setAttribute("href", onShow ? href({ page: "show", lang: ctx.lang, show: ctx.show }) : "#/");
  brandEl.replaceChildren(
    h("span", { class: "brand-mark", "aria-hidden": "true" }, onShow ? (SHOWS[ctx.show].mark || "剧") : "剧"),
    onShow
      ? h("span", {}, langName(lang), h("small", {}, langVariant(lang)))
      : h("span", {}, t("brand.title"), h("small", {}, t("brand.sub"))),
  );

  const links = [h("a", { href: "#/", "data-nav": "home" }, t("nav.languages"))];
  if (onShow) {
    const base = { lang: ctx.lang, show: ctx.show };
    const track = ctx.track;
    links.push(
      h("a", { href: href({ page: "show", ...base }), "data-nav": "show" }, t("nav.show")),
      trackSwitch(route),
      h("a", { href: href({ page: "track", ...base, track }), "data-nav": "today" }, track === "long" && !multi ? "本周" : t("nav.today")),
      h("a", { href: href({ page: "plan", ...base, track }), "data-nav": "plan" }, t("nav.plan")),
      h("a", { href: href({ page: "parts", ...base }), "data-nav": "parts" }, t("nav.episodes")),
      h("a", { href: href({ page: "review", ...base }), "data-nav": "review" }, t("nav.review")),
    );
    if (!multi) {
      links.push(
        h("a", { href: href({ page: "scenes", ...base }), "data-nav": "scenes" }, "场景"),
        h("a", { href: href({ page: "search", ...base }), "data-nav": "search" }, "搜索"),
        h("a", { href: href({ page: "vlc", ...base }), "data-nav": "vlc" }, "VLC"),
      );
    }
  } else if (route.page !== "notfound" && route.lang) {
    links.push(h("a", { href: href({ page: "lang", lang: route.lang }), "data-nav": "lang" }, lang ? langName(lang) : t("nav.languages")));
  }
  links.push(userMenu());
  navEl.replaceChildren(...links);
  const navKey = { home: "home", lang: "lang", show: "show", track: "today", day: "today", week: "today", plan: "plan", stage: "plan", part: "parts", ep: "parts", parts: "parts", review: "review", scenes: "scenes", search: "search", vlc: "vlc", lesson: "today" }[route.page];
  navEl.querySelectorAll(":scope > a").forEach((a) => a.toggleAttribute("aria-current", a.dataset.nav === navKey));
  if (route.page === "home") document.title = t("brand.title");
  else if (route.page === "lang" && lang) document.title = `${langName(lang)} · ${t("brand.title")}`;
  else if (onShow) document.title = `${SHOWS[route.show].titleZh} · ${langName(lang)}`;
}

function plannedList(lang) {
  if (!lang.planned?.length) return null;
  return h("ul", { class: "planned" }, lang.planned.map((p) => h("li", {},
    h("b", {}, uiLang() === "vi" ? (p.titleVi || p.title) : p.title), " · ",
    h("span", { class: "muted" }, `${t("track." + (p.track === "short" ? "short" : "long"))} · ${uiLang() === "vi" ? p.noteVi : p.noteZh}`))));
}

function viewHome() {
  const list = homeLanguages(LANGUAGES, prefs);
  const filtered = prefs.visibleLangs && list.length < LANGUAGES.length;
  const canToggle = !!prefs.visibleLangs;
  return [
    h("section", { class: "hero reveal" },
      h("p", { class: "eyebrow" }, "Language school · by TV"),
      titleEl(t("brand.title")),
      h("p", { class: "lede" }, t("home.lede"))),
    h("div", { class: "lang-grid" }, list.map((lang) =>
      h("a", { class: "lang-card reveal " + lang.status, href: href({ page: "lang", lang: lang.id }), "data-tilt": "1" },
        h("span", { class: "pill " + (lang.status === "ready" ? "on" : "wait") }, lang.status === "ready" ? t("lang.ready") : t("lang.coming")),
        h("div", { class: "native" }, lang.nameNative),
        h("div", { class: "name" }, langName(lang)),
        h("div", { class: "variant" }, langVariant(lang),
          lang.status === "coming" && lang.planned?.length ? ` · ${t("lang.planned")}：${lang.planned.map((p) => uiLang() === "vi" ? (p.titleVi || p.title) : p.title).join(" / ")}` : ""),
      ))),
    canToggle ? h("div", { class: "actions reveal" }, h("button", { class: "btn ghost", type: "button", onclick: () => {
      localPrefs.showAllLangs = !localPrefs.showAllLangs; saveLocalPrefs(localPrefs); applyPrefs(); route({ transition: false, preserveScroll: true });
    } }, filtered ? t("home.showAll") : t("home.showMine"))) : null,
  ];
}

function viewLang(langId) {
  const lang = languageById(langId);
  if (!lang) return viewNotFound();
  if (isComingLanguage(langId)) {
    return [h("section", { class: "panel placeholder reveal" },
      h("p", { class: "eyebrow" }, langVariant(lang)),
      titleEl(`${langName(lang)} · ${lang.nameNative}`),
      h("p", { class: "lede" }, t("lang.comingLede")),
      plannedList(lang),
      h("div", { class: "actions" }, h("a", { class: "btn primary", href: "#/" }, t("lang.back"))))];
  }
  const shows = showsForLanguage(langId);
  const vn = langId === "vi";
  return [
    h("section", { class: "hero reveal" },
      h("p", { class: "eyebrow" }, langVariant(lang)),
      titleEl(langName(lang)),
      h("p", { class: "lede" }, vn ? "目前开放的教材是《Về nhà đi con》（回家吧，孩子）。同一部剧有两条轨道：12 周短期版，和按五年生活排的长期版。"
        : t("lang.ledeShow", { title: shows[0]?.titleNative || "" }))),
    h("div", { class: "track-grid" }, shows.map((show) =>
      h("a", { class: "track-card reveal", href: href({ page: "show", lang: langId, show: show.id }), "data-tilt": "1" },
        h("p", { class: "length" }, show.kind === "multi" ? t("lang.episodesN", { n: show.episodes }) : `${show.parts} 段 · 两条轨道`),
        h("h2", {}, show.kind === "multi" ? show.titleNative : show.titleZh),
        h("p", {}, show.kind === "multi" ? [show.titleEn, uiLang() === "vi" ? show.titleVi : show.titleZh].filter((x) => x && x !== show.titleNative).join(" · ") : show.titleNative),
        h("p", { class: "muted" }, vn ? "点进去选择短期或长期。" : t("lang.pickShow"))))),
    lang.planned?.length ? h("section", { class: "panel reveal" }, h("h2", {}, t("lang.later")), plannedList(lang)) : null,
  ];
}

function viewShow() {
  const show = SHOWS[ctx.show];
  const shortDone = state.doneDays.length;
  const longDone = longState.doneWeeks.length;
  return [
    h("section", { class: "hero reveal" },
      h("p", { class: "eyebrow" }, "VTV1 / VFC · 2019"),
      titleEl(`《${show.titleNative}》`),
      h("p", { class: "lede" }, `${show.titleZh}。先选一条轨道：短期版 12 周过完全剧；长期版用同一 82 段做五年精读，从生存句走到工厂职场和接近母语的听力。`)),
    h("div", { class: "track-grid" },
      h("a", { class: "track-card reveal", href: go({ page: "track", track: "short" }), "data-tilt": "1" },
        h("p", { class: "length" }, TRACKS.short.lengthZh),
        h("h2", {}, TRACKS.short.nameZh),
        h("p", {}, TRACKS.short.blurb),
        progressBar(shortDone, 84),
        h("p", { class: "muted" }, `已完成 ${shortDone} / 84 天`)),
      h("a", { class: "track-card long reveal", href: go({ page: "track", track: "long" }), "data-tilt": "1" },
        h("p", { class: "length" }, TRACKS.long.lengthZh),
        h("h2", {}, TRACKS.long.nameZh),
        h("p", {}, TRACKS.long.blurb),
        progressBar(longDone, LONG_TOTAL_WEEKS),
        h("p", { class: "muted" }, `已完成 ${longDone} / ${LONG_TOTAL_WEEKS} 周`))),
  ];
}

async function viewShortHome() {
  const d = nextDay(DAYS, state.doneDays);
  const wk = WEEKS[d.week - 1];
  await loadData();
  const due = dueCount();
  return [
    h("section", { class: "hero reveal" },
      h("p", { class: "eyebrow" }, `短期版 · 第 ${d.week} 周 · 第 ${d.day} 天 / 84`),
      titleEl("今天的课"),
      h("p", { class: "lede" }, "用原剧原声学北越口语：先学当天的日常用语，再用 VLC 配双语字幕看一段，最后复习。"),
      h("div", { class: "actions" },
        h("a", { class: "btn primary", href: go({ page: "day", day: d.day }) }, "开始今天的课"),
        h("a", { class: "btn", href: go({ page: "review" }) }, `复习${data ? `（到期 ${due}）` : ""}`))),
    h("section", { class: "panel reveal" }, h("h2", {}, `本周：${wk.title}`), h("p", {}, wk.focus),
      progressBar(state.doneDays.length, 84),
      h("p", { class: "muted" }, `已完成 ${state.doneDays.length} / 84 天 · 已学卡片 ${Object.keys(state.srs).length}`)),
    data ? null : loginCard(),
  ];
}

async function viewDay(n) {
  const d = DAYS[n - 1]; if (!d) return [h("p", {}, "没有这一天。")];
  const done = state.doneDays.includes(d.day);
  const out = [h("p", { class: "eyebrow reveal" }, `短期版 · 第 ${d.week} 周 · ${WEEKS[d.week - 1].title}`), h("h1", { class: "reveal" }, `第 ${d.day} 天`)];
  if (d.pron) {
    out.push(...lessonView(d.pron));
    await loadData();
    if (data) out.push(...corpusExamples(LESSONS[d.pron].practice));
  }
  if (d.reviewOnly) out.push(h("section", { class: "panel reveal" }, h("p", {}, "今天只复习：把到期卡片做完，再回看第 1 段里最难的 5 句。"), h("a", { class: "btn primary", href: go({ page: "review" }) }, "去复习")));
  if (d.parts.length) {
    await loadData();
    if (!data) out.push(loginCard());
    else for (const pn of d.parts) out.push(...(await partBlock(pn, true)));
  }
  out.push(h("div", { class: "actions reveal" }, h("button", { class: "btn primary", type: "button", onclick: () => {
    if (!done) state.doneDays.push(d.day); else state.doneDays = state.doneDays.filter((x) => x !== d.day);
    save(); route({ transition: false, preserveScroll: true });
  } }, done ? "✓ 已完成（点击取消）" : "完成今天"), d.day < 84 ? h("a", { class: "btn", href: go({ page: "day", day: d.day + 1 }) }, "下一天 →") : null));
  return out;
}

function lessonView(key) {
  const L = LESSONS[key];
  if (!L) return [h("p", {}, "没有这一课。")];
  return [h("section", { class: "panel reveal" }, h("h2", {}, L.title), h("p", {}, L.intro),
    h("div", { class: "table-wrap" }, h("table", {}, h("tbody", {}, L.rows.map((r) => h("tr", {}, r.map((c, i) => h(i ? "td" : "th", {}, c))))))),
    h("h3", {}, "跟读练习"),
    h("div", { class: "chips" }, L.practice.map((t) => h("button", { class: "chip", type: "button", onclick: () => { if (!speak(t)) alert("这台设备没有越南语语音，先看拼音读法练。"); } }, t))),
    h("p", { class: "muted" }, "练习按钮用设备自带的越南语合成音（如有）。从第 6 天起全部用原剧原声。"))];
}

function corpusExamples(practice) {
  const norm = (t) => t.toLowerCase().normalize("NFC");
  const words = new Set(practice.flatMap((t) => norm(t).split(/\s+/)).filter((w) => w.length > 1));
  const picks = data.phrases.filter((p) => p.clip && p.level === 1 && norm(p.phrase).split(/\s+/).some((w) => words.has(w.replace(/[.,!?]/g, ""))));
  if (!picks.length) return [];
  return [h("h3", { class: "section-title" }, "原剧里的真实发音"), h("div", { class: "cards" }, picks.slice(0, 9).map((p) => phraseCard(p, data.parts.find((m) => m.part === p.part).videoId)))];
}

async function partBlock(n, compact = false) {
  const meta = data.parts.find((p) => p.part === n); if (!meta) return [];
  const phrases = data.phrases.filter((p) => p.part === n);
  const watched = !!state.watched[n];
  return [h("section", { class: "panel reveal" },
    h("h2", {}, `P${String(n).padStart(2, "0")} · ${meta.titleZh || meta.title}`),
    h("p", { class: "muted" }, meta.title, ` · ${Math.round(meta.duration / 60)} 分钟 · ${meta.lines} 句台词${meta.source === "whisper" ? " · 字幕由 Whisper 识别" : ""}`),
    h("div", { class: "actions" },
      h("a", { class: "btn primary", href: `https://www.youtube.com/watch?v=${meta.videoId}`, target: "_blank", rel: "noopener" }, "在 YouTube 看"),
      h("a", { class: "btn", href: meta.srt, download: meta.srt.split("/").pop() }, "下载双语字幕 .srt"),
      h("a", { class: "btn ghost", href: go({ page: "vlc" }) }, "VLC 怎么用"),
      compact ? h("a", { class: "btn ghost", href: go({ page: "part", part: n }) }, "全文台词") : null,
      h("button", { class: "btn ghost", type: "button", onclick: () => { state.watched[n] = !watched; save(); route({ transition: false, preserveScroll: true }); } }, watched ? "✓ 已看" : "标记已看")),
    h("h3", { class: "section-title" }, `今日用语 ${phrases.length} 条`),
    h("div", { class: "cards" }, phrases.map((p) => phraseCard(p, meta.videoId))))];
}

async function viewPart(n) {
  await loadData(); if (!data) return [loginCard()];
  const meta = data.parts.find((p) => p.part === n);
  if (!meta) return [h("p", {}, "没有这一段。"), h("a", { class: "btn", href: go({ page: "parts" }) }, "全部剧集")];
  const out = await partBlock(n);
  const part = await loadPart(n);
  out.push(h("section", { class: "panel reveal" }, h("h2", {}, "双语全文"), h("p", { class: "muted" }, "点时间跳到 YouTube 对应位置。自动识别 + 机器翻译，未人工校对。"),
    h("ol", { class: "transcript" }, part.lines.map((L) => h("li", {},
      h("a", { href: yt(meta.videoId, L.startMs), target: "_blank", rel: "noopener", class: "ts" }, fmt(L.startMs)),
      h("span", { class: "vi" }, L.vi), h("span", { class: "zh" }, L.zh))))));
  return out;
}

async function viewParts() {
  await loadData(); if (!data) return [h("h1", {}, "全部 82 段"), loginCard()];
  return [h("h1", { class: "reveal" }, "全部 82 段"), h("p", { class: "muted reveal" }, "来源：VFC Official YouTube 播放列表（按剧情顺序）。字幕时间轴只对这个版本有效。"),
    h("ol", { class: "part-list reveal" }, data.parts.map((m) => h("li", {},
      h("a", { href: go({ page: "part", part: m.part }) }, h("b", {}, `P${String(m.part).padStart(2, "0")}`), " ", m.titleZh || m.title),
      h("span", { class: "muted" }, ` ${Math.round(m.duration / 60)} 分`), state.watched[m.part] ? h("span", { class: "tag lv1" }, "已看") : null,
      h("a", { class: "mini", href: `https://www.youtube.com/watch?v=${m.videoId}`, target: "_blank", rel: "noopener" }, "YouTube"),
      h("a", { class: "mini", href: m.srt, download: m.srt.split("/").pop() }, "SRT"))))];
}

function unlockedParts() {
  if (ctx.track === "long") {
    const cur = nextWeek(LONG_WEEKS, longState.doneWeeks);
    return new Set(LONG_WEEKS.filter((w) => longState.doneWeeks.includes(w.week) || w.week === cur.week).flatMap((w) => w.parts));
  }
  return new Set(DAYS.filter((d) => state.doneDays.includes(d.day) || d.day === nextDay(DAYS, state.doneDays).day).flatMap((d) => d.parts));
}
function reviewPhraseIds() {
  if (!data) return [];
  const unlocked = unlockedParts();
  return data.phrases.filter((p) => state.srs[p.id] || unlocked.has(p.part)).sort((a, b) => a.level - b.level || a.part - b.part).map((p) => p.id);
}
function dueCount() {
  return data ? queue(reviewPhraseIds(), state.srs).due.length : 0;
}

async function viewReview() {
  await loadData(); if (!data) return [h("h1", {}, "复习"), loginCard()];
  const day = today();
  if (state.newToday.day !== day) state.newToday = { day, n: 0 };
  const ids = reviewPhraseIds();
  const q = queue(ids, state.srs, { day, newLimit: state.newLimit, newSeenToday: state.newToday.n });
  const id = q.due[0] || q.fresh[0];
  const wrap = [h("h1", { class: "reveal" }, "复习"), h("p", { class: "muted reveal" }, `到期 ${q.due.length} · 今天还可学新卡 ${q.fresh.length} · 新卡上限 `,
    h("select", { onchange: (e) => { state.newLimit = +e.target.value; save(); route({ transition: false, preserveScroll: true }); } }, [5, 10, 15, 20, 30].map((v) => h("option", { value: v, selected: v === state.newLimit }, v))), " 张/天")];
  if (!id) return [...wrap, h("section", { class: "panel reveal" }, h("p", {}, "今天的复习做完了。新卡来自已完成和当前的课程。"), h("a", { class: "btn", href: go({ page: "track", track: ctx.track }) }, "回轨道首页"))];
  const p = data.phrases.find((x) => x.id === id);
  const isNew = !state.srs[id];
  const back = h("div", { class: "back", hidden: true },
    h("p", { class: "vi" }, p.phrase), h("p", { class: "reading" }, p.reading), h("p", { class: "zh" }, p.zh),
    h("p", { class: "line" }, p.lineVi), h("p", { class: "line zh" }, p.lineZh),
    h("div", { class: "actions grades" }, [["again", "忘了"], ["hard", "难"], ["good", "会"], ["easy", "简单"]].map(([g, t]) =>
      h("button", { class: "btn grade " + g, type: "button", onclick: () => {
        state.srs[id] = review(state.srs[id], g, day); if (isNew) state.newToday.n += 1; save(); route({ transition: false });
      } }, t))));
  const front = h("section", { class: "panel flash reveal" },
    h("p", { class: "eyebrow" }, isNew ? "新卡" : "复习", " · ", CATS[p.category] || ""),
    p.clip ? h("p", {}, "先听原声，想想是什么意思：") : h("p", { class: "vi" }, p.phrase),
    h("div", { class: "actions" }, playButton(p), h("button", { class: "btn primary", type: "button", onclick: (e) => { back.hidden = false; e.currentTarget.remove(); } }, "看答案")),
    back);
  if (p.clip) setTimeout(() => front.querySelector(".play")?.click(), 50);
  return [...wrap, front];
}

function viewPlan() {
  return [h("h1", { class: "reveal" }, "12 周短期课程"), h("p", { class: "reveal" }, "每天约 45 分钟：日常用语（10 分钟）→ VLC 双语字幕看一段（30 分钟）→ 复习（5–10 分钟）。第 8 周起第二遍关字幕。"),
    ...WEEKS.map((w) => h("section", { class: "panel week reveal" }, h("h2", {}, `第 ${w.week} 周 · ${w.title}`), h("p", {}, w.focus),
      h("div", { class: "chips" }, DAYS.filter((d) => d.week === w.week).map((d) => h("a", { class: "chip" + (state.doneDays.includes(d.day) ? " done" : ""), href: go({ page: "day", day: d.day }) },
        `D${d.day}${d.pron ? " 发音" : d.reviewOnly ? " 复习" : " P" + d.parts.join("+P")}`)))))];
}

async function viewLongHome() {
  const w = nextWeek(LONG_WEEKS, longState.doneWeeks);
  const stage = stageById(w.stage);
  const done = longState.doneWeeks.length;
  await loadData();
  return [
    h("section", { class: "hero reveal" },
      h("p", { class: "eyebrow" }, `长期版 · ${stage.yearHint} · 第 ${w.week} / ${LONG_TOTAL_WEEKS} 周`),
      titleEl(stage.title),
      h("p", { class: "lede" }, stage.goal),
      h("div", { class: "actions" },
        h("a", { class: "btn primary", href: go({ page: "week", week: w.week }) }, "开始本周"),
        h("a", { class: "btn", href: go({ page: "plan", track: "long" }) }, "五年总表"),
        h("a", { class: "btn", href: go({ page: "review" }) }, `复习${data ? `（到期 ${dueCount()}）` : ""}`))),
    h("section", { class: "panel reveal" },
      h("h2", {}, `本阶段：${stage.title}`),
      h("p", {}, stage.grammar),
      h("p", { class: "muted" }, "技能：" + stage.skills.join(" · ")),
      progressBar(done, LONG_TOTAL_WEEKS),
      h("p", { class: "muted" }, `已完成 ${done} / ${LONG_TOTAL_WEEKS} 周`)),
    data ? null : loginCard(),
  ];
}

function viewLongPlan() {
  return [
    h("h1", { class: "reveal" }, "五年长期课程"),
    h("p", { class: "reveal" }, "同一 82 段、同一批用语。前四年按阶段精读并回看，第五年循环保持。职场阶段配自编工厂 IT 补充包（不是剧中台词）。"),
    progressBar(longState.doneWeeks.length, LONG_TOTAL_WEEKS),
    h("div", { class: "stage-list" }, LONG_STAGES.map((s) => {
      const weeks = LONG_WEEKS.filter((w) => w.stage === s.id);
      const done = weeks.filter((w) => longState.doneWeeks.includes(w.week)).length;
      return h("section", { class: "panel stage-card reveal" },
        h("p", { class: "eyebrow" }, `${s.yearHint} · ${s.months} 个月 · P${String(s.partStart).padStart(2, "0")}–P${String(s.partEnd).padStart(2, "0")}${s.rewatchBefore ? "，并回看 P01–P" + String(s.rewatchBefore).padStart(2, "0") : s.cycle ? "，全剧循环" : ""}`),
        h("h2", {}, h("a", { href: go({ page: "stage", stage: s.id }) }, s.title)),
        h("p", {}, s.goal),
        h("p", { class: "muted" }, s.grammar),
        progressBar(done, s.weekCount),
        h("div", { class: "chips" }, weeks.map((w) => h("a", {
          class: "chip" + (longState.doneWeeks.includes(w.week) ? " done" : ""),
          href: go({ page: "week", week: w.week }),
        }, weekChipLabel(w)))));
    })),
  ];
}

function viewLongStage(id) {
  const s = stageById(id);
  if (!s) return [h("p", {}, "没有这一阶段。"), h("a", { href: go({ page: "plan", track: "long" }) }, "回总表")];
  const weeks = LONG_WEEKS.filter((w) => w.stage === s.id);
  const done = weeks.filter((w) => longState.doneWeeks.includes(w.week)).length;
  return [
    h("p", { class: "eyebrow reveal" }, `${s.yearHint} · ${s.months} 个月`),
    h("h1", { class: "reveal" }, s.title),
    h("p", { class: "lede reveal" }, s.goal),
    h("section", { class: "panel reveal" }, h("h2", {}, "这一阶段练什么"), h("p", {}, s.grammar), h("p", { class: "muted" }, s.skills.join(" · ")), progressBar(done, s.weekCount)),
    h("div", { class: "chips reveal" }, weeks.map((w) => h("a", {
      class: "chip" + (longState.doneWeeks.includes(w.week) ? " done" : ""),
      href: go({ page: "week", week: w.week }),
    }, weekChipLabel(w)))),
  ];
}

async function viewLongWeek(n) {
  const w = LONG_WEEKS[n - 1];
  if (!w) return [h("p", {}, "没有这一周。")];
  const stage = stageById(w.stage);
  const done = longState.doneWeeks.includes(w.week);
  const out = [
    h("p", { class: "eyebrow reveal" }, `长期版 · ${stage.title} · ${stage.yearHint}`),
    h("h1", { class: "reveal" }, `第 ${w.week} 周`),
    h("section", { class: "panel reveal" }, h("h2", {}, WEEK_MODES[w.mode].slice(0, 2) + "周"), h("p", {}, WEEK_MODES[w.mode]), h("p", { class: "muted" }, stage.grammar)),
  ];
  if (w.topic) {
    out.push(h("section", { class: "panel work-pack reveal" },
      h("p", { class: "eyebrow" }, "自编职场补充包 · 非剧中台词（Chilisin 工厂 IT）"),
      h("h2", {}, w.topic.title),
      h("p", { class: "vi" }, w.topic.vi),
      w.topic.reading ? h("p", { class: "reading" }, w.topic.reading) : null,
      h("p", { class: "zh" }, w.topic.zh),
      h("p", { class: "muted" }, w.topic.note),
      h("div", { class: "actions" }, h("button", { class: "btn play tts", type: "button", onclick: () => { if (!speak(w.topic.vi)) alert("这台设备没有越南语语音，可按拼音读法练。"); } }, "▶ 合成音"))));
  }
  if (w.parts.length) {
    await loadData();
    if (!data) out.push(loginCard());
    else for (const pn of w.parts) out.push(...(await partBlock(pn, true)));
  }
  out.push(h("div", { class: "actions reveal" }, h("button", { class: "btn primary", type: "button", onclick: () => {
    if (!done) longState.doneWeeks.push(w.week); else longState.doneWeeks = longState.doneWeeks.filter((x) => x !== w.week);
    saveLong(); route({ transition: false, preserveScroll: true });
  } }, done ? "✓ 本周已完成（点击取消）" : "完成本周"),
    h("a", { class: "btn", href: go({ page: "review" }) }, "去复习"),
    w.week < LONG_TOTAL_WEEKS ? h("a", { class: "btn", href: go({ page: "week", week: w.week + 1 }) }, "下一周 →") : null));
  return out;
}

async function viewScenes(cat) {
  await loadData(); if (!data) return [h("h1", {}, "按场景"), loginCard()];
  cat = cat || "food";
  const list = data.phrases.filter((p) => p.category === cat).sort((a, b) => a.level - b.level || a.part - b.part);
  return [h("h1", { class: "reveal" }, "按场景学"), h("div", { class: "chips reveal" }, Object.entries(CATS).map(([k, v]) => h("a", { class: "chip" + (k === cat ? " done" : ""), href: go({ page: "scenes", cat: k }) }, `${v} ${data.phrases.filter((p) => p.category === k).length}`))),
    h("div", { class: "cards" }, list.slice(0, 120).map((p) => phraseCard(p, data.parts.find((m) => m.part === p.part).videoId))),
    list.length > 120 ? h("p", { class: "muted" }, `只显示前 120 条（共 ${list.length}）。`) : null];
}

async function viewSearch(qs) {
  await loadData(); if (!data) return [h("h1", {}, "全剧搜索"), loginCard()];
  const input = h("input", { type: "search", placeholder: "输入越南语（可不带声调）或中文，例如 bao nhiêu / 多少钱", value: qs || "" });
  const results = h("ol", { class: "transcript" });
  const norm = (s) => s.normalize("NFD").replace(/[\u0300-\u036f]/g, "").replace(/đ/gi, "d").toLowerCase();
  const run = async () => {
    const q = input.value.trim(); results.replaceChildren(); if (q.length < 2) return;
    if (!searchIndex) searchIndex = await fetch(`${dataBase()}/search.json`, { credentials: "same-origin" }).then((r) => r.json());
    const nq = norm(q); let n = 0;
    for (const [part, ms, vi, zh] of searchIndex) {
      if (!(norm(vi).includes(nq) || zh.includes(q))) continue;
      const m = data.parts.find((x) => x.part === part);
      results.append(h("li", {}, h("a", { class: "ts", href: yt(m.videoId, ms), target: "_blank", rel: "noopener" }, `P${part} ${fmt(ms)}`), h("span", { class: "vi" }, vi), h("span", { class: "zh" }, zh)));
      if (++n >= 200) break;
    }
    if (!n) results.append(h("li", {}, "没找到。"));
  };
  input.addEventListener("change", run);
  if (qs) setTimeout(run, 0);
  return [h("h1", { class: "reveal" }, "全剧搜索"), h("p", { class: "muted reveal" }, "在 82 段台词里找一个词出现在哪些场景，点时间去 YouTube 听原声。"), input, results];
}

async function viewVlc() {
  const md = await fetch("./vlc.html").then((r) => r.text());
  const box = h("section", { class: "panel prose reveal" }); box.innerHTML = md; return [box];
}

function viewNotFound() {
  return [h("p", { class: "reveal" }, "页面不存在。"), h("a", { class: "btn", href: "#/" }, "回语言首页")];
}

async function render(route) {
  if (route.show && isMultiShow(route.show) && route.page !== "notfound") return renderMulti(route);
  switch (route.page) {
    case "home": return viewHome();
    case "lang": return viewLang(route.lang);
    case "show": return viewShow();
    case "track": return route.track === "long" ? viewLongHome() : viewShortHome();
    case "day": return viewDay(route.day);
    case "week": return viewLongWeek(route.week);
    case "stage": return viewLongStage(route.stage);
    case "plan": return route.track === "long" ? viewLongPlan() : viewPlan();
    case "part": return viewPart(route.part);
    case "parts": return viewParts();
    case "review": return viewReview();
    case "scenes": return viewScenes(route.cat);
    case "search": return viewSearch(route.q);
    case "vlc": return viewVlc();
    case "lesson": return lessonView(route.lesson);
    default: return viewNotFound();
  }
}

let routeGen = 0;
async function route({ transition = true, preserveScroll = false } = {}) {
  const rec = matchRoute(location.hash || "#/");
  renderShell(rec);
  const gen = ++routeGen;
  const nodes = await render(rec);
  if (gen !== routeGen) return;
  if (transition) await swapMain(main, nodes);
  else paintMain(main, nodes);
  if (!preserveScroll) window.scrollTo(0, 0);
}

// Per-user defaults: server suggestion (/private/me.json, Access-protected) + localStorage overrides.
let me = { ...DEFAULT_ME };
const localPrefs = loadLocalPrefs();
let prefs = effectivePrefs(me, localPrefs);
function applyPrefs() { prefs = effectivePrefs(me, localPrefs); setUiLang(prefs.uiLang); }
applyPrefs();
initMulti({ rerender: (opts) => route(opts), prefs: () => prefs });

initMotion();
window.addEventListener("hashchange", () => route());
route();
fetchMe().then((got) => {
  const before = JSON.stringify(prefs);
  me = got; applyPrefs();
  if (JSON.stringify(prefs) !== before) route({ transition: false, preserveScroll: true });
});
