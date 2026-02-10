import { type Page, type Locator, expect } from '@playwright/test'

export class RegisterPage {
  readonly page: Page
  readonly usernameInput: Locator
  readonly passwordInput: Locator
  readonly confirmPasswordInput: Locator
  readonly submitButton: Locator
  readonly loginLink: Locator
  readonly errorMessage: Locator

  constructor(page: Page) {
    this.page = page
    this.usernameInput = page.locator('input[name="username"]')
    this.passwordInput = page.locator('input[name="password"]')
    this.confirmPasswordInput = page.locator('input[name="confirmPassword"]')
    this.submitButton = page.locator('button[type="submit"]')
    this.loginLink = page.getByRole('button', { name: 'Login' })
    this.errorMessage = page.locator('.v-snackbar, .v-alert')
  }

  async goto() {
    await this.page.goto('/register')
    // Wait for registration form to be fully loaded (confirm password is unique to register form)
    await expect(this.confirmPasswordInput).toBeVisible({ timeout: 10000 })
  }

  async register(username: string, password: string, _email?: string) {
    // Ensure we're on the register page
    await expect(this.confirmPasswordInput).toBeVisible({ timeout: 5000 })

    // Fill form fields
    await this.usernameInput.fill(username)
    await this.passwordInput.fill(password)
    await this.confirmPasswordInput.fill(password)

    // Wait for the registration API response
    const responsePromise = this.page.waitForResponse(
      (response) => response.url().includes('/auth/register'),
      { timeout: 30000 }
    )

    // Click submit button
    await this.submitButton.click()

    // Wait for response
    await responsePromise.catch(() => {
      // Response might not come if there's a client-side validation error
    })
  }

  async waitForEnvelopes() {
    // Wait for navigation to complete and envelopes heading to appear
    await this.page.waitForURL('/', { timeout: 30000 })
    await expect(this.page.getByRole('heading', { name: 'Envelopes' })).toBeVisible({ timeout: 15000 })
  }

  async expectError() {
    await this.errorMessage.waitFor({ state: 'visible', timeout: 10000 })
  }
}
