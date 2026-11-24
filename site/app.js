import { episodes } from "./episodes.js";
import { parseSubtitles } from "./import-subtitles.js";

const storageKey = "language-studio-v1";
const main = document.querySelector("main");
const course = document.querySelector("#course");
const announcement = document.querySelector("#status-announcement");
const playlist = "https://www.youtube.com/playlist?list=PL3m_2IMNSXxcd1Ff3_Czw8je8BvHUpK6C";
const transcriptHelp = "https://support.google.com/youtube/answer/15930243?hl=zh-Hans";
const phases = { preview: "预习", watch: "看剧", review: "复习" };
const languages = { "vi-VN": "越南语", "en-US": "英语", "fr-FR": "法语", "ja-JP": "日语", "es-ES": "西班牙语", other: "其他语言" };
let state = { progress: {}, imported: [] };
let storageNotice = "";
let activeAudio;
let run;

try {
  const saved = JSON.parse(localStorage.getItem(storageKey));
  if (saved?.progress && Array.isArray(saved.imported)) state = saved;
} catch {
  storageNotice = "无法读取浏览器中的学习记录。";
}

function save() {
  try {
    localStorage.setItem(storageKey, JSON.stringify(state));
    storageNotice = "";
    return true;
  } catch {
    storageNotice = "浏览器存储空间不足或已被禁用。本次学习进度可能无法在刷新后保留。";
    announcement.textContent = storageNotice;
    return false;
  }
}

function el(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text != null) node.textContent = text;
  return node;
}

function append(parent, ...children) {
  parent.append(...children);
  return parent;
}

function button(text, action, primary = false, className = "button") {
  const node = el("button", primary ? className + " primary" : className, text);
  node.type = "button";
  node.addEventListener("click", action);
  return node;
}

function link(text, href, className, external = false) {
  const node = el("a", className, text);
  node.href = href;
  if (external) {
    node.target = "_blank";
    node.rel = "noopener noreferrer";
  }
  return node;
}

function progressFor(lesson) {
  return state.progress[lesson.id] ??= { preview: [], review: [], watched: false };
}

function remaining(lesson, phase) {
  const done = progressFor(lesson)[phase];
  return lesson.cards.map((_, index) => index).filter(index => !done.includes(index));
}

function complete(lesson) {
  return progressFor(lesson).watched && !remaining(lesson, "preview").length && !remaining(lesson, "review").length;
}

function nextPhase(lesson) {
  if (remaining(lesson, "preview").length) return "preview";
  return progressFor(lesson).watched ? "review" : "watch";
}

function timestamp(seconds) {
  const mins = Math.floor(seconds / 60);
  const secs = String(Math.floor(seconds % 60)).padStart(2, "0");
  return mins + ":" + secs;
}

function watchLink(lesson, start) {
  if (!lesson.videoId) return lesson.url;
  const url = new URL("https://www.youtube.com/watch");
  url.searchParams.set("v", lesson.videoId);
  if (start != null) url.searchParams.set("t", Math.floor(start) + "s");
  return url.href;
}

function renderCourse(current) {
  const finished = episodes.filter(complete).length;
  const progress = el("progress");
  progress.max = episodes.length;
  progress.value = finished;
  progress.setAttribute("aria-label", "五集学习进度");
  const list = el("ol", "episode-list");
  for (const episode of episodes) {
    const saved = progressFor(episode);
    const phaseCount = Number(!remaining(episode, "preview").length) + Number(saved.watched)
      + Number(!remaining(episode, "review").length);
    const item = link("", "#drama/" + episode.id, "episode-link");
    if (episode.id === current) item.setAttribute("aria-current", "page");
    const labels = append(el("span"), el("strong", "", episode.zh),
      el("small", "", timestamp(episode.duration) + " · " + (phaseCount === 3 ? "已完成" : phaseCount + "/3 步")));
    append(item, el("span", "number", String(episode.number).padStart(2, "0")), labels);
    list.append(append(el("li"), item));
  }
  course.replaceChildren(el("h2", "", "5S Online"), el("p", "muted", "第一季 · 已完成 " + finished + " / " + episodes.length + " 集"), progress, list);
  if (state.imported.length) {
    const imports = el("ul", "local-list");
    for (const lesson of state.imported) {
      const item = link(lesson.title, "#local/" + lesson.id, "");
      if (lesson.id === current) item.setAttribute("aria-current", "page");
      imports.append(append(el("li"), item));
    }
    append(course, el("h3", "local-label", "我导入的台词"), imports);
  }
}

function hero(kicker, title, subtitle, language) {
  const heading = el("h1", "", title);
  if (language) heading.lang = language;
  return append(el("section", "hero"), el("p", "eyebrow", kicker), heading, el("p", "subtitle", subtitle));
}

function renderScene() {
  const frame = el("iframe", "scenario-frame");
  frame.src = "./scenario/flashcards.html";
  frame.title = "越南语 IT 现场排障场景刷卡";
  const panel = append(el("section", "panel scenario-panel"), frame);
  const head = hero("默认场景 · 越南语", "IT 现场排障", "从电脑连不上网到重新连接。打开词块和原句音频，练习 6 个现场表达。");
  append(head, append(el("div", "row actions"), link("开始《5S Online》", "#drama", "button")));
  main.replaceChildren(head, panel);
}

function parseTone(word) {
  const marks = {
    "\u0300": "huyền · 低降",
    "\u0301": "sắc · 高升",
    "\u0309": "hỏi · 低折",
    "\u0303": "ngã · 断升",
    "\u0323": "nặng · 重短",
  };
  return Array.from(word.normalize("NFD")).map(letter => marks[letter]).find(Boolean) ?? "ngang · 平";
}

function stopAudio() {
  activeAudio?.pause();
  window.speechSynthesis?.cancel();
}

function audioButton(lesson, card, index, status) {
  if (lesson.imported && lesson.language === "other") return null;
  return button(lesson.imported ? "用浏览器听原句" : "听北越慢读", async () => {
    stopAudio();
    status.textContent = "";
    if (!lesson.imported) {
      activeAudio = new Audio("./audio/" + lesson.id + "/" + (index + 1) + ".mp3");
      try {
        await activeAudio.play();
      } catch {
        status.textContent = "这段音频暂时无法播放，请重试。";
      }
      return;
    }
    const synth = window.speechSynthesis;
    const voice = synth?.getVoices().find(item => item.lang.toLowerCase().split("-")[0] === lesson.language.split("-")[0]);
    if (!voice) {
      status.textContent = "设备未提供该语言的浏览器语音。";
      return;
    }
    const utterance = new SpeechSynthesisUtterance(card.vi);
    utterance.voice = voice;
    utterance.lang = lesson.language;
    utterance.rate = 0.8;
    synth.speak(utterance);
  });
}

function renderCards(lesson, phase, panel) {
  const graded = progressFor(lesson)[phase];
  const index = run.queue[0];
  const heading = el("h2", "", phase === "preview" ? "听音辨认" : "回想词义");
  heading.tabIndex = -1;
  const count = el("p", "muted", graded.length + " / " + lesson.cards.length + " 张已完成");
  const meter = el("progress");
  meter.max = lesson.cards.length;
  meter.value = graded.length;
  meter.setAttribute("aria-label", phases[phase] + "卡片进度");
  append(panel, append(el("div", "row row-spread"), heading, count), meter);
  if (index == null) {
    panel.append(el("p", "", phases[phase] + "已完成。"));
    const following = episodes.find(episode => episode.number === lesson.number + 1);
    const controls = el("div", "row actions");
    if (phase === "preview") controls.append(button("去看完整一集", () => renderLesson(lesson, "watch", true), true));
    if (phase === "review" && following) controls.append(link("开始第 " + following.number + " 集", "#drama/" + following.id, "button primary"));
    if (phase === "review" && !progressFor(lesson).watched) controls.append(button("返回看剧", () => renderLesson(lesson, "watch", true), true));
    controls.append(button("再练一遍", () => {
      run = { id: lesson.id, phase, queue: lesson.cards.map((_, i) => i) };
      renderLesson(lesson, phase, true);
    }));
    panel.append(controls);
    return;
  }

  const card = lesson.cards[index];
  const expression = el("h3", "expression", card.vi);
  if (lesson.language !== "other") expression.lang = lesson.language ?? "vi";
  const cardView = append(el("div", "card"), expression);
  if (!lesson.imported || lesson.language === "vi-VN") {
    const tones = el("div", "tones");
    for (const word of card.vi.match(/[\p{L}\p{M}]+/gu) ?? []) {
      const item = el("span", "tone");
      append(item, el("span", "", word), el("small", "", parseTone(word)));
      tones.append(item);
    }
    cardView.append(tones);
  }
  const status = el("p", "status");
  status.setAttribute("role", "status");
  const audio = audioButton(lesson, card, index, status);
  const controls = el("div", "row actions");
  if (audio) controls.append(audio);
  if (card.startSeconds != null && lesson.videoId) {
    controls.append(link("回听 " + timestamp(card.startSeconds), watchLink(lesson, card.startSeconds), "button", true));
  }
  const answer = el("div", "answer");
  if (!lesson.imported) {
    append(answer, el("p", "", card.zh), el("p", "", card.en), el("p", "muted", card.tip));
    const example = el("p", "", card.example);
    example.lang = "vi";
    append(answer, example, el("p", "muted", card.exampleZh), el("p", "muted", card.exampleEn));
    answer.hidden = true;
    const reveal = button("查看英中释义", () => {
      answer.hidden = false;
      reveal.setAttribute("aria-expanded", "true");
      reveal.disabled = true;
      mark.focus();
    });
    reveal.setAttribute("aria-expanded", "false");
    answer.id = "card-answer";
    reveal.setAttribute("aria-controls", answer.id);
    controls.append(reveal);
  }
  const mark = button("已认出", () => {
    if (!graded.includes(index)) graded.push(index);
    run.queue.shift();
    save();
    renderLesson(lesson, phase, true);
  }, true);
  const again = button("稍后再练", () => {
    run.queue.push(run.queue.shift());
    renderLesson(lesson, phase, true);
  });
  append(cardView, controls, status, answer, append(el("div", "row actions"), again, mark));
  panel.append(cardView);
}

function renderWatch(lesson, panel) {
  const heading = el("h2", "", "看剧");
  heading.tabIndex = -1;
  panel.append(heading);
  if (lesson.videoId) {
    const cover = el("div", "video-cover");
    const text = el("p", "", lesson.imported ? lesson.title : "5S Online · 第 " + lesson.number + " 集");
    const launch = button("在这里播放", () => {
      const frame = el("iframe", "player");
      frame.title = lesson.title;
      frame.src = "https://www.youtube-nocookie.com/embed/" + lesson.videoId + "?autoplay=1&cc_load_policy=1&cc_lang_pref=vi";
      frame.referrerPolicy = "strict-origin-when-cross-origin";
      frame.allow = "autoplay; encrypted-media; picture-in-picture";
      frame.allowFullscreen = true;
      frame.tabIndex = 0;
      cover.replaceWith(frame);
      frame.focus();
    });
    append(cover, text, launch);
    append(panel, append(el("div", "actions"), cover));
  }
  if (watchLink(lesson)) {
    panel.append(append(el("div", "row actions"), link("打开原片与文字稿", watchLink(lesson), "button", true)));
  }
  if (!lesson.imported) {
    append(panel, el("p", "muted", "五集均有越南语自动字幕。打开原片后，展开简介选择「显示文字稿」，可按时间点回听。用播放器的字幕设置切换英文或简体中文自动翻译。"),
      append(el("p", "muted"), link("YouTube 文字稿说明", transcriptHelp, "", true), " · ", link("第一季播放列表", playlist, "", true)));
  }
  if (lesson.imported && !watchLink(lesson)) panel.append(el("p", "muted", "看完手头的影片后，回来标记已观看。"));
  panel.append(append(el("div", "row actions"), button(progressFor(lesson).watched ? "已观看，去复习" : "我看完了，去复习", () => {
    progressFor(lesson).watched = true;
    save();
    renderLesson(lesson, "review", true);
  }, true)));
}

function renderTranscript(lesson) {
  const section = append(el("section", "panel"), el("h2", "", "导入的台词"));
  const details = append(el("details"), el("summary", "", "展开全文 · " + lesson.cues.length + " 条"));
  details.addEventListener("toggle", () => {
    if (!details.open || details.querySelector("ol")) return;
    const list = el("ol", "transcript");
    for (const cue of lesson.cues) {
      const line = el("li");
      if (cue.startSeconds != null) {
        line.append(lesson.videoId ? link(timestamp(cue.startSeconds), watchLink(lesson, cue.startSeconds), "", true)
          : el("span", "timestamp muted", timestamp(cue.startSeconds)));
      }
      line.append(document.createTextNode(cue.text));
      list.append(line);
    }
    details.append(list);
  });
  append(section, el("p", "muted", "本次用前 " + lesson.cards.length + " 条台词做预习与复习，全文保存在当前浏览器。"), details);
  return section;
}

function renderLesson(lesson, phase = nextPhase(lesson), focus = false) {
  stopAudio();
  if (run?.id !== lesson.id || run.phase !== phase) {
    run = { id: lesson.id, phase, queue: phase === "watch" ? [] : remaining(lesson, phase) };
  }
  renderCourse(lesson.id);
  const header = lesson.imported ? hero("我的台词 · " + languages[lesson.language], lesson.title, "先听读，再看原片，最后复习。")
    : hero("5S Online · 第一季第 " + lesson.number + " 集 · " + timestamp(lesson.duration), lesson.title, lesson.zh + " · " + lesson.en, "vi");
  if (!lesson.imported) header.append(el("p", "muted", lesson.focus + " 三语卡是原创练习。实际对白请看原片文字稿。"));
  const stages = el("nav", "stage-nav");
  stages.setAttribute("aria-label", "学习步骤");
  for (const [key, label] of Object.entries(phases)) {
    const done = key === "watch" ? progressFor(lesson).watched : !remaining(lesson, key).length;
    const detail = done ? "已完成" : (key === "watch" ? "观看原片" : progressFor(lesson)[key].length + " / " + lesson.cards.length);
    const step = button("", () => renderLesson(lesson, key, true), false, "step");
    if (phase === key) step.setAttribute("aria-current", "step");
    append(step, el("strong", "", label), el("span", "", detail));
    stages.append(step);
  }
  const panel = el("section", "panel");
  if (phase === "watch") renderWatch(lesson, panel);
  else renderCards(lesson, phase, panel);
  main.replaceChildren(header, stages, panel);
  if (storageNotice) main.append(el("p", "form-error", storageNotice));
  if (lesson.imported) main.append(renderTranscript(lesson));
  if (focus) panel.querySelector("h2").focus();
}

function externalUrl(raw) {
  if (!raw) return { url: "", videoId: "" };
  const url = new URL(raw);
  if (url.protocol !== "https:" || url.username || url.password) throw new Error("影片链接请输入完整的 HTTPS 地址。");
  const host = url.hostname.toLowerCase();
  let id = "";
  if (host === "youtu.be") id = url.pathname.slice(1).split("/")[0];
  if (["youtube.com", "www.youtube.com", "m.youtube.com"].includes(host)) id = url.searchParams.get("v") ?? "";
  return { url: url.href, videoId: /^[A-Za-z0-9_-]{11}$/.test(id) ? id : "" };
}

function renderImport() {
  const panel = el("section", "panel");
  panel.innerHTML = `
    <h2 id="import-heading">添加台词</h2>
    <form aria-labelledby="import-heading" method="post">
      <div class="form-grid">
        <div class="field"><label for="title">学习标题</label><input id="title" name="title" required maxlength="100" placeholder="例如 5S Online 第 1 集"></div>
        <div class="field"><label for="language">台词语言</label><select id="language" name="language"></select></div>
        <div class="field wide"><label for="video">影片地址（可选）</label><input id="video" name="video" type="url" maxlength="1000" placeholder="https://…" autocomplete="off"></div>
        <div class="field wide"><label for="file">字幕文件（可选）</label><input id="file" name="file" type="file" accept=".srt,.vtt,.txt"></div>
        <div class="field wide"><label for="transcript-text">或粘贴台词</label><textarea id="transcript-text" name="transcript" maxlength="524288" aria-describedby="import-help"></textarea></div>
      </div>
      <p class="muted" id="import-help">支持 SRT、VTT、TXT 或带时间点的 YouTube 文字稿。内容和进度仅保存在这个浏览器。</p>
      <p class="form-error" role="status" id="import-error"></p>
      <button class="button primary" type="submit">导入并开始学习</button>
    </form>`;
  const form = panel.querySelector("form");
  const selector = form.elements.language;
  for (const [code, label] of Object.entries(languages)) selector.add(new Option(label, code));
  const error = panel.querySelector("#import-error");
  const submit = panel.querySelector("button");
  form.addEventListener("submit", async event => {
    event.preventDefault();
    if (submit.disabled) return;
    submit.disabled = true;
    error.textContent = "";
    try {
      const title = form.elements.title.value.trim();
      const file = form.elements.file.files[0];
      const pasted = form.elements.transcript.value.trim();
      if (!title) throw new Error("请输入学习标题。");
      if (file && pasted) throw new Error("请选择文件或粘贴台词其中一种。");
      if (file?.size > 524288) throw new Error("文件超过 512 KB，请按集缩小后再导入。");
      const cues = parseSubtitles(file ? await file.text() : pasted, file?.name);
      const lesson = {
        id: crypto.randomUUID(), title, language: selector.value, imported: true,
        ...externalUrl(form.elements.video.value.trim()), cues,
        cards: cues.slice(0, 10).map(cue => ({ vi: cue.text, startSeconds: cue.startSeconds })),
      };
      state.imported.push(lesson);
      if (!save()) state.imported.pop();
      if (storageNotice) throw new Error("无法保存这份台词，请检查浏览器存储或导入较少文字。");
      location.hash = "#local/" + lesson.id;
    } catch (problem) {
      error.textContent = problem instanceof TypeError ? "请检查影片链接或字幕文件后重试。" : problem.message;
    } finally {
      submit.disabled = false;
    }
  });
  main.replaceChildren(hero("影视学习", "导入你正在看的剧", "放入字幕或台词，按同样的三步练习。"), panel);
}

function navigate(focus = false) {
  stopAudio();
  const [page, id] = location.hash.slice(1).split("/");
  if (page === "main-content") return;
  const section = page === "local" ? "import" : (["scene", "drama", "import"].includes(page) ? page : "scene");
  for (const anchor of document.querySelectorAll(".top-nav a")) {
    if (anchor.id === "nav-" + section) anchor.setAttribute("aria-current", "page");
    else anchor.removeAttribute("aria-current");
  }
  run = null;
  renderCourse();
  const match = page === "local" ? state.imported.find(item => item.id === id)
    : page === "drama" ? episodes.find(item => item.id === id) ?? episodes.find(item => !complete(item)) ?? episodes[0] : null;
  if (match) {
    if (page === "drama" && id !== match.id) history.replaceState(null, "", "#drama/" + match.id);
    renderLesson(match);
  }
  else if (section === "import") renderImport();
  else renderScene();
  if (focus) main.focus();
}

window.addEventListener("hashchange", () => navigate(true));
document.querySelector(".skip").addEventListener("click", event => {
  event.preventDefault();
  main.focus();
  main.scrollIntoView();
});
navigate();
