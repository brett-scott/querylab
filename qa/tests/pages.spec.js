import { test, expect } from '@playwright/test';
import { createHash } from 'node:crypto';
import { readFile } from 'node:fs/promises';

test('static Pages build keeps assets, downloads, home and refresh inside the site base', async ({ page, request, baseURL }) => {
  const site = new URL(baseURL);
  const errors = [];
  const requests = [];
  page.on('pageerror', error => errors.push(error.message));
  page.on('request', request => requests.push(new URL(request.url())));
  await page.goto('./?challenge=BI-P02');
  await expect(page.getByRole('heading', { name: 'Your workbench, powered locally.' })).toBeVisible();
  const downloadLink = page.getByRole('link', { name: 'Download Windows helper', exact: true });
  await expect(downloadLink).toBeVisible();
  await expect(downloadLink).toHaveAttribute('href', `${site.pathname}downloads/querylab-helper-windows.zip`);
  await expect(page.getByLabel('Website address for the launcher')).toHaveValue(site.origin);

  const manifestResponse = await request.get(new URL('downloads/querylab-helper-windows.json', site).href);
  expect(manifestResponse.status()).toBe(200);
  expect(manifestResponse.headers()['content-type']).toContain('application/json');
  const manifest = await manifestResponse.json();
  const downloadPromise = page.waitForEvent('download');
  await downloadLink.click();
  const download = await downloadPromise;
  expect(download.suggestedFilename()).toBe(manifest.filename);
  const bytes = await readFile(await download.path());
  expect(bytes.subarray(0, 4).toString('hex')).toBe('504b0304');
  expect(bytes.length).toBe(manifest.bytes);
  expect(createHash('sha256').update(bytes).digest('hex')).toBe(manifest.sha256);

  await page.reload();
  await expect(downloadLink).toBeVisible();
  expect(new URL(page.url()).searchParams.get('challenge')).toBe('BI-P02');
  const home = page.getByRole('link', { name: 'QueryLab home' });
  await expect(home).toHaveAttribute('href', `${site.pathname}?helper=1`);
  await home.click();
  await expect(downloadLink).toBeVisible();
  expect(new URL(page.url()).pathname).toBe(site.pathname);
  // Static hosting must never be asked to execute API requests, and absolute
  // root links must not accidentally escape /querylab/ on a project site.
  expect(requests.filter(url => url.origin === site.origin && !url.pathname.startsWith(site.pathname))).toEqual([]);
  expect(requests.filter(url => /\/api\//.test(url.pathname))).toEqual([]);
  expect(errors).toEqual([]);
});

test('Pages build pairs with the real helper and grades a query, function and procedure', async ({ page, baseURL }) => {
  test.skip(process.env.QUERYLAB_PAGES_WITH_HELPER !== '1', 'Opt in with a running local helper and its private .env.helper.');
  const api = process.env.QUERYLAB_HELPER_API_URL || 'http://127.0.0.1:8765';
  const tokenKey = 'querylab:helper:token';
  const configuration = await readFile(process.env.QUERYLAB_PAGES_HELPER_ENV || new URL('../../.env.helper', import.meta.url), 'utf8');
  const code = configuration.match(/^QUERYLAB_PAIRING_TOKEN=(.+)$/m)?.[1].trim().replace(/^(['"])(.*)\1$/, '$2');
  if (!code) throw new Error('Local helper configuration is missing a pairing code.');
  const errors = [];
  const hostedApiRequests = [];
  page.on('pageerror', error => errors.push(error.message));
  page.on('request', request => {
    const url = new URL(request.url());
    if (url.origin === new URL(baseURL).origin && /\/api\//.test(url.pathname)) hostedApiRequests.push(url.pathname);
  });
  await page.goto('./?challenge=OS-Q01');
  await page.getByLabel('Helper URL', { exact: true }).fill(api);
  await page.getByLabel('Pairing code', { exact: true }).fill(code);
  try {
    await page.getByRole('button', { name: 'Pair helper', exact: true }).click();
    await expect(page.locator('.workbench')).toBeVisible();
  } finally {
    const input = page.getByLabel('Pairing code', { exact: true });
    if (await input.count()) await input.fill('');
  }

  const editor = page.getByRole('textbox', { name: 'SQL editor' });
  await editor.fill('SELECT 21 * 2 AS answer;');
  await page.locator('#run-sql').click();
  await expect(page.getByRole('cell', { name: '42', exact: true })).toBeVisible();
  await page.reload();
  await expect(editor).toHaveText('SELECT 21 * 2 AS answer;', { useInnerText: true });

  for (const id of ['OS-Q01', 'OS-F01', 'OS-P01']) {
    if (id !== 'OS-Q01') {
      await page.getByRole('button', { name: 'Challenges', exact: true }).click();
      await page.locator('.challenge-card').filter({ hasText: id }).click();
    }
    const reference = await page.evaluate(async ({ api, tokenKey, id }) => {
      const response = await fetch(`${api}/api/challenges/${id}/solution`, { headers: { Authorization: `Bearer ${sessionStorage.getItem(tokenKey)}` } });
      if (!response.ok) throw new Error('Reference solution unavailable.');
      return response.json();
    }, { api, tokenKey, id });
    await editor.fill(reference.sql);
    await page.getByRole('button', { name: 'Submit', exact: true }).click();
    await expect(page.getByRole('heading', { name: 'Your answer passes all checks.' })).toBeVisible();
    expect(new URL(page.url()).pathname).toBe(new URL(baseURL).pathname);
  }
  expect(hostedApiRequests).toEqual([]);
  expect(errors).toEqual([]);
});
