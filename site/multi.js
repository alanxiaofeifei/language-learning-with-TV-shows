// Views for generic shows (kind "multi"). Data: public episode list under
// /shows/<id>/episodes.json, private lines/phrases under /private/shows/<id>/ (Access + Worker JWT).
import { h, fmt, titleEl, progressBar } from "./lib/dom.js";
import { SHOWS, href } from "./lib/catalog.js";
import { t, pick, uiLang } from "./lib/i18n.js";
import { buildShowDays, nextShowDay, SHORT_WEEKS, LONG_OUTLINES, SHORT_DAYS } from "./lib/show-curriculum.js";
import { review, queue, today } from "./lib/srs.js";

import { DEFAULT_ME } from "./lib/prefs.js";

let env = { rerender: () => {}, prefs: () => DEFAULT_ME };
export function initMulti(e) { env = { ...env, ...e }; }

// ---- per-show state (localStorage, keyed per show) ----
const stores = {};
function store(id) {
  if (!stores[id]) {
    const base = { doneDays: [], watched: {}, srs: {}, newToday: { day: 0, n: 0 }, newLimit: 15, toggles: null, track: "short" };
    try { stores[id] = { ...base, ...JSON.parse(localStorage.getItem(`tv:show:${id}:v1`) || "{}") }; }
    catch { stores[id] = base; }
  }
  return stores[id];
}
function persist(id) { try { localStorage.setItem(`tv:show:${id}:v1`, JSON.stringify(store(id))); } catch { /* ignore */ } }
// Last track picked for a show (read with one argument, set with two), so nav keeps it across pages.
export function multiTrack(id, track) {
  const st = store(id);
  if (track === "short" || track === "long") { if (st.track !== track) { st.track = track; persist(id); } }
  return st.track === "long" ? "long" : "short";
}

// ---- data ----
const cache = {};
function c(id) { return (cache[id] ||= { pub: null, pubPromise: null, idx: null, idxErr: null, idxPromise: null, eps: {} }); }
// Both loaders share one in-flight request. Failures are not cached (except "login" for the index),
// so the next view retries after a transient network error.
async function loadPublic(show) {
  const k = c(show.id);
  if (k.pub) return k.pub;
  k.pubPromise ||= (async () => {
    try { const r = await fetch(`${show.publicBase}/episodes.json`); if (r.ok) k.pub = await r.json(); }
    catch { /* retry next time */ }
    finally { k.pubPromise = null; }
    return k.pub || { episodes: [] };
  })();
  return k.pubPromise;
}
async function loadIndex(show) {
  const k = c(show.id);
  if (k.idx || k.idxErr === "login") return k.idx;
  k.idxPromise ||= (async () => {
    try {
      const r = await fetch(`${show.dataBase}/index.json`, { credentials: "same-origin", redirect: "manual" });
      if (r.type === "opaqueredirect" || r.status === 0 || r.status === 401 || r.status === 403) throw new Error("login");
      if (!r.ok) throw new Error("http " + r.status);
      k.idx = await r.json(); k.idxErr = null;
    } catch (e) { k.idxErr = e.message === "login" ? "login" : "error"; }
    finally { k.idxPromise = null; }
    return k.idx;
  })();
  return k.idxPromise;
}
async function loadEp(show, rec) {
  const k = c(show.id);
  if (!k.eps[rec.code]) {
    k.eps[rec.code] = fetch(rec.file, { credentials: "same-origin" })
      .then((r) => { if (!r.ok) throw new Error("http " + r.status); return r.json(); })
      .catch((e) => { delete k.eps[rec.code]; throw e; });
  }
  return k.eps[rec.code];
}
function epList(show) {
  const k = c(show.id);
  const built = new Map((k.idx?.episodes || []).map((e) => [e.n, e]));
  const pub = k.pub?.episodes || [];
  const list = pub.length ? pub.map((e) => ({ ...e, ...(built.get(e.n) || {}) })) : [...built.values()];
  return list.sort((a, b) => a.n - b.n);
}

// ---- small pieces ----
const isYt = (show) => show.source === "youtube-official";
const ytUrl = (id, ms = 0) => `https://www.youtube.com/watch?v=${id}` + (ms > 0 ? `&t=${Math.max(0, Math.floor(ms / 1000) - 2)}s` : "");
const go = (show, parts) => href({ lang: show.language, show: show.id, ...parts });
const channelName = (show) => (uiLang() === "vi" ? show.channelVi || show.channel : show.channel);
const showTitle = (show) => (show.language === "zh" ? `《${show.titleNative}》` : show.titleNative);
function epLabel(show, e) {
  return isYt(show) ? t("ep.title", { n: e.n }) : `${e.code}${e.title ? " · " + e.title : ""}`;
}
function loginCard(show) {
  const err = c(show.id).idxErr;
  return h("section", { class: "panel login reveal" },
    h("h2", {}, err === "error" ? t("login.error") : t("login.need")),
    h("p", {}, t("login.body")),
    h("a", { class: "btn primary", href: "/private/login.html" }, t("login.btn")));
}
function watchPanel(show) {
  if (isYt(show)) {
    return h("section", { class: "panel notice reveal" },
      h("p", {}, t("show.officialNote", { channel: channelName(show) || "YouTube" })),
      show.playlist ? h("div", { class: "actions" },
        h("a", { class: "btn", href: `https://www.youtube.com/playlist?list=${show.playlist}`, target: "_blank", rel: "noopener" }, t("show.playlist"))) : null);
  }
  return h("section", { class: "panel notice reveal" },
    h("p", {}, t("show.textOnly")),
    show.watch ? h("div", { class: "actions" },
      h("a", { class: "btn primary", href: show.watch.url, target: "_blank", rel: "noopener" }, `${t("show.watchOwn")} · ${show.watch.name}`)) : h("p", {}, t("show.watchOwn")),
    h("p", { class: "muted" }, t("show.timesApprox")));
}
export function readerLanguages(show, prefs, available = show.langs ?? [show.language]) {
  const hidden = prefs.hideLangs ?? DEFAULT_ME.hideLangs;
  return available.filter((k) => k === show.language || ((show.langs ?? available).includes(k) && !hidden.includes(k)));
}
export function explainOf(show, p, prefs) {
  const allowed = readerLanguages(show, prefs);
  const preferred = prefs.explainLang === "vi" ? "vi" : "zh";
  const other = preferred === "vi" ? "zh" : "vi";
  const field = (key, langs) => langs.filter((k) => allowed.includes(k)).map((k) => p[`${key}_${k}`]).find(Boolean) || "";
  return {
    meaning: field("meaning", [preferred, "en", other]),
    explain: field("explain", [preferred, other]),
    usage: field("usage", [preferred, other]),
  };
}

let currentAudio = null;
function playClip(src, rate = 1) { currentAudio?.pause(); currentAudio = new Audio(src); currentAudio.playbackRate = rate; currentAudio.play().catch(() => {}); }
function clipButtons(p) {
  if (!p.clip) return [];
  return [
    h("button", { class: "btn play", type: "button", onclick: (e) => { e.stopPropagation(); playClip(p.clip); } }, t("card.play")),
    h("button", { class: "btn ghost", type: "button", onclick: (e) => { e.stopPropagation(); playClip(p.clip, 0.7); } }, t("card.slow")),
  ];
}
function timeLink(show, ep, ms) {
  if (isYt(show) && ep?.youtubeId) return h("a", { class: "btn ghost", href: ytUrl(ep.youtubeId, ms), target: "_blank", rel: "noopener", onclick: (e) => e.stopPropagation() }, `YouTube ${fmt(ms)}`);
  return h("span", { class: "muted", title: t("show.timesApprox") }, `≈ ${fmt(ms)}`);
}
function sourceLines(show, p) {
  const lt = p.lineText || {};
  return readerLanguages(show, env.prefs()).filter((k) => lt[k]).map((k) => h("p", { class: "line l-" + k }, lt[k]));
}
function setFlipped(card, front, back, flipped) {
  card.classList.toggle("is-flipped", flipped);
  front.inert = flipped; back.inert = !flipped;
  (flipped ? back : front).querySelector("button, a")?.focus();
}
function phraseCard(show, p, ep) {
  const x = explainOf(show, p, env.prefs());
  const front = h("div", { class: "face front" },
    h("div", { class: "card-top" }, p.level ? h("span", { class: "tag level" }, p.level) : null, h("span", { class: "tag" }, t("card.at", { ep: isYt(show) ? t("ep.title", { n: p.ep }) : p.code, t: fmt(p.start) }))),
    h("p", { class: "vi phrase-" + show.language }, p.phrase),
    (p.py || p.reading) ? h("p", { class: "reading" }, p.py || p.reading) : null,
    h("div", { class: "actions" }, ...clipButtons(p),
      h("button", { class: "btn primary", type: "button", onclick: (e) => { e.stopPropagation(); setFlipped(card, front, back, true); } }, t("card.show"))),
    h("p", { class: "flip-hint" }, t("card.hint")));
  const back = h("div", { class: "face back" },
    x.meaning ? h("p", { class: "zh" }, h("b", {}, x.meaning)) : null,
    x.explain ? h("p", { class: "usage" }, x.explain) : null,
    h("details", { onclick: (e) => e.stopPropagation() }, h("summary", {}, `${t("card.usage")} · ${t("card.source")}`),
      x.usage ? h("p", { class: "usage" }, x.usage) : null, ...sourceLines(show, p)),
    h("div", { class: "actions" }, ...clipButtons(p).slice(0, 1), timeLink(show, ep, p.start),
      h("button", { class: "btn", type: "button", onclick: (e) => { e.stopPropagation(); setFlipped(card, front, back, false); } }, t("card.hide"))));
  const card = h("article", { class: "flip" }, h("div", { class: "flip-inner" }, front, back));
  back.inert = true;
  return card;
}

// ---- views ----
async function viewShow(show) {
  const st = store(show.id);
  await Promise.all([loadPublic(show), loadIndex(show)]);
  const stages = LONG_OUTLINES[show.language] || [];
  const next = stages.filter((s) => s.status === "planned").map((s) => uiLang() === "vi" ? s.showVi || s.show : s.show).join(" → ");
  const techStage = show.id === "silicon-valley" && stages.find((s) => s.showId === show.id);
  const subtitle = [show.titleEn, uiLang() === "vi" ? show.titleVi : show.titleZh].filter((x) => x && x !== show.titleNative).join(" · ");
  return [
    h("section", { class: "hero reveal" },
      h("p", { class: "eyebrow" }, [channelName(show), show.year].filter(Boolean).join(" · ")),
      titleEl(showTitle(show)),
      subtitle ? h("p", { class: "lede" }, subtitle) : null,
      techStage ? h("p", {}, pick(techStage.goal)) : null),
    h("div", { class: "track-grid" },
      h("a", { class: "track-card reveal", href: go(show, { page: "track", track: "short" }), "data-tilt": "1" },
        h("p", { class: "length" }, t("track.shortLength")), h("h2", {}, t("track.short")),
        h("p", {}, t("show.shortBlurb", { n: show.episodes })),
        progressBar(st.doneDays.length, SHORT_DAYS), h("p", { class: "muted" }, t("show.progressDays", { d: st.doneDays.length }))),
      h("a", { class: "track-card long reveal", href: go(show, { page: "track", track: "long" }), "data-tilt": "1" },
        h("p", { class: "length" }, t("track.longLength")), h("h2", {}, t("track.long")),
        h("p", {}, show.language === "en" ? t("show.longBlurbEn") : t("show.longBlurb", { next })))),
    watchPanel(show),
    episodeList(show),
  ];
}

function episodeList(show) {
  const st = store(show.id);
  const list = epList(show);
  return h("section", { class: "panel reveal" }, h("h2", {}, t("show.episodes")),
    h("ol", { class: "part-list" }, list.map((e) => h("li", {},
      h("a", { href: go(show, { page: "ep", ep: e.n }) }, h("b", {}, isYt(show) ? `EP${String(e.n).padStart(2, "0")}` : e.code), " ", isYt(show) ? "" : e.title || ""),
      e.duration ? h("span", { class: "muted" }, " " + t("ep.minutes", { m: Math.round(e.duration / 60) })) : null,
      st.watched[e.n] ? h("span", { class: "tag lv1" }, t("ep.watched")) : null,
      e.youtubeId ? h("a", { class: "mini", href: ytUrl(e.youtubeId), target: "_blank", rel: "noopener" }, "YouTube") : null))));
}

async function viewEpisodes(show) {
  await Promise.all([loadPublic(show), loadIndex(show)]);
  return [h("h1", { class: "reveal" }, `${showTitle(show)} · ${t("show.episodes")}`), watchPanel(show), episodeList(show)];
}

export function defaultToggles(show, prefs, langs = readerLanguages(show, prefs)) {
  const ex = prefs.explainLang;
  const on = { [show.language]: true };
  if (langs.includes("py")) on.py = true;
  if (langs.includes("reading")) on.reading = true;
  if (show.language !== ex && langs.includes(ex)) on[ex] = true;
  else if (ex === "vi" && !langs.includes(ex) && show.language !== "zh" && langs.includes("zh")) on.zh = true;
  else if (langs.includes("en") && show.language !== "en") on.en = true;
  return on;
}

function episodeBlock(show, n, idx, { compact = false } = {}) {
  if (!idx) return [loginCard(show)];
  const st = store(show.id);
  const e = epList(show).find((x) => x.n === n);
  if (!e) return [h("p", { class: "reveal" }, t("ep.notFound"))];
  const phrases = idx.phrases.filter((p) => p.ep === n);
  const watched = !!st.watched[n];
  const langs = readerLanguages(show, env.prefs());
  return [h("section", { class: "panel reveal" },
    h("h2", {}, `${showTitle(show)} · ${epLabel(show, e)}`),
    h("p", { class: "muted" }, [e.duration ? t("ep.minutes", { m: Math.round(e.duration / 60) }) : null, e.lines ? t("ep.lines", { n: e.lines }) : null, t("ep.phrases", { n: phrases.length })].filter(Boolean).join(" · ")),
    h("div", { class: "actions" },
      e.youtubeId ? h("a", { class: "btn primary", href: ytUrl(e.youtubeId), target: "_blank", rel: "noopener" }, t("show.watchYoutube")) : null,
      !isYt(show) && show.watch ? h("a", { class: "btn primary", href: show.watch.url, target: "_blank", rel: "noopener" }, t("show.watchOwn")) : null,
      ...(e.srt || []).filter((s) => s.langs.every((k) => langs.includes(k))).map((s) => h("a", { class: "btn", href: s.href, download: s.href.split("/").pop() }, t("ep.srt", { pair: s.langs.map((k) => t("langname." + k)).join("+") }))),
      compact ? h("a", { class: "btn ghost", href: go(show, { page: "ep", ep: n }) }, t("ep.transcript")) : null,
      h("button", { class: "btn ghost", type: "button", onclick: () => { st.watched[n] = !watched; persist(show.id); env.rerender({ transition: false, preserveScroll: true }); } }, watched ? t("ep.watched") : t("ep.markWatched"))),
    !isYt(show) && !show.watch ? h("p", {}, t("show.watchOwn")) : null,
    !isYt(show) ? h("p", { class: "muted" }, t("show.timesApprox")) : null,
    phrases.length ? h("h3", { class: "section-title" }, t("ep.phrases", { n: phrases.length })) : null,
    h("div", { class: "cards" }, phrases.map((p) => phraseCard(show, p, e))))];
}

async function viewEp(show, n) {
  const [, idx] = await Promise.all([loadPublic(show), loadIndex(show)]);
  const out = episodeBlock(show, n, idx);
  const e = epList(show).find((x) => x.n === n);
  const total = epList(show).length;
  const nav = h("div", { class: "actions reveal" },
    n > 1 ? h("a", { class: "btn", href: go(show, { page: "ep", ep: n - 1 }) }, t("ep.prev")) : null,
    n < total ? h("a", { class: "btn", href: go(show, { page: "ep", ep: n + 1 }) }, t("ep.next")) : null);
  if (!idx || !e) return [...out, nav];
  if (!e.file) return [...out, h("p", { class: "muted reveal" }, t("ep.noData")), nav];
  let data;
  try { data = await loadEp(show, e); } catch { return [...out, h("p", { class: "muted reveal" }, t("login.error")), nav]; }
  const st = store(show.id);
  const prefs = env.prefs();
  const langs = readerLanguages(show, prefs, data.langs || show.langs);
  const tog = { ...defaultToggles(show, prefs, langs), ...(st.toggles || {}) };
  const list = h("ol", { class: "transcript multi" });
  const applyToggles = () => {
    langs.forEach((k) => list.classList.toggle("hide-" + k, !tog[k]));
    for (const li of list.children) li.hidden = !li.dataset.langs.split(" ").some((k) => tog[k]);
  };
  const toggles = h("div", { class: "chips lang-toggles", role: "group", "aria-label": t("ep.toggles") },
    h("span", { class: "muted" }, t("ep.toggles") + t("common.colon")),
    langs.map((k) => {
      const box = h("input", { type: "checkbox", checked: !!tog[k], onchange: (ev) => { tog[k] = ev.target.checked; st.toggles = { ...tog }; persist(show.id); applyToggles(); } });
      return h("label", { class: "chip toggle" }, box, " ", t("langname." + k));
    }));
  for (const L of data.lines) {
    const ts = isYt(show) && e.youtubeId
      ? h("a", { class: "ts", href: ytUrl(e.youtubeId, L.start), target: "_blank", rel: "noopener" }, fmt(L.start))
      : h("span", { class: "ts", title: t("show.timesApprox") }, fmt(L.start));
    list.append(h("li", { "data-langs": langs.filter((k) => L[k]).join(" ") }, ts, h("div", { class: "stack" }, langs.filter((k) => L[k]).map((k) => h("span", { class: "l-" + k, lang: k === "py" ? "zh-Latn-pinyin" : k === "reading" ? "ja-Hira" : k }, L[k])))));
  }
  applyToggles();
  out.push(h("section", { class: "panel reveal" }, h("h2", {}, t("ep.transcript")),
    h("p", { class: "muted" }, isYt(show) ? t("ep.noteYoutube") : `${t("ep.noteText")} ${t("show.timesApprox")}`), toggles, list));
  out.push(nav);
  return out;
}

function weekTheme(show, w) {
  const row = (SHORT_WEEKS[show.language] || [])[w - 1];
  const [title, focus] = row ? pick(row) : ["", ""];
  return { title, focus };
}

async function viewShortHome(show) {
  const st = store(show.id);
  const days = buildShowDays(show.episodes);
  const d = nextShowDay(days, st.doneDays);
  const wk = weekTheme(show, d.week);
  const idx = await loadIndex(show);
  return [
    h("section", { class: "hero reveal" },
      h("p", { class: "eyebrow" }, t("day.eyebrow", { w: d.week, theme: wk.title }) + ` · ${d.day} / ${SHORT_DAYS}`),
      titleEl(t("day.today")),
      h("p", { class: "lede" }, t("day." + (d.kind === "intro" ? "introBody" : d.kind))),
      h("div", { class: "actions" },
        h("a", { class: "btn primary", href: go(show, { page: "day", day: d.day }) }, t("day.start")),
        h("a", { class: "btn", href: go(show, { page: "review" }) }, idx ? t("review.withDue", { n: dueCount(show) }) : t("nav.review")))),
    h("section", { class: "panel reveal" }, h("h2", {}, t("short.thisWeek", { title: wk.title })), h("p", {}, wk.focus),
      progressBar(st.doneDays.length, SHORT_DAYS), h("p", { class: "muted" }, t("show.progressDays", { d: st.doneDays.length }))),
    idx ? null : loginCard(show),
  ];
}

async function viewDay(show, n) {
  const st = store(show.id);
  const days = buildShowDays(show.episodes);
  const d = days[n - 1];
  if (!d) return [h("p", {}, t("day.none"))];
  const [, idx] = await Promise.all([loadPublic(show), loadIndex(show)]);
  const done = st.doneDays.includes(d.day);
  const wk = weekTheme(show, d.week);
  const out = [h("p", { class: "eyebrow reveal" }, t("day.eyebrow", { w: d.week, theme: wk.title })), h("h1", { class: "reveal" }, t("day.title", { n: d.day }))];
  if (d.kind === "intro") out.push(h("section", { class: "panel reveal" }, h("h2", {}, t("day.introTitle")), h("p", {}, t("day.introBody")), h("p", { class: "muted" }, wk.focus)), watchPanel(show));
  else out.push(h("section", { class: "panel reveal" }, h("p", {}, t("day." + d.kind)), h("p", { class: "muted" }, wk.focus),
    d.kind === "review" ? h("a", { class: "btn primary", href: go(show, { page: "review" }) }, t("nav.review")) : null));
  if (d.kind === "watch" || d.kind === "deep") {
    if (!idx) out.push(loginCard(show));
    else for (const e of d.eps) out.push(...episodeBlock(show, e, idx, { compact: true }));
  }
  if (d.kind === "review" && d.eps.length) out.push(h("div", { class: "chips reveal" }, d.eps.map((n) => h("a", { class: "chip", href: go(show, { page: "ep", ep: n }) }, epLabel(show, epList(show).find((x) => x.n === n) || { n, code: "#" + n })))));
  out.push(h("div", { class: "actions reveal" },
    h("button", { class: "btn primary", type: "button", onclick: () => {
      if (!done) st.doneDays.push(d.day); else st.doneDays = st.doneDays.filter((x) => x !== d.day);
      persist(show.id); env.rerender({ transition: false, preserveScroll: true });
    } }, done ? t("day.undone") : t("day.done")),
    d.day < SHORT_DAYS ? h("a", { class: "btn", href: go(show, { page: "day", day: d.day + 1 }) }, t("day.next")) : null));
  return out;
}

function viewPlan(show) {
  const st = store(show.id);
  const days = buildShowDays(show.episodes);
  const label = (d) => d.kind === "intro" ? t("short.chipIntro") : d.kind === "review" ? t("short.chipReview")
    : (d.kind === "deep" ? t("short.chipDeep") + " " : "") + "EP" + d.eps.join("+");
  return [h("h1", { class: "reveal" }, t("short.planTitle")), h("p", { class: "reveal" }, t("short.planLede")),
    progressBar(st.doneDays.length, SHORT_DAYS),
    ...Array.from({ length: 12 }, (_, i) => i + 1).map((w) => {
      const wk = weekTheme(show, w);
      return h("section", { class: "panel week reveal" }, h("h2", {}, t("short.week", { w, title: wk.title })), h("p", {}, wk.focus),
        h("div", { class: "chips" }, days.filter((d) => d.week === w).map((d) => h("a", {
          class: "chip" + (st.doneDays.includes(d.day) ? " done" : ""), href: go(show, { page: "day", day: d.day }) }, `D${d.day} ${label(d)}`))));
    })];
}

function viewLong(show) {
  const stages = LONG_OUTLINES[show.language] || [];
  return [
    h("section", { class: "hero reveal" }, h("p", { class: "eyebrow" }, t("track.longLength")), titleEl(t("long.title")), h("p", { class: "lede" }, t(show.language === "en" ? "show.longBlurbEn" : "long.lede"))),
    h("div", { class: "stage-list" }, stages.map((s) => h("section", { class: "panel stage-card reveal" + (s.status === "now" ? " now" : "") },
      h("p", { class: "eyebrow" }, `${pick(s.span)} · ${s.status === "now" ? t("long.now") : t("long.planned")}`),
      h("h2", {}, s.status === "now" ? h("a", { href: go(SHOWS[s.showId || show.id], { page: "track", track: "short" }) }, s.show) : uiLang() === "vi" ? s.showVi || s.show : s.show),
      h("p", {}, pick(s.goal))))),
  ];
}

function unlockedEps(show) {
  const st = store(show.id);
  const days = buildShowDays(show.episodes);
  // Done days, plus not-yet-done days up to the next one that carries an episode (day 1 is intro only).
  const open = new Set(days.filter((d) => st.doneDays.includes(d.day)).flatMap((d) => d.eps));
  for (const d of days) {
    if (st.doneDays.includes(d.day)) continue;
    d.eps.forEach((e) => open.add(e));
    if (d.eps.length) break;
  }
  return open;
}
function reviewIds(show) {
  const idx = c(show.id).idx; if (!idx) return [];
  const st = store(show.id); const open = unlockedEps(show);
  return idx.phrases.filter((p) => st.srs[p.id] || open.has(p.ep)).sort((a, b) => a.ep - b.ep || a.line - b.line).map((p) => p.id);
}
function dueCount(show) { return queue(reviewIds(show), store(show.id).srs).due.length; }

async function viewReview(show) {
  const idx = await loadIndex(show);
  if (!idx) return [h("h1", {}, t("review.title")), loginCard(show)];
  await loadPublic(show);
  const st = store(show.id); const day = today();
  if (st.newToday.day !== day) st.newToday = { day, n: 0 };
  const q = queue(reviewIds(show), st.srs, { day, newLimit: st.newLimit, newSeenToday: st.newToday.n });
  const id = q.due[0] || q.fresh[0];
  const wrap = [h("h1", { class: "reveal" }, t("review.title")), h("p", { class: "muted reveal" }, t("review.stats", { due: q.due.length, fresh: q.fresh.length }) + " ",
    h("select", { "aria-label": t("review.newLimit"), onchange: (e) => { st.newLimit = +e.target.value; persist(show.id); env.rerender({ transition: false, preserveScroll: true }); } },
      [5, 10, 15, 20, 30].map((v) => h("option", { value: v, selected: v === st.newLimit }, v))), " " + t("review.perDay"))];
  if (!id) return [...wrap, h("section", { class: "panel reveal" }, h("p", {}, t("review.empty")), h("a", { class: "btn", href: go(show, { page: "track", track: multiTrack(show.id) }) }, t("review.backTrack")))];
  const p = idx.phrases.find((x) => x.id === id);
  const e = epList(show).find((x) => x.n === p.ep);
  const isNew = !st.srs[id]; const x = explainOf(show, p, env.prefs());
  const back = h("div", { class: "back", hidden: true },
    h("p", { class: "vi" }, p.phrase), (p.py || p.reading) ? h("p", { class: "reading" }, p.py || p.reading) : null,
    x.meaning ? h("p", { class: "zh" }, h("b", {}, x.meaning)) : null, x.explain ? h("p", { class: "usage" }, x.explain) : null,
    ...sourceLines(show, p), h("div", { class: "actions" }, timeLink(show, e, p.start)),
    h("div", { class: "actions grades" }, ["again", "hard", "good", "easy"].map((g) =>
      h("button", { class: "btn grade " + g, type: "button", onclick: () => {
        st.srs[id] = review(st.srs[id], g, day); if (isNew) st.newToday.n += 1; persist(show.id); env.rerender({ transition: false });
      } }, t("grade." + g)))));
  const front = h("section", { class: "panel flash reveal" },
    h("p", { class: "eyebrow" }, (isNew ? t("review.new") : t("review.due")) + (p.level ? " · " + p.level : "")),
    p.clip ? h("p", {}, t("review.listen")) : h("p", { class: "vi" }, p.phrase),
    h("div", { class: "actions" }, ...clipButtons(p).slice(0, 1),
      h("button", { class: "btn primary", type: "button", onclick: (ev) => { back.hidden = false; ev.currentTarget.remove(); back.querySelector(".grades button")?.focus(); } }, t("review.answer"))),
    back);
  if (p.clip) setTimeout(() => front.querySelector(".play")?.click(), 50);
  return [...wrap, front];
}

export async function renderMulti(rec) {
  const show = SHOWS[rec.show];
  switch (rec.page) {
    case "show": return viewShow(show);
    case "parts": return viewEpisodes(show);
    case "ep": return viewEp(show, rec.ep);
    case "part": return viewEp(show, rec.part);
    case "track": return rec.track === "long" ? viewLong(show) : viewShortHome(show);
    case "plan": return rec.track === "long" ? viewLong(show) : viewPlan(show);
    case "day": return viewDay(show, rec.day);
    case "review": return viewReview(show);
    default: return [h("p", { class: "reveal" }, t("common.notFound")), h("a", { class: "btn", href: go(show, { page: "show" }) }, t("nav.show"))];
  }
}
