import test from 'node:test';
import assert from 'node:assert/strict';
import { spawnSync } from 'node:child_process';
import { mkdtempSync, rmSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join, resolve } from 'node:path';

test('scripts/check-no-private.sh passes (no SRT/audio/site/private/emails in Git)', (t) => {
  if (spawnSync('git', ['rev-parse', '--git-dir']).status !== 0) return t.skip('not a git checkout');
  const r = spawnSync('bash', ['scripts/check-no-private.sh'], { encoding: 'utf8' });
  assert.equal(r.status, 0, r.stdout + r.stderr);
});

test('email scan flags a non-allowlisted address beside an example address', (t) => {
  const cwd = mkdtempSync(join(tmpdir(), 'check-no-private-'));
  t.after(() => rmSync(cwd, { recursive: true, force: true }));
  const options = { cwd, encoding: 'utf8' };
  const script = resolve('scripts/check-no-private.sh');
  const scan = () => spawnSync('bash', [script], options);
  const git = (...args) => {
    const r = spawnSync('git', args, options);
    assert.equal(r.status, 0, r.stderr);
  };
  const fixture = join(cwd, 'fixture.txt');
  const example = 'allowed@Example.Test';
  const blocked = 'blocked@' + 'fixture.invalid';
  const mixedLine = `${example} ${blocked}\n`;

  git('init', '-q');
  writeFileSync(fixture, example + '\n');
  git('add', 'fixture.txt');
  assert.equal(scan().status, 0);

  writeFileSync(fixture, mixedLine);
  const working = scan();
  assert.equal(working.status, 1, working.stdout + working.stderr);
  assert.ok(working.stdout.includes(`\nfixture.txt:1:${blocked}\n`));

  git('add', 'fixture.txt');
  writeFileSync(fixture, example + '\n');
  const staged = scan();
  assert.equal(staged.status, 1, staged.stdout + staged.stderr);
  assert.ok(staged.stdout.includes(`\n(staged) fixture.txt:1:${blocked}\n`));
});
