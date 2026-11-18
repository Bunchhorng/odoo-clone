import { defineConfig } from '@playwright/test'
export default defineConfig({
  testDir: './tests/e2e',
  timeout: 60000,
  expect: { timeout: 15000 },
  workers: 1,
  reporter: [['list'], ['json', { outputFile: 'test-results/ui-results.json' }]],
  use: {
    baseURL: process.env.KERP_BASE_URL || 'http://localhost:5175',
    channel: process.env.CI ? undefined : 'msedge',
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
  },
})
