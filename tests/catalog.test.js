import test from 'node:test';
import assert from 'node:assert/strict';
import {
  LANGUAGES, SHOWS, TRACKS, DEFAULT_SHOW,
  languageById, showsForLanguage, href, matchRoute, isComingLanguage, safeDecode, isMultiShow, showDataBase,
} from '../site/lib/catalog.js';

test('catalog: vi, zh, en, fr, ja ready; es/yue placeholders with planned picks', () => {
  assert.deepEqual(LANGUAGES.map((l) => l.id), ['vi', 'zh', 'en', 'fr', 'ja', 'es', 'yue']);
  const ready = LANGUAGES.filter((l) => l.status === 'ready').map((l) => l.id);
  assert.deepEqual(ready, ['vi', 'zh', 'en', 'fr', 'ja']);
  assert.deepEqual(languageById('vi').shows, ['ve-nha-di-con']);
  assert.deepEqual(languageById('zh').shows, ['dou-ting-hao']);
  assert.deepEqual(languageById('en').shows, ['friends', 'seinfeld', 'silicon-valley', 'desperate-housewives']);
  for (const lang of LANGUAGES.filter((l) => l.status === 'coming')) {
    assert.equal(lang.shows.length, 0);
    assert.equal(isComingLanguage(lang.id), true);
    assert.equal(showsForLanguage(lang.id).length, 0);
    assert.ok(lang.planned.length >= 1, lang.id + ' lists planned picks');
  }
  const titles = (id) => languageById(id).planned.map((p) => p.title).join('|');
  assert.match(titles('fr'), /魁北克/);
  assert.deepEqual(languageById('fr').shows, ['lupin']);
  assert.deepEqual(languageById('ja').shows, ['nigeru-wa-haji']);
  assert.match(titles('es'), /Club de Cuervos/); assert.match(titles('es'), /La casa de las flores/);
  assert.match(titles('yue'), /愛·回家之開心速遞/);
  assert.deepEqual(languageById('en').planned, []);
  assert.match(titles('zh'), /欢乐颂/); assert.match(titles('zh'), /我们与恶的距离/);
  assert.match(titles('vi'), /Gạo nếp gạo tẻ/);
  assert.equal(SHOWS[DEFAULT_SHOW].language, 'vi');
  assert.equal(SHOWS[DEFAULT_SHOW].dataBase, '/private/data');
  assert.deepEqual(SHOWS[DEFAULT_SHOW].tracks, ['short', 'long']);
  assert.ok(TRACKS.short && TRACKS.long);
});

test('new shows have their own private data base and source types', () => {
  const dtt = SHOWS['dou-ting-hao'], fr = SHOWS.friends;
  assert.equal(dtt.language, 'zh'); assert.equal(dtt.episodes, 46); assert.equal(dtt.source, 'youtube-official');
  assert.equal(dtt.playlist, 'PL2Vcf2jYz5dfh5rHzOEok_gDLJf39MhuO');
  assert.equal(dtt.dataBase, '/private/shows/dou-ting-hao'); assert.equal(showDataBase('x'), '/private/shows/x');
  assert.equal(fr.language, 'en'); assert.equal(fr.source, 'text-only'); assert.equal(fr.episodes, 48);
  assert.equal(fr.dataBase, '/private/shows/friends'); assert.equal(fr.watch.url, 'https://www.hbomax.com/');
  assert.ok(isMultiShow('friends') && isMultiShow('dou-ting-hao') && !isMultiShow('ve-nha-di-con'));
});

for (const [id, count, year] of [
  ['seinfeld', 17, '1990–1993 · S01–S02'],
  ['silicon-valley', 8, '2014 · S01'],
  ['desperate-housewives', 22, '2004–2005 · S01'],
]) {
  test(`${id} has text-only English routes for both tracks`, () => {
    const show = SHOWS[id];
    assert.ok(isMultiShow(id));
    assert.equal(show.language, 'en');
    assert.equal(show.source, 'text-only');
    assert.equal(show.watch, null);
    assert.equal(show.year, year);
    assert.equal(show.episodes, count);
    assert.equal(show.dataBase, `/private/shows/${id}`);
    assert.equal(show.publicBase, `/shows/${id}`);
    assert.deepEqual(show.tracks, ['short', 'long']);
    for (const track of show.tracks) {
      const route = matchRoute(href({ page: 'track', lang: 'en', show: id, track }));
      assert.equal(route.page, 'track');
      assert.equal(route.show, id);
      assert.equal(route.track, track);
    }
    const route = matchRoute(href({ page: 'ep', lang: 'en', show: id, ep: count }));
    assert.equal(route.page, 'ep');
    assert.equal(route.ep, count);
  });
}

test('new show routes round-trip and cross-language shows 404', () => {
  const cases = [
    { page: 'lang', lang: 'zh' },
    { page: 'show', lang: 'zh', show: 'dou-ting-hao' },
    { page: 'ep', lang: 'zh', show: 'dou-ting-hao', ep: 46 },
    { page: 'track', lang: 'zh', show: 'dou-ting-hao', track: 'long' },
    { page: 'day', lang: 'en', show: 'friends', track: 'short', day: 84 },
    { page: 'plan', lang: 'en', show: 'friends', track: 'short' },
    { page: 'parts', lang: 'en', show: 'friends' },
    { page: 'review', lang: 'en', show: 'friends' },
    { page: 'ep', lang: 'en', show: 'friends', ep: 1 },
    { page: 'ep', lang: 'ja', show: 'nigeru-wa-haji', ep: 11 },
    { page: 'track', lang: 'ja', show: 'nigeru-wa-haji', track: 'long' },
    { page: 'ep', lang: 'fr', show: 'lupin', ep: 5 },
    { page: 'track', lang: 'fr', show: 'lupin', track: 'long' },
  ];
  for (const rec of cases) {
    const got = matchRoute(href(rec));
    for (const [k, v] of Object.entries(rec)) assert.equal(got[k], v, `${href(rec)} ${k}`);
  }
  assert.equal(matchRoute('#/en/dou-ting-hao').page, 'notfound');
  assert.equal(matchRoute('#/zh/friends/ep/1').page, 'notfound');
  assert.equal(matchRoute('#/vi/ve-nha-di-con/part/3').part, 3);
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
