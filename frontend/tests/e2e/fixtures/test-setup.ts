/**
 * Test setup fixtures for per-file database isolation.
 *
 * This module provides fixtures that:
 * 1. Reset the database schema for each worker
 * 2. Create a fresh user with auth tokens for each test file
 * 3. Provide an authenticated page context
 *
 * Usage in spec files:
 *
 * ```typescript
 * import { test, expect } from '../fixtures/test-setup'
 *
 * test.beforeAll(async ({ testApi, testContext }) => {
 *   // Create test data using testApi
 *   await testApi.createAccount(testContext.user.budgetId, { name: 'Test Account' })
 * })
 *
 * test('my test', async ({ authenticatedPage }) => {
 *   // Use the pre-authenticated page
 *   await authenticatedPage.goto('/accounts')
 * })
 * ```
 */

import { test as base, type Page, type BrowserContext } from '@playwright/test'
import { TestApi, type UserData, type AccountData, type EnvelopeData, type PayeeData, type TransactionData, type BudgetData } from './test-api'

export interface TestContext {
  workerId: string
  schemaName: string
  user: UserData
}

interface TestFixtures {
  /**
   * Test API client for creating test data.
   * The API client is tied to the current worker's schema.
   */
  testApi: TestApi

  /**
   * Test context containing worker info, schema name, and user credentials.
   * The schema is reset and user is created once per test file.
   */
  testContext: TestContext

  /**
   * Pre-authenticated browser context with httpOnly cookies set up.
   */
  authenticatedContext: BrowserContext

  /**
   * Pre-authenticated page ready for testing.
   */
  authenticatedPage: Page

  /**
   * Page with schema isolation but no pre-loaded auth tokens.
   * Use for testing login/register flows that need a clean auth state.
   */
  unauthenticatedPage: Page
}

// Storage for per-file setup (shared across tests in the same file)
const fileContexts = new Map<string, TestContext>()

export const test = base.extend<TestFixtures>({
  /**
   * TestApi fixture - provides access to test factory endpoints.
   * One instance per worker, persists across all tests in the file.
   */
  // eslint-disable-next-line no-empty-pattern
  testApi: async ({}, use, workerInfo) => {
    const api = new TestApi(workerInfo.workerIndex)
    await use(api)
  },

  /**
   * TestContext fixture - resets DB and creates user once per file.
   * This runs in beforeAll scope (auto fixture with scope: 'worker' behavior).
   */
  testContext: async ({ testApi }, use, testInfo) => {
    // Use test file path as key for per-file caching
    const fileKey = `${testInfo.workerIndex}:${testInfo.file}`

    let context = fileContexts.get(fileKey)

    if (!context) {
      // Reset database for this worker
      const { schemaName } = await testApi.reset()

      // Create a user for this test file
      const user = await testApi.createUser()

      context = {
        workerId: testApi.workerIdValue,
        schemaName,
        user,
      }

      fileContexts.set(fileKey, context)
    }

    await use(context)
  },

  /**
   * Authenticated browser context with httpOnly cookies pre-configured.
   * Creates a new context for each test.
   */
  authenticatedContext: async ({ browser, testContext }, use) => {
    // Cookie expiry: 30 minutes from now
    const accessExpiry = Math.floor(Date.now() / 1000) + 30 * 60
    // Refresh cookie expiry: 7 days from now
    const refreshExpiry = Math.floor(Date.now() / 1000) + 7 * 86400

    const context = await browser.newContext({
      storageState: {
        cookies: [
          {
            name: 'access_token',
            value: testContext.user.accessToken,
            domain: 'localhost',
            path: '/',
            httpOnly: true,
            secure: false,
            sameSite: 'Lax',
            expires: accessExpiry,
          },
          {
            name: 'refresh_token',
            value: testContext.user.refreshToken,
            domain: 'localhost',
            path: '/api/v1/auth',
            httpOnly: true,
            secure: false,
            sameSite: 'Lax',
            expires: refreshExpiry,
          },
        ],
        origins: [
          {
            origin: 'http://localhost:5173',
            localStorage: [
              {
                name: 'budge_current_budget',
                value: testContext.user.budgetId,
              },
            ],
          },
        ],
      },
      // Add E2E schema header for per-worker database isolation
      extraHTTPHeaders: {
        'X-E2E-Schema': testContext.schemaName,
      },
    })

    await use(context)
    await context.close()
  },

  /**
   * Pre-authenticated page ready for testing.
   * Creates a new page from the authenticated context for each test.
   */
  authenticatedPage: async ({ authenticatedContext }, use) => {
    const page = await authenticatedContext.newPage()
    await use(page)
    // Page is closed when context is closed
  },

  /**
   * Page with schema isolation but no pre-loaded auth tokens.
   * Use for testing login/register flows that need a clean auth state.
   */
  unauthenticatedPage: async ({ browser, testContext }, use) => {
    const context = await browser.newContext({
      storageState: { cookies: [], origins: [] },
      extraHTTPHeaders: {
        'X-E2E-Schema': testContext.schemaName,
      },
    })
    const page = await context.newPage()
    await use(page)
    await context.close()
  },
})

export { expect } from '@playwright/test'

// Re-export types for convenience
export type { TestApi, UserData, AccountData, EnvelopeData, PayeeData, TransactionData, BudgetData }
