import { test, expect } from '../fixtures/test-setup'
import { SettingsPage } from '../pages/settings.page'

test.describe('Admin Settings', () => {
  test.describe('Registration Toggle', () => {
    test('admin can toggle registration off', async ({ authenticatedPage, testApi }) => {
      // Ensure registration starts enabled
      await testApi.setRegistrationEnabled(true)

      const settingsPage = new SettingsPage(authenticatedPage)

      await settingsPage.goto()
      await settingsPage.expectAdminCardVisible()

      // Verify registration is enabled initially
      const initialState = await settingsPage.isRegistrationEnabled()
      expect(initialState).toBe(true)

      // Toggle off
      const responsePromise = authenticatedPage.waitForResponse(
        (response) =>
          response.url().includes('/admin/settings') && response.request().method() === 'PATCH'
      )
      await settingsPage.toggleRegistration()
      await responsePromise

      // Verify it's now disabled
      const newState = await settingsPage.isRegistrationEnabled()
      expect(newState).toBe(false)
    })

    test('registration page redirects to login when disabled', async ({
      browser,
      testApi,
      testContext,
    }) => {
      // Disable registration via API
      await testApi.setRegistrationEnabled(false)

      // Open a new unauthenticated context
      const anonContext = await browser.newContext({
        extraHTTPHeaders: { 'X-E2E-Schema': testContext.schemaName },
      })
      const anonPage = await anonContext.newPage()

      // Try to navigate to register page
      await anonPage.goto('/register')

      // Should redirect to login
      await expect(anonPage).toHaveURL(/\/login/)

      await anonContext.close()
    })

    test('admin can re-enable registration', async ({ authenticatedPage, testApi }) => {
      // Ensure registration starts enabled so toggle-off works
      await testApi.setRegistrationEnabled(true)

      const settingsPage = new SettingsPage(authenticatedPage)

      await settingsPage.goto()
      await settingsPage.expectAdminCardVisible()

      // Toggle off first
      let responsePromise = authenticatedPage.waitForResponse(
        (response) =>
          response.url().includes('/admin/settings') && response.request().method() === 'PATCH'
      )
      await settingsPage.toggleRegistration()
      await responsePromise

      // Verify disabled
      expect(await settingsPage.isRegistrationEnabled()).toBe(false)

      // Toggle back on
      responsePromise = authenticatedPage.waitForResponse(
        (response) =>
          response.url().includes('/admin/settings') && response.request().method() === 'PATCH'
      )
      await settingsPage.toggleRegistration()
      await responsePromise

      // Verify enabled again
      expect(await settingsPage.isRegistrationEnabled()).toBe(true)
    })
  })
})
