import { defineConfig, devices } from '@playwright/test';

const baseURL = process.env.E2E_BASE_URL || 'http://localhost:5173';
const apiURL = process.env.E2E_API_URL || 'http://localhost:8000';

export default defineConfig({
  testDir: '.',
  testMatch: '**/*.spec.ts',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 1,
  workers: process.env.CI ? 2 : undefined,
  reporter: [
    ['html', { outputFolder: 'playwright-report', open: 'never' }],
    ['list'],
  ],
  use: {
    baseURL,
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
    actionTimeout: 15000,
    navigationTimeout: 30000,
    extraHTTPHeaders: {},
  },
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
    {
      name: 'mobile-chrome',
      use: { ...devices['Pixel 7'] },
    },
  ],
  webServer: process.env.CI
    ? [
        {
          command: 'cd ../../backend && uvicorn app.main:app --host 127.0.0.1 --port 8000',
          url: `${apiURL}/health`,
          reuseExistingServer: false,
          timeout: 120000,
          env: {
            JWT_SECRET: 'e2e-test-secret',
            APP_ENV: 'testing',
            DATABASE_URL: 'e2e_nebula.db',
          },
        },
        {
          command: 'cd ../../frontend && npm run dev -- --host 127.0.0.1 --port 5173',
          url: baseURL,
          reuseExistingServer: false,
          timeout: 120000,
        },
      ]
    : undefined,
  globalSetup: './config/global-setup.ts',
});
