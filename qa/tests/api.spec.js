import { test, expect } from '@playwright/test';

const headers = { Origin: process.env.QUERYLAB_URL || 'http://127.0.0.1:8080' };
async function queue(request, mode, id, sql) {
  const response = await request.post(`/api/${mode}`, { data: { challenge_id: id, sql }, headers });
  expect(response.status(), await response.text()).toBe(202);
  return (await response.json()).job_id;
}
async function completed(request, id) {
  let job;
  await expect.poll(async () => {
    const response = await request.get(`/api/jobs/${id}`);
    expect(response.status()).toBe(200);
    job = await response.json();
    return ['completed', 'failed', 'cancelled'].includes(job.status);
  }, { timeout: 60000, intervals: [200, 500] }).toBe(true);
  return job;
}

test('real SQL, all twelve reference graders, practice isolation and privilege boundaries', async ({ request, playwright, baseURL }, testInfo) => {
  const record = {};
  const catalog = await (await request.get('/api/challenges')).json();
  expect(catalog.challenges).toHaveLength(12);
  const ready = catalog.challenges.filter(c => c.ready);
  expect(ready).toHaveLength(12);
  expect(ready.filter(c => c.type === 'query')).toHaveLength(6);
  expect(ready.filter(c => c.type === 'function')).toHaveLength(3);
  expect(ready.filter(c => c.type === 'procedure')).toHaveLength(3);
  expect(catalog.challenges.every(c => !('solution' in c))).toBe(true);
  record.catalog = { total: catalog.challenges.length, executable: ready.map(c => c.id) };

  const session = await request.post('/api/session', { headers });
  expect(session.status(), await session.text()).toBe(200);
  expect(session.headers()['set-cookie']).toMatch(/httponly/i);
  const crossOrigin = await request.post('/api/run', { headers: { Origin: 'https://unrelated.example' }, data: { challenge_id: 'OS-Q01', sql: 'SELECT 1;' } });
  expect(crossOrigin.status()).toBe(403);
  const runId = await queue(request, 'run', 'OS-Q01', 'SELECT 21 * 2 AS answer, CAST(12.34 AS DECIMAL(12,2)) AS precise, NULL AS missing;');
  const real = await completed(request, runId);
  expect(real.status, JSON.stringify(real)).toBe('completed');
  expect(real.result.result_sets[0].rows[0]).toEqual([42, '12.34', null]);
  record.real_run = real;

  const other = await playwright.request.newContext({ baseURL });
  expect((await other.post('/api/session', { headers })).status()).toBe(200);
  expect((await other.get(`/api/jobs/${runId}`)).status()).toBe(404);
  const otherDatabase = await completed(other, await queue(other, 'run', 'OS-Q01', 'SELECT DATABASE() AS db;'));
  expect(otherDatabase.status, JSON.stringify(otherDatabase)).toBe('completed');
  const databaseName = otherDatabase.result.result_sets[0].rows[0][0];
  expect(databaseName).toMatch(/^[A-Za-z0-9_]+$/);
  const crossWorkspace = await completed(request, await queue(request, 'run', 'OS-Q01', `SELECT * FROM \`${databaseName}\`.customers;`));
  expect(crossWorkspace.status).toBe('failed');
  record.cross_workspace_denial = crossWorkspace;
  await other.dispose();

  const incorrect = await completed(request, await queue(request, 'submit', 'OS-Q01', 'SELECT 1 AS customer_id;'));
  expect(incorrect.status, JSON.stringify(incorrect)).toBe('completed');
  expect(incorrect.result.grading.passed).toBe(false);
  record.incorrect_submission = incorrect;

  for (const challenge of ready) {
    const solution = await (await request.get(`/api/challenges/${challenge.id}/solution`)).json();
    expect(solution.sql).toBeTruthy();
    const result = await completed(request, await queue(request, 'submit', challenge.id, solution.sql));
    record[challenge.id] = result;
    expect(result.status, JSON.stringify(result)).toBe('completed');
    expect(result.result.grading.passed, JSON.stringify(result)).toBe(true);
  }

  const marker = await completed(request, await queue(request, 'run', 'OS-Q01', "UPDATE customers SET customer_name = 'QA practice marker' WHERE customer_id = 1; SELECT customer_name FROM customers WHERE customer_id = 1;"));
  expect(marker.status, JSON.stringify(marker)).toBe('completed');
  const solution = await (await request.get('/api/challenges/OS-Q01/solution')).json();
  expect((await completed(request, await queue(request, 'submit', 'OS-Q01', solution.sql))).result.grading.passed).toBe(true);
  const preserved = await completed(request, await queue(request, 'run', 'OS-Q01', 'SELECT customer_name FROM customers WHERE customer_id = 1;'));
  expect(preserved.result.result_sets[0].rows).toEqual([['QA practice marker']]);

  const forbidden = await request.post('/api/run', { headers, data: { challenge_id: 'OS-Q01', sql: 'SELECT User FROM mysql.user;' } });
  expect([400, 422]).toContain(forbidden.status());
  record.policy_denial = await forbidden.json();

  const syntax = await completed(request, await queue(request, 'run', 'OS-Q01', 'SELEKT broken;'));
  expect(syntax.status).toBe('failed');
  expect(syntax.error.code.toUpperCase()).toBe('SQL_ERROR');
  record.syntax_error = syntax;

  const bounded = await completed(request, await queue(request, 'run', 'OS-Q01', 'WITH RECURSIVE n AS (SELECT 1 AS value UNION ALL SELECT value+1 FROM n WHERE value<600) SELECT value FROM n;'));
  expect(bounded.status, JSON.stringify(bounded)).toBe('completed');
  expect(bounded.result.result_sets[0].rows).toHaveLength(500);
  expect(bounded.result.result_sets[0].truncated).toBe(true);
  record.result_limit = { rows: bounded.result.result_sets[0].rows.length, truncated: bounded.result.result_sets[0].truncated };

  const reset = await request.post('/api/reset', { data: { challenge_id: 'OS-Q01' }, headers });
  expect(reset.status(), await reset.text()).toBe(200);
  const cleared = await completed(request, await queue(request, 'run', 'OS-Q01', 'SELECT customer_name FROM customers WHERE customer_id = 1;'));
  expect(cleared.status).toBe('completed');
  expect(cleared.result.result_sets[0].rows).not.toEqual([['QA practice marker']]);
  record.reset_restores_practice_data = cleared;
  await testInfo.attach('api-outcomes', { body: JSON.stringify(record, null, 2), contentType: 'application/json' });
});

test('database execution cancellation is confirmed, with busy protection', async ({ request }, testInfo) => {
  await request.post('/api/session', { headers });
  const sql = 'DELIMITER $$\nCREATE PROCEDURE qa_wait() SQL SECURITY INVOKER BEGIN DECLARE n BIGINT DEFAULT 0; WHILE n >= 0 DO SET n = n + 1; END WHILE; END$$\nDELIMITER ;\nCALL qa_wait();';
  const id = await queue(request, 'run', 'OS-Q01', sql);
  await expect.poll(async () => (await (await request.get(`/api/jobs/${id}`)).json()).status, { intervals: [100, 200] }).toBe('running');
  const busy = await request.post('/api/run', { data: { challenge_id: 'OS-Q01', sql: 'SELECT 1;' }, headers });
  expect(busy.status()).toBe(409);
  const cancelled = await request.post(`/api/jobs/${id}/cancel`, { headers });
  expect(cancelled.status(), await cancelled.text()).toBe(200);
  const terminal = await completed(request, id);
  expect(terminal.status, JSON.stringify(terminal)).toBe('cancelled');
  const next = await completed(request, await queue(request, 'run', 'OS-Q01', 'SELECT 123 AS after_cancel;'));
  expect(next.status).toBe('completed');
  expect(next.result.result_sets[0].rows).toEqual([[123]]);
  const reset = await request.post('/api/reset', { data: { challenge_id: 'OS-Q01' }, headers });
  expect(reset.status()).toBe(200);
  const routineRemoved = await completed(request, await queue(request, 'run', 'OS-Q01', 'CALL qa_wait();'));
  expect(routineRemoved.status).toBe('failed');
  await testInfo.attach('cancel-and-recovery', { body: JSON.stringify({ terminal, next }, null, 2), contentType: 'application/json' });
});
