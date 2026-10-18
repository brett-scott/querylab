import { defineConfig } from '@playwright/test';

const basePath = process.env.QUERYLAB_BASE_PATH || '/querylab/';
const site = new URL(basePath, 'http://127.0.0.1:5173').href;

export default defineConfig({
  testDir: './tests',
  testMatch: 'pages.spec.js',
  timeout: 90000,
  expect: { timeout: 15000 },
  workers: 1,
  retries: 0,
  outputDir: './pages-test-artifacts',
  reporter: [['list'], ['json', { outputFile: 'pages-test-results.json' }]],
  webServer: {
    command: 'npm --prefix ../frontend run preview -- --host 127.0.0.1 --port 5173 --strictPort',
    env: { QUERYLAB_BASE_PATH: basePath },
    url: site,
    reuseExistingServer: false,
    timeout: 30000,
  },
  use: {
    baseURL: site,
    browserName: 'chromium',
    channel: process.env.QUERYLAB_BROWSER_CHANNEL || (process.platform === 'win32' ? 'msedge' : undefined),
    viewport: { width: 1600, height: 1000 },
    // The optional real-helper test handles private pairing credentials.
    screenshot: 'off',
    trace: 'off',
    video: 'off',
  },
});
