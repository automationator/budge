import { type Page, type Locator, expect } from '@playwright/test'

/**
 * Page object for the Budget Settings page.
 * Handles budget name editing, member management, and budget deletion.
 */
export class BudgetSettingsPage {
  readonly page: Page

  // Page title
  readonly pageTitle: Locator
  readonly backButton: Locator

  // Budget name section
  readonly budgetNameCard: Locator
  readonly budgetNameDisplay: Locator
  readonly editNameButton: Locator
  readonly nameInput: Locator
  readonly saveNameButton: Locator
  readonly cancelNameButton: Locator

  // Budget members section
  readonly membersCard: Locator
  readonly addMemberButton: Locator
  readonly membersList: Locator

  // Add member dialog
  readonly addMemberDialog: Locator
  readonly usernameInput: Locator
  readonly roleSelect: Locator
  readonly addMemberConfirmButton: Locator
  readonly addMemberCancelButton: Locator

  // Danger zone (delete budget)
  readonly dangerZoneCard: Locator
  readonly deleteBudgetButton: Locator

  // Delete budget dialog
  readonly deleteDialog: Locator
  readonly deletePasswordInput: Locator
  readonly deleteConfirmButton: Locator
  readonly deleteCancelButton: Locator

  // Data management section
  readonly dataManagementCard: Locator
  readonly exportButton: Locator
  readonly importButton: Locator

  // Import dialog
  readonly importDialog: Locator
  readonly importFileInput: Locator
  readonly importPreview: Locator
  readonly importMergeRadio: Locator
  readonly importReplaceRadio: Locator
  readonly importPasswordInput: Locator
  readonly importConfirmButton: Locator
  readonly importCancelButton: Locator

  // Import result dialog
  readonly importResultDialog: Locator
  readonly importResultCloseButton: Locator

  constructor(page: Page) {
    this.page = page

    // Page elements
    this.pageTitle = page.locator('h1', { hasText: 'Budget Settings' })
    this.backButton = page.locator('button', { hasText: 'Back' })

    // Budget name section
    this.budgetNameCard = page.locator('.v-card', { hasText: 'Budget Name' })
    this.budgetNameDisplay = this.budgetNameCard.locator('.text-h6')
    this.editNameButton = this.budgetNameCard.locator('button:has(.mdi-pencil)')
    this.nameInput = this.budgetNameCard.locator('input')
    this.saveNameButton = this.budgetNameCard.getByRole('button', { name: 'Save' })
    this.cancelNameButton = this.budgetNameCard.getByRole('button', { name: 'Cancel' })

    // Budget members section
    this.membersCard = page.locator('.v-card', { hasText: 'Budget Members' })
    this.addMemberButton = this.membersCard.getByRole('button', { name: 'Add Member' })
    this.membersList = this.membersCard.locator('.v-list')

    // Add member dialog
    this.addMemberDialog = page.locator('.v-dialog .v-card', { hasText: 'Add Budget Member' })
    this.usernameInput = this.addMemberDialog.locator('input').first()
    this.roleSelect = this.addMemberDialog.locator('.v-select')
    this.addMemberConfirmButton = this.addMemberDialog.getByRole('button', { name: 'Add Member' })
    this.addMemberCancelButton = this.addMemberDialog.getByRole('button', { name: 'Cancel' })

    // Danger zone
    this.dangerZoneCard = page.locator('.v-card', { hasText: 'Danger Zone' })
    this.deleteBudgetButton = this.dangerZoneCard.getByRole('button', { name: 'Delete Budget' })

    // Delete dialog
    this.deleteDialog = page.locator('.v-dialog .v-card', { hasText: 'Delete Budget' })
    this.deletePasswordInput = this.deleteDialog.locator('input[type="password"]')
    this.deleteConfirmButton = this.deleteDialog.getByRole('button', { name: 'Delete Budget' })
    this.deleteCancelButton = this.deleteDialog.getByRole('button', { name: 'Cancel' })

    // Data management section
    this.dataManagementCard = page.locator('.v-card', { hasText: 'Data Management' })
    this.exportButton = page.locator('[data-testid="export-button"]')
    this.importButton = page.locator('[data-testid="import-button"]')

    // Import dialog
    this.importDialog = page.locator('.v-dialog .v-card', { hasText: 'Import Budget Data' })
    this.importFileInput = page.locator('[data-testid="import-file-input"]')
    this.importPreview = page.locator('[data-testid="import-preview"]')
    this.importMergeRadio = page.locator('[data-testid="import-merge-radio"]')
    this.importReplaceRadio = page.locator('[data-testid="import-replace-radio"]')
    this.importPasswordInput = page.locator('[data-testid="import-password-input"] input')
    this.importConfirmButton = page.locator('[data-testid="import-confirm-button"]')
    this.importCancelButton = page.locator('[data-testid="import-cancel-button"]')

    // Import result dialog
    this.importResultDialog = page.locator('.v-dialog .v-card', { hasText: 'Import Complete' })
    this.importResultCloseButton = page.locator('[data-testid="import-result-close-button"]')
  }

  /**
   * Navigate to the Budget Settings page.
   */
  async goto() {
    await this.page.goto('/settings/budget-settings')
    await this.waitForPageLoad()
  }

  /**
   * Wait for the page to fully load.
   */
  async waitForPageLoad() {
    await expect(this.pageTitle).toBeVisible({ timeout: 10000 })
  }

  /**
   * Get the current budget name displayed.
   */
  async getBudgetName(): Promise<string> {
    return (await this.budgetNameDisplay.textContent()) ?? ''
  }

  /**
   * Start editing the budget name.
   */
  async startEditingName() {
    await this.editNameButton.click()
    await expect(this.nameInput).toBeVisible()
  }

  /**
   * Rename the budget.
   */
  async renameBudget(newName: string) {
    await this.startEditingName()
    await this.nameInput.fill(newName)
    await this.saveNameButton.click()
    await expect(this.nameInput).not.toBeVisible()
  }

  /**
   * Cancel editing the budget name.
   */
  async cancelEditingName() {
    await this.cancelNameButton.click()
    await expect(this.nameInput).not.toBeVisible()
  }

  /**
   * Get the list of member usernames.
   */
  async getMemberUsernames(): Promise<string[]> {
    const memberItems = this.membersList.locator('.v-list-item')
    const count = await memberItems.count()
    const usernames: string[] = []
    for (let i = 0; i < count; i++) {
      const subtitle = await memberItems.nth(i).locator('.v-list-item-subtitle').textContent()
      if (subtitle) {
        // Extract username from "@username · email" format
        const match = subtitle.match(/@(\w+)/)
        if (match) usernames.push(match[1])
      }
    }
    return usernames
  }

  /**
   * Check if the add member button is visible.
   */
  async canManageMembers(): Promise<boolean> {
    return this.addMemberButton.isVisible()
  }

  /**
   * Check if the delete budget section is visible.
   */
  async canDeleteBudget(): Promise<boolean> {
    return this.dangerZoneCard.isVisible()
  }

  /**
   * Open the delete budget dialog.
   */
  async openDeleteDialog() {
    await this.deleteBudgetButton.click()
    await expect(this.deleteDialog).toBeVisible()
  }

  /**
   * Delete the budget with password confirmation.
   */
  async deleteBudget(password: string) {
    await this.openDeleteDialog()
    await this.deletePasswordInput.fill(password)
    await this.deleteConfirmButton.click()
  }

  /**
   * Cancel the delete budget dialog.
   */
  async cancelDelete() {
    await this.deleteCancelButton.click()
    await expect(this.deleteDialog).not.toBeVisible()
  }

  // Data Management methods

  /**
   * Check if the data management section is visible (owner only).
   */
  async canManageData(): Promise<boolean> {
    return this.dataManagementCard.isVisible()
  }

  /**
   * Click the export button and wait for download.
   * Returns the downloaded file path.
   */
  async exportBudget(): Promise<string> {
    const downloadPromise = this.page.waitForEvent('download')
    await this.exportButton.click()
    const download = await downloadPromise
    const path = await download.path()
    return path ?? ''
  }

  /**
   * Open the import dialog.
   */
  async openImportDialog() {
    await this.importButton.click()
    await expect(this.importDialog).toBeVisible()
  }

  /**
   * Select a file for import using the file input.
   */
  async selectImportFile(filePath: string) {
    // Get the actual input element inside v-file-input
    const fileInput = this.importFileInput.locator('input[type="file"]')
    await fileInput.setInputFiles(filePath)
  }

  /**
   * Select merge mode for import.
   */
  async selectMergeMode() {
    await this.importMergeRadio.click()
  }

  /**
   * Select replace mode for import.
   */
  async selectReplaceMode() {
    await this.importReplaceRadio.click()
  }

  /**
   * Wait for import preview to appear.
   */
  async waitForImportPreview() {
    await expect(this.importPreview).toBeVisible({ timeout: 5000 })
  }

  /**
   * Confirm import with password.
   */
  async confirmImport(password: string) {
    await this.importPasswordInput.fill(password)
    await this.importConfirmButton.click()
  }

  /**
   * Wait for import result dialog.
   */
  async waitForImportResult() {
    await expect(this.importResultDialog).toBeVisible({ timeout: 30000 })
  }

  /**
   * Close the import result dialog.
   */
  async closeImportResult() {
    await this.importResultCloseButton.click()
    await expect(this.importResultDialog).toBeHidden()
  }

  /**
   * Cancel the import dialog.
   */
  async cancelImport() {
    await this.importCancelButton.click()
    await expect(this.importDialog).toBeHidden()
  }
}
