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

export async function verifyAccessJwt(token, { team, aud, now = Date.now() / 1000, fetchKeys = keys }) {
  if (!token || !team || !aud) return false;
  const parts = token.split(".");
  if (parts.length !== 3) return false;
  let header, payload;
  try { header = decodeJson(parts[0]); payload = decodeJson(parts[1]); } catch { return false; }
  if (header.alg !== "RS256") return false;
  const auds = Array.isArray(payload.aud) ? payload.aud : [payload.aud];
  if (!auds.includes(aud) || payload.iss !== team || !(payload.exp > now) || (payload.nbf && payload.nbf > now + 60)) return false;
  const jwk = (await fetchKeys(team)).find((k) => k.kid === header.kid);
  if (!jwk) return false;
  const key = await crypto.subtle.importKey("jwk", jwk, { name: "RSASSA-PKCS1-v1_5", hash: "SHA-256" }, false, ["verify"]);
  return crypto.subtle.verify("RSASSA-PKCS1-v1_5", key, b64urlToBytes(parts[2]), new TextEncoder().encode(parts[0] + "." + parts[1]));
}

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    if (url.pathname.startsWith("/private/") || url.pathname === "/private") {
      let ok = false;
      try { ok = await verifyAccessJwt(tokenFrom(request), { team: env.ACCESS_TEAM_DOMAIN, aud: env.ACCESS_AUD }); } catch { ok = false; }
      if (!ok) return new Response("Forbidden", { status: 403, headers: { "Cache-Control": "no-store" } });
      const res = await env.ASSETS.fetch(request);
      const out = new Response(res.body, res);
      out.headers.set("Cache-Control", "private, max-age=3600");
      out.headers.set("X-Robots-Tag", "noindex");
      return out;
    }
    return env.ASSETS.fetch(request);
  },
};
