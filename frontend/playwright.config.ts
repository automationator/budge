import { defineConfig, devices } from '@playwright/test'

const isCI = !!process.env.CI

export default defineConfig({
  testDir: './tests/e2e',
  fullyParallel: true,
  forbidOnly: isCI,
  retries: 2, // Handle flaky parallel execution
  workers: 5,

  // No global setup - each test file resets its own schema via test-setup fixture

  timeout: isCI ? 90000 : 60000,
  expect: {
    timeout: isCI ? 30000 : 15000,
  },

  reporter: [['html', { open: 'never' }], ['list']],
  use: {
    baseURL: 'http://localhost:5173',
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
    actionTimeout: isCI ? 30000 : 15000,
    navigationTimeout: isCI ? 60000 : 30000,
    // No shared storageState - each test file manages its own auth via test-setup fixture
  },
  projects: [
    // Auth tests need fresh state (they test auth itself)
    {
      name: 'auth-chromium',
      testMatch: /auth\.spec\.ts/,
      use: {
        ...devices['Desktop Chrome'],
        storageState: { cookies: [], origins: [] }, // No pre-auth
      },
      fullyParallel: false,
    },
    // Firefox and WebKit auth tests only run in CI
    ...(isCI
      ? [
          {
            name: 'auth-firefox',
            testMatch: /auth\.spec\.ts/,
            use: {
              ...devices['Desktop Firefox'],
              storageState: { cookies: [], origins: [] },
            },
            dependencies: ['auth-chromium'],
            fullyParallel: false,
          },
          {
            name: 'auth-webkit',
            testMatch: /auth\.spec\.ts/,
            use: {
              ...devices['Desktop Safari'],
              storageState: { cookies: [], origins: [] },
            },
            dependencies: ['auth-firefox'],
            fullyParallel: false,
          },
        ]
      : []),

    // Main browser project - auth handled by test-setup fixture per file
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
      testIgnore: [/auth\.spec\.ts/, /\.mobile\.spec\.ts/],
      fullyParallel: false, // Tests within a file run serially
    },
    // Mobile project - runs *.mobile.spec.ts files at mobile viewport
    {
      name: 'mobile',
      use: {
        ...devices['Desktop Chrome'],
        viewport: { width: 430, height: 715 },
      },
      testMatch: /\.mobile\.spec\.ts/,
      fullyParallel: false,
    },
    // Firefox and WebKit only run in CI
    ...(isCI
      ? [
          {
            name: 'firefox',
            use: { ...devices['Desktop Firefox'] },
            testIgnore: /auth\.spec\.ts/,
          },
          {
            name: 'webkit',
            use: { ...devices['Desktop Safari'] },
            testIgnore: /auth\.spec\.ts/,
          },
        ]
      : []),
  ],
  webServer: {
    command: 'npm run dev',
    url: 'http://localhost:5173',
    reuseExistingServer: !process.env.CI,
    timeout: 120000,
  },
})
