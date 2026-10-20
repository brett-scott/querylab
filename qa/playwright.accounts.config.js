import { defineConfig } from '@playwright/test';
import pages from './playwright.pages.config.js';

export default defineConfig({
  ...pages,
  testMatch: 'accounts.spec.js',
  outputDir: './accounts-test-artifacts',
  reporter: [['list'], ['json', { outputFile: 'accounts-test-results.json' }]],
});
