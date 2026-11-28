// Tiny DOM helpers shared by app.js (Vietnamese course) and multi.js (generic shows).
import { motionOn, splitChars } from "./motion.js";

export function h(tag, attrs = {}, ...kids) {
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

export const fmt = (ms) => { const s = Math.floor(ms / 1000); return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, "0")}`; };

export function titleEl(text, className = "hero-title") {
  const el = h("h1", { class: className }, text);
  if (motionOn()) splitChars(el, text);
  return el;
}

export function progressBar(done, total) {
  const bar = h("div", { class: "progress", role: "progressbar", "aria-valuemin": "0", "aria-valuemax": String(total), "aria-valuenow": String(done) },
    h("span"));
  requestAnimationFrame(() => { bar.firstChild.style.width = `${Math.round((done / total) * 100)}%`; });
  return bar;
}
