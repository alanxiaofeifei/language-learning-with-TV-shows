import test from 'node:test';
import assert from 'node:assert/strict';
import { buildDays } from '../site/lib/curriculum.js';
import {
  LONG_STAGES, LONG_TOTAL_WEEKS, WORK_TOPICS,
  buildLongWeeks, firstPassParts, nextWeek, stageById,
} from '../site/lib/long-curriculum.js';

test('12-week short plan covers every part exactly once in 84 days', () => {
  const days = buildDays(82);
  assert.equal(days.length, 84);
  const parts = days.flatMap((d) => d.parts);
  assert.deepEqual(parts, Array.from({ length: 82 }, (_, i) => i + 1));
  assert.equal(days.at(-1).week, 12);
});

test('5-year long plan spans 260 weeks and first-pass covers each part once', () => {
  const weeks = buildLongWeeks(82);
  assert.equal(weeks.length, LONG_TOTAL_WEEKS);
  assert.deepEqual(weeks.map((w) => w.week), Array.from({ length: 260 }, (_, i) => i + 1));
  const first = firstPassParts(weeks);
  assert.deepEqual(first, Array.from({ length: 82 }, (_, i) => i + 1));
  assert.equal(new Set(weeks.map((w) => w.stage)).size, LONG_STAGES.length);
  const sums = LONG_STAGES.reduce((n, s) => n + s.weekCount, 0);
  assert.equal(sums, 260);
  const work = stageById('work');
  assert.equal(work.workPack, true);
  assert.ok(work.goal.includes('Chilisin'));
  const workWeeks = weeks.filter((w) => w.stage === 'work');
  assert.equal(workWeeks.length, 52);
  assert.ok(workWeeks.every((w) => w.topic && WORK_TOPICS.some((t) => t.id === w.topic.id)));
  const maintain = weeks.filter((w) => w.stage === 'maintain');
  assert.equal(maintain.length, 52);
  assert.ok(maintain.every((w) => w.mode === 'cycle' && w.parts.length >= 1));
  const maintainParts = maintain.flatMap((w) => w.parts);
  assert.deepEqual(maintainParts, Array.from({ length: 82 }, (_, i) => i + 1));
  const nativeRewatch = weeks.filter((w) => w.mode === 'rewatch');
  assert.ok(nativeRewatch.length > 0);
  assert.ok(nativeRewatch.every((w) => w.parts.every((p) => p <= 68)));
  assert.equal(nextWeek(weeks, []).week, 1);
  assert.equal(nextWeek(weeks, Array.from({ length: 10 }, (_, i) => i + 1)).week, 11);
});
