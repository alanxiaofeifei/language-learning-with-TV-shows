import { WEEKS, buildDays, nextDay } from "./lib/curriculum.js";
import { LESSONS } from "./lib/pron.js";
import { review, queue, today } from "./lib/srs.js";

const KEY = "vndc:v1";
const CATS = { food: "吃饭", shopping: "购物", work: "工作", survival: "出行求助", social: "寒暄礼貌", feeling: "情绪回应" };
const DAYS = buildDays();
const main = document.getElementById("main-content");
let data = null, dataError = null, searchIndex = null;
const partCache = {};

const state = load();
function load() {
  try { return { doneDays: [], watched: {}, srs: {}, newToday: { day: 0, n: 0 }, newLimit: 15, ...JSON.parse(localStorage.getItem(KEY) || "{}") }; }
  catch { return { doneDays: [], watched: {}, srs: {}, newToday: { day: 0, n: 0 }, newLimit: 15 }; }
}
function save() { localStorage.setItem(KEY, JSON.stringify(state)); }

function h(tag, attrs = {}, ...kids) {
  const n = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs || {})) {
    if (v == null || v === false) continue;
    if (k.startsWith("on")) n.addEventListener(k.slice(2), v);
    else if (k === "class") n.className = v;
    else n.setAttribute(k, v === true ? "" : v);
  }
  for (const k of kids.flat()) if (k != null && k !== false) n.append(k.nodeType ? k : String(k));
  return n;
}
const fmt = (ms) => { const s = Math.floor(ms / 1000); return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, "0")}`; };
const yt = (videoId, ms) => `https://www.youtube.com/watch?v=${videoId}&t=${Math.max(0, Math.floor(ms / 1000) - 2)}s`;

async function loadData() {
  if (data || dataError) return data;
  try {
    const r = await fetch("/private/data/index.json", { credentials: "same-origin", redirect: "manual" });
    if (r.type === "opaqueredirect" || r.status === 0 || r.status === 401 || r.status === 403) throw new Error("login");
    if (!r.ok) throw new Error("http " + r.status);
    data = await r.json();
  } catch (e) { dataError = e.message === "login" ? "login" : "error"; }
  return data;
}
async function loadPart(n) {
  if (!partCache[n]) partCache[n] = fetch(`/private/data/P${String(n).padStart(2, "0")}.json`, { credentials: "same-origin" }).then((r) => r.json());
  return partCache[n];
}

function loginCard() {
  return h("section", { class: "panel login" },
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
      currentAudio?.pause(); currentAudio = new Audio(p.clip);
      const slow = e.shiftKey || e.currentTarget.dataset.slow === "1"; currentAudio.playbackRate = slow ? 0.75 : 1;
      currentAudio.play();
    } }, label);
  }
  return h("button", { class: "btn play tts", type: "button", title: "没有核实过的原声片段，使用设备的越南语合成音",
    onclick: () => { if (!speak(p.phrase)) alert("这台设备没有越南语语音。可以点「YouTube」听原声。"); } }, "▶ 合成音");
}
function slowButton(p) {
  if (!p.clip) return null;
  return h("button", { class: "btn ghost", type: "button", onclick: () => { currentAudio?.pause(); currentAudio = new Audio(p.clip); currentAudio.playbackRate = 0.7; currentAudio.play(); } }, "慢放");
}

function phraseCard(p, video) {
  return h("article", { class: "card" },
    h("div", { class: "card-top" }, h("span", { class: "tag " + p.category }, CATS[p.category] || p.category), p.level === 1 ? h("span", { class: "tag lv1" }, "第一周必会") : null),
    h("p", { class: "vi" }, p.phrase),
    h("p", { class: "reading", title: "拼音读法：辅音按汉语拼音读；箭头是声调" }, p.reading),
    h("p", { class: "zh" }, p.zh, p.en ? h("span", { class: "en" }, " · " + p.en) : null),
    p.usage ? h("p", { class: "usage" }, p.usage) : null,
    h("details", {}, h("summary", {}, "原句与声调"),
      h("p", { class: "line" }, p.lineVi), h("p", { class: "line zh" }, p.lineZh), h("p", { class: "tones" }, p.tones)),
    h("div", { class: "actions" }, playButton(p), slowButton(p),
      h("a", { class: "btn ghost", href: p.youtube || yt(video, p.startMs), target: "_blank", rel: "noopener" }, `YouTube ${fmt(p.startMs)}`)));
}

// ---------- views ----------
async function viewHome() {
  const d = nextDay(DAYS, state.doneDays);
  const wk = WEEKS[d.week - 1];
  await loadData();
  const dueCount = data ? queue(data.phrases.map((p) => p.id), state.srs).due.length : 0;
  return [
    h("section", { class: "hero" },
      h("p", { class: "eyebrow" }, `第 ${d.week} 周 · 第 ${d.day} 天 / 84`),
      h("h1", {}, "《Về nhà đi con》回家吧，孩子"),
      h("p", {}, "用原剧原声学北越（河内）口语：先学当天的日常用语，再用 VLC 配双语字幕看一集，最后复习。"),
      h("div", { class: "actions" }, h("a", { class: "btn primary", href: "#/day/" + d.day }, "开始今天的课"), h("a", { class: "btn", href: "#/review" }, `复习${data ? `（到期 ${dueCount}）` : ""}`))),
    h("section", { class: "panel" }, h("h2", {}, `本周：${wk.title}`), h("p", {}, wk.focus),
      h("div", { class: "progress" }, h("span", { style: `width:${Math.round((state.doneDays.length / 84) * 100)}%` })),
      h("p", { class: "muted" }, `已完成 ${state.doneDays.length} / 84 天 · 已学卡片 ${Object.keys(state.srs).length}`)),
    data ? null : loginCard(),
  ];
}

async function viewDay(n) {
  const d = DAYS[n - 1]; if (!d) return [h("p", {}, "没有这一天。")];
  const done = state.doneDays.includes(d.day);
  const out = [h("p", { class: "eyebrow" }, `第 ${d.week} 周 · ${WEEKS[d.week - 1].title}`), h("h1", {}, `第 ${d.day} 天`)];
  if (d.pron) {
    out.push(...lessonView(d.pron));
    await loadData();
    if (data) out.push(...corpusExamples(LESSONS[d.pron].practice));
  }
  if (d.reviewOnly) out.push(h("section", { class: "panel" }, h("p", {}, "今天只复习：把到期卡片做完，再回看第 1 段里最难的 5 句。"), h("a", { class: "btn primary", href: "#/review" }, "去复习")));
  if (d.parts.length) {
    await loadData();
    if (!data) out.push(loginCard());
    else for (const n of d.parts) out.push(...(await partBlock(n, true)));
  }
  out.push(h("div", { class: "actions" }, h("button", { class: "btn primary", type: "button", onclick: () => {
    if (!done) state.doneDays.push(d.day); else state.doneDays = state.doneDays.filter((x) => x !== d.day);
    save(); route();
  } }, done ? "✓ 已完成（点击取消）" : "完成今天"), d.day < 84 ? h("a", { class: "btn", href: "#/day/" + (d.day + 1) }, "下一天 →") : null));
  return out;
}

function lessonView(key) {
  const L = LESSONS[key];
  return [h("section", { class: "panel" }, h("h2", {}, L.title), h("p", {}, L.intro),
    h("div", { class: "table-wrap" }, h("table", {}, h("tbody", {}, L.rows.map((r) => h("tr", {}, r.map((c, i) => h(i ? "td" : "th", {}, c))))))),
    h("h3", {}, "跟读练习"),
    h("div", { class: "chips" }, L.practice.map((t) => h("button", { class: "chip", type: "button", onclick: () => { if (!speak(t)) alert("这台设备没有越南语语音，先看拼音读法练。"); } }, t))),
    h("p", { class: "muted" }, "练习按钮用设备自带的越南语合成音（如有）。从第 6 天起全部用原剧原声。"))];
}

// Week-1 lessons: show real clips from the show that contain the practice words.
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
  return [h("section", { class: "panel" },
    h("h2", {}, `P${String(n).padStart(2, "0")} · ${meta.titleZh || meta.title}`),
    h("p", { class: "muted" }, meta.title, ` · ${Math.round(meta.duration / 60)} 分钟 · ${meta.lines} 句台词${meta.source === "whisper" ? " · 字幕由 Whisper 识别" : ""}`),
    h("div", { class: "actions" },
      h("a", { class: "btn primary", href: `https://www.youtube.com/watch?v=${meta.videoId}`, target: "_blank", rel: "noopener" }, "在 YouTube 看"),
      h("a", { class: "btn", href: meta.srt, download: meta.srt.split("/").pop() }, "下载双语字幕 .srt"),
      h("a", { class: "btn ghost", href: "#/vlc" }, "VLC 怎么用"),
      compact ? h("a", { class: "btn ghost", href: "#/part/" + n }, "全文台词") : null,
      h("button", { class: "btn ghost", type: "button", onclick: () => { state.watched[n] = !watched; save(); route(); } }, watched ? "✓ 已看" : "标记已看"))),
    h("h3", { class: "section-title" }, `今日用语 ${phrases.length} 条`),
    h("div", { class: "cards" }, phrases.map((p) => phraseCard(p, meta.videoId)))];
}

async function viewPart(n) {
  await loadData(); if (!data) return [loginCard()];
  const out = await partBlock(n);
  const meta = data.parts.find((p) => p.part === n);
  const part = await loadPart(n);
  out.push(h("section", { class: "panel" }, h("h2", {}, "双语全文"), h("p", { class: "muted" }, "点时间跳到 YouTube 对应位置。自动识别 + 机器翻译，未人工校对。"),
    h("ol", { class: "transcript" }, part.lines.map((L) => h("li", {},
      h("a", { href: yt(meta.videoId, L.startMs), target: "_blank", rel: "noopener", class: "ts" }, fmt(L.startMs)),
      h("span", { class: "vi" }, L.vi), h("span", { class: "zh" }, L.zh))))));
  return out;
}

async function viewParts() {
  await loadData(); if (!data) return [h("h1", {}, "全部 82 段"), loginCard()];
  return [h("h1", {}, "全部 82 段"), h("p", { class: "muted" }, "来源：VFC Official YouTube 播放列表（按剧情顺序）。字幕时间轴只对这个版本有效。"),
    h("ol", { class: "part-list" }, data.parts.map((m) => h("li", {},
      h("a", { href: "#/part/" + m.part }, h("b", {}, `P${String(m.part).padStart(2, "0")}`), " ", m.titleZh || m.title),
      h("span", { class: "muted" }, ` ${Math.round(m.duration / 60)} 分`), state.watched[m.part] ? h("span", { class: "tag lv1" }, "已看") : null,
      h("a", { class: "mini", href: `https://www.youtube.com/watch?v=${m.videoId}`, target: "_blank", rel: "noopener" }, "YouTube"),
      h("a", { class: "mini", href: m.srt, download: m.srt.split("/").pop() }, "SRT"))))];
}

async function viewReview() {
  await loadData(); if (!data) return [h("h1", {}, "复习"), loginCard()];
  const day = today();
  if (state.newToday.day !== day) state.newToday = { day, n: 0 };
  const unlocked = new Set(DAYS.filter((d) => state.doneDays.includes(d.day) || d.day === nextDay(DAYS, state.doneDays).day).flatMap((d) => d.parts));
  const ids = data.phrases.filter((p) => unlocked.has(p.part)).sort((a, b) => a.level - b.level || a.part - b.part).map((p) => p.id);
  const q = queue(ids, state.srs, { day, newLimit: state.newLimit, newSeenToday: state.newToday.n });
  const id = q.due[0] || q.fresh[0];
  const wrap = [h("h1", {}, "复习"), h("p", { class: "muted" }, `到期 ${q.due.length} · 今天还可学新卡 ${q.fresh.length} · 新卡上限 `,
    h("select", { onchange: (e) => { state.newLimit = +e.target.value; save(); route(); } }, [5, 10, 15, 20, 30].map((v) => h("option", { value: v, selected: v === state.newLimit }, v))), " 张/天")];
  if (!id) return [...wrap, h("section", { class: "panel" }, h("p", {}, "今天的复习做完了 🎉 新卡来自已完成和当天的课程。"), h("a", { class: "btn", href: "#/" }, "回首页"))];
  const p = data.phrases.find((x) => x.id === id);
  const isNew = !state.srs[id];
  const back = h("div", { class: "back", hidden: true },
    h("p", { class: "vi" }, p.phrase), h("p", { class: "reading" }, p.reading), h("p", { class: "zh" }, p.zh),
    h("p", { class: "line" }, p.lineVi), h("p", { class: "line zh" }, p.lineZh),
    h("div", { class: "actions grades" }, [["again", "忘了"], ["hard", "难"], ["good", "会"], ["easy", "简单"]].map(([g, t]) =>
      h("button", { class: "btn grade " + g, type: "button", onclick: () => {
        state.srs[id] = review(state.srs[id], g, day); if (isNew) state.newToday.n += 1; save(); route();
      } }, t))));
  const front = h("section", { class: "panel flash" },
    h("p", { class: "eyebrow" }, isNew ? "新卡" : "复习", " · ", CATS[p.category] || ""),
    p.clip ? h("p", {}, "先听原声，想想是什么意思：") : h("p", { class: "vi" }, p.phrase),
    h("div", { class: "actions" }, playButton(p), h("button", { class: "btn primary", type: "button", onclick: (e) => { back.hidden = false; e.currentTarget.remove(); } }, "看答案")),
    back);
  if (p.clip) setTimeout(() => front.querySelector(".play")?.click(), 50);
  return [...wrap, front];
}

function viewPlan() {
  return [h("h1", {}, "12 周课程"), h("p", {}, "每天约 45 分钟：日常用语（10 分钟）→ VLC 双语字幕看一段（30 分钟）→ 复习（5–10 分钟）。第 8 周起第二遍关字幕。"),
    ...WEEKS.map((w) => h("section", { class: "panel week" }, h("h2", {}, `第 ${w.week} 周 · ${w.title}`), h("p", {}, w.focus),
      h("div", { class: "chips" }, DAYS.filter((d) => d.week === w.week).map((d) => h("a", { class: "chip" + (state.doneDays.includes(d.day) ? " done" : ""), href: "#/day/" + d.day },
        `D${d.day}${d.pron ? " 发音" : d.reviewOnly ? " 复习" : " P" + d.parts.join("+P")}`)))))];
}

async function viewScenes(cat) {
  await loadData(); if (!data) return [h("h1", {}, "按场景"), loginCard()];
  cat = cat || "food";
  const list = data.phrases.filter((p) => p.category === cat).sort((a, b) => a.level - b.level || a.part - b.part);
  return [h("h1", {}, "按场景学"), h("div", { class: "chips" }, Object.entries(CATS).map(([k, v]) => h("a", { class: "chip" + (k === cat ? " done" : ""), href: "#/scenes/" + k }, `${v} ${data.phrases.filter((p) => p.category === k).length}`))),
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
    if (!searchIndex) searchIndex = await fetch("/private/data/search.json", { credentials: "same-origin" }).then((r) => r.json());
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
  return [h("h1", {}, "全剧搜索"), h("p", { class: "muted" }, "在 82 段台词里找一个词出现在哪些场景，点时间去 YouTube 听原声。"), input, results];
}

async function viewVlc() {
  const md = await fetch("./vlc.html").then((r) => r.text());
  const box = h("section", { class: "panel prose" }); box.innerHTML = md; return [box];
}

const ROUTES = [
  [/^#?\/?$/, viewHome], [/^#\/day\/(\d+)$/, (m) => viewDay(+m[1])], [/^#\/part\/(\d+)$/, (m) => viewPart(+m[1])],
  [/^#\/parts$/, viewParts], [/^#\/review$/, viewReview], [/^#\/plan$/, viewPlan], [/^#\/scenes(?:\/(\w+))?$/, (m) => viewScenes(m[1])],
  [/^#\/search(?:\/(.*))?$/, (m) => viewSearch(m[1] && decodeURIComponent(m[1]))], [/^#\/vlc$/, viewVlc],
  [/^#\/lesson\/(\w+)$/, (m) => lessonView(m[1])],
];
async function route() {
  const hash = location.hash || "#/";
  for (const [re, fn] of ROUTES) {
    const m = hash.match(re);
    if (m) {
      const nodes = await fn(m);
      main.replaceChildren(...[nodes].flat().filter(Boolean));
      document.querySelectorAll(".top-nav a").forEach((a) => a.toggleAttribute("aria-current", a.getAttribute("href") === hash));
      window.scrollTo(0, 0); return;
    }
  }
  main.replaceChildren(h("p", {}, "页面不存在。"), h("a", { href: "#/" }, "回首页"));
}
window.addEventListener("hashchange", route);
route();
