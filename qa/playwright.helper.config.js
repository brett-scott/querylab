import { defineConfig } from '@playwright/test';

export default defineConfig({
  testDir: './tests',
  testMatch: 'helper.spec.js',
  timeout: 90000,
  expect: { timeout: 15000 },
  workers: 1,
  retries: 0,
  outputDir: './helper-test-artifacts',
  reporter: [['list'], ['json', { outputFile: 'helper-test-results.json' }]],
  use: {
    baseURL: process.env.QUERYLAB_HELPER_SITE_URL || 'http://127.0.0.1:8081',
    browserName: 'chromium',
    channel: process.env.QUERYLAB_BROWSER_CHANNEL || (process.platform === 'win32' ? 'msedge' : undefined),
    viewport: { width: 1600, height: 1000 },
    // Pairing codes and Authorization headers must never enter traces or
    // automatic failure captures. Deliberate screenshots mask the code field.
    screenshot: 'off',
    trace: 'off',
    video: 'off',
  },
});
