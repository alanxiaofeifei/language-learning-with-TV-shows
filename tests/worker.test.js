import test from 'node:test';
import assert from 'node:assert/strict';
import worker, { verifyAccessJwt, verifyAccess, prefsFor, DEFAULT_PREFS, keys, resetJwksCache } from '../src/worker.js';

const team = 'https://team.cloudflareaccess.com', aud = 'aud123';
const enc = (o) => Buffer.from(JSON.stringify(o)).toString('base64url');

// header overrides the JOSE header (e.g. drop kid); jwkKid overrides the kid on the published JWK.
async function signed(payload, kid = 'k1', { header, jwkKid } = {}) {
  const { publicKey, privateKey } = await crypto.subtle.generateKey({ name: 'RSASSA-PKCS1-v1_5', modulusLength: 2048, publicExponent: new Uint8Array([1, 0, 1]), hash: 'SHA-256' }, true, ['sign', 'verify']);
  const head = enc(header || { alg: 'RS256', kid }), body = enc(payload);
  const sig = Buffer.from(await crypto.subtle.sign('RSASSA-PKCS1-v1_5', privateKey, new TextEncoder().encode(head + '.' + body))).toString('base64url');
  const jwk = { ...(await crypto.subtle.exportKey('jwk', publicKey)) };
  if (jwkKid !== null) jwk.kid = jwkKid === undefined ? kid : jwkKid;
  return { token: `${head}.${body}.${sig}`, jwk, fetchKeys: async () => [jwk] };
}

test('accepts a valid Access JWT and rejects wrong aud, expiry, issuer or signature', async () => {
  const now = 1_000_000;
  const good = await signed({ aud: [aud], iss: team, exp: now + 60 });
  assert.equal(await verifyAccessJwt(good.token, { team, aud, now, fetchKeys: good.fetchKeys }), true);
  assert.equal(await verifyAccessJwt(good.token, { team, aud: 'other', now, fetchKeys: good.fetchKeys }), false);
  assert.equal(await verifyAccessJwt(good.token, { team, aud, now: now + 120, fetchKeys: good.fetchKeys }), false);
  assert.equal(await verifyAccessJwt(good.token, { team: 'https://evil', aud, now, fetchKeys: good.fetchKeys }), false);
  const other = await signed({ aud: [aud], iss: team, exp: now + 60 });
  assert.equal(await verifyAccessJwt(good.token, { team, aud, now, fetchKeys: other.fetchKeys }), false);
  assert.equal(await verifyAccessJwt('', { team, aud, now }), false);
});

test('private paths without a token are 403 and never reach assets; public paths are served', async () => {
  let served = 0;
  const env = { ACCESS_TEAM_DOMAIN: team, ACCESS_AUD: aud, ASSETS: { fetch: async () => { served++; return new Response('ok'); } } };
  const r = await worker.fetch(new Request('https://tv.example/private/data/index.json'), env);
  assert.equal(r.status, 403); assert.equal(served, 0);
  const pub = await worker.fetch(new Request('https://tv.example/'), env);
  assert.equal(pub.status, 200); assert.equal(served, 1);
});

test('verifyAccess returns the payload only for a valid token', async () => {
  const now = 1_000_000;
  const good = await signed({ aud: [aud], iss: team, exp: now + 60, email: 'alan@example.test' });
  const payload = await verifyAccess(good.token, { team, aud, now, fetchKeys: good.fetchKeys });
  assert.equal(payload.email, 'alan@example.test');
  assert.equal(await verifyAccess(good.token, { team, aud: 'nope', now, fetchKeys: good.fetchKeys }), null);
  assert.equal(await verifyAccess('a.b', { team, aud, now }), null);
});

test('prefsFor maps lowercase emails, ignores junk and defaults unknown users', () => {
  const map = JSON.stringify({
    'linh@example.test': { visibleLangs: ['zh', 'en', 'BAD!', 7], uiLang: 'vi', explainLang: 'vi', name: 'Linh' },
    'Mixed@Example.Test': { uiLang: 'xx', name: 'who@example.test' },
  });
  assert.deepEqual(prefsFor('LINH@example.test', map), { visibleLangs: ['zh', 'en'], uiLang: 'vi', explainLang: 'vi', name: 'Linh' });
  assert.deepEqual(prefsFor('mixed@example.test', map), DEFAULT_PREFS);
  assert.deepEqual(prefsFor('stranger@example.test', map), DEFAULT_PREFS);
  assert.deepEqual(prefsFor(undefined, map), DEFAULT_PREFS);
  assert.deepEqual(prefsFor('linh@example.test', 'not json'), DEFAULT_PREFS);
  assert.deepEqual(prefsFor('linh@example.test', { 'linh@example.test': { uiLang: 'vi' } }).uiLang, 'vi');
  assert.equal(DEFAULT_PREFS.visibleLangs, null);
});

async function meEnv(prefs) {
  const now = Math.floor(Date.now() / 1000);
  const tokens = {};
  let jwks = [];
  for (const email of ['linh@example.test', 'alan@example.test', 'nobody@example.test']) {
    const s = await signed({ aud: [aud], iss: team, exp: now + 600, email }, 'kid-' + email);
    tokens[email] = s.token; jwks = jwks.concat(await s.fetchKeys());
  }
  let served = 0;
  const env = { ACCESS_TEAM_DOMAIN: team, ACCESS_AUD: aud, USER_PREFS: prefs, ASSETS: { fetch: async () => { served++; return new Response('asset'); } } };
  return { env, tokens, jwks, served: () => served };
}

test('GET /private/me.json returns prefs for the signed-in user, never the email', async () => {
  const realFetch = globalThis.fetch;
  const prefs = JSON.stringify({ 'linh@example.test': { visibleLangs: ['zh', 'en'], uiLang: 'vi', explainLang: 'vi', name: 'Linh' } });
  const m = await meEnv(prefs);
  // Stub the JWKS fetch the Worker makes to the Access team domain.
  globalThis.fetch = async (u) => {
    assert.equal(String(u), `${team}/cdn-cgi/access/certs`);
    return new Response(JSON.stringify({ keys: m.jwks }), { headers: { 'Content-Type': 'application/json' } });
  };
  try {
    const call = (email) => worker.fetch(new Request('https://tv.example/private/me.json', { headers: email ? { 'Cf-Access-Jwt-Assertion': m.tokens[email] } : {} }), m.env);
    const r = await call('linh@example.test');
    assert.equal(r.status, 200);
    assert.equal(r.headers.get('Cache-Control'), 'no-store');
    const text = await r.text();
    assert.ok(!text.includes('@'), 'no email in body');
    assert.deepEqual(JSON.parse(text), { visibleLangs: ['zh', 'en'], uiLang: 'vi', explainLang: 'vi', name: 'Linh' });

    const unknown = await call('nobody@example.test');
    const body = await unknown.text();
    assert.ok(!body.includes('@'));
    assert.deepEqual(JSON.parse(body), { visibleLangs: null, uiLang: 'zh', explainLang: 'zh', name: null });

    const anon = await call(null);
    assert.equal(anon.status, 403);
    assert.equal(m.served(), 0, 'me.json never falls through to static assets');

    const noPrefsEnv = { ...m.env, USER_PREFS: undefined };
    const r2 = await worker.fetch(new Request('https://tv.example/private/me.json', { headers: { 'Cf-Access-Jwt-Assertion': m.tokens['alan@example.test'] } }), noPrefsEnv);
    assert.deepEqual(await r2.json(), DEFAULT_PREFS);

    const asset = await worker.fetch(new Request('https://tv.example/private/shows/friends/index.json', { headers: { Cookie: 'CF_Authorization=' + m.tokens['alan@example.test'] } }), m.env);
    assert.equal(asset.status, 200); assert.equal(await asset.text(), 'asset');
    assert.equal(asset.headers.get('Cache-Control'), 'private, max-age=3600');
  } finally {
    globalThis.fetch = realFetch;
  }
});

test('rejects missing/non-string kid and non-numeric exp/nbf even with a valid signature', async () => {
  const now = 1_000_000;
  const base = { aud: [aud], iss: team, exp: now + 60 };
  // No kid in the header, and a published JWK that also lacks kid: undefined === undefined must not match.
  const noKid = await signed(base, 'k1', { header: { alg: 'RS256' }, jwkKid: null });
  assert.equal(await verifyAccess(noKid.token, { team, aud, now, fetchKeys: noKid.fetchKeys }), null);
  const numKid = await signed(base, 'k1', { header: { alg: 'RS256', kid: 7 }, jwkKid: 7 });
  assert.equal(await verifyAccess(numKid.token, { team, aud, now, fetchKeys: numKid.fetchKeys }), null);
  const emptyKid = await signed(base, '', { header: { alg: 'RS256', kid: '' } });
  assert.equal(await verifyAccess(emptyKid.token, { team, aud, now, fetchKeys: emptyKid.fetchKeys }), null);
  const strExp = await signed({ ...base, exp: String(now + 60) });
  assert.equal(await verifyAccess(strExp.token, { team, aud, now, fetchKeys: strExp.fetchKeys }), null);
  const noExp = await signed({ aud: [aud], iss: team });
  assert.equal(await verifyAccess(noExp.token, { team, aud, now, fetchKeys: noExp.fetchKeys }), null);
  const strNbf = await signed({ ...base, nbf: String(now) });
  assert.equal(await verifyAccess(strNbf.token, { team, aud, now, fetchKeys: strNbf.fetchKeys }), null);
  const futureNbf = await signed({ ...base, nbf: now + 600 });
  assert.equal(await verifyAccess(futureNbf.token, { team, aud, now, fetchKeys: futureNbf.fetchKeys }), null);
  const okNbf = await signed({ ...base, nbf: now - 10 });
  assert.ok(await verifyAccess(okNbf.token, { team, aud, now, fetchKeys: okNbf.fetchKeys }));
  const hs = await signed(base, 'k1', { header: { alg: 'HS256', kid: 'k1' } });
  assert.equal(await verifyAccess(hs.token, { team, aud, now, fetchKeys: hs.fetchKeys }), null);
});

test('unknown kid triggers one forced JWKS refresh (key rotation)', async () => {
  const now = 1_000_000;
  const rotated = await signed({ aud: [aud], iss: team, exp: now + 60 }, 'new-kid');
  const old = await signed({ aud: [aud], iss: team, exp: now + 60 }, 'old-kid');
  const calls = [];
  const fetchKeys = async (_t, opts = {}) => { calls.push(!!opts.refresh); return opts.refresh ? [old.jwk, rotated.jwk] : [old.jwk]; };
  assert.ok(await verifyAccess(rotated.token, { team, aud, now, fetchKeys }));
  assert.deepEqual(calls, [false, true]);
  calls.length = 0;
  assert.ok(await verifyAccess(old.token, { team, aud, now, fetchKeys }));
  assert.deepEqual(calls, [false], 'known kid: no refresh');
});

test('keys() caches for an hour, refetches on refresh only after a minute, and drops kid-less JWKs', async () => {
  resetJwksCache();
  let n = 0, list = [{ kid: 'a', kty: 'RSA' }, { kty: 'RSA' }];
  const fetchImpl = async () => { n++; return new Response(JSON.stringify({ keys: list })); };
  const t0 = 5_000_000;
  assert.deepEqual((await keys(team, { now: t0, fetchImpl })).map((k) => k.kid), ['a']);
  await keys(team, { now: t0 + 30_000, fetchImpl });
  await keys(team, { now: t0 + 30_000, refresh: true, fetchImpl });
  assert.equal(n, 1, 'refresh within 60 s reuses the cache');
  list = [{ kid: 'a' }, { kid: 'b' }];
  assert.deepEqual((await keys(team, { now: t0 + 61_000, refresh: true, fetchImpl })).map((k) => k.kid), ['a', 'b']);
  assert.equal(n, 2);
  await keys(team, { now: t0 + 61_000 + 3_500_000, fetchImpl });
  assert.equal(n, 2, 'still within the 1 h TTL');
  await keys(team, { now: t0 + 61_000 + 3_600_001, fetchImpl });
  assert.equal(n, 3);
  await keys('https://other.cloudflareaccess.com', { now: t0 + 61_000 + 3_600_002, fetchImpl });
  assert.equal(n, 4, 'cache is per team domain');
  resetJwksCache();
});
