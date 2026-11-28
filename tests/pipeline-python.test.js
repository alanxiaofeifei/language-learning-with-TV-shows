import test from 'node:test';
import assert from 'node:assert/strict';
import { spawnSync } from 'node:child_process';
import { existsSync } from 'node:fs';

// Pure-function tests for pipeline/multi (phrase matching, SRT cleaning, cue alignment, clip spans).
// Prefers the pipeline venv (has pypinyin); falls back to python3 (alignment test then skips).
const VENV = '/home/box/venvs/ytdlp/bin/python';
test('pipeline/multi python unit tests', (t) => {
  const py = existsSync(VENV) ? VENV : 'python3';
  if (spawnSync(py, ['--version']).status !== 0) return t.skip('no python3');
  const r = spawnSync(py, ['-B', 'tests/python/test_pipeline_text.py'], { encoding: 'utf8', env: { ...process.env, PYTHONDONTWRITEBYTECODE: '1' } });
  assert.equal(r.status, 0, r.stdout + r.stderr);
});
