// Static site + defence-in-depth for /private/*: Cloudflare Access protects the path at the edge,
// and this Worker re-checks the Access JWT so private assets never leak through another hostname.
let jwksCache = { at: 0, keys: [] };

const b64urlToBytes = (s) => Uint8Array.from(atob(s.replace(/-/g, "+").replace(/_/g, "/").padEnd(Math.ceil(s.length / 4) * 4, "=")), (c) => c.charCodeAt(0));
const decodeJson = (s) => JSON.parse(new TextDecoder().decode(b64urlToBytes(s)));

async function keys(team) {
  if (Date.now() - jwksCache.at < 3600_000 && jwksCache.keys.length) return jwksCache.keys;
  const r = await fetch(`${team}/cdn-cgi/access/certs`);
  if (!r.ok) throw new Error("certs " + r.status);
  jwksCache = { at: Date.now(), keys: (await r.json()).keys || [] };
  return jwksCache.keys;
}

function tokenFrom(request) {
  const h = request.headers.get("Cf-Access-Jwt-Assertion");
  if (h) return h;
  const m = (request.headers.get("Cookie") || "").match(/(?:^|;\s*)CF_Authorization=([^;]+)/);
  return m ? m[1] : null;
}

// Returns the verified JWT payload, or null. Every check must pass: RS256, aud, iss, exp/nbf, signature.
export async function verifyAccess(token, { team, aud, now = Date.now() / 1000, fetchKeys = keys }) {
  if (!token || !team || !aud) return null;
  const parts = token.split(".");
  if (parts.length !== 3) return null;
  let header, payload;
  try { header = decodeJson(parts[0]); payload = decodeJson(parts[1]); } catch { return null; }
  if (!header || !payload || header.alg !== "RS256") return null;
  const auds = Array.isArray(payload.aud) ? payload.aud : [payload.aud];
  if (!auds.includes(aud) || payload.iss !== team || !(payload.exp > now) || (payload.nbf && payload.nbf > now + 60)) return null;
  const jwk = (await fetchKeys(team)).find((k) => k.kid === header.kid);
  if (!jwk) return null;
  const key = await crypto.subtle.importKey("jwk", jwk, { name: "RSASSA-PKCS1-v1_5", hash: "SHA-256" }, false, ["verify"]);
  const ok = await crypto.subtle.verify("RSASSA-PKCS1-v1_5", key, b64urlToBytes(parts[2]), new TextEncoder().encode(parts[0] + "." + parts[1]));
  return ok === true ? payload : null;
}

// Boolean form kept for callers/tests that only need yes/no.
export async function verifyAccessJwt(token, opts) {
  return (await verifyAccess(token, opts)) !== null;
}

// Per-user display defaults from env USER_PREFS (JSON object or JSON string: lowercase email -> prefs).
// Display only, NOT authorization: Access + the JWT check above decide who may read /private/*.
// The response never contains the email.
export const DEFAULT_PREFS = Object.freeze({ visibleLangs: null, uiLang: "zh", explainLang: "zh", name: null });
const UI_LANGS = ["zh", "vi"];

function parsePrefsMap(raw) {
  if (!raw) return {};
  if (typeof raw === "object") return raw;
  try { const m = JSON.parse(raw); return m && typeof m === "object" && !Array.isArray(m) ? m : {}; } catch { return {}; }
}

export function prefsFor(email, rawMap) {
  const out = { ...DEFAULT_PREFS };
  if (typeof email !== "string" || !email) return out;
  const map = parsePrefsMap(rawMap);
  const want = email.trim().toLowerCase();
  const key = Object.keys(map).find((k) => k.trim().toLowerCase() === want);
  const p = key ? map[key] : null;
  if (!p || typeof p !== "object") return out;
  if (Array.isArray(p.visibleLangs)) {
    const list = p.visibleLangs.filter((x) => typeof x === "string" && /^[a-z]{2,3}$/.test(x));
    out.visibleLangs = list.length ? list : null;
  }
  if (UI_LANGS.includes(p.uiLang)) out.uiLang = p.uiLang;
  if (UI_LANGS.includes(p.explainLang)) out.explainLang = p.explainLang;
  if (typeof p.name === "string" && p.name.trim() && !p.name.includes("@")) out.name = p.name.trim().slice(0, 40);
  return out;
}

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    if (url.pathname.startsWith("/private/") || url.pathname === "/private") {
      let payload = null;
      try { payload = await verifyAccess(tokenFrom(request), { team: env.ACCESS_TEAM_DOMAIN, aud: env.ACCESS_AUD }); } catch { payload = null; }
      if (!payload) return new Response("Forbidden", { status: 403, headers: { "Cache-Control": "no-store" } });
      if (url.pathname === "/private/me.json") {
        if (request.method !== "GET" && request.method !== "HEAD") return new Response("Method Not Allowed", { status: 405, headers: { "Cache-Control": "no-store" } });
        return new Response(JSON.stringify(prefsFor(payload.email, env.USER_PREFS)), {
          headers: { "Content-Type": "application/json; charset=utf-8", "Cache-Control": "no-store", "X-Robots-Tag": "noindex" },
        });
      }
      const res = await env.ASSETS.fetch(request);
      const out = new Response(res.body, res);
      out.headers.set("Cache-Control", "private, max-age=3600");
      out.headers.set("X-Robots-Tag", "noindex");
      return out;
    }
    return env.ASSETS.fetch(request);
  },
};
