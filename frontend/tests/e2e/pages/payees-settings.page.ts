import { type Page, type Locator, expect } from '@playwright/test'
import { BasePage } from './base.page'

/**
 * Page object for the Manage Payees settings view.
 */
export class PayeesSettingsPage extends BasePage {
  // Header
  readonly backButton: Locator
  readonly pageTitle: Locator
  readonly addPayeeButton: Locator

  // Payees List
  readonly payeesCard: Locator
  readonly payeesList: Locator

  // Create/Edit Dialog
  readonly editDialog: Locator
  readonly nameInput: Locator
  readonly iconInput: Locator
  readonly descriptionInput: Locator
  readonly defaultEnvelopeSelect: Locator
  readonly saveButton: Locator
  readonly cancelButton: Locator

  // Delete Dialog
  readonly deleteDialog: Locator
  readonly confirmDeleteButton: Locator
  readonly cancelDeleteButton: Locator

  constructor(page: Page) {
    super(page)

    // Header
    this.backButton = page.getByRole('button', { name: 'Back to Settings' })
    this.pageTitle = page.locator('h1').filter({ hasText: 'Manage Payees' })
    this.addPayeeButton = page.getByRole('button', { name: 'Add Payee' })

    // Payees List
    this.payeesCard = page.locator('.v-card').filter({ has: page.locator('.v-list') })
    this.payeesList = this.payeesCard.locator('.v-list')

    // Create/Edit Dialog (title changes based on mode)
    this.editDialog = page.locator('.v-dialog').filter({
      has: page.locator('.v-card-title').filter({ hasText: /Add Payee|Edit Payee/ }),
    })
    this.nameInput = this.editDialog
      .locator('.v-text-field')
      .filter({ hasText: 'Name' })
      .locator('input')
    this.iconInput = this.editDialog
      .locator('.v-text-field')
      .filter({ hasText: 'Icon' })
      .locator('input')
    this.descriptionInput = this.editDialog.locator('.v-textarea').locator('textarea')
    this.defaultEnvelopeSelect = this.editDialog.locator('.v-autocomplete').filter({ hasText: 'Default Envelope' })
    this.saveButton = this.editDialog.getByRole('button', { name: /Save|Create/ })
    this.cancelButton = this.editDialog.getByRole('button', { name: 'Cancel' })

    // Delete Dialog
    this.deleteDialog = page.locator('.v-dialog').filter({ hasText: 'Delete Payee' })
    this.confirmDeleteButton = this.deleteDialog.getByRole('button', { name: 'Delete' })
    this.cancelDeleteButton = this.deleteDialog.getByRole('button', { name: 'Cancel' })
  }

  async goto() {
    await this.page.goto('/settings/payees')
    await this.waitForPageLoad()
  }

  /**
   * Get a payee list item by name.
   */
  getPayeeItem(name: string): Locator {
    return this.payeesList.locator('.v-list-item').filter({ hasText: name })
  }

  /**
   * Open the add payee dialog.
   */
  async openAddDialog() {
    await this.addPayeeButton.click()
    await expect(this.editDialog).toBeVisible()
  }

  /**
   * Open the edit dialog for a payee.
   */
  async openEditDialog(payeeName: string) {
    await this.getPayeeItem(payeeName).click()
    await expect(this.editDialog).toBeVisible()
  }

  /**
   * Create a new payee.
   */
  async createPayee(data: {
    name: string
    icon?: string
    description?: string
    defaultEnvelope?: string
  }) {
    await this.openAddDialog()
    await this.fillPayeeForm(data)
    await this.saveButton.click()
    await expect(this.editDialog).toBeHidden({ timeout: 10000 })
  }

  /**
   * Edit an existing payee.
   */
  async editPayee(
    payeeName: string,
    data: {
      name?: string
      icon?: string
      description?: string
      defaultEnvelope?: string
    }
  ) {
    await this.openEditDialog(payeeName)
    await this.fillPayeeForm(data)
    await this.saveButton.click()
    await expect(this.editDialog).toBeHidden({ timeout: 10000 })
  }

  /**
   * Fill the payee form fields.
   */
  private async fillPayeeForm(data: {
    name?: string
    icon?: string
    description?: string
    defaultEnvelope?: string
  }) {
    if (data.name !== undefined) {
      await this.nameInput.clear()
      await this.nameInput.fill(data.name)
    }
    if (data.icon !== undefined) {
      await this.iconInput.clear()
      await this.iconInput.fill(data.icon)
    }
    if (data.description !== undefined) {
      await this.descriptionInput.clear()
      await this.descriptionInput.fill(data.description)
    }
    if (data.defaultEnvelope !== undefined) {
      await this.selectDefaultEnvelope(data.defaultEnvelope)
    }
  }

  /**
   * Select a default envelope from the v-select.
   */
  async selectDefaultEnvelope(envelopeName: string) {
    // Click on the select to open the dropdown
    await this.defaultEnvelopeSelect.click()
    // Wait for the menu to appear
    const menu = this.page.locator('.v-overlay--active .v-list')
    await menu.waitFor({ state: 'visible', timeout: 5000 })
    // Find and click the option
    const option = menu.locator('.v-list-item').filter({ hasText: envelopeName })
    await option.waitFor({ state: 'visible', timeout: 5000 })
    await option.click()
    // Wait for menu to close
    await menu.waitFor({ state: 'hidden', timeout: 5000 })
  }

  /**
   * Clear the default envelope selection.
   */
  async clearDefaultEnvelope() {
    const clearButton = this.defaultEnvelopeSelect.locator('.v-field__clearable button')
    if (await clearButton.isVisible()) {
      await clearButton.click()
    }
  }

  /**
   * Click the delete button for a payee.
   */
  async clickDeleteButton(payeeName: string) {
    const item = this.getPayeeItem(payeeName)
    await item.locator('button').filter({ has: this.page.locator('[class*="mdi-delete"]') }).click()
    await expect(this.deleteDialog).toBeVisible()
  }

  /**
   * Delete a payee.
   */
  async deletePayee(payeeName: string) {
    await this.clickDeleteButton(payeeName)
    await this.confirmDeleteButton.click()
    await expect(this.deleteDialog).toBeHidden({ timeout: 10000 })
  }

  /**
   * Cancel delete dialog.
   */
  async cancelDelete() {
    await this.cancelDeleteButton.click()
    await expect(this.deleteDialog).toBeHidden()
  }

  /**
   * Go back to settings.
   */
  async goBackToSettings() {
    await this.backButton.click()
    await expect(this.page).toHaveURL('/settings')
  }

  /**
   * Get payee count.
   */
  async getPayeeCount(): Promise<number> {
    const items = this.payeesList.locator('.v-list-item')
    const count = await items.count()
    // Check if empty state is showing
    const emptyText = await items.first().textContent()
    if (emptyText?.includes('No payees yet')) {
      return 0
    }
    return count
  }

  /**
   * Check if a payee exists.
   */
  async payeeExists(name: string): Promise<boolean> {
    const item = this.getPayeeItem(name)
    return await item.isVisible({ timeout: 2000 }).catch(() => false)
  }

  /**
   * Get the default envelope shown for a payee.
   */
  async getPayeeDefaultEnvelope(payeeName: string): Promise<string | null> {
    const item = this.getPayeeItem(payeeName)
    await expect(item).toBeVisible({ timeout: 5000 })
    // Get all text content from the item
    const allText = await item.textContent()
    if (!allText) return null
    // Look for "Default: <envelope name>" pattern
    const match = allText.match(/Default:\s*(.+?)(?:$|󰆴)/)
    if (match && match[1]) {
      return match[1].trim()
    }
    return null
  }

  /**
   * Assert page title is visible.
   */
  async expectPageTitle() {
    await expect(this.pageTitle).toBeVisible()
  }

  /**
   * Assert payees list is visible.
   */
  async expectPayeesListVisible() {
    await expect(this.payeesCard).toBeVisible()
  }

  /**
   * Assert empty state is shown.
   */
  async expectEmptyState() {
    const emptyMessage = this.payeesList.locator('.v-list-item').filter({ hasText: 'No payees yet' })
    await expect(emptyMessage).toBeVisible()
  }
}
