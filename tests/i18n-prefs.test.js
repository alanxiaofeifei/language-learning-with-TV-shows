import { readerLanguages, defaultToggles, explainOf } from "../site/multi.js";
import { SHOWS } from "../site/lib/catalog.js";
import test from 'node:test';
import assert from 'node:assert/strict';
import { DICT, UI_LANGS, t, setUiLang, pick } from '../site/lib/i18n.js';
import { normalizeMe, effectivePrefs, homeLanguages, fetchMe, DEFAULT_ME } from '../site/lib/prefs.js';
import { LANGUAGES } from '../site/lib/catalog.js';

test('i18n: zh and vi have the same non-empty keys and the same placeholders', () => {
  assert.deepEqual(UI_LANGS, ['zh', 'vi']);
  const zk = Object.keys(DICT.zh).sort(), vk = Object.keys(DICT.vi).sort();
  assert.deepEqual(vk, zk);
  for (const k of zk) {
    for (const l of UI_LANGS) assert.ok(DICT[l][k].trim(), `${l}.${k} empty`);
    const ph = (s) => (s.match(/\{\w+\}/g) || []).sort();
    assert.deepEqual(ph(DICT.vi[k]), ph(DICT.zh[k]), `placeholders differ for ${k}`);
  }
  assert.equal(DICT.vi['home.showAll'], 'Hiện tất cả ngôn ngữ');
  assert.equal(DICT.zh['home.showAll'], '显示全部语言');
  assert.equal(DICT.zh['show.watchOwn'], '用你自己的正版来源观看');
  assert.equal(DICT.vi['show.watchOwn'], 'Xem bằng nguồn chính thức của bạn');
});

test('i18n: t() switches language, fills vars, falls back to zh', () => {
  setUiLang('vi'); assert.equal(t('ep.title', { n: 3 }), 'Tập 3'); assert.equal(pick({ zh: '中', vi: 'Việt' }), 'Việt');
  setUiLang('xx'); assert.equal(t('ep.title', { n: 3 }), '第 3 集');
  assert.equal(t('nav.today'), '今天'); assert.equal(pick({ zh: '中' }, 'vi'), '中');
});

test('prefs: defaults, local overrides, visible languages are display-only filtering', () => {
  assert.deepEqual(normalizeMe(null), DEFAULT_ME);
  const linh = normalizeMe({ visibleLangs: ['zh', 'en', 'NOPE'], uiLang: 'vi', explainLang: 'vi', name: 'Linh' });
  assert.deepEqual(linh.visibleLangs, ['zh', 'en']);
  assert.equal(effectivePrefs(linh, {}).uiLang, 'vi');
  assert.equal(effectivePrefs(linh, { uiLang: 'zh' }).uiLang, 'zh');
  assert.deepEqual(homeLanguages(LANGUAGES, effectivePrefs(linh, {})).map((l) => l.id), ['zh', 'en']);
  assert.equal(homeLanguages(LANGUAGES, effectivePrefs(linh, { showAllLangs: true })).length, LANGUAGES.length);
  // Alan / unknown / anonymous: everything, Chinese UI.
  const alan = effectivePrefs(DEFAULT_ME, {});
  assert.equal(alan.uiLang, 'zh'); assert.equal(alan.explainLang, 'zh');
  assert.equal(homeLanguages(LANGUAGES, alan).length, LANGUAGES.length);
});

test('fetchMe falls back to defaults on redirect, 403, non-JSON or network failure', async () => {
  const resp = (o) => async () => o;
  assert.equal((await fetchMe(resp({ type: 'opaqueredirect', ok: false, status: 0 }))).uiLang, 'zh');
  assert.equal((await fetchMe(resp({ type: 'basic', ok: false, status: 403 }))).signedIn, false);
  assert.equal((await fetchMe(resp(new Response('<html>', { headers: { 'content-type': 'text/html' } })))).signedIn, false);
  assert.equal((await fetchMe(async () => { throw new TypeError('offline'); })).uiLang, 'zh');
  const ok = await fetchMe(resp(new Response(JSON.stringify({ uiLang: 'vi', explainLang: 'vi', visibleLangs: ['zh'] }), { headers: { 'content-type': 'application/json' } })));
  assert.equal(ok.uiLang, 'vi'); assert.equal(ok.signedIn, true); assert.deepEqual(ok.visibleLangs, ['zh']);
});

test('reader preferences hide Vietnamese translations and preserve target languages', () => {
  const alan = effectivePrefs();
  const linh = effectivePrefs({ hideLangs: [], explainLang: 'vi' });
  assert.deepEqual(alan.hideLangs, ['vi']);
  assert.deepEqual(linh.hideLangs, []);
  assert.deepEqual(normalizeMe({ hideLangs: ['vi', 'BAD', 5, 'abcd'] }).hideLangs, ['vi']);

  const show = SHOWS.friends;
  assert.deepEqual(readerLanguages(show, alan), ['en', 'zh']);
  assert.deepEqual(readerLanguages(show, linh), ['en', 'zh', 'vi']);
  assert.deepEqual(defaultToggles(show, { ...alan, explainLang: 'vi' }), { en: true, zh: true });
  assert.deepEqual(defaultToggles(show, linh), { en: true, vi: true });
  assert.deepEqual(readerLanguages(SHOWS.lupin, linh, ['fr', 'zh', 'vi']), ['fr', 'zh']);
  assert.deepEqual(readerLanguages(SHOWS['ve-nha-di-con'], alan, ['vi', 'zh']), ['vi', 'zh']);

  const card = { meaning_vi: 'vi meaning', explain_vi: 'vi explanation', usage_vi: 'vi usage', explain_zh: 'zh explanation' };
  assert.deepEqual(explainOf(show, card, { ...alan, explainLang: 'vi' }), { meaning: '', explain: 'zh explanation', usage: '' });
  assert.deepEqual(explainOf(show, card, linh), { meaning: 'vi meaning', explain: 'vi explanation', usage: 'vi usage' });
});
