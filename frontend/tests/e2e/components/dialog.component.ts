import { type Page, type Locator, expect } from '@playwright/test'

/**
 * Component helper for interacting with Vuetify dialogs.
 * Used across tests for form dialogs, confirmations, etc.
 */
export class DialogComponent {
  readonly page: Page
  readonly overlay: Locator

  constructor(page: Page) {
    this.page = page
    this.overlay = page.locator('.v-overlay--active .v-dialog')
  }

  /**
   * Get a dialog by its title text.
   */
  getByTitle(title: string): Locator {
    return this.overlay.filter({ hasText: title })
  }

  /**
   * Get the dialog's title element.
   */
  getTitle(): Locator {
    return this.overlay.locator('.v-card-title')
  }

  /**
   * Get the primary action button (usually "Save", "Create", "Confirm", etc.).
   */
  getSubmitButton(): Locator {
    return this.overlay.locator('.v-card-actions .v-btn[color="primary"], .v-card-actions .v-btn[color="error"]').last()
  }

  /**
   * Get the cancel button.
   */
  getCancelButton(): Locator {
    return this.overlay.locator('.v-card-actions .v-btn').filter({ hasText: /cancel/i })
  }

  /**
   * Click the primary submit/confirm button.
   */
  async submit() {
    await this.getSubmitButton().click()
  }

  /**
   * Click the cancel button.
   */
  async cancel() {
    await this.getCancelButton().click()
  }

  /**
   * Assert the dialog is currently open/visible.
   */
  async expectOpen() {
    await expect(this.overlay).toBeVisible({ timeout: 5000 })
  }

  /**
   * Assert the dialog is closed/hidden.
   */
  async expectClosed() {
    await expect(this.overlay).toBeHidden({ timeout: 5000 })
  }

  /**
   * Wait for the dialog to close (useful after submit).
   */
  async waitForClose() {
    await this.expectClosed()
  }

  /**
   * Fill a text field within the dialog by label.
   */
  async fillField(label: string, value: string) {
    const field = this.overlay.locator('.v-text-field, .v-textarea').filter({ hasText: label }).locator('input, textarea')
    await field.fill(value)
  }

  /**
   * Select a value from a dropdown within the dialog.
   */
  async selectOption(label: string, value: string) {
    const select = this.overlay.locator('.v-select').filter({ hasText: label })
    await select.click()
    await this.page.locator('.v-list-item').filter({ hasText: value }).click()
  }
}
