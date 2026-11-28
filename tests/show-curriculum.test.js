import test from 'node:test';
import assert from 'node:assert/strict';
import { SHOWS } from '../site/lib/catalog.js';
import { buildShowDays, watchDays, nextShowDay, SHORT_WEEKS, LONG_OUTLINES, SHORT_DAYS } from '../site/lib/show-curriculum.js';

for (const n of [46, 48, 82, 100, 1, 8, 17, 23]) {
  test(`short track for ${n} episodes: 84 days, each episode watched exactly once, in order`, () => {
    const days = buildShowDays(n);
    assert.equal(days.length, SHORT_DAYS);
    assert.deepEqual(days.map((d) => d.day), Array.from({ length: 84 }, (_, i) => i + 1));
    assert.equal(days[0].kind, 'intro');
    assert.ok(days.filter((d) => d.day % 7 === 0).every((d) => d.kind === 'review'));
    assert.deepEqual(watchDays(days).flatMap((d) => d.eps), Array.from({ length: n }, (_, i) => i + 1));
    assert.equal(days.at(-1).week, 12);
    assert.ok(days.every((d) => d.week === Math.ceil(d.day / 7)));
    for (const d of days.filter((x) => x.kind === 'deep')) assert.equal(d.eps.length, 1);
    assert.deepEqual(buildShowDays(n), days, 'deterministic');
  });
}

test('46 vs 48 episodes: deep days fill the gap; next day follows progress', () => {
  const a = buildShowDays(46), b = buildShowDays(48);
  assert.equal(a.filter((d) => d.kind === 'deep').length, 71 - 46);
  assert.equal(b.filter((d) => d.kind === 'deep').length, 71 - 48);
  assert.equal(nextShowDay(a, []).day, 1);
  assert.equal(nextShowDay(a, [1, 2, 3]).day, 4);
  assert.throws(() => buildShowDays(0));
});

test('weekly themes and long outlines exist in zh and vi for both new languages', () => {
  for (const lang of ['zh', 'en']) {
    assert.equal(SHORT_WEEKS[lang].length, 12);
    for (const w of SHORT_WEEKS[lang]) for (const ui of ['zh', 'vi']) { assert.equal(w[ui].length, 2); assert.ok(w[ui][0] && w[ui][1]); }
    assert.equal(LONG_OUTLINES[lang][0].status, 'now');
    for (const s of LONG_OUTLINES[lang]) assert.ok(s.goal.zh && s.goal.vi && s.span.zh && s.span.vi);
  }
  assert.deepEqual(LONG_OUTLINES.zh.map((s) => s.show), ['都挺好', '欢乐颂 1', '我们与恶的距离']);
  for (const { show, showId, status } of LONG_OUTLINES.en) {
    assert.equal(SHOWS[showId].titleNative, show);
    assert.equal(status, 'now');
  }
  assert.deepEqual(LONG_OUTLINES.en.map((s) => s.show), ['Friends', 'Seinfeld', 'Desperate Housewives', 'Silicon Valley']);
});
