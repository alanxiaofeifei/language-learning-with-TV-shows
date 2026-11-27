import test from 'node:test';
import assert from 'node:assert/strict';
import { review, queue, newCard } from '../site/lib/srs.js';
import { buildDays } from '../site/lib/curriculum.js';

test('good answers grow the interval; again resets to today', () => {
  let c = review(newCard(), 'good', 100);
  assert.equal(c.due, 101);
  c = review(c, 'good', 101); assert.equal(c.due, 104);
  c = review(c, 'good', 104); assert.ok(c.interval >= 7);
  const lapsed = review(c, 'again', 120);
  assert.equal(lapsed.due, 120); assert.equal(lapsed.reps, 0); assert.ok(lapsed.ease < c.ease);
});

test('queue returns due cards and caps new cards', () => {
  const states = { a: { due: 5 }, b: { due: 9 } };
  const q = queue(['a', 'b', 'c', 'd', 'e'], states, { day: 6, newLimit: 2 });
  assert.deepEqual(q.due, ['a']); assert.deepEqual(q.fresh, ['c', 'd']);
});

test('12-week plan covers every part exactly once in 84 days', () => {
  const days = buildDays(82);
  assert.equal(days.length, 84);
  const parts = days.flatMap((d) => d.parts);
  assert.deepEqual(parts, Array.from({ length: 82 }, (_, i) => i + 1));
  assert.equal(days.at(-1).week, 12);
});
