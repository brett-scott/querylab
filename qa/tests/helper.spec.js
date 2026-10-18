import { test, expect } from '@playwright/test';
import { mkdir, readFile } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import { createHash } from 'node:crypto';

const api = process.env.QUERYLAB_HELPER_API_URL || 'http://127.0.0.1:8765';
const site = process.env.QUERYLAB_HELPER_SITE_URL || 'http://127.0.0.1:8081';
const evidence = fileURLToPath(new URL('../screenshots/helper/', import.meta.url));
const tokenKey = 'querylab:helper:token';
function expectPublicSetup(sql) {
  const statements = sql.replace(/^\s*--.*$/gm, '');
  expect(statements).toMatch(/CREATE TABLE/i);
  expect(statements).toMatch(/INSERT INTO/i);
  expect(statements).not.toMatch(/\bDROP\s|\bCREATE\s+USER\b|\bGRANT\s/i);
  expect(sql).not.toMatch(/hidden|variant/i);
}
async function privateConfiguration() {
  const content = await readFile(new URL('../../.env.helper', import.meta.url), 'utf8');
  const result = Object.fromEntries(content.split(/\r?\n/).filter(line => /^[A-Z_][A-Z0-9_]*=/.test(line)).map(line => {
    const split = line.indexOf('=');
    return [line.slice(0, split), line.slice(split + 1).replace(/^(['"])(.*)\1$/, '$2')];
  }));
  if (!result.QUERYLAB_PAIRING_TOKEN) throw new Error('Local helper pairing configuration is missing; run the documented setup first.');
  return result;
}
async function capture(page, filename) {
  await mkdir(evidence, { recursive: true });
  await page.screenshot({ path: `${evidence}/${filename}.png`, fullPage: true, mask: [page.locator('#helper-code')] });
}
async function pair(page) {
  const config = await privateConfiguration();
  await page.getByLabel('Helper URL', { exact: true }).fill(api);
  await page.getByLabel('Pairing code', { exact: true }).fill(config.QUERYLAB_PAIRING_TOKEN);
  await page.locator('.helper-form').getByRole('button', { name: 'Pair helper', exact: true }).click();
  try {
    await expect(page.locator('.workbench')).toBeVisible();
    await expect(page.getByRole('dialog')).toHaveCount(0);
    await expect(page.getByRole('textbox', { name: 'SQL editor' })).toBeVisible();
  } finally {
    // Error-context snapshots can include input values even with traces off.
    const code = page.getByLabel('Pairing code', { exact: true });
    if (await code.count()) await code.fill('');
  }
}
async function edit(page, sql) {
  await page.getByRole('textbox', { name: 'SQL editor' }).fill(sql);
  await expect.poll(() => page.evaluate(value => Object.values(localStorage).includes(value), sql)).toBe(true);
}

test('helper API enforces exact origin, bearer pairing and preflight without browser cookies', async ({ request }, testInfo) => {
  const config = await privateConfiguration();
  const home = await request.get(`${api}/`);
  expect(home.status()).toBe(200);
  expect(home.headers()['content-type']).toContain('text/html');
  const homeText = await home.text();
  expect(homeText).toContain('Your QueryLab helper is running.');
  expect(homeText).toContain('Helper URL');
  expect(homeText).not.toContain(config.QUERYLAB_PAIRING_TOKEN);
  const status = await request.get(`${api}/api/helper/status`, { headers: { Origin: site } });
  expect(status.status()).toBe(200);
  expect(status.headers()['access-control-allow-origin']).toBe(site);
  const readiness = await status.json();
  expect(readiness.mode).toBe('helper');
  expect(readiness.database.connected).toBe(true);
  expect(JSON.stringify(readiness).includes(config.QUERYLAB_PAIRING_TOKEN)).toBe(false);
  expect(JSON.stringify(readiness).includes(config.MYSQL_ADMIN_PASSWORD || config.MYSQL_ROOT_PASSWORD || 'not-a-configured-password')).toBe(false);

  const deniedGet = await request.get(`${api}/api/helper/status`, { headers: { Origin: 'https://unrelated.example' } });
  const deniedPost = await request.post(`${api}/api/helper/pair`, { headers: { Origin: 'https://unrelated.example' }, data: { pairing_code: 'invalid' } });
  for (const response of [deniedGet, deniedPost]) {
    expect(response.status()).toBe(403);
    expect(response.headers()['access-control-allow-origin']).toBeUndefined();
  }
  const unauthenticated = await request.get(`${api}/api/challenges`, { headers: { Origin: site } });
  expect(unauthenticated.status()).toBe(401);
  const wrongCode = await request.post(`${api}/api/helper/pair`, { headers: { Origin: site }, data: { pairing_code: 'intentionally-incorrect-pairing-code' } });
  expect(wrongCode.status()).toBe(401);

  const preflight = await request.fetch(`${api}/api/run`, { method: 'OPTIONS', headers: {
    Origin: site, 'Access-Control-Request-Method': 'POST', 'Access-Control-Request-Headers': 'authorization,content-type',
  } });
  expect([200, 204]).toContain(preflight.status());
  expect(preflight.headers()['access-control-allow-origin']).toBe(site);
  expect(preflight.headers()['access-control-allow-headers'].toLowerCase()).toContain('authorization');
  const deniedPreflight = await request.fetch(`${api}/api/run`, { method: 'OPTIONS', headers: {
    Origin: 'https://unrelated.example', 'Access-Control-Request-Method': 'POST', 'Access-Control-Request-Headers': 'authorization',
  } });
  expect(deniedPreflight.status()).toBe(403);

  const pairing = await request.post(`${api}/api/helper/pair`, { headers: { Origin: site }, data: { pairing_code: config.QUERYLAB_PAIRING_TOKEN } });
  expect(pairing.status()).toBe(200);
  expect(pairing.headers()['set-cookie']).toBeUndefined();
  const { token } = await pairing.json();
  expect(typeof token).toBe('string');
  const protectedHeaders = { Origin: site, Authorization: `Bearer ${token}` };
  const catalogResponse = await request.get(`${api}/api/challenges`, { headers: protectedHeaders });
  expect(catalogResponse.status()).toBe(200);
  const catalog = await catalogResponse.json();
  expect(catalog.challenges).toHaveLength(12);
  expect(catalog.challenges.every(challenge => challenge.ready)).toBe(true);
  const grading = {};
  for (const challenge of catalog.challenges) {
    const solutionResponse = await request.get(`${api}/api/challenges/${challenge.id}/solution`, { headers: protectedHeaders });
    expect(solutionResponse.status()).toBe(200);
    const { sql } = await solutionResponse.json();
    const queued = await request.post(`${api}/api/submit`, { headers: protectedHeaders, data: { challenge_id: challenge.id, sql } });
    expect(queued.status()).toBe(202);
    const { job_id } = await queued.json();
    let result;
    await expect.poll(async () => {
      const response = await request.get(`${api}/api/jobs/${job_id}`, { headers: protectedHeaders });
      expect(response.status()).toBe(200);
      result = await response.json();
      return result.status;
    }, { timeout: 15000, intervals: [100, 250] }).toBe('completed');
    expect(result.result.grading.passed, JSON.stringify(result)).toBe(true);
    grading[challenge.id] = { passed: result.result.grading.passed, checks: result.result.grading.checks.length, elapsed_ms: result.result.elapsed_ms };
  }
  await testInfo.attach('all-twelve-helper-graders', { body: JSON.stringify(grading, null, 2), contentType: 'application/json' });
  const renewed = await request.post(`${api}/api/session`, { headers: protectedHeaders, data: {} });
  expect(renewed.status()).toBe(200);
  expect(renewed.headers()['set-cookie']).toBeUndefined();
  expect((await renewed.json()).created).toBe(false);
  for (const dataset of ['online-store', 'inventory']) {
    const download = await request.get(`${api}/api/datasets/${dataset}/setup.sql`, { headers: protectedHeaders });
    expect(download.status()).toBe(200);
    expect(download.headers()['content-type']).toContain('application/sql');
    const sql = await download.text();
    expectPublicSetup(sql);
  }
  expect((await request.get(`${api}/api/challenges`, { headers: { Origin: site, Authorization: 'Bearer invalid-token' } })).status()).toBe(401);
  await testInfo.attach('helper-api-outcomes', { body: JSON.stringify({
    readiness, wrongOriginGet: deniedGet.status(), wrongOriginPost: deniedPost.status(), unauthenticated: unauthenticated.status(),
    wrongPairingCode: wrongCode.status(), allowedPreflight: preflight.status(), deniedPreflight: deniedPreflight.status(),
    pairing: pairing.status(), bearerSession: renewed.status(), cookiesIssued: false,
  }, null, 2), contentType: 'application/json' });
});

test('cross-origin browser pairs, executes real SQL, grades, downloads datasets and retains drafts after refresh/disconnect', async ({ page }, testInfo) => {
  const consoleErrors = [];
  page.on('pageerror', error => consoleErrors.push(error.message));
  await page.goto('/');
  await expect(page.getByLabel('Pairing code', { exact: true })).toHaveAttribute('type', 'password');
  await capture(page, 'connection-desktop');
  await page.getByLabel('Helper URL', { exact: true }).fill(api);
  await page.getByRole('button', { name: 'Check connection', exact: true }).click();
  await expect(page.getByText(/MySQL connected/)).toBeVisible();
  await page.getByLabel('Pairing code', { exact: true }).fill('intentionally-incorrect-pairing-code');
  await page.getByRole('button', { name: 'Pair helper', exact: true }).click();
  await expect(page.locator('.helper-content').getByRole('alert')).toBeVisible();
  await capture(page, 'pairing-rejected');
  await pair(page);

  const config = await privateConfiguration();
  const storage = await page.evaluate(tokenKey => {
    const token = sessionStorage.getItem(tokenKey);
    const persisted = Object.values(localStorage);
    return {
      tokenInTab: Boolean(token), tokenInLocalStorage: Boolean(token && persisted.some(value => value.includes(token))),
      persisted,
      passwordInputPresent: Boolean(document.querySelector('input[name="mysql-password"]')),
    };
  }, tokenKey);
  const secrets = [config.QUERYLAB_PAIRING_TOKEN, config.MYSQL_ADMIN_PASSWORD, config.MYSQL_ROOT_PASSWORD].filter(Boolean);
  const privacy = {
    tokenInTab: storage.tokenInTab, tokenInLocalStorage: storage.tokenInLocalStorage,
    secretsInLocalStorage: secrets.some(secret => storage.persisted.some(value => value.includes(secret))),
    passwordInputPresent: storage.passwordInputPresent,
  };
  expect(privacy).toEqual({ tokenInTab: true, tokenInLocalStorage: false, secretsInLocalStorage: false, passwordInputPresent: false });
  const sql = 'SELECT 21 * 2 AS answer;';
  await edit(page, sql);
  await page.locator('#run-sql').click();
  await expect(page.getByRole('cell', { name: '42', exact: true })).toBeVisible();
  await capture(page, 'paired-workbench-real-result');
  await page.reload();
  await expect(page.getByRole('textbox', { name: 'SQL editor' })).toHaveText(sql, { useInnerText: true });
  await expect(page.getByRole('button', { name: 'Connection', exact: true })).toContainText(/Connected/);

  const reference = await page.evaluate(async ({ api, tokenKey }) => {
    const response = await fetch(`${api}/api/challenges/OS-Q01/solution`, { headers: { Authorization: `Bearer ${sessionStorage.getItem(tokenKey)}` } });
    if (!response.ok) throw new Error('Reference solution could not be loaded.');
    return response.json();
  }, { api, tokenKey });
  await edit(page, reference.sql);
  await page.getByRole('button', { name: 'Submit', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'Your answer passes all checks.' })).toBeVisible();
  await capture(page, 'paired-grading-pass');

  const downloadPromise = page.waitForEvent('download');
  await page.getByRole('button', { name: 'Schema', exact: true }).first().click();
  await page.getByRole('button', { name: 'Download dataset SQL', exact: true }).click();
  const download = await downloadPromise;
  expect(download.suggestedFilename()).toBe('querylab-online-store-setup.sql');
  const setupSql = await readFile(await download.path(), 'utf8');
  expect(setupSql).toMatch(/CREATE TABLE customers/i);
  expectPublicSetup(setupSql);

  await edit(page, sql);
  await page.getByRole('button', { name: 'Connection', exact: true }).click();
  await capture(page, 'paired-connection-status');
  await page.getByRole('button', { name: 'Disconnect helper', exact: true }).click();
  expect(await page.evaluate(key => sessionStorage.getItem(key) === null, tokenKey)).toBe(true);
  await expect(page.getByLabel('Pairing code', { exact: true })).toBeVisible();
  await page.keyboard.press('Escape');
  await expect(page.getByRole('textbox', { name: 'SQL editor' })).toHaveText(sql, { useInnerText: true });
  await expect(page.locator('#run-sql')).toBeDisabled();
  await page.getByRole('button', { name: 'Connection', exact: true }).click();
  await pair(page);
  await expect(page.getByRole('textbox', { name: 'SQL editor' })).toHaveText(sql, { useInnerText: true });
  expect(consoleErrors).toEqual([]);
  await testInfo.attach('helper-browser-outcomes', { body: JSON.stringify({
    privacy, crossOrigin: new URL(site).origin !== new URL(api).origin, realRunAnswer: 42, referenceGradingPassed: true,
    refreshedDraftPreserved: true, disconnectDraftPreserved: true, downloadedFile: download.suggestedFilename(),
  }, null, 2), contentType: 'application/json' });
});

test('invalid bearer opens pairing recovery and preserves the browser draft', async ({ page }) => {
  let holdSchema = false;
  let releaseSchema;
  const schemaGate = new Promise(resolve => { releaseSchema = resolve; });
  await page.route(/\/api\/schema\?/, async route => {
    if (!holdSchema) { await route.continue(); return; }
    const response = await route.fetch();
    await schemaGate;
    await route.fulfill({ response });
  });
  await page.goto('/');
  await pair(page);
  await page.getByRole('button', { name: 'Focus', exact: true }).click();
  const sql = 'SELECT 123 AS recovery_draft;';
  await edit(page, sql);
  await page.evaluate(key => sessionStorage.setItem(key, 'intentionally-invalid-session'), tokenKey);
  await page.locator('#run-sql').click();
  await expect(page.getByLabel('Pairing code', { exact: true })).toBeVisible();
  await expect(page.getByRole('dialog', { name: 'Connect your local helper' })).toBeVisible();
  await capture(page, 'invalid-bearer-recovery');
  holdSchema = true;
  await pair(page);
  await expect(page.getByRole('button', { name: 'Exit focus', exact: true })).toBeVisible();
  await expect(page.getByRole('textbox', { name: 'SQL editor' })).toHaveText(sql, { useInnerText: true });
  try {
    await expect(page.getByText(/Preparing your practice data\./)).toBeVisible();
    await expect(page.locator('#run-sql')).toBeDisabled();
    await expect(page.getByRole('button', { name: 'Submit', exact: true })).toBeDisabled();
    await capture(page, 'recovery-preparing-workspace');
  } finally { holdSchema = false; releaseSchema(); }
  await page.locator('#run-sql').click();
  try { await expect(page.getByRole('cell', { name: '123', exact: true })).toBeVisible(); }
  finally { await capture(page, 'recovery-run-outcome'); }
  // A stale tab token at startup must recover through the same pairing form.
  await page.evaluate(key => sessionStorage.setItem(key, 'intentionally-invalid-session'), tokenKey);
  await page.reload();
  await expect(page.getByLabel('Pairing code', { exact: true })).toBeVisible();
  await pair(page);
  await expect(page.getByRole('textbox', { name: 'SQL editor' })).toHaveText(sql, { useInnerText: true });
});

test('connection setup rejects remote helper URLs and explains unreachable localhost on narrow screens', async ({ page }) => {
  await page.setViewportSize({ width: 375, height: 667 });
  await page.goto('/');
  await expect(page.getByLabel('Pairing code', { exact: true })).toBeVisible();
  await expect(page.getByRole('link', { name: 'Download Windows helper', exact: true })).toBeVisible();
  await expect(page.getByRole('link', { name: 'Download Windows helper', exact: true })).toBeInViewport();
  await expect(page.locator('#helper-url-description')).toContainText('Leave this prefilled address unchanged');
  const firstTime = page.locator('.helper-setup').first();
  await expect(firstTime).toHaveAttribute('open', '');
  await expect(firstTime).toContainText('Extract All');
  await expect(firstTime).toContainText('Start-QueryLab-Helper.cmd');
  await expect(firstTime).toContainText('Copy pairing code');
  await expect(page.getByLabel('Website address for the launcher')).toHaveValue(new URL(site).origin);
  await expect(page.getByLabel('Helper URL', { exact: true })).toHaveValue(api);
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
  await capture(page, 'first-time-setup-mobile');
  await page.screenshot({ path: `${evidence}/download-mobile-viewport.png`, fullPage: false, mask: [page.locator('#helper-code')] });
  await firstTime.locator('summary').focus();
  await page.keyboard.press('Enter');
  await expect(firstTime).not.toHaveAttribute('open');
  await firstTime.locator('summary').click();
  const existingHelper = page.locator('.helper-setup').nth(1);
  await existingHelper.locator('summary').click();
  await expect(existingHelper).toContainText('Start-QueryLab-Helper.cmd');
  await expect(existingHelper).toContainText('Copy pairing code');
  await existingHelper.locator('summary').click();
  await firstTime.locator('summary').click();
  await capture(page, 'connection-mobile');
  await page.getByRole('button', { name: 'Check connection', exact: true }).scrollIntoViewIfNeeded();
  await expect(page.getByRole('button', { name: 'Check connection', exact: true })).toBeInViewport();
  await expect(page.getByLabel('Pairing code', { exact: true })).toBeInViewport();
  await capture(page, 'connection-mobile-form');
  let remoteRequests = 0;
  await page.route('https://unrelated.example/**', async route => { remoteRequests++; await route.abort(); });
  await page.getByLabel('Helper URL', { exact: true }).fill('https://unrelated.example');
  await page.getByRole('button', { name: 'Check connection', exact: true }).click();
  await expect(page.locator('.helper-content').getByRole('alert')).toContainText(/HTTP on localhost|local helper URL/i);
  expect(remoteRequests).toBe(0);
  await page.getByLabel('Helper URL', { exact: true }).fill(api);
  await page.route(`${api}/api/helper/status`, route => route.abort('failed'));
  await page.getByRole('button', { name: 'Check connection', exact: true }).click();
  await expect(page.locator('.helper-content').getByRole('alert')).toContainText(/Unable to reach your local helper/i);
  await capture(page, 'connection-unreachable-mobile');
});

test('Windows download delivers a real ZIP matching its manifest and copies the current website address', async ({ page, request, context }, testInfo) => {
  await context.grantPermissions(['clipboard-read', 'clipboard-write'], { origin: new URL(site).origin });
  await page.goto('/');
  const downloadLink = page.getByRole('link', { name: 'Download Windows helper', exact: true });
  await expect(downloadLink).toBeInViewport();
  await expect(downloadLink).toHaveAttribute('href', '/downloads/querylab-helper-windows.zip');
  await capture(page, 'download-ready-desktop');
  const manifestResponse = await request.get(`${site}/downloads/querylab-helper-windows.json`);
  expect(manifestResponse.status()).toBe(200);
  expect(manifestResponse.headers()['content-type']).toContain('application/json');
  const manifest = await manifestResponse.json();
  expect(manifest.platform).toBe('windows');
  expect(manifest.filename).toBe('querylab-helper-windows.zip');
  expect(manifest.requires).toContain('Docker Desktop');
  expect(manifest.sha256).toMatch(/^[a-f\d]{64}$/i);
  expect(manifest.files).toEqual(expect.arrayContaining([
    'QueryLab-Helper/Start-QueryLab-Helper.cmd', 'QueryLab-Helper/scripts/launch-helper.ps1',
    'QueryLab-Helper/compose.helper.yaml', 'QueryLab-Helper/README.txt',
  ]));
  expect(manifest.files.some(path => /(^|\/)(?:\.env(?:\.|$)|\.git(?:\/|$)|node_modules(?:\/|$)|\.querylab(?:\/|$))/.test(path))).toBe(false);
  const archiveResponse = await request.get(`${site}/downloads/${manifest.filename}`);
  expect(archiveResponse.status()).toBe(200);
  expect(archiveResponse.headers()['content-type']).toMatch(/application\/(?:zip|x-zip-compressed|octet-stream)/i);
  const body = await archiveResponse.body();
  expect(body.subarray(0, 4).toString('hex')).toBe('504b0304');
  expect(body.length).toBe(manifest.bytes);
  expect(createHash('sha256').update(body).digest('hex')).toBe(manifest.sha256.toLowerCase());
  const actualDownload = page.waitForEvent('download');
  await downloadLink.click();
  const downloaded = await actualDownload;
  expect(downloaded.suggestedFilename()).toBe(manifest.filename);
  const downloadedBody = await readFile(await downloaded.path());
  expect(createHash('sha256').update(downloadedBody).digest('hex')).toBe(manifest.sha256.toLowerCase());
  await page.getByRole('button', { name: 'Copy website address', exact: true }).click();
  await expect(page.getByText('Website address copied. Paste it into the launcher.')).toBeVisible();
  expect(await page.evaluate(() => navigator.clipboard.readText())).toBe(new URL(site).origin);
  // The address remains selectable when clipboard access is denied.
  await page.evaluate(() => Object.defineProperty(navigator, 'clipboard', { configurable: true, value: { writeText: async () => { throw new Error('Clipboard deliberately denied for QA'); } } }));
  await page.getByRole('button', { name: 'Copy website address', exact: true }).click();
  await expect(page.getByText('Copy was unavailable. Select and copy the website address shown below.')).toBeVisible();
  const address = page.getByLabel('Website address for the launcher');
  await expect(address).toHaveAttribute('readonly', '');
  await address.focus();
  expect(await address.evaluate(input => input.value.slice(input.selectionStart, input.selectionEnd))).toBe(new URL(site).origin);
  await capture(page, 'download-clipboard-fallback');
  await testInfo.attach('windows-download-outcomes', { body: JSON.stringify({ manifest, httpStatus: archiveResponse.status(), zipSignature: '504b0304', actualBytes: body.length, sha256Matches: true, browserDownloadedFile: downloaded.suggestedFilename(), clipboardCopy: true, selectableFallback: true }, null, 2), contentType: 'application/json' });
});

test('unavailable or invalid Windows download stays disabled and can recover through retry', async ({ page }) => {
  let failManifest = true;
  let failArchive = true;
  let archiveChecks = 0;
  await page.route('**/downloads/querylab-helper-windows.json', async route => {
    if (failManifest) { await route.fulfill({ status: 404, contentType: 'text/html', body: '<html>Missing package</html>' }); return; }
    await route.continue();
  });
  await page.route('**/downloads/querylab-helper-windows.zip', async route => {
    archiveChecks++;
    if (failArchive) { await route.fulfill({ status: 200, contentType: 'text/html', body: '<html>SPA fallback is not a ZIP</html>' }); return; }
    await route.continue();
  });
  await page.goto('/');
  const retry = page.getByRole('button', { name: 'Retry download check', exact: true });
  await expect(retry).toBeVisible();
  await expect(page.getByRole('link', { name: 'Download Windows helper', exact: true })).toHaveCount(0);
  await expect(page.getByText('The Windows download is temporarily unavailable. Retry the check, or return when it is available.')).toBeVisible();
  await capture(page, 'download-unavailable');
  failManifest = false;
  await retry.click();
  await expect.poll(() => archiveChecks).toBe(1);
  await expect(retry).toBeEnabled();
  await expect(page.getByRole('link', { name: 'Download Windows helper', exact: true })).toHaveCount(0);
  failArchive = false;
  await retry.click();
  await expect(page.getByRole('link', { name: 'Download Windows helper', exact: true })).toBeVisible();
  await expect(retry).toHaveCount(0);
  await capture(page, 'download-retry-recovered');
});
