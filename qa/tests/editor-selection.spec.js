import { test, expect } from '@playwright/test';

const modifier = process.platform === 'darwin' ? 'Meta' : 'Control';
const sqlRequest = (page, mode) => page.waitForRequest(request =>
  request.method() === 'POST' && new URL(request.url()).pathname === `/api/${mode}`);

test('Run honors highlighted SQL and newline query batches; Submit grades the full draft', async ({ page, request }) => {
  await page.goto('/');
  const editor = page.getByRole('textbox', { name: 'SQL editor' });
  const run = page.locator('#run-sql');
  await expect(run).toBeEnabled();

  await test.step('Tab inserts at the cursor; selected lines indent and outdent together', async () => {
    const draftKey = await page.evaluate(() => Object.keys(localStorage).find(key => key.startsWith('querylab:draft:online-store:OS-Q01:')));
    expect(draftKey).toBeTruthy();
    const expectDraft = async value => {
      await expect.poll(() => page.evaluate(key => localStorage.getItem(key), draftKey)).toBe(value);
    };

    await editor.fill('SELECT 1');
    await editor.press(`${modifier}+End`);
    await editor.press('Tab');
    await expectDraft('SELECT 1\t');
    await editor.pressSequentially('AS result');
    await expectDraft('SELECT 1\tAS result');
    await expect(editor).toBeFocused();

    await editor.fill('SELECT 1');
    await editor.press(`${modifier}+End`);
    await editor.press('ArrowLeft');
    await editor.press('ArrowLeft');
    await editor.press('Tab');
    await expectDraft('SELECT\t 1');

    await editor.fill('SELECT 1\nFROM orders');
    await editor.press(`${modifier}+a`);
    await editor.press('Tab');
    await expectDraft('  SELECT 1\n  FROM orders');
    await editor.press('Shift+Tab');
    await expectDraft('SELECT 1\nFROM orders');
  });

  const selected = 'SELECT 42 AS highlighted_value;\nSELECT 43 AS another_highlighted_value;';
  const draft = `UPDATE customers SET customer_name='Unselected write' WHERE customer_id=1;\n${selected}\nSELEKT invalid_outside_selection;`;
  await editor.fill(draft);
  await editor.press(`${modifier}+Home`);
  await editor.press('ArrowDown');
  await editor.press('Home');
  await editor.press('Shift+ArrowDown');
  await editor.press('Shift+End');
  const toolbarRequest = sqlRequest(page, 'run');
  await run.click();
  expect((await toolbarRequest).postDataJSON().sql).toBe(selected);
  await expect(page.getByRole('cell', { name: '42', exact: true })).toBeVisible();
  await page.getByLabel('Result set', { exact: false }).selectOption('1');
  await expect(page.getByRole('cell', { name: '43', exact: true })).toBeVisible();
  await expect(editor).toHaveText(draft, { useInnerText: true });
  await expect(run).toBeEnabled();

  const shortcutSql = 'SELECT 84 AS shortcut_value;';
  const shortcutDraft = `SELEKT unselected_error;\n${shortcutSql}\nSELECT 999 AS unselected_value;`;
  await editor.fill(shortcutDraft);
  await editor.press(`${modifier}+Home`);
  await editor.press('ArrowDown');
  await editor.press('End');
  await editor.press('Shift+Home');
  const shortcutRequest = sqlRequest(page, 'run');
  await editor.press(`${modifier}+Enter`);
  expect((await shortcutRequest).postDataJSON().sql).toBe(shortcutSql);
  await expect(page.getByRole('cell', { name: '84', exact: true })).toBeVisible();
  await expect(editor).toHaveText(shortcutDraft, { useInnerText: true });
  await expect(run).toBeEnabled();

  const fullScript = 'SELECT 7 AS result_one;\nSELECT 9 AS result_two;';
  await editor.fill(fullScript);
  await editor.press(`${modifier}+End`);
  const fullRequest = sqlRequest(page, 'run');
  await editor.press(`${modifier}+Enter`);
  expect((await fullRequest).postDataJSON().sql).toBe(fullScript);
  await expect(page.getByRole('cell', { name: '7', exact: true })).toBeVisible();
  await page.getByLabel('Result set', { exact: false }).selectOption('1');
  await expect(page.getByRole('cell', { name: '9', exact: true })).toBeVisible();
  await expect(run).toBeEnabled();

  const solution = await (await request.get('/api/challenges/OS-Q01/solution')).json();
  await editor.fill(solution.sql);
  await editor.press(`${modifier}+Home`);
  await editor.press('Shift+End');
  const submitRequest = sqlRequest(page, 'submit');
  await editor.press(`${modifier}+Shift+Enter`);
  expect((await submitRequest).postDataJSON().sql).toBe(solution.sql);
  await expect(page.getByRole('heading', { name: 'Your answer passes all checks.' })).toBeVisible();
  await expect(editor).toHaveText(solution.sql, { useInnerText: true });
  await expect(run).toBeEnabled();
  await editor.fill(`WITH source_rows AS (
  SELECT 21 AS n
)
SELECT n * 2 AS answer FROM source_rows
UNION ALL
SELECT (SELECT 43) AS answer
SELECT 84 AS second_answer`);
  await run.click();
  await expect(page.getByRole('cell', { name: '42', exact: true })).toBeVisible();
  await expect(page.getByRole('cell', { name: '43', exact: true })).toBeVisible();
  await page.getByLabel('Result set', { exact: false }).selectOption('1');
  await expect(page.getByRole('cell', { name: '84', exact: true })).toBeVisible();
  await expect(run).toBeEnabled();

  const corrected = `SELECT srcorders.order_id,
SUM(srcorder_items.quantity * srcorder_items.unit_price) AS total
FROM orders srcorders
INNER JOIN order_items srcorder_items
ON srcorders.order_id = srcorder_items.order_id
WHERE srcorders.status = 'Completed'
GROUP BY srcorders.order_id`;
  await editor.fill(corrected.replace("'Completed'\n", "'Completed';\n"));
  await run.click();
  await expect(page.getByRole('alert')).toContainText('Remove the semicolon before GROUP BY');
  await editor.fill(corrected);
  await run.click();
  await expect(page.getByRole('columnheader', { name: 'total', exact: true })).toBeVisible();
  expect(await page.locator('.result-content tbody tr').count()).toBeGreaterThan(1);
  await expect(run).toBeEnabled();

  await editor.fill(corrected.split('\nGROUP BY')[0]);
  await run.click();
  await expect(page.getByRole('alert')).toContainText('only_full_group_by');
});
