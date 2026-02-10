import { type Page, type Locator, expect } from '@playwright/test'

export class LoginPage {
  readonly page: Page
  readonly usernameInput: Locator
  readonly passwordInput: Locator
  readonly submitButton: Locator
  readonly registerLink: Locator
  readonly errorMessage: Locator

  constructor(page: Page) {
    this.page = page
    this.usernameInput = page.locator('input[name="username"], input[type="text"]').first()
    this.passwordInput = page.locator('input[name="password"], input[type="password"]')
    this.submitButton = page.locator('button[type="submit"]')
    this.registerLink = page.locator('a[href="/register"]')
    this.errorMessage = page.locator('.v-snackbar, .v-alert')
  }

  async goto() {
    await this.page.goto('/login')
  }

  async login(username: string, password: string) {
    await this.usernameInput.fill(username)
    await this.passwordInput.fill(password)
    // Wait for the login API response before continuing
    const responsePromise = this.page.waitForResponse(
      (response) => response.url().includes('/auth/login'),
      { timeout: 15000 }
    )
    await this.submitButton.click()
    await responsePromise.catch(() => {
      // Response might not come if invalid credentials
    })
  }

  async waitForEnvelopes() {
    // Wait for either navigation to / or the heading to appear
    // Using Promise.race to handle cases where URL might already be / but heading not yet visible
    await Promise.race([
      this.page.waitForURL('/', { timeout: 30000 }),
      this.page.getByRole('heading', { name: 'Envelopes' }).waitFor({ state: 'visible', timeout: 30000 }),
    ])
    // Then ensure both conditions are met
    await this.page.waitForURL('/', { timeout: 5000 }).catch(() => {})
    await this.page.getByRole('heading', { name: 'Envelopes' }).waitFor({
      state: 'visible',
      timeout: 15000,
    })
  }

  async expectError() {
    // Wait for error message to appear - could be snackbar or inline alert
    // Use a longer timeout and poll for visibility
    await expect(this.errorMessage).toBeVisible({ timeout: 15000 })
  }
}
