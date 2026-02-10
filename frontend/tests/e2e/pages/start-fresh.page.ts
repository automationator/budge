import { type Page, type Locator, expect } from '@playwright/test'
import { BasePage } from './base.page'

/**
 * Page object for the Start Fresh settings page.
 */
export class StartFreshPage extends BasePage {
  // Header
  readonly pageTitle: Locator
  readonly backButton: Locator

  // Warning Alert
  readonly warningAlert: Locator

  // Category Selection
  readonly deleteAllRadio: Locator
  readonly selectiveRadio: Locator
  readonly transactionsCheckbox: Locator
  readonly recurringCheckbox: Locator
  readonly envelopesCheckbox: Locator
  readonly allocationsCheckbox: Locator
  readonly accountsCheckbox: Locator
  readonly payeesCheckbox: Locator
  readonly locationsCheckbox: Locator

  // Preview Card
  readonly previewCard: Locator

  // Delete Button
  readonly deleteButton: Locator

  // Confirmation Dialog
  readonly confirmDialog: Locator
  readonly passwordInput: Locator
  readonly cancelButton: Locator
  readonly confirmDeleteButton: Locator

  constructor(page: Page) {
    super(page)

    // Header
    this.pageTitle = page.locator('h1').filter({ hasText: 'Start Fresh' })
    this.backButton = page.getByRole('button', { name: 'Back to Settings' })

    // Warning Alert
    this.warningAlert = page.locator('.v-alert').filter({ hasText: 'Danger Zone' })

    // Category Selection
    this.deleteAllRadio = page.locator('.v-radio').filter({ hasText: 'Delete ALL data' })
    this.selectiveRadio = page.locator('.v-radio').filter({ hasText: 'Select specific data types' })
    // Use regex with ^ to match labels that START with the category name
    this.transactionsCheckbox = page.locator('.v-checkbox').filter({ hasText: /^Transactions \(/ })
    this.recurringCheckbox = page.locator('.v-checkbox').filter({ hasText: /^Recurring Transactions$/ })
    this.envelopesCheckbox = page.locator('.v-checkbox').filter({ hasText: /^Envelopes \(/ })
    this.allocationsCheckbox = page
      .locator('.v-checkbox')
      .filter({ hasText: /^Clear envelope allocations/ })
    this.accountsCheckbox = page.locator('.v-checkbox').filter({ hasText: /^Accounts \(/ })
    this.payeesCheckbox = page.locator('.v-checkbox').filter({ hasText: /^Payees \(/ })
    this.locationsCheckbox = page.locator('.v-checkbox').filter({ hasText: /^Locations$/ })

    // Preview Card
    this.previewCard = page.locator('.v-card').filter({ hasText: 'Data to be Deleted' })

    // Delete Button
    this.deleteButton = page.getByRole('button', { name: 'Delete Selected Data' })

    // Confirmation Dialog
    this.confirmDialog = page.locator('.v-dialog').filter({ hasText: 'Confirm Deletion' })
    this.passwordInput = this.confirmDialog.locator('.v-text-field').locator('input')
    this.cancelButton = this.confirmDialog.getByRole('button', { name: 'Cancel' })
    this.confirmDeleteButton = this.confirmDialog.getByRole('button', { name: 'Delete Forever' })
  }

  async goto() {
    await this.page.goto('/settings/start-fresh')
    await this.waitForPageLoad()
  }

  /**
   * Go back to settings page.
   */
  async goBackToSettings() {
    await this.backButton.click()
    await expect(this.page).toHaveURL('/settings')
  }

  /**
   * Select delete all mode.
   */
  async selectDeleteAll() {
    // Click the label text which triggers the radio selection
    await this.page.getByText('Delete ALL data').click()
    // Wait for the radio to be checked
    await expect(this.deleteAllRadio.getByRole('radio')).toBeChecked()
  }

  /**
   * Select selective deletion mode.
   */
  async selectSelective() {
    // Click the label text which triggers the radio selection
    await this.page.getByText('Select specific data types').click()
    // Wait for the radio to be checked
    await expect(this.selectiveRadio.getByRole('radio')).toBeChecked()
  }

  /**
   * Toggle a specific category checkbox.
   */
  async toggleCategory(
    category:
      | 'transactions'
      | 'recurring'
      | 'envelopes'
      | 'allocations'
      | 'accounts'
      | 'payees'
      | 'locations'
  ) {
    const checkboxMap = {
      transactions: this.transactionsCheckbox,
      recurring: this.recurringCheckbox,
      envelopes: this.envelopesCheckbox,
      allocations: this.allocationsCheckbox,
      accounts: this.accountsCheckbox,
      payees: this.payeesCheckbox,
      locations: this.locationsCheckbox,
    }
    await checkboxMap[category].click()
  }

  /**
   * Open the confirmation dialog.
   */
  async openConfirmDialog() {
    await this.deleteButton.click()
    await expect(this.confirmDialog).toBeVisible()
  }

  /**
   * Enter password and confirm deletion.
   */
  async confirmDeletion(password: string) {
    await this.passwordInput.fill(password)
    await this.confirmDeleteButton.click()
  }

  /**
   * Cancel the confirmation dialog.
   */
  async cancelDeletion() {
    await this.cancelButton.click()
    await expect(this.confirmDialog).toBeHidden()
  }

  /**
   * Perform full delete flow.
   */
  async deleteData(password: string) {
    await this.openConfirmDialog()
    await this.confirmDeletion(password)
  }

  /**
   * Assert page title is visible.
   */
  async expectPageTitle() {
    await expect(this.pageTitle).toBeVisible()
  }

  /**
   * Assert warning alert is visible.
   */
  async expectWarningVisible() {
    await expect(this.warningAlert).toBeVisible()
  }

  /**
   * Assert preview card is visible (waits for API to load).
   */
  async expectPreviewVisible() {
    // The preview loads from API, so give it time to appear
    await expect(this.previewCard).toBeVisible({ timeout: 10000 })
  }

  /**
   * Assert preview card is not visible (no data to delete).
   */
  async expectPreviewHidden() {
    await expect(this.previewCard).toBeHidden()
  }
}
