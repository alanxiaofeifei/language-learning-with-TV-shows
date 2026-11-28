import test from 'node:test';
import assert from 'node:assert/strict';
import { spawnSync } from 'node:child_process';

test('scripts/check-no-private.sh passes (no SRT/audio/site/private/emails in Git)', (t) => {
  if (spawnSync('git', ['rev-parse', '--git-dir']).status !== 0) return t.skip('not a git checkout');
  const r = spawnSync('bash', ['scripts/check-no-private.sh'], { encoding: 'utf8' });
  assert.equal(r.status, 0, r.stdout + r.stderr);
});
