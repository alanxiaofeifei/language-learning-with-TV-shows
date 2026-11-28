// Per-user display defaults. The server (/private/me.json, behind Cloudflare Access + Worker JWT check)
// suggests defaults per signed-in user; localStorage overrides win.
// NOTE: visibleLangs is a DISPLAY preference only, not authorization. Anyone who can sign in can open
// every language's pages; access control lives in Cloudflare Access + src/worker.js.

export const DEFAULT_ME = Object.freeze({ visibleLangs: null, uiLang: "zh", explainLang: "zh", name: null });
const UI = ["zh", "vi"];
const PREFS_KEY = "tv:prefs:v1";

export function normalizeMe(raw) {
  const out = { ...DEFAULT_ME };
  if (!raw || typeof raw !== "object") return out;
  if (Array.isArray(raw.visibleLangs)) {
    const list = raw.visibleLangs.filter((x) => typeof x === "string" && /^[a-z]{2,3}$/.test(x));
    out.visibleLangs = list.length ? list : null;
  }
  if (UI.includes(raw.uiLang)) out.uiLang = raw.uiLang;
  if (UI.includes(raw.explainLang)) out.explainLang = raw.explainLang;
  if (typeof raw.name === "string" && raw.name.trim()) out.name = raw.name.trim().slice(0, 40);
  return out;
}

// me = normalized server defaults; local = { uiLang?, explainLang?, showAllLangs? } from localStorage.
export function effectivePrefs(me, local = {}) {
  const m = normalizeMe(me);
  return {
    uiLang: UI.includes(local.uiLang) ? local.uiLang : m.uiLang,
    explainLang: UI.includes(local.explainLang) ? local.explainLang : m.explainLang,
    visibleLangs: m.visibleLangs,
    showAllLangs: !!local.showAllLangs,
    name: m.name,
  };
}

// Which language cards the home page shows. Null visibleLangs (default) = all.
export function homeLanguages(languages, prefs) {
  if (!prefs.visibleLangs || prefs.showAllLangs) return languages;
  const set = new Set(prefs.visibleLangs);
  const mine = languages.filter((l) => set.has(l.id));
  return mine.length ? mine : languages;
}

export function loadLocalPrefs(storage = globalThis.localStorage) {
  try { return JSON.parse(storage?.getItem(PREFS_KEY) || "{}") || {}; } catch { return {}; }
}
export function saveLocalPrefs(p, storage = globalThis.localStorage) {
  try { storage?.setItem(PREFS_KEY, JSON.stringify(p)); } catch { /* private mode */ }
}

// Anonymous visitors get a redirect to the Access login (opaque with redirect: "manual") or 403;
// any failure falls back to defaults so the public home always renders.
export async function fetchMe(fetchImpl = globalThis.fetch) {
  try {
    const r = await fetchImpl("/private/me.json", { credentials: "same-origin", redirect: "manual", cache: "no-store" });
    if (!r || r.type === "opaqueredirect" || !r.ok) return { ...DEFAULT_ME, signedIn: false };
    const ct = r.headers?.get?.("content-type") || "";
    if (!ct.includes("json")) return { ...DEFAULT_ME, signedIn: false };
    return { ...normalizeMe(await r.json()), signedIn: true };
  } catch {
    return { ...DEFAULT_ME, signedIn: false };
  }
}
