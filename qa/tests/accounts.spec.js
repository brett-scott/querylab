import { test, expect } from '@playwright/test';
import { mkdir, readFile } from 'node:fs/promises';

const auth = 'https://querylab-auth.test';
const firstId = '11111111-1111-4111-8111-111111111111';
const secondId = '22222222-2222-4222-8222-222222222222';
function session(id = firstId) {
  const expires = Math.floor(Date.now() / 1000) + 3600;
  const payload = Buffer.from(JSON.stringify({ sub: id, role: 'authenticated', aud: 'authenticated', exp: expires })).toString('base64url');
  return { access_token: `eyJhbGciOiJIUzI1NiJ9.${payload}.test-signature`, refresh_token: `test-refresh-${id}`, expires_in: 3600, expires_at: expires, token_type: 'bearer', user: { id, aud: 'authenticated', role: 'authenticated', email: id === firstId ? 'learner@example.test' : 'second@example.test', app_metadata: { provider: 'google' }, user_metadata: {}, created_at: new Date().toISOString() } };
}

// OAuth and hosted REST are controlled test doubles. SQL grading below uses the
// real local helper. Separate PostgreSQL checks exercise actual RLS policies.
async function cloudRoutes(page) {
  const cloud = { attempts: [], failWrites: false, writes: [], exchanges: [], authorization: null };
  await page.route(`${auth}/**`, async route => {
    const request = route.request();
    const url = new URL(request.url());
    const json = body => route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(body) });
    if (url.pathname === '/auth/v1/authorize') {
      cloud.authorization = Object.fromEntries(url.searchParams);
      const callback = new URL(url.searchParams.get('redirect_to'));
      callback.searchParams.set('code', 'test-authorization-code');
      return route.fulfill({ contentType: 'text/html', body: `<a href="${callback.href}">Complete test sign-in</a>` });
    }
    if (url.pathname === '/auth/v1/token') { cloud.exchanges.push(request.postDataJSON()); return json(session()); }
    if (url.pathname === '/auth/v1/logout') return route.fulfill({ status: 204 });
    if (url.pathname === '/auth/v1/user') return json(session().user);
    const token = request.headers().authorization?.replace('Bearer ', '');
    const owner = [firstId, secondId].find(id => token === session(id).access_token);
    // Expiry seconds can roll over between calls; identify the stable subject.
    const subject = token?.split('.')[1];
    let uid = owner;
    try { uid ??= JSON.parse(Buffer.from(subject, 'base64url').toString()).sub; } catch { /* No session. */ }
    if (!uid) return route.fulfill({ status: 401, contentType: 'application/json', body: '{"message":"No session"}' });
    if (url.pathname === '/rest/v1/challenge_attempts' && request.method() === 'POST') {
      const attempt = request.postDataJSON();
      cloud.writes.push(attempt);
      if (cloud.failWrites) return route.fulfill({ status: 503, contentType: 'application/json', body: '{"message":"Temporary test outage"}' });
      if (attempt.user_id !== uid) return route.fulfill({ status: 403, contentType: 'application/json', body: '{"message":"Wrong owner"}' });
      if (!cloud.attempts.some(row => row.id === attempt.id)) cloud.attempts.push(attempt);
      return route.fulfill({ status: 201 });
    }
    const own = cloud.attempts.filter(row => row.user_id === uid);
    if (url.pathname === '/rest/v1/challenge_attempts') return json(own.toSorted((a, b) => b.completed_at.localeCompare(a.completed_at)).slice(0, 20));
    if (url.pathname === '/rest/v1/challenge_progress') {
      const groups = new Map();
      for (const item of own) {
        const key = `${item.challenge_id}:${item.challenge_version}`;
        const row = groups.get(key) ?? { user_id: uid, challenge_id: item.challenge_id, challenge_version: item.challenge_version, challenge_title: item.challenge_title, challenge_type: item.challenge_type, attempt_count: 0, passed_count: 0, unassisted_pass_count: 0, last_attempt_at: item.completed_at };
        row.attempt_count++; row.passed_count += Number(item.passed); row.unassisted_pass_count += Number(item.passed && !item.hints_used && !item.solution_viewed);
        groups.set(key, row);
      }
      return json([...groups.values()]);
    }
    return route.fulfill({ status: 404, body: 'Unexpected test request' });
  });
  return cloud;
}

test('Google PKCE callback returns to the repository path and restores the selected challenge', async ({ page, baseURL }) => {
  const cloud = await cloudRoutes(page);
  await page.goto('./?error=access_denied&error_description=Consent%20cancelled');
  await page.getByRole('button', { name: 'Sign in', exact: true }).click();
  await expect(page.getByRole('alert')).toContainText('Google sign-in could not be completed');
  expect(new URL(page.url()).searchParams.has('error')).toBe(false);
  await page.getByRole('button', { name: 'Close dialog', exact: true }).click();
  await page.goto('./?challenge=BI-P02');
  await page.getByRole('button', { name: 'Sign in', exact: true }).click();
  await expect(page.getByText(/Signing in is optional/)).toBeVisible();
  await page.getByRole('button', { name: 'Continue with Google', exact: true }).click();
  await page.getByRole('link', { name: 'Complete test sign-in' }).click();
  await expect(page.getByRole('button', { name: 'Progress', exact: true })).toBeVisible();
  expect(cloud.authorization.provider).toBe('google');
  expect(cloud.authorization.code_challenge_method).toBe('s256');
  expect(cloud.authorization.code_challenge.length).toBeGreaterThan(30);
  expect(cloud.authorization.redirect_to).toBe(baseURL);
  expect(cloud.exchanges).toHaveLength(1);
  expect(cloud.exchanges[0].auth_code).toBe('test-authorization-code');
  expect(cloud.exchanges[0].code_verifier.length).toBeGreaterThan(30);
  expect(new URL(page.url()).pathname).toBe(new URL(baseURL).pathname);
  expect(new URL(page.url()).searchParams.get('challenge')).toBe('BI-P02');
  expect(new URL(page.url()).searchParams.has('code')).toBe(false);
  await page.getByRole('button', { name: 'Progress', exact: true }).click();
  await expect(page.getByText('learner@example.test', { exact: true })).toBeVisible();
  await expect(page.locator('.progress-stats>div').nth(1).locator('strong')).toHaveText('0');
});

test('real helper grades sync metadata once, preserve assistance, and keep account records separate', async ({ page, baseURL }) => {
  test.skip(process.env.QUERYLAB_ACCOUNTS_WITH_HELPER !== '1', 'Requires the private development helper.');
  const api = process.env.QUERYLAB_HELPER_API_URL || 'http://127.0.0.1:8765';
  const authKey = `querylab:account:${new URL(baseURL).pathname}`;
  const cloud = await cloudRoutes(page);
  const errors = [];
  page.on('pageerror', error => errors.push(error.message));
  await page.addInitScript(({ authKey, session }) => {
    if (!localStorage.getItem('querylab:qa:seeded')) {
      localStorage.setItem(authKey, JSON.stringify(session)); localStorage.setItem('querylab:qa:seeded', '1');
    }
  }, { authKey, session: session() });
  await page.goto('./?challenge=OS-Q01');
  const configuration = await readFile(process.env.QUERYLAB_ACCOUNTS_HELPER_ENV || new URL('../../.env.helper', import.meta.url), 'utf8');
  const pairingCode = configuration.match(/^QUERYLAB_PAIRING_TOKEN=(.+)$/m)?.[1].trim().replace(/^(['"])(.*)\1$/, '$2');
  if (!pairingCode) throw new Error('Configure the development helper first.');
  await page.getByLabel('Helper URL', { exact: true }).fill(api);
  try {
    await page.getByLabel('Pairing code', { exact: true }).fill(pairingCode);
    await page.getByRole('button', { name: 'Pair helper', exact: true }).click();
    await expect(page.locator('.workbench')).toBeVisible();
  } finally {
    const code = page.getByLabel('Pairing code', { exact: true });
    if (await code.count()) await code.fill('');
  }
  const editor = page.getByRole('textbox', { name: 'SQL editor' });
  await editor.fill('SELECT 42 AS answer;');
  await page.locator('#run-sql').click();
  await expect(page.getByRole('cell', { name: '42', exact: true })).toBeVisible();
  expect(cloud.writes).toHaveLength(0);
  cloud.failWrites = true;
  await page.getByRole('button', { name: 'Submit', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'A few things to revisit.' })).toBeVisible();
  await expect.poll(() => cloud.writes.length).toBe(1);
  await page.reload();
  await expect(editor).toHaveText('SELECT 42 AS answer;', { useInnerText: true });
  await expect.poll(() => cloud.writes.length).toBe(2);
  await page.getByRole('button', { name: 'Progress', exact: true }).click();
  await expect(page.getByText('1 result waiting to sync', { exact: true })).toBeVisible();
  cloud.failWrites = false;
  await page.getByRole('button', { name: 'Retry sync', exact: true }).click();
  await expect(page.locator('.progress-stats>div').nth(1).locator('strong')).toHaveText('1');
  expect(cloud.attempts).toHaveLength(1);
  expect(cloud.attempts[0].passed).toBe(false);
  expect(cloud.writes[0].id).toBe(cloud.writes[1].id);
  expect(cloud.writes[0].id).toBe(cloud.writes[2].id);
  expect(Object.keys(cloud.attempts[0]).sort()).toEqual(['id','user_id','challenge_id','challenge_version','challenge_title','challenge_type','dataset','passed','hints_used','solution_viewed','completed_at'].sort());
  expect(JSON.stringify(cloud.writes)).not.toContain('SELECT 42');
  expect(JSON.stringify(cloud.writes)).not.toContain(pairingCode);
  await page.getByRole('button', { name: 'Close dialog', exact: true }).click();
  await page.getByRole('button', { name: 'Get a hint', exact: true }).click();
  await page.locator('.more-help>summary').click();
  await page.getByRole('button', { name: 'View explained solution', exact: true }).click();
  await page.getByRole('button', { name: 'Reveal solution', exact: true }).click();
  await expect(page.locator('.solution-code')).toBeVisible();
  await page.getByRole('button', { name: 'Close dialog', exact: true }).click();
  const reference = await page.evaluate(async api => {
    const response = await fetch(`${api}/api/challenges/OS-Q01/solution`, { headers: { Authorization: `Bearer ${sessionStorage.getItem('querylab:helper:token')}` } });
    return response.json();
  }, api);
  await editor.fill(reference.sql);
  await page.reload();
  await expect(editor).toHaveText(reference.sql, { useInnerText: true });
  // Let real grading finish while the first poll is held, then refresh. The
  // saved submission ID must recover the grade and count it exactly once.
  let heldPoll = false;
  let holdPoll = true;
  await page.route(`${api}/api/jobs/*`, async route => {
    if (!holdPoll) { await route.continue(); return; }
    heldPoll = true;
    await new Promise(resolve => setTimeout(resolve, 500));
    await route.continue().catch(() => {});
  });
  await page.getByRole('button', { name: 'Submit', exact: true }).click();
  await expect.poll(() => heldPoll).toBe(true);
  holdPoll = false;
  await page.reload();
  await expect(page.getByRole('heading', { name: 'Your answer passes all checks.' })).toBeVisible();
  await expect(page.locator('#run-sql')).toBeEnabled();
  await expect.poll(() => cloud.attempts.length).toBe(2);
  expect(cloud.attempts[1].hints_used).toBe(1);
  expect(cloud.attempts[1].solution_viewed).toBe(true);
  await page.getByRole('button', { name: 'Progress', exact: true }).click();
  await expect(page.locator('.progress-stats>div').nth(0).locator('strong')).toHaveText('1');
  await expect(page.locator('.progress-stats>div').nth(1).locator('strong')).toHaveText('2');
  await expect(page.locator('.progress-stats>div').nth(2).locator('strong')).toHaveText('50%');
  await expect(page.locator('.progress-stats>div').nth(3).locator('strong')).toHaveText('0');
  await mkdir(new URL('../screenshots/accounts/', import.meta.url), { recursive: true });
  await page.screenshot({ path: new URL('../screenshots/accounts/progress-desktop.png', import.meta.url).pathname.replace(/^\/([A-Za-z]:)/, '$1') });
  await page.setViewportSize({ width: 375, height: 800 });
  await expect(page.getByRole('button', { name: 'Sign out', exact: true })).toBeInViewport();
  expect(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth)).toBe(false);
  await page.screenshot({ path: new URL('../screenshots/accounts/progress-mobile.png', import.meta.url).pathname.replace(/^\/([A-Za-z]:)/, '$1') });
  await page.getByRole('button', { name: 'Sign out', exact: true }).click();
  await expect(page.getByRole('button', { name: 'Continue with Google', exact: true })).toBeVisible();
  await page.getByRole('button', { name: 'Close dialog', exact: true }).click();
  await expect(page.getByRole('button', { name: 'Connection', exact: true })).toContainText('Connected');
  await page.evaluate(({ authKey, next }) => localStorage.setItem(authKey, JSON.stringify(next)), { authKey, next: session(secondId) });
  await page.reload();
  await page.getByRole('button', { name: 'Progress', exact: true }).click();
  await expect(page.getByText('second@example.test', { exact: true })).toBeVisible();
  await expect(page.locator('.progress-stats>div').nth(1).locator('strong')).toHaveText('0');
  expect(cloud.attempts.every(item => item.user_id === firstId)).toBe(true);
  expect(errors).toEqual([]);
});
