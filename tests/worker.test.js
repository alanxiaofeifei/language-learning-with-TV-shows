import test from 'node:test';
import assert from 'node:assert/strict';
import worker, { verifyAccessJwt } from '../src/worker.js';

const team = 'https://team.cloudflareaccess.com', aud = 'aud123';
const enc = (o) => Buffer.from(JSON.stringify(o)).toString('base64url');

async function signed(payload, kid = 'k1') {
  const { publicKey, privateKey } = await crypto.subtle.generateKey({ name: 'RSASSA-PKCS1-v1_5', modulusLength: 2048, publicExponent: new Uint8Array([1, 0, 1]), hash: 'SHA-256' }, true, ['sign', 'verify']);
  const head = enc({ alg: 'RS256', kid }), body = enc(payload);
  const sig = Buffer.from(await crypto.subtle.sign('RSASSA-PKCS1-v1_5', privateKey, new TextEncoder().encode(head + '.' + body))).toString('base64url');
  const jwk = { ...(await crypto.subtle.exportKey('jwk', publicKey)), kid };
  return { token: `${head}.${body}.${sig}`, fetchKeys: async () => [jwk] };
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
