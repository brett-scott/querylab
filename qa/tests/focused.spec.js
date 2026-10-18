import { test, expect } from '@playwright/test';
import { mkdir } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';

const evidence = fileURLToPath(new URL('../screenshots/focused/', import.meta.url));
async function capture(page, name) {
  await mkdir(evidence, { recursive: true });
  await page.screenshot({ path: `${evidence}/${name}.png`, fullPage: true });
}
async function noHorizontalOverflow(page) {
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1)).toBe(true);
}

test('focused workbench keeps the full contract, schema, cursor and real results available on demand', async ({ page, request }, testInfo) => {
  await page.goto('/');
  const editor = page.getByRole('textbox', { name: 'SQL editor' });
  const schema = page.getByRole('button', { name: 'Schema', exact: true }).first();
  const results = page.getByRole('button', { name: 'Results', exact: true });
  await expect(page.locator('#run-sql')).toBeEnabled();
  await expect(results).toHaveAttribute('aria-expanded', 'false');
  await expect(page.getByRole('heading', { name: 'Database schema' })).not.toBeVisible();
  await expect(page.locator('.requirements-list')).not.toBeVisible();
  await expect(page.locator('.column-chips')).not.toBeVisible();
  await noHorizontalOverflow(page);
  await capture(page, 'desktop-default');

  const catalog = await (await request.get('/api/challenges')).json();
  const challenge = catalog.challenges.find(item => item.id === 'OS-Q01');
  const requirements = page.locator('.requirements-section summary');
  await expect(requirements).toContainText(String(challenge.requirements.length));
  await requirements.focus();
  await page.keyboard.press('Enter');
  for (const requirement of challenge.requirements) await expect(page.locator('.requirements-list')).toContainText(requirement);
  await requirements.focus();
  await page.keyboard.press('Enter');
  await expect(page.locator('.requirements-list')).not.toBeVisible();
  await expect(requirements).toBeFocused();
  await page.keyboard.press('Enter');
  await expect(page.locator('.requirements-list')).toBeVisible();
  await page.locator('.output-contract summary').click();
  for (const column of challenge.expected_columns) await expect(page.locator('.column-chips')).toContainText(column);
  await capture(page, 'full-contract');

  const sql = 'SELECT 21 * 2 AS answer;\n-- Keep this cursor and draft';
  await editor.fill(sql);
  await editor.press('Control+Home');
  await editor.press('ArrowRight');
  await editor.press('ArrowRight');
  await editor.press('ArrowRight');
  await editor.press('ArrowRight');
  await editor.press('ArrowRight');
  await editor.press('ArrowRight');
  await editor.press('ArrowRight');
  const originalEditor = await editor.elementHandle();
  await schema.click();
  await expect(schema).toHaveAttribute('aria-expanded', 'true');
  await expect(page.locator('.schema-table-heading')).toHaveCount(8);
  for (const table of await page.locator('.schema-table-heading').all()) await expect(table).toHaveAttribute('aria-expanded', 'false');
  await page.getByRole('textbox', { name: 'Search tables or columns' }).fill('customers');
  await expect(page.locator('.schema-table-heading')).toHaveCount(1);
  await page.locator('.schema-table-heading').click();
  await expect(page.locator('.schema-columns')).toContainText('customer_id');
  await page.getByRole('button', { name: 'Preview rows', exact: true }).click();
  await expect(page.getByRole('dialog').getByRole('table')).toBeVisible();
  await capture(page, 'schema-sample');
  await page.keyboard.press('Escape');
  await expect(page.getByRole('button', { name: 'Preview rows', exact: true })).toBeFocused();
  await capture(page, 'schema-dock');

  await page.getByRole('button', { name: 'Focus', exact: true }).click();
  await expect(page.locator('.brief-pane')).not.toBeVisible();
  await expect(page.getByRole('heading', { name: 'Database schema' })).not.toBeVisible();
  await expect(page.getByRole('button', { name: 'Exit focus', exact: true })).toBeVisible();
  await expect(page.getByRole('button', { name: 'Challenge', exact: true }).first()).toBeVisible();
  await capture(page, 'focus-editor');
  await page.getByRole('button', { name: 'Exit focus', exact: true }).focus();
  await page.keyboard.press('Enter');
  await expect(page.locator('.brief-pane')).toBeVisible();
  await expect(page.getByRole('heading', { name: 'Database schema' })).toBeVisible();
  await expect(page.locator('.requirements-list')).toBeVisible();
  await page.getByRole('button', { name: 'Focus', exact: true }).click();
  await page.setViewportSize({ width: 375, height: 667 });
  await page.getByRole('button', { name: 'Exit focus', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'Database schema' })).toBeVisible();
  await expect(page.getByRole('navigation', { name: 'Workspace panes' }).getByRole('button', { name: 'Schema', exact: true })).toBeFocused();
  await capture(page, 'mobile-focus-restored-schema');
  await page.setViewportSize({ width: 1600, height: 1000 });
  await expect(editor).toHaveText(sql, { useInnerText: true });
  expect(await originalEditor.evaluate(element => element.isConnected)).toBe(true);
  await page.getByRole('button', { name: 'Close schema', exact: true }).click();
  await expect(schema).toBeFocused();
  await editor.focus();
  await page.keyboard.type('/*cursor*/');
  await expect(editor).toHaveText(`${sql.slice(0, 7)}/*cursor*/${sql.slice(7)}`, { useInnerText: true });
  await editor.fill(sql);
  await page.locator('#run-sql').click();
  await expect(page.getByRole('cell', { name: '42', exact: true })).toBeVisible();
  await expect(results).toHaveAttribute('aria-expanded', 'true');
  await expect(page.getByRole('tab', { name: 'Practice results', exact: true })).toHaveAttribute('aria-selected', 'true');
  await expect(page.getByText(/rows.*not graded/).first()).toBeVisible();
  await capture(page, 'real-results');
  const height = page.getByRole('separator', { name: 'Resize results' });
  await expect(page.getByRole('slider', { name: 'Results height' })).toHaveCount(0);
  const before = Number(await height.getAttribute('aria-valuenow'));
  await height.focus();
  await page.keyboard.press('ArrowUp');
  expect(Number(await height.getAttribute('aria-valuenow'))).toBeGreaterThan(before);
  const pane = page.getByRole('region', { name: 'Results', exact: true });
  const resultBeforeDrag = await pane.boundingBox();
  const editorBeforeDrag = await page.locator('.editor-panel').boundingBox();
  const divider = await height.boundingBox();
  await page.mouse.move(divider.x + divider.width / 2, divider.y + divider.height / 2);
  await page.mouse.down();
  // Pointer capture must keep resizing after leaving the divider horizontally.
  await page.mouse.move(20, divider.y + divider.height / 2 - 96, { steps: 8 });
  await expect.poll(async () => (await pane.boundingBox()).height).toBeCloseTo(resultBeforeDrag.height + 96, 0);
  await page.mouse.up();
  expect((await page.locator('.editor-panel').boundingBox()).height).toBeCloseTo(editorBeforeDrag.height - 96, 0);
  await expect(page.locator('body')).not.toHaveClass(/resizing-results/);
  await expect(editor).toHaveText(sql, { useInnerText: true });
  expect(await originalEditor.evaluate(element => element.isConnected)).toBe(true);
  const afterDrag = (await pane.boundingBox()).height;
  await page.mouse.move(20, divider.y - 150);
  expect((await pane.boundingBox()).height).toBeCloseTo(afterDrag, 0);
  await capture(page, 'results-drag-resized');

  const cancelDivider = await height.boundingBox();
  await page.mouse.move(cancelDivider.x + cancelDivider.width / 2, cancelDivider.y + cancelDivider.height / 2);
  await page.mouse.down();
  await page.mouse.move(cancelDivider.x + cancelDivider.width / 2, cancelDivider.y + 60, { steps: 4 });
  await page.keyboard.press('Escape');
  await page.mouse.up();
  expect((await pane.boundingBox()).height).toBeCloseTo(afterDrag, 0);
  await expect(page.locator('body')).not.toHaveClass(/resizing-results/);
  await results.click();
  await expect(results).toHaveAttribute('aria-expanded', 'false');
  await expect(page.getByRole('cell', { name: '42', exact: true })).not.toBeVisible();
  await capture(page, 'results-collapsed');
  await results.focus();
  await page.keyboard.press('Enter');
  await expect(page.getByRole('cell', { name: '42', exact: true })).toBeVisible();

  await page.getByRole('button', { name: 'Focus', exact: true }).click();
  await editor.fill('SELEKT invalid;');
  await page.locator('#run-sql').click();
  await expect(page.getByRole('alert').filter({ hasText: /syntax|SQL|SELEKT/i })).toBeVisible();
  await expect(page.getByRole('button', { name: 'Exit focus', exact: true })).toBeVisible();
  await capture(page, 'focus-sql-error');
  await page.getByRole('button', { name: 'Exit focus', exact: true }).click();

  await page.setViewportSize({ width: 1600, height: 600 });
  await editor.fill('WITH RECURSIVE numbers AS (SELECT 1 AS n UNION ALL SELECT n + 1 FROM numbers WHERE n < 20) SELECT n FROM numbers;');
  await page.locator('#run-sql').click();
  await expect(page.getByRole('cell', { name: '20', exact: true })).toBeVisible();
  // Schema refresh briefly changes the available space after Run completes.
  // Wait for readiness, then click the settled divider before testing End.
  await expect(page.locator('#run-sql')).toBeEnabled();
  await height.click();
  await page.keyboard.press('End');
  await expect.poll(() => height.getAttribute('aria-valuenow')).toBe(await height.getAttribute('aria-valuemax'));
  expect((await page.locator('.editor-panel').boundingBox()).height).toBeGreaterThanOrEqual(199);
  expect((await pane.boundingBox()).height).toBeGreaterThanOrEqual(147);
  await page.getByRole('cell', { name: '20', exact: true }).scrollIntoViewIfNeeded();
  await expect(page.getByRole('cell', { name: '20', exact: true })).toBeInViewport();
  await capture(page, 'short-desktop-maximum-results');

  await page.setViewportSize({ width: 1024, height: 1000 });
  await schema.click();
  await expect(page.getByRole('heading', { name: 'Database schema' })).toBeVisible();
  await expect(page.locator('.task-context')).toBeVisible();
  await expect(page.locator('.task-context')).toContainText(challenge.id);
  await expect(page.locator('.task-context')).toContainText(challenge.title);
  await noHorizontalOverflow(page);
  await capture(page, 'tablet-schema');
  await page.getByRole('button', { name: 'Challenge', exact: true }).first().click();
  await expect(page.locator('.requirements-list')).toBeVisible();
  await capture(page, 'tablet-challenge');
  await page.setViewportSize({ width: 375, height: 667 });
  await page.getByRole('button', { name: 'Editor', exact: true }).click();
  await expect(editor).toBeVisible();
  await expect(page.locator('#run-sql')).toBeInViewport();
  await expect(page.getByRole('button', { name: 'Submit', exact: true })).toBeInViewport();
  await noHorizontalOverflow(page);
  await capture(page, 'mobile-editor');
  await page.getByRole('button', { name: 'Challenge', exact: true }).first().click();
  await expect(page.locator('.requirements-list')).toBeVisible();
  await noHorizontalOverflow(page);
  await capture(page, 'mobile-challenge');
  await page.getByRole('button', { name: 'Schema', exact: true }).first().click();
  await expect(page.getByRole('heading', { name: 'Database schema' })).toBeVisible();
  await noHorizontalOverflow(page);
  await capture(page, 'mobile-schema');

  // A 1600x1000 browser at 200% page zoom exposes about 800x500 CSS pixels.
  // This checks equivalent reflow dimensions; it does not claim browser zoom.
  await page.setViewportSize({ width: 800, height: 500 });
  await page.getByRole('button', { name: 'Editor', exact: true }).click();
  await expect(page.locator('#run-sql')).toBeInViewport();
  await expect(page.getByRole('button', { name: 'Submit', exact: true })).toBeInViewport();
  await noHorizontalOverflow(page);
  // Narrow layouts stack results instead of showing the desktop resize control.
  await expect(height).toHaveCount(0);
  await page.getByRole('cell', { name: '20', exact: true }).scrollIntoViewIfNeeded();
  await expect(page.getByRole('cell', { name: '20', exact: true })).toBeInViewport();
  await capture(page, 'zoom-equivalent-reflow');
  await page.locator('#run-sql').scrollIntoViewIfNeeded();
  await expect(page.locator('#run-sql')).toBeInViewport();
  await expect(page.getByRole('button', { name: 'Submit', exact: true })).toBeInViewport();
  await testInfo.attach('focused-ui-outcomes', { body: JSON.stringify({
    fullAuthoredRequirementsCompared: challenge.requirements.length,
    expectedOutputColumnsCompared: challenge.expected_columns.length,
    originalEditorStayedMounted: true, cursorInsertionOffset: 7,
    realRunAnswer: 42, collapsedOutputRestored: true,
    resultsHeightKeyboardBefore: before, testedWidths: [1600, 1024, 375, 800],
    zoom: 'Equivalent CSS viewport reflow only; actual browser zoom not tested',
  }, null, 2), contentType: 'application/json' });
});
