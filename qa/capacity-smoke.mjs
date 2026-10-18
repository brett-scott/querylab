// Bounded local smoke only: run after the operator clears existing sessions.
// Uses no npm dependencies. Never prints cookies, submitted SQL or result rows.
import { performance } from 'node:perf_hooks';
import { writeFile } from 'node:fs/promises';

const base = new URL(process.env.QUERYLAB_URL || 'http://127.0.0.1:8080');
if (!['127.0.0.1', 'localhost', '[::1]'].includes(base.hostname)) {
  throw new Error('This smoke is restricted to a local target.');
}
const reportPath = new URL('../docs/capacity-smoke.md', import.meta.url);
const clients = Array.from({ length: 11 }, () => ({ cookie: '' }));
const round = value => Math.round(value * 10) / 10;
const percentile = (values, p) => [...values].sort((a, b) => a - b)[Math.ceil(values.length * p) - 1];
const sleep = milliseconds => new Promise(resolve => setTimeout(resolve, milliseconds));
function assert(condition, message) { if (!condition) throw new Error(message); }

async function request(client, path, body) {
  const response = await fetch(new URL(path, base), {
    method: body === undefined ? 'GET' : 'POST',
    headers: {
      Origin: base.origin,
      ...(client.cookie ? { Cookie: client.cookie } : {}),
      ...(body !== undefined ? { 'Content-Type': 'application/json' } : {}),
    },
    body: body === undefined ? undefined : JSON.stringify(body),
    signal: AbortSignal.timeout(15000),
  });
  // Preserve the server's opaque value exactly; do not decode/re-encode it.
  const cookie = response.headers.get('set-cookie')?.match(/(?:^|,\s*)(querylab_session=[^;]+)/)?.[1];
  if (cookie) client.cookie = cookie;
  const data = await response.json();
  return { status: response.status, data };
}

async function perform(client, work) {
  const started = performance.now();
  const queued = await request(client, `/api/${work.mode}`, { challenge_id: work.id, sql: work.sql });
  assert(queued.status === 202, `${work.id} ${work.mode}: HTTP ${queued.status}, ${queued.data.error?.code || 'no error code'}`);
  const deadline = started + 90000;
  let polls = 0;
  while (performance.now() < deadline) {
    const response = await request(client, `/api/jobs/${queued.data.job_id}`);
    polls++;
    assert(response.status === 200, `Job polling: HTTP ${response.status}`);
    const job = response.data;
    if (['completed', 'failed', 'cancelled'].includes(job.status)) {
      assert(job.status === 'completed', `${work.id} ${work.mode}: ${job.status}, ${job.error?.code || 'no error code'}`);
      if (work.mode === 'submit') assert(job.result?.grading?.passed === true, `${work.id}: reference grading did not pass`);
      if (work.mode === 'run') {
        assert(job.result?.result_sets?.[0]?.columns?.includes('order_count'), 'Exploratory query returned unexpected columns');
        assert(job.result.result_sets[0].rows.length === 8, 'Exploratory query returned unexpected fixture row count');
      }
      return { challenge: work.id, mode: work.mode, terminal: job.status,
        grading_passed: job.result?.grading?.passed ?? null,
        wall_ms: round(performance.now() - started), execution_ms: job.result?.elapsed_ms ?? null, polls };
    }
    await sleep(100);
  }
  // Do not leave a timed-out workload running if the polling deadline is reached.
  await request(client, `/api/jobs/${queued.data.job_id}/cancel`, {});
  throw new Error(`${work.id}: smoke polling deadline exceeded; cancellation requested`);
}

const startedAt = new Date().toISOString();
const summary = { started_at_utc: startedAt, target: base.origin, scope: 'One local burst, 10 short fixture jobs; no public capacity certification' };
try {
  const health = await request(clients[0], '/api/health');
  assert(health.status === 200 && health.data.database === 'mysql', 'Healthy real MySQL API required');
  summary.api = health.data;
  const submissions = [];
  for (const id of ['OS-Q01', 'OS-F01', 'OS-P01']) {
    const solution = await request(clients[0], `/api/challenges/${id}/solution`);
    assert(solution.status === 200 && typeof solution.data.sql === 'string', `${id}: explained solution missing`);
    submissions.push({ id, mode: 'submit', sql: solution.data.sql });
  }
  const sessionTimes = [];
  for (const client of clients.slice(0, 10)) {
    const start = performance.now();
    const session = await request(client, '/api/session', {});
    assert(session.status === 200 && session.data.created === true && client.cookie, 'Expected ten fresh sessions. Restart the API before running this smoke.');
    sessionTimes.push(round(performance.now() - start));
    summary.session_ttl_seconds = session.data.ttl_seconds;
  }
  const rejected = await request(clients[10], '/api/session', {});
  assert(rejected.status === 429 && rejected.data.error?.code === 'capacity_reached', 'Eleventh session must receive capacity_reached/429');
  summary.eleventh_session = { status: rejected.status, code: rejected.data.error.code };
  summary.session_creation_ms = { p50: percentile(sessionTimes, .5), p95: percentile(sessionTimes, .95) };
  const exploratory = {
    id: 'OS-Q01', mode: 'run',
    sql: 'SELECT c.customer_id, COUNT(o.order_id) AS order_count FROM customers c LEFT JOIN orders o ON o.customer_id=c.customer_id GROUP BY c.customer_id ORDER BY c.customer_id;',
  };
  const workload = [...submissions, ...Array.from({ length: 7 }, () => exploratory)];
  const batchStarted = performance.now();
  const outcomes = await Promise.allSettled(workload.map((work, index) => perform(clients[index], work)));
  summary.batch_wall_ms = round(performance.now() - batchStarted);
  summary.completed_jobs = outcomes.filter(outcome => outcome.status === 'fulfilled').map(outcome => outcome.value);
  summary.errors = outcomes.filter(outcome => outcome.status === 'rejected').map(outcome => outcome.reason.message);
  const walls = summary.completed_jobs.map(job => job.wall_ms);
  summary.job_wall_ms = walls.length ? { p50: percentile(walls, .5), p95: percentile(walls, .95) } : null;
  summary.passed = summary.errors.length === 0 && summary.completed_jobs.length === 10;
} catch (error) {
  summary.passed = false;
  summary.errors = [...(summary.errors || []), error.message];
}

const rows = (summary.completed_jobs || []).map((job, index) => `| ${index + 1} | ${job.challenge} | ${job.mode} | ${job.wall_ms} | ${job.execution_ms ?? 'Unavailable'} | ${job.grading_passed ?? 'N/A'} |`).join('\n');
await writeFile(reportPath, `# QueryLab bounded local capacity smoke

Observed at ${startedAt} against ${base.origin}. Result: **${summary.passed ? 'PASS' : 'FAIL'}**.

This is one burst of ten short jobs on synthetic teaching fixtures: seven exploratory join/aggregate queries and the three available reference submissions. Reference solutions are deliberately fetched from the explicit explained-solution endpoint. There are ten independent opaque cookie contexts, one job per visitor. No cookies, SQL scripts or result rows are recorded here.

## Results

- Fresh sessions: ${summary.session_creation_ms ? '10' : 'Not completed'}; eleventh-session response: ${summary.eleventh_session?.status ?? 'Not measured'} (${summary.eleventh_session?.code ?? 'N/A'}).
- Session creation p50 / p95: ${summary.session_creation_ms?.p50 ?? 'N/A'} / ${summary.session_creation_ms?.p95 ?? 'N/A'} ms.
- Successful jobs: ${summary.completed_jobs?.length ?? 0}/10; errors: ${summary.errors?.length ?? 0}.
- Job wall-clock p50 / p95: ${summary.job_wall_ms?.p50 ?? 'N/A'} / ${summary.job_wall_ms?.p95 ?? 'N/A'} ms.
- Burst wall-clock duration: ${summary.batch_wall_ms ?? 'N/A'} ms.
- Idle session expiry returned by API: ${summary.session_ttl_seconds ?? 'N/A'} seconds.

| Visitor | Challenge | Operation | Wall time including queue + polling (ms) | Server execution time (ms) | Grade passed |
| --- | --- | --- | ---: | ---: | --- |
${rows}

${summary.errors?.length ? `Errors: ${summary.errors.join('; ')}.\n` : ''}
## Interpretation and limits

The local implementation defaults to ten sessions, four execution workers and an eight-second SQL deadline. The smoke records observed completion and admission behaviour; it does not measure sustained throughput, resource headroom, destructive/adversarial workloads, network latency, browser rendering or production costs. The p95 is the nearest-rank estimate from only ten heterogeneous job samples, with 100 ms polling resolution. It has no statistical confidence claim and is not a public-hosting SLA or proof that the A$150/month budget is sufficient. Server execution times include engine workspace/grader work but are distinct from client-visible queue and polling time.

Run after a clean API restart with no competing tests:

    node qa/capacity-smoke.mjs

The script does not restart services or delete workspaces. The operator must clear its ten sessions afterward before opening the preview to learners. A second run without cleanup is expected to fail on occupied capacity. The local-host check prevents inadvertently using this script against a public deployment.
`, 'utf8');
console.log(JSON.stringify(summary, null, 2));
if (!summary.passed) process.exitCode = 1;
