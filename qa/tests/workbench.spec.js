import { test, expect } from '@playwright/test';
import { mkdir } from 'node:fs/promises';

const evidence = new URL('../screenshots/', import.meta.url).pathname.replace(/^\/([A-Za-z]:)/, '$1');
async function capture(page, name) {
  await mkdir(evidence, { recursive: true });
  await page.screenshot({ path: `${evidence}${name}.png`, fullPage: true });
}
async function edit(page, sql) {
  const editor = page.getByRole('textbox', { name: 'SQL editor' });
  await editor.fill(sql);
  await expect(editor).toHaveText(sql, { useInnerText: true });
}
async function choose(page, id) {
  await page.getByRole('button', { name: /^Challenges/ }).click();
  await page.locator('.challenge-card').filter({ hasText: id }).click();
  await expect(page.getByRole('heading', { level: 1 })).toBeVisible();
}

test('anonymous learning loop: real Run, incorrect/correct Submit, drafts, hints, solution, schema, reset', async ({ page, request }) => {
  const consoleErrors = [];
  page.on('pageerror', error => consoleErrors.push(error.message));
  let solutionReads = 0;
  page.on('request', req => { if (req.url().endsWith('/solution')) solutionReads++; });
  await page.goto('/');
  await expect(page.getByRole('heading', { name: 'Recover inactive high-value customers' })).toBeVisible();
  await expect(page.getByText('Draft saved', { exact: true })).toBeVisible();
  await expect(page.getByRole('button', { name: 'Results', exact: true })).toHaveAttribute('aria-expanded', 'false');
  await expect(page.getByRole('heading', { name: 'Database schema' })).not.toBeVisible();
  expect(solutionReads).toBe(0);
  await capture(page, 'responsive-desktop');

  await page.getByRole('button', { name: 'Schema', exact: true }).first().click();
  await expect(page.locator('.schema-table-heading').first()).toHaveAttribute('aria-expanded', 'false');
  await page.locator('.schema-table-heading').first().click();
  await page.getByRole('button', { name: 'Preview rows', exact: true }).first().click();
  await expect(page.getByRole('dialog')).toBeVisible();
  await expect(page.getByRole('dialog').getByRole('table')).toBeVisible();
  await capture(page, 'schema-sample');
  await page.keyboard.press('Escape');
  await expect(page.getByRole('dialog')).toHaveCount(0);
  await page.getByRole('button', { name: 'Close schema', exact: true }).click();

  await edit(page, 'SELECT 21 * 2 AS answer;');
  await page.locator('#run-sql').click();
  await expect(page.getByRole('cell', { name: '42', exact: true })).toBeVisible();
  await expect(page.getByText(/rows · not graded/).first()).toBeVisible();
  await capture(page, 'real-run-result');
  await page.reload();
  await expect(page.getByRole('textbox', { name: 'SQL editor' })).toHaveText('SELECT 21 * 2 AS answer;');

  await page.getByRole('button', { name: /^Challenges/ }).click();
  await expect(page.locator('.challenge-card')).toHaveCount(12);
  await expect(page.locator('.availability.ready')).toHaveCount(12);
  await capture(page, 'challenge-library');
  await page.locator('.challenge-card').filter({ hasText: 'OS-F01' }).click();
  await edit(page, '-- QA separate function draft');
  await choose(page, 'OS-Q01');
  await expect(page.getByRole('textbox', { name: 'SQL editor' })).toHaveText('SELECT 21 * 2 AS answer;');
  const keys = await page.evaluate(() => Object.keys(localStorage).filter(k => k.startsWith('querylab:draft:')));
  expect(keys.some(k => k.includes('OS-Q01:v1.0.0'))).toBe(true);
  expect(keys.some(k => k.includes('OS-F01:v1.0.0'))).toBe(true);

  await page.getByRole('button', { name: 'Get a hint', exact: true }).click();
  await expect(page.locator('.hint')).toHaveCount(1);
  await page.getByRole('button', { name: 'Reveal hint 2 of 3' }).click();
  await expect(page.locator('.hint')).toHaveCount(2);
  expect(solutionReads).toBe(0);
  await capture(page, 'progressive-hints');
  await page.getByText('More help', { exact: true }).click();
  await page.getByRole('button', { name: /View explained solution/ }).click();
  await expect(page.getByRole('dialog')).toBeVisible();
  expect(solutionReads).toBe(0);
  await page.getByRole('button', { name: 'Reveal solution', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'An explained solution' })).toBeVisible();
  expect(solutionReads).toBe(1);
  await capture(page, 'explained-solution');
  await page.keyboard.press('Escape');

  await edit(page, 'SELECT 1 AS customer_id;');
  await page.getByRole('button', { name: 'Submit', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'A few things to revisit.' })).toBeVisible();
  await capture(page, 'incorrect-submission');

  const solution = await (await request.get('/api/challenges/OS-Q01/solution')).json();
  await edit(page, solution.sql);
  await page.getByRole('button', { name: 'Submit', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'Your answer passes all checks.' })).toBeVisible();
  await capture(page, 'passing-submission');

  const resetButton = page.getByRole('button', { name: 'Reset workspace', exact: true });
  await page.getByLabel('Workspace menu', { exact: true }).click();
  await resetButton.click();
  const dialog = page.getByRole('dialog');
  await expect(dialog).toBeVisible();
  await expect(dialog.getByText(/online store tables, data and routines/)).toBeVisible();
  expect(await page.evaluate(() => document.querySelector('dialog')?.contains(document.activeElement))).toBe(true);
  await page.keyboard.press('Escape');
  await expect(page.getByLabel('Workspace menu', { exact: true })).toBeFocused();
  await page.getByLabel('Workspace menu', { exact: true }).focus();
  await page.keyboard.press('Enter');
  await resetButton.click();
  await page.getByRole('dialog').getByRole('button', { name: 'Reset workspace', exact: true }).click();
  await expect(page.getByText('Practice data and routines restored. Your SQL draft is unchanged.')).toBeVisible();
  await expect(page.getByRole('textbox', { name: 'SQL editor' })).toHaveText(solution.sql, { useInnerText: true });

  await choose(page, 'BI-Q01');
  await expect(page.locator('#run-sql')).toBeEnabled();
  await expect(page.getByRole('button', { name: 'Submit', exact: true })).toBeEnabled();
  const inventorySolution = await (await request.get('/api/challenges/BI-Q01/solution')).json();
  await edit(page, inventorySolution.sql);
  await page.locator('#run-sql').click();
  await expect(page.getByRole('columnheader', { name: 'suggested_order_qty', exact: true })).toBeVisible();
  await page.getByRole('button', { name: 'Submit', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'Your answer passes all checks.' })).toBeVisible();
  await capture(page, 'inventory-query-passing');
  await choose(page, 'OS-Q01');
  await expect(page.getByRole('textbox', { name: 'SQL editor' })).toHaveText(solution.sql, { useInnerText: true });
  await choose(page, 'BI-Q01');
  await expect(page.getByRole('textbox', { name: 'SQL editor' })).toHaveText(inventorySolution.sql, { useInnerText: true });
  await choose(page, 'BI-P01');
  const transferSolution = await (await request.get('/api/challenges/BI-P01/solution')).json();
  await edit(page, `DELIMITER $$\n${transferSolution.sql}$$\nDELIMITER ;\nCALL transfer_stock('browser-transfer',1,1,2,5,'2026-06-30');`);
  await page.locator('#run-sql').click();
  await expect(page.getByRole('cell', { name: 'COMPLETED', exact: true })).toBeVisible();
  await edit(page, transferSolution.sql);
  await page.getByRole('button', { name: 'Submit', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'Your answer passes all checks.' })).toBeVisible();
  await capture(page, 'inventory-procedure-passing');
  await edit(page, 'SELECT on_hand AS source_balance FROM stock WHERE store_id=1 AND product_id=1;');
  await page.locator('#run-sql').click();
  await expect(page.getByRole('cell', { name: '25', exact: true })).toBeVisible();
  await page.getByLabel('Workspace menu', { exact: true }).click();
  await resetButton.click();
  await page.getByRole('dialog').getByRole('button', { name: 'Reset workspace', exact: true }).click();
  await expect(page.getByText('Practice data and routines restored. Your SQL draft is unchanged.')).toBeVisible();
  await page.locator('#run-sql').click();
  await expect(page.getByRole('cell', { name: '30', exact: true })).toBeVisible();
  expect(consoleErrors).toEqual([]);
});

test('1024px and narrow workbench evidence, keyboard editing escape, connection failure', async ({ page }) => {
  await page.goto('/');
  await expect(page.getByRole('heading', { level: 1 })).toBeVisible();
  await expect(page.locator('#run-sql')).toBeEnabled();
  await page.setViewportSize({ width: 1024, height: 1000 });
  await capture(page, 'responsive-tablet');
  await page.getByRole('button', { name: 'Schema', exact: true }).first().click();
  await expect(page.getByRole('heading', { name: 'Database schema' })).toBeVisible();
  await capture(page, 'responsive-tablet-schema');
  await page.getByRole('button', { name: 'Challenge', exact: true }).first().click();
  await page.setViewportSize({ width: 375, height: 667 });
  await page.getByRole('button', { name: 'Editor', exact: true }).click();
  await capture(page, 'responsive-mobile');
  await expect(page.getByText('Draft saved', { exact: true })).toBeInViewport();
  await page.getByRole('button', { name: 'Challenge', exact: true }).first().click();
  await expect(page.getByRole('heading', { level: 1 })).toBeVisible();
  await capture(page, 'responsive-mobile-brief');
  await page.getByRole('button', { name: 'Editor', exact: true }).click();
  await page.setViewportSize({ width: 1600, height: 1000 });
  await edit(page, 'SELECT 8675309 AS offline_draft;');
  await page.getByRole('textbox', { name: 'SQL editor' }).press('Escape');
  await page.keyboard.press('Tab');
  await expect(page.getByRole('textbox', { name: 'SQL editor' })).not.toBeFocused();
  await page.route('**/api/run', route => route.abort('failed'));
  await page.locator('#run-sql').click();
  await expect(page.getByRole('alert').filter({ hasText: /connection|network|reach|fetch/i })).toBeVisible();
  await expect(page.getByRole('textbox', { name: 'SQL editor' })).toHaveText('SELECT 8675309 AS offline_draft;');
  await capture(page, 'connection-error-draft');
});

test('browser storage failure never claims draft saved', async ({ page }) => {
  await page.addInitScript(() => { Storage.prototype.setItem = () => { throw new DOMException('Storage unavailable', 'QuotaExceededError'); }; });
  await page.goto('/');
  await expect(page.getByRole('heading', { level: 1 })).toBeVisible();
  await edit(page, 'SELECT 99 AS unsaved;');
  await expect(page.getByText('Browser storage unavailable · draft not saved')).toBeVisible();
  await expect(page.getByText('Draft saved', { exact: true })).toHaveCount(0);
  await capture(page, 'storage-unavailable');
});

test('function and procedure definitions submit through the real editor', async ({ page, request }) => {
  await page.goto('/?challenge=OS-F01');
  await expect(page.getByRole('heading', { name: 'Apply consistent loyalty tiers' })).toBeVisible();
  const functionSolution = await (await request.get('/api/challenges/OS-F01/solution')).json();
  await page.getByRole('textbox', { name: 'SQL editor' }).fill(functionSolution.sql);
  await page.getByRole('button', { name: 'Submit', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'Your answer passes all checks.' })).toBeVisible();
  await capture(page, 'function-passing-submission');
  await page.getByRole('textbox', { name: 'SQL editor' }).fill(`DELIMITER $$\n${functionSolution.sql}$$\nDELIMITER ;\nSELECT loyalty_tier(2000.00) AS tier;`);
  await page.locator('#run-sql').click();
  await expect(page.getByRole('cell', { name: 'GOLD', exact: true })).toBeVisible();
  await capture(page, 'function-real-run');

  await choose(page, 'OS-P01');
  const procedureSolution = await (await request.get('/api/challenges/OS-P01/solution')).json();
  await page.getByRole('textbox', { name: 'SQL editor' }).fill(procedureSolution.sql);
  await expect.poll(async () => page.evaluate(sql => Object.values(localStorage).includes(sql), procedureSolution.sql)).toBe(true);
  await page.getByRole('button', { name: 'Submit', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'Your answer passes all checks.' })).toBeVisible();
  await capture(page, 'procedure-passing-submission');
});

test('failed polling preserves busy state and real cancellation recovers even after a nonterminal cancel response', async ({ page }) => {
  await page.goto('/');
  await expect(page.getByRole('heading', { level: 1 })).toBeVisible();
  await page.getByRole('button', { name: 'Focus', exact: true }).click();
  let interrupted = false;
  let nonterminalCancel = false;
  await page.route('**/api/jobs/**', async route => {
    if (route.request().method() === 'GET' && !interrupted) {
      interrupted = true;
      await route.abort('failed');
    } else if (route.request().method() === 'POST' && route.request().url().endsWith('/cancel')) {
      const response = await route.fetch();
      expect(response.status()).toBe(200);
      const job = await response.json();
      nonterminalCancel = true;
      await route.fulfill({ response, json: { ...job, status: 'running', result: null, error: null } });
    } else await route.continue();
  });
  await page.getByRole('textbox', { name: 'SQL editor' }).fill('DELIMITER $$\nCREATE PROCEDURE qa_wait() SQL SECURITY INVOKER BEGIN DECLARE n BIGINT DEFAULT 0; WHILE n >= 0 DO SET n = n + 1; END WHILE; END$$\nDELIMITER ;\nCALL qa_wait();');
  await page.locator('#run-sql').click();
  await expect(page.getByRole('alert').filter({ hasText: /Checking has stopped/ })).toBeVisible();
  await expect(page.locator('#run-sql')).toBeDisabled();
  await expect(page.getByRole('button', { name: 'Exit focus', exact: true })).toBeVisible();
  await expect(page.getByRole('button', { name: 'Cancel', exact: true })).toBeVisible();
  await capture(page, 'polling-error-busy');
  await page.getByRole('button', { name: 'Cancel', exact: true }).click();
  await expect(page.getByText(/Execution cancelled\. Your SQL draft is unchanged\./)).toBeVisible();
  expect(interrupted).toBe(true);
  expect(nonterminalCancel).toBe(true);
  await expect(page.locator('#run-sql')).toBeEnabled();
  await edit(page, 'SELECT 123 AS after_cancel;');
  await page.locator('#run-sql').click();
  await expect(page.getByRole('cell', { name: '123', exact: true })).toBeVisible();
  await capture(page, 'cancelled-polling-recovery');
});
