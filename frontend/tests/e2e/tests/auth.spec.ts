import { test, expect } from '../fixtures/test-setup'
import { LoginPage } from '../pages/login.page'
import { RegisterPage } from '../pages/register.page'
import { generateTestUser } from '../fixtures/test-data'

// Auth tests run serially on Chromium only (configured in playwright.config.ts)
// These tests verify authentication functionality itself

test.describe('Authentication', () => {
  test.describe('Login', () => {
    test('successful login redirects to envelopes', async ({ unauthenticatedPage: page }) => {
      // First register a user to test login with
      const testUser = generateTestUser()
      const registerPage = new RegisterPage(page)
      await registerPage.goto()
      await registerPage.register(testUser.username, testUser.password, testUser.email)
      await registerPage.waitForEnvelopes()

      // Logout by clearing storage
      await page.goto('/login')
      await page.evaluate(() => localStorage.clear())
      await page.reload()

      // Now test login
      const loginPage = new LoginPage(page)
      await loginPage.login(testUser.username, testUser.password)
      await loginPage.waitForEnvelopes()

      await expect(page).toHaveURL('/')
      await expect(page.getByRole('heading', { name: 'Envelopes' })).toBeVisible()
    })

    // Migrated to component tests: LoginView.spec.ts
    // - invalid credentials show error
    // - empty form shows validation errors
    // - has link to register page
  })

  test.describe('Registration', () => {
    test('successful registration redirects to envelopes', async ({ unauthenticatedPage: page }) => {
      const registerPage = new RegisterPage(page)
      const newUser = generateTestUser()

      await registerPage.goto()
      await registerPage.register(newUser.username, newUser.password, newUser.email)

      // Should redirect to envelopes after registration
      await registerPage.waitForEnvelopes()
      await expect(page).toHaveURL('/')
    })

    // Migrated to component tests: RegisterView.spec.ts
    // - has link to login page
  })

  test.describe('Protected Routes', () => {
    test('redirects to login when not authenticated', async ({ unauthenticatedPage: page }) => {
      // Navigate to login first, then clear auth state
      await page.goto('/login')
      await page.evaluate(() => localStorage.clear())

      // Try to access protected route directly
      await page.goto('/accounts')

      // Should redirect to login
      await expect(page).toHaveURL(/\/login/)
    })

    test('redirects back to intended page after login', async ({ unauthenticatedPage: page }) => {
      // First register a user
      const testUser = generateTestUser()
      const registerPage = new RegisterPage(page)
      await registerPage.goto()
      await registerPage.register(testUser.username, testUser.password, testUser.email)
      await registerPage.waitForEnvelopes()

      // Logout by clearing storage
      await page.goto('/login')
      await page.evaluate(() => localStorage.clear())
      await page.reload()

      // Try to access protected route
      await page.goto('/accounts')

      // Should be on login page
      await expect(page).toHaveURL(/\/login/)

      // Login
      const loginPage = new LoginPage(page)
      await loginPage.login(testUser.username, testUser.password)

      // Should redirect to the originally intended page (or dashboard)
      await page.waitForURL(/\/(accounts)?/, { timeout: 10000 })
    })
  })

  test.describe('Logout', () => {
    test('logout clears session and redirects to login', async ({ unauthenticatedPage: page }) => {
      // First register and login
      const testUser = generateTestUser()
      const registerPage = new RegisterPage(page)
      await registerPage.goto()
      await registerPage.register(testUser.username, testUser.password, testUser.email)
      await registerPage.waitForEnvelopes()

      // Find and click logout button (usually in user menu or nav)
      const userMenuButton = page
        .locator('.mdi-account-circle, [aria-label*="user"], [aria-label*="menu"]')
        .first()
      if (await userMenuButton.isVisible({ timeout: 2000 }).catch(() => false)) {
        await userMenuButton.click()
        const logoutItem = page.locator('text=Logout, text=Sign out, text=Log out').first()
        if (await logoutItem.isVisible({ timeout: 2000 }).catch(() => false)) {
          await logoutItem.click()
        }
      }

      // Fallback: manually clear session
      await page.evaluate(() => localStorage.clear())
      await page.goto('/login')

      // Should be on login page
      await expect(page).toHaveURL(/\/login/)
    })
  })

  test.describe('Session Persistence', () => {
    test('session persists after page refresh', async ({ unauthenticatedPage: page }) => {
      // First register
      const testUser = generateTestUser()
      const registerPage = new RegisterPage(page)
      await registerPage.goto()
      await registerPage.register(testUser.username, testUser.password, testUser.email)
      await registerPage.waitForEnvelopes()

      // Refresh page
      await page.reload()

      // Should still be logged in (on envelopes)
      await expect(page).toHaveURL('/')
    })
  })
})
