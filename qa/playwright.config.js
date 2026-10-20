import { defineConfig } from '@playwright/test';

export default defineConfig({
  testDir: './tests',
  testIgnore: ['helper.spec.js', 'pages.spec.js', 'accounts.spec.js'],
  timeout: 90000,
  expect: { timeout: 15000 },
  workers: 1,
  retries: 0,
  outputDir: './test-artifacts',
  reporter: [['list'], ['json', { outputFile: 'test-results.json' }]],
  use: {
    baseURL: process.env.QUERYLAB_URL || 'http://127.0.0.1:8080',
    browserName: 'chromium',
    channel: process.env.QUERYLAB_BROWSER_CHANNEL || (process.platform === 'win32' ? 'msedge' : undefined),
    viewport: { width: 1600, height: 1000 },
    screenshot: 'only-on-failure',
    trace: 'retain-on-failure',
  },
});
