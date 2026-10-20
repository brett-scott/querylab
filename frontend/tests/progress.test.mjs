import { test } from 'node:test';
import assert from 'node:assert/strict';
import { clearActiveSubmission, completedAttempt, progressSummary, readPending, readAssistance, rememberAssistance, readActiveSubmission, saveActiveSubmission } from '../src/accounts/progress.ts';
import { validateAccountConfig } from '../config/accounts.mjs';

const snapshot = {
  id: 'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa', userId: '11111111-1111-4111-8111-111111111111',
  challenge: { id: 'OS-Q01', version: '1.0.0', title: 'Customer analysis', type: 'query', dataset: 'online-store', solution: 'private SQL' },
  hintsUsed: 2, solutionViewed: false,
};
const result = { mode: 'submit', result_sets: [{ columns: ['private'], rows: [['private row']] }], elapsed_ms: 123, grading: { passed: false, checks: [] }, sql: 'private SQL', helper_token: 'private token' };

test('saved attempts contain only progress metadata, never SQL, rows or helper secrets', () => {
  const attempt = completedAttempt(snapshot, result, '2026-10-18T01:00:00.000Z');
  assert.deepEqual(attempt, {
    id: snapshot.id, user_id: snapshot.userId, challenge_id: 'OS-Q01', challenge_version: '1.0.0',
    challenge_title: 'Customer analysis', challenge_type: 'query', dataset: 'online-store',
    passed: false, hints_used: 2, solution_viewed: false, completed_at: '2026-10-18T01:00:00.000Z',
  });
  assert.doesNotMatch(JSON.stringify(attempt), /private/);
});

test('Run and submissions without a completed grade cannot become attempts', () => {
  assert.equal(completedAttempt(snapshot, { ...result, mode: 'run' }), null);
  assert.equal(completedAttempt(snapshot, { mode: 'submit', result_sets: [], elapsed_ms: 1 }), null);
});

test('summary counts challenges once across versions and computes pass rate from all graded submissions', () => {
  const summary = progressSummary([
    { challenge_id: 'OS-Q01', challenge_version: '1.0.0', attempt_count: 2, passed_count: 1, unassisted_pass_count: 0 },
    { challenge_id: 'OS-Q01', challenge_version: '1.1.0', attempt_count: 1, passed_count: 1, unassisted_pass_count: 1 },
    { challenge_id: 'BI-F01', challenge_version: '1.0.0', attempt_count: 1, passed_count: 0, unassisted_pass_count: 0 },
  ]);
  assert.deepEqual(summary, { completed: 1, attempts: 4, passes: 2, passRate: 50, unassisted: 1 });
  assert.deepEqual(progressSummary([]), { completed: 0, attempts: 0, passes: 0, passRate: null, unassisted: 0 });
});

test('pending retries retain their original ID and owner, and discard extra private fields', () => {
  const attempt = completedAttempt(snapshot, result);
  const queue = readPending(JSON.stringify([{ ...attempt, sql: 'private SQL' }, { ...attempt, user_id: 'someone-else' }]), snapshot.userId);
  assert.deepEqual(queue, [attempt]);
  assert.deepEqual(readPending(JSON.stringify(queue), snapshot.userId), queue);
  assert.deepEqual(readPending(JSON.stringify(queue), 'someone-else'), []);
  assert.deepEqual(readPending('broken', snapshot.userId), []);
  assert.deepEqual(readPending(JSON.stringify([{ ...attempt, hints_used: 99 }]), snapshot.userId), []);
});

test('assistance survives refresh and cannot be downgraded by a later lower count', () => {
  const values = new Map();
  const original = globalThis.localStorage;
  globalThis.localStorage = { getItem: key => values.get(key) ?? null, setItem: (key, value) => values.set(key, value) };
  try {
    rememberAssistance('draft', 2, true);
    rememberAssistance('draft', 1, false);
    assert.deepEqual(readAssistance('draft'), { hintsUsed: 2, solutionViewed: true });
    assert.deepEqual(readAssistance('other-version'), { hintsUsed: 0, solutionViewed: false });
    values.set('draft:assistance', 'null');
    assert.deepEqual(readAssistance('draft'), { hintsUsed: 0, solutionViewed: false });
  } finally { globalThis.localStorage = original; }
});

test('account configuration accepts guest mode, public publishable and legacy anon keys', () => {
  assert.doesNotThrow(() => validateAccountConfig('', ''));
  assert.doesNotThrow(() => validateAccountConfig('https://project.supabase.co', 'sb_publishable_example'));
  const anon = `header.${Buffer.from(JSON.stringify({ role: 'anon' })).toString('base64url')}.signature`;
  assert.doesNotThrow(() => validateAccountConfig('http://127.0.0.1:54321', anon));
});

test('grading recovery is bound to the account, helper and challenge version', () => {
  const values = new Map();
  const original = globalThis.sessionStorage;
  globalThis.sessionStorage = { getItem: key => values.get(key) ?? null, setItem: (key, value) => values.set(key, value), removeItem: key => values.delete(key) };
  try {
    saveActiveSubmission('job-123', 'http://127.0.0.1:8765', snapshot);
    assert.deepEqual(readActiveSubmission(snapshot.userId, 'http://127.0.0.1:8765', snapshot.challenge), { jobId: 'job-123', snapshot });
    assert.equal(readActiveSubmission('someone-else', 'http://127.0.0.1:8765', snapshot.challenge), null);
    assert.equal(readActiveSubmission(snapshot.userId, 'http://127.0.0.1:8766', snapshot.challenge), null);
    assert.equal(readActiveSubmission(snapshot.userId, 'http://127.0.0.1:8765', { ...snapshot.challenge, version: '2.0.0' }), null);
    clearActiveSubmission(snapshot.userId);
    assert.equal(readActiveSubmission(snapshot.userId, 'http://127.0.0.1:8765', snapshot.challenge), null);
  } finally { globalThis.sessionStorage = original; }
});

test('configuration rejects secret/service-role keys, incomplete config and unsafe URLs', () => {
  const service = `header.${Buffer.from(JSON.stringify({ role: 'service_role' })).toString('base64url')}.signature`;
  for (const key of ['sb_secret_do_not_publish', service, 'not-a-public-key']) {
    assert.throws(() => validateAccountConfig('https://project.supabase.co', key), /public/);
  }
  assert.throws(() => validateAccountConfig('https://project.supabase.co', ''), /both/);
  for (const url of ['http://remote.example', 'https://user:password@remote.example', 'https://remote.example/path', 'https://remote.example?key=value']) {
    assert.throws(() => validateAccountConfig(url, 'sb_publishable_example'));
  }
});
