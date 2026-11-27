import test from 'node:test';
import assert from 'node:assert/strict';
import {
  LANGUAGES, SHOWS, TRACKS, DEFAULT_SHOW,
  languageById, showsForLanguage, href, matchRoute, isComingLanguage, safeDecode,
} from '../site/lib/catalog.js';

test('catalog lists six languages and only Vietnamese is ready', () => {
  assert.deepEqual(LANGUAGES.map((l) => l.id), ['vi', 'en', 'fr', 'ja', 'es', 'yue']);
  const ready = LANGUAGES.filter((l) => l.status === 'ready');
  assert.equal(ready.length, 1);
  assert.equal(ready[0].id, 'vi');
  assert.deepEqual(ready[0].shows, ['ve-nha-di-con']);
  for (const lang of LANGUAGES.filter((l) => l.status === 'coming')) {
    assert.equal(lang.shows.length, 0);
    assert.equal(isComingLanguage(lang.id), true);
    assert.equal(showsForLanguage(lang.id).length, 0);
  }
  assert.equal(SHOWS[DEFAULT_SHOW].language, 'vi');
  assert.deepEqual(SHOWS[DEFAULT_SHOW].tracks, ['short', 'long']);
  assert.ok(TRACKS.short && TRACKS.long);
});

test('href and matchRoute round-trip for language, show and track pages', () => {
  const cases = [
    { page: 'home' },
    { page: 'lang', lang: 'fr' },
    { page: 'lang', lang: 'yue' },
    { page: 'show', lang: 'vi', show: 've-nha-di-con' },
    { page: 'track', lang: 'vi', show: 've-nha-di-con', track: 'short' },
    { page: 'track', lang: 'vi', show: 've-nha-di-con', track: 'long' },
    { page: 'day', lang: 'vi', show: 've-nha-di-con', track: 'short', day: 6 },
    { page: 'plan', lang: 'vi', show: 've-nha-di-con', track: 'short' },
    { page: 'plan', lang: 'vi', show: 've-nha-di-con', track: 'long' },
    { page: 'stage', lang: 'vi', show: 've-nha-di-con', track: 'long', stage: 'work' },
    { page: 'week', lang: 'vi', show: 've-nha-di-con', track: 'long', week: 120 },
    { page: 'part', lang: 'vi', show: 've-nha-di-con', part: 12 },
    { page: 'parts', lang: 'vi', show: 've-nha-di-con' },
    { page: 'review', lang: 'vi', show: 've-nha-di-con' },
    { page: 'scenes', lang: 'vi', show: 've-nha-di-con', cat: 'food' },
    { page: 'search', lang: 'vi', show: 've-nha-di-con', q: 'bao nhiêu' },
    { page: 'vlc', lang: 'vi', show: 've-nha-di-con' },
    { page: 'lesson', lang: 'vi', show: 've-nha-di-con', lesson: 'tones' },
  ];
  for (const rec of cases) {
    const got = matchRoute(href(rec));
    for (const [k, v] of Object.entries(rec)) {
      if (v == null) continue;
      assert.equal(got[k], v, `${href(rec)} ${k}`);
    }
  }
});

test('legacy hashes alias to the Vietnamese show and unknown routes 404', () => {
  const plan = matchRoute('#/plan');
  assert.equal(plan.page, 'plan');
  assert.equal(plan.lang, 'vi');
  assert.equal(plan.show, 've-nha-di-con');
  assert.equal(plan.track, 'short');
  assert.equal(plan.alias, true);
  assert.equal(matchRoute('#/day/12').day, 12);
  assert.equal(matchRoute('#/part/3').part, 3);
  assert.equal(matchRoute('#/scenes/work').cat, 'work');
  const bad = matchRoute('#/en/ve-nha-di-con');
  assert.equal(bad.page, 'notfound');
  assert.equal(bad.show, undefined);
  assert.equal(bad.lang, undefined);
  assert.equal(matchRoute('#/lang/xx').page, 'notfound');
  assert.equal(matchRoute('#/vi/unknown-show').page, 'notfound');
  assert.equal(safeDecode('bao%20nhi%C3%AAu'), 'bao nhiêu');
  assert.equal(safeDecode('100%'), '100%');
  assert.equal(matchRoute('#/search/100%').q, '100%');
  assert.equal(languageById('ja').variant, '东京标准音');
});
