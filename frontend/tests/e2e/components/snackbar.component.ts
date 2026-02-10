import { type Page, type Locator, expect } from '@playwright/test'

/**
 * Component helper for interacting with Vuetify snackbar messages.
 * Used across tests to verify error/warning messages.
 * Note: Success snackbars have been removed from the app - only errors are shown.
 */
export class SnackbarComponent {
  readonly page: Page
  readonly snackbar: Locator

  constructor(page: Page) {
    this.page = page
    // Use the wrapper element which is only visible when snackbar is active
    this.snackbar = page.locator('.v-snackbar__wrapper')
  }

  /**
   * Wait for and verify an error snackbar appears with optional message check.
   */
  async expectError(message?: string) {
    const snackbar = this.snackbar.filter({ has: this.page.locator('.bg-error, .text-error') })
    await expect(snackbar).toBeVisible({ timeout: 5000 })
    if (message) {
      await expect(snackbar).toContainText(message)
    }
  }

  /**
   * Wait for and verify a warning snackbar appears with optional message check.
   */
  async expectWarning(message?: string) {
    const snackbar = this.snackbar.filter({ has: this.page.locator('.bg-warning, .text-warning') })
    await expect(snackbar).toBeVisible({ timeout: 5000 })
    if (message) {
      await expect(snackbar).toContainText(message)
    }
  }

  /**
   * Wait for the snackbar to disappear.
   */
  async waitForDismiss() {
    await expect(this.snackbar).toBeHidden({ timeout: 10000 })
  }
}
