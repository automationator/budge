import { type Page, type Locator, expect } from '@playwright/test'
import { BasePage } from './base.page'

/**
 * Page object for the Transaction form dialog (create/edit).
 * This dialog is used for creating and editing transactions throughout the app.
 */
export class TransactionFormPage extends BasePage {
  // Dialog container
  readonly dialog: Locator
  readonly dialogTitle: Locator
  readonly clearedButton: Locator
  readonly closeButton: Locator

  // Transaction type tabs
  readonly transactionTab: Locator
  readonly transferTab: Locator

  // Standard transaction form elements
  readonly accountSelect: Locator
  readonly payeeAutocomplete: Locator
  readonly amountSignToggle: Locator
  readonly amountInput: Locator

  // Transfer form elements
  readonly fromAccountSelect: Locator
  readonly toAccountSelect: Locator
  readonly transferEnvelopeSelect: Locator

  // Common form elements
  readonly dateInput: Locator
  readonly memoInput: Locator
  readonly locationAutocomplete: Locator

  // Envelope selection elements
  readonly envelopeSection: Locator
  readonly envelopeSelect: Locator
  readonly splitEnvelopesButton: Locator
  readonly useSingleEnvelopeButton: Locator
  readonly addAllocationButton: Locator
  readonly allocationRows: Locator

  // Action buttons
  readonly createButton: Locator
  readonly saveButton: Locator
  readonly saveAndAddAnotherButton: Locator
  readonly cancelButton: Locator
  readonly deleteButton: Locator

  // Delete confirmation dialog
  readonly deleteDialog: Locator
  readonly deleteConfirmButton: Locator
  readonly deleteCancelButton: Locator

  // Income allocation mode (for new income in budget accounts)
  readonly incomeAllocationModeGroup: Locator
  readonly autoDistributeRadio: Locator
  readonly envelopeModeRadio: Locator
  readonly noneModeRadio: Locator

  // Allocation preview dialog
  readonly previewDialog: Locator
  readonly previewConfirmButton: Locator
  readonly previewCancelButton: Locator

  constructor(page: Page) {
    super(page)

    // Dialog container - target the main transaction form dialog (excludes delete confirmation)
    // The main form dialog has "New Transaction", "Edit Transaction", "New Transfer", etc.
    this.dialog = page.locator('.v-dialog').filter({
      has: page.locator('.v-card-title', { hasText: /^(New|Edit) (Transaction|Transfer)$/ })
    })
    this.dialogTitle = this.dialog.locator('.v-card-title').first()
    // Cleared button is in header (first button), close button is second
    this.clearedButton = this.dialog.locator('[data-testid="cleared-toggle"]')
    this.closeButton = this.dialog.locator('.v-card-title .v-btn[icon="mdi-close"]')

    // Transaction type tabs
    this.transactionTab = this.dialog.getByRole('tab', { name: 'Transaction' })
    this.transferTab = this.dialog.getByRole('tab', { name: 'Transfer' })

    // Standard transaction form - match v-select with label exactly "Account" (not "From Account"/"To Account")
    this.accountSelect = this.dialog.locator('.v-select:has(.v-label:text-is("Account"))')
    this.payeeAutocomplete = this.dialog.locator('.v-autocomplete').filter({ hasText: 'Payee' })
    // Amount sign toggle is a clickable prefix in the amount field
    this.amountSignToggle = this.dialog.locator('[data-testid="amount-sign-toggle"]')
    this.amountInput = this.dialog.locator('input[inputmode="numeric"]').first()

    // Transfer form
    this.fromAccountSelect = this.dialog.locator('.v-select').filter({ hasText: 'From Account' })
    this.toAccountSelect = this.dialog.locator('.v-select').filter({ hasText: 'To Account' })
    // Transfer envelope select appears for budget -> tracking transfers
    this.transferEnvelopeSelect = this.dialog.locator('.v-autocomplete').filter({
      hasText: 'Which envelope is this money coming from?',
    })

    // Common form elements
    this.dateInput = this.dialog.locator('input[type="date"]')
    // Memo field - use "Memo (optional)" to avoid matching account names containing "Memo"
    this.memoInput = this.dialog.locator('.v-text-field').filter({ hasText: 'Memo (optional)' }).locator('textarea, input').first()
    this.locationAutocomplete = this.dialog.locator('.v-autocomplete').filter({ hasText: 'Location (optional)' })

    // Envelope selection elements - use more specific locator to avoid matching other selects
    this.envelopeSection = this.dialog.locator('.text-subtitle-1').filter({ hasText: 'Envelope' }).locator('..')
    this.envelopeSelect = this.dialog.locator('.v-autocomplete:has(.v-label:text("Envelope"):not(:text("Link to Envelope")))').first()
    this.splitEnvelopesButton = this.dialog.getByRole('button', { name: 'Split across envelopes' })
    this.useSingleEnvelopeButton = this.dialog.getByRole('button', { name: 'Use single envelope' })
    this.addAllocationButton = this.dialog.getByRole('button', { name: 'Add Allocation' })
    this.allocationRows = this.dialog.locator('.d-flex.gap-2.mb-2.align-center')

    // Action buttons
    this.createButton = this.dialog.getByRole('button', { name: 'Create' })
    this.saveButton = this.dialog.getByRole('button', { name: 'Save', exact: true })
    this.saveAndAddAnotherButton = this.dialog.getByRole('button', { name: 'Save & Add Another' })
    this.cancelButton = this.dialog.getByRole('button', { name: 'Cancel' })
    this.deleteButton = this.dialog.getByRole('button', { name: 'Delete' })

    // Delete dialog
    this.deleteDialog = page.locator('.v-dialog').filter({ hasText: 'Delete Transaction' })
    this.deleteConfirmButton = this.deleteDialog.getByRole('button', { name: 'Delete' })
    this.deleteCancelButton = this.deleteDialog.getByRole('button', { name: 'Cancel' })

    // Income allocation mode radio group (for new income in budget accounts)
    this.incomeAllocationModeGroup = this.dialog.locator('.v-radio-group')
    this.autoDistributeRadio = this.dialog.getByRole('radio', { name: 'Auto-distribute' })
    this.envelopeModeRadio = this.dialog.getByRole('radio', { name: 'Envelope' })
    this.noneModeRadio = this.dialog.getByRole('radio', { name: 'None' })

    // Allocation preview dialog
    this.previewDialog = page.locator('.v-dialog').filter({ hasText: 'Allocation Preview' })
    this.previewConfirmButton = this.previewDialog.getByRole('button', { name: 'Confirm & Save' })
    this.previewCancelButton = this.previewDialog.getByRole('button', { name: 'Cancel' })
  }

  /**
   * Wait for the dialog to be visible.
   */
  async waitForDialog() {
    await expect(this.dialog).toBeVisible({ timeout: 5000 })
  }

  /**
   * Wait for the dialog to be hidden.
   */
  async waitForDialogHidden() {
    await expect(this.dialog).toBeHidden({ timeout: 5000 })
  }

  /**
   * Close the dialog by clicking the close button.
   */
  async closeDialog() {
    await this.closeButton.click()
    await this.waitForDialogHidden()
  }

  /**
   * Switch to transfer mode.
   */
  async switchToTransfer() {
    // Click the dialog title to close any open dropdowns (without using Escape which closes the dialog)
    await this.dialogTitle.click()
    // Wait for any active dropdown overlay to close
    await this.page.locator('.v-overlay--active .v-list').waitFor({ state: 'hidden', timeout: 5000 }).catch(() => {})
    // Use JavaScript click to bypass pointer event interception from overlapping elements
    await this.transferTab.evaluate((el) => (el as HTMLElement).click())
    await expect(this.fromAccountSelect).toBeVisible()
  }

  /**
   * Switch to standard transaction mode.
   */
  async switchToTransaction() {
    // Click the dialog title to close any open dropdowns
    await this.dialogTitle.click()
    // Wait for any active dropdown overlay to close
    await this.page.locator('.v-overlay--active .v-list').waitFor({ state: 'hidden', timeout: 5000 }).catch(() => {})
    // Use JavaScript click to bypass pointer event interception from overlapping elements
    await this.transactionTab.evaluate((el) => (el as HTMLElement).click())
    await expect(this.accountSelect).toBeVisible()
  }

  /**
   * Select an account.
   */
  async selectAccount(accountName: string) {
    await this.accountSelect.click()
    const menu = this.page.locator('.v-overlay--active .v-list')
    await menu.waitFor({ state: 'visible', timeout: 5000 })
    // Use exact matching to avoid partial matches (e.g., "Checking" matching "Budget Checking")
    const items = menu.locator('.v-list-item')
    const count = await items.count()
    for (let i = 0; i < count; i++) {
      const item = items.nth(i)
      const text = await item.textContent()
      if (text?.trim() === accountName) {
        await item.click()
        return
      }
    }
    // Fallback to hasText if exact match not found
    const targetItem = menu.locator('.v-list-item').filter({ hasText: accountName }).first()
    await targetItem.click()
  }

  /**
   * Get the currently selected account name.
   * Returns null if no account is selected.
   */
  async getSelectedAccount(): Promise<string | null> {
    const selectedText = await this.accountSelect
      .locator('.v-select__selection-text')
      .textContent()
      .catch(() => null)
    return selectedText?.trim() || null
  }

  /**
   * Select a payee from existing options.
   */
  async selectPayee(payeeName: string) {
    await this.payeeAutocomplete.locator('input').fill(payeeName)
    // Wait for the autocomplete dropdown to appear and select the item
    // Use the active overlay list to target the visible dropdown
    const dropdown = this.page.locator('.v-overlay--active .v-list')
    await dropdown.waitFor({ state: 'visible', timeout: 10000 })
    const targetItem = dropdown.locator('.v-list-item').filter({ hasText: payeeName }).first()
    await targetItem.click()
  }

  /**
   * Create a new payee (inline, no dialog).
   */
  async createNewPayee(payeeName: string) {
    await this.payeeAutocomplete.locator('input').fill(payeeName)
    // Wait for the autocomplete dropdown to appear
    const dropdown = this.page.locator('.v-overlay--active .v-list')
    await dropdown.waitFor({ state: 'visible', timeout: 10000 })
    // Click the "Create ..." option - payee is created immediately
    await dropdown.locator('.v-list-item').filter({ hasText: `Create "${payeeName}"` }).click()
    // Wait for the payee to be selected (autocomplete dropdown closes)
    await expect(this.payeeAutocomplete.locator('.v-field__input')).toContainText(payeeName, { timeout: 5000 })
  }

  /**
   * Set as expense.
   * Clicks the sign toggle if it's currently showing income (+$).
   */
  async setAsExpense() {
    const text = await this.amountSignToggle.textContent()
    if (text?.includes('+')) {
      await this.amountSignToggle.click()
    }
  }

  /**
   * Set as income.
   * Clicks the sign toggle if it's currently showing expense (-$).
   */
  async setAsIncome() {
    const text = await this.amountSignToggle.textContent()
    if (text?.includes('−') || text?.includes('-')) {
      await this.amountSignToggle.click()
    }
  }

  /**
   * Fill the amount.
   */
  async fillAmount(amount: string) {
    await this.amountInput.fill(amount)
  }

  /**
   * Fill the date.
   */
  async fillDate(date: string) {
    await this.dateInput.fill(date)
  }

  /**
   * Toggle cleared status.
   */
  async toggleCleared() {
    await this.clearedButton.click()
  }

  /**
   * Fill the memo field.
   */
  async fillMemo(memo: string) {
    // Find the Memo input/textarea specifically - use "Memo (optional)" label to avoid
    // matching account selects that might contain "Memo" in the account name
    const memoContainer = this.dialog.locator('.v-text-field').filter({ hasText: 'Memo (optional)' })
    await memoContainer.waitFor({ state: 'visible', timeout: 5000 })
    const memoField = memoContainer.locator('textarea, input').first()
    await memoField.fill(memo)
  }

  /**
   * Select a location from the dropdown (creates new if doesn't exist).
   */
  async selectLocation(locationName: string) {
    const locationInput = this.locationAutocomplete.locator('input')
    await locationInput.click()
    await locationInput.fill(locationName)

    // Wait for autocomplete menu to appear
    const menu = this.page.locator('.v-overlay--active .v-list')
    await menu.waitFor({ state: 'visible', timeout: 5000 })

    // Look for create option or existing location
    const createOption = menu.locator('.v-list-item').filter({ hasText: `Create "${locationName}"` }).first()
    const existingLocation = menu.locator('.v-list-item').filter({ hasText: locationName }).first()

    if (await createOption.isVisible({ timeout: 1000 }).catch(() => false)) {
      // Create new location
      await createOption.click()
      // Wait for the location to be selected
      await expect(this.locationAutocomplete.locator('.v-field__input')).toContainText(locationName, { timeout: 5000 })
    } else if (await existingLocation.isVisible({ timeout: 1000 }).catch(() => false)) {
      await existingLocation.click()
      // Wait for menu to close
      await menu.waitFor({ state: 'hidden', timeout: 5000 }).catch(() => {})
    }
  }

  /**
   * Get the currently selected location name.
   * Returns null if no location is selected.
   */
  async getSelectedLocation(): Promise<string | null> {
    const selectedText = await this.locationAutocomplete
      .locator('.v-field__input')
      .textContent()
      .catch(() => null)
    return selectedText?.trim() || null
  }

  /**
   * Check if envelope selector is visible (for budget accounts).
   */
  async isEnvelopeSelectorVisible(): Promise<boolean> {
    // Check if the "Split across envelopes" button is visible - this is a unique indicator
    // of the envelope section being visible
    return await this.splitEnvelopesButton.isVisible({ timeout: 2000 }).catch(() => false)
  }

  /**
   * Get the currently selected envelope name.
   * Returns null if no envelope is selected or if the envelope selector isn't visible.
   */
  async getSelectedEnvelope(): Promise<string | null> {
    if (!(await this.isEnvelopeSelectorVisible())) {
      return null
    }

    // v-autocomplete renders selected value in .v-field__input
    const selectedText = await this.envelopeSelect
      .locator('.v-field__input')
      .textContent()
      .catch(() => null)

    // Strip any placeholder text - if it only contains whitespace or "Envelope", nothing is selected
    const trimmed = selectedText?.trim() || null
    if (!trimmed || trimmed === 'Envelope') return null
    return trimmed
  }

  /**
   * Wait for an envelope to be auto-filled (selected).
   * Polls until an envelope value appears or timeout is reached.
   */
  async waitForEnvelopeAutoFill(expectedEnvelope: string, timeout = 5000): Promise<void> {
    await expect(
      this.envelopeSelect.locator('.v-field__input')
    ).toContainText(expectedEnvelope, { timeout })
  }

  /**
   * Select an envelope from the dropdown.
   */
  async selectEnvelope(envelopeName: string) {
    await this.envelopeSelect.click()
    const menu = this.page.locator('.v-overlay--active .v-list')
    await menu.waitFor({ state: 'visible', timeout: 5000 })
    // Wait specifically for the target item (not just any item)
    const targetItem = menu.locator('.v-list-item').filter({ hasText: envelopeName }).first()
    await targetItem.waitFor({ state: 'visible', timeout: 10000 })
    await targetItem.click()
    await menu.waitFor({ state: 'hidden', timeout: 5000 }).catch(() => {})
  }

  /**
   * Enable split mode for multiple envelopes.
   */
  async enableSplitMode() {
    await this.splitEnvelopesButton.click()
    await expect(this.addAllocationButton).toBeVisible()
  }

  /**
   * Disable split mode and return to single envelope.
   */
  async disableSplitMode() {
    await this.useSingleEnvelopeButton.click()
    await expect(this.envelopeSelect).toBeVisible()
  }

  /**
   * Add an allocation in split mode.
   */
  async addAllocation(envelopeName: string, amount: string) {
    await this.addAllocationButton.click()
    const rows = this.allocationRows
    const lastRow = rows.last()

    // Select envelope
    await lastRow.locator('.v-select').click()
    const menu = this.page.locator('.v-overlay--active .v-list')
    await menu.waitFor({ state: 'visible', timeout: 5000 })
    // Wait specifically for the target item (not just any item)
    const targetItem = menu.locator('.v-list-item').filter({ hasText: envelopeName }).first()
    await targetItem.waitFor({ state: 'visible', timeout: 10000 })
    await targetItem.click()
    await menu.waitFor({ state: 'hidden', timeout: 5000 }).catch(() => {})

    // Fill amount
    await lastRow.locator('input[inputmode="numeric"]').fill(amount)
  }

  /**
   * Select the source account for a transfer.
   */
  async selectFromAccount(accountName: string) {
    await this.fromAccountSelect.click()
    // Wait for the dropdown menu to appear
    const menu = this.page.locator('.v-overlay--active .v-list')
    await menu.waitFor({ state: 'visible', timeout: 5000 })
    // Find the item in the menu, not the sidebar
    const targetItem = menu.locator('.v-list-item').filter({ hasText: accountName }).first()
    await targetItem.waitFor({ state: 'visible', timeout: 10000 })
    await targetItem.click()
  }

  /**
   * Select the destination account for a transfer.
   */
  async selectToAccount(accountName: string) {
    await this.toAccountSelect.click()
    // Wait for the dropdown menu to appear
    const menu = this.page.locator('.v-overlay--active .v-list')
    await menu.waitFor({ state: 'visible', timeout: 5000 })
    // Find the item in the menu, not the sidebar
    const targetItem = menu.locator('.v-list-item').filter({ hasText: accountName }).first()
    await targetItem.waitFor({ state: 'visible', timeout: 10000 })
    await targetItem.click()
  }

  /**
   * Create a standard transaction.
   */
  async createTransaction(data: {
    account?: string
    payee: string
    amount: string
    isExpense?: boolean
    date?: string
    memo?: string
    location?: string
    cleared?: boolean
    envelope?: string
  }) {
    if (data.account) {
      await this.selectAccount(data.account)
    }

    // Handle payee selection/creation
    const payeeInput = this.payeeAutocomplete.locator('input')

    // Click to focus and open dropdown
    await payeeInput.click()
    await payeeInput.fill(data.payee)

    // Wait for autocomplete menu to appear
    const menu = this.page.locator('.v-overlay--active .v-list')
    await menu.waitFor({ state: 'visible', timeout: 5000 })

    // Look for create option or existing payee
    const createOption = menu.locator('.v-list-item').filter({ hasText: `Create "${data.payee}"` }).first()
    const existingPayee = menu.locator('.v-list-item').filter({ hasText: data.payee }).first()

    if (await createOption.isVisible({ timeout: 1000 }).catch(() => false)) {
      // Create new payee (inline, no dialog)
      await createOption.click()
      // Wait for the payee to be selected
      await expect(this.payeeAutocomplete.locator('.v-field__input')).toContainText(data.payee, { timeout: 5000 })
    } else if (await existingPayee.isVisible({ timeout: 1000 }).catch(() => false)) {
      await existingPayee.click()
      // Wait for autocomplete dropdown to close
      await menu.waitFor({ state: 'hidden', timeout: 5000 }).catch(() => {})
    } else {
      // Fallback: press Enter to accept first match
      await payeeInput.press('Enter')
      // Wait for menu to close
      await menu.waitFor({ state: 'hidden', timeout: 5000 }).catch(() => {})
    }

    if (data.isExpense === false) {
      await this.setAsIncome()
    }

    await this.fillAmount(data.amount)

    if (data.date) {
      await this.fillDate(data.date)
    }

    if (data.memo) {
      await this.fillMemo(data.memo)
    }

    if (data.location) {
      await this.selectLocation(data.location)
    }

    if (data.cleared) {
      await this.toggleCleared()
    }

    // Select envelope if provided and selector is visible (budget account)
    if (data.envelope && (await this.isEnvelopeSelectorVisible())) {
      await this.selectEnvelope(data.envelope)
    }

    await this.createButton.click()
  }

  /**
   * Create a transfer.
   */
  async createTransfer(data: {
    fromAccount: string
    toAccount: string
    amount: string
    date?: string
    memo?: string
    cleared?: boolean
    envelope?: string // Required for budget -> tracking transfers
  }) {
    await this.switchToTransfer()

    await this.selectFromAccount(data.fromAccount)
    await this.selectToAccount(data.toAccount)

    // Select envelope if provided (for budget -> tracking transfers)
    if (data.envelope) {
      await this.selectTransferEnvelope(data.envelope)
    }

    await this.fillAmount(data.amount)

    if (data.date) {
      await this.fillDate(data.date)
    }

    if (data.memo) {
      await this.fillMemo(data.memo)
    }

    if (data.cleared) {
      await this.toggleCleared()
    }

    await this.createButton.click()
  }

  /**
   * Check if the transfer envelope selector is visible (for budget -> tracking transfers).
   */
  async isTransferEnvelopeSelectorVisible(): Promise<boolean> {
    return await this.transferEnvelopeSelect.isVisible()
  }

  /**
   * Select an envelope for a transfer (budget -> tracking).
   */
  async selectTransferEnvelope(envelopeName: string) {
    await this.transferEnvelopeSelect.click()
    await this.page.getByRole('option', { name: envelopeName }).click()
  }

  /**
   * Submit the form (create or save).
   */
  async submit() {
    const createBtn = await this.createButton.isVisible()
    if (createBtn) {
      await this.createButton.click()
    } else {
      await this.saveButton.click()
    }
  }

  /**
   * Click Save & Add Another and wait for form to reset.
   */
  async saveAndAddAnother() {
    await this.saveAndAddAnotherButton.click()
    // Wait for the form to reset - amount should be empty after reset
    await expect(this.amountInput).toHaveValue('', { timeout: 5000 })
  }

  /**
   * Open delete confirmation dialog.
   */
  async openDeleteDialog() {
    await this.deleteButton.click()
    await expect(this.deleteDialog).toBeVisible()
  }

  /**
   * Confirm deletion.
   */
  async confirmDelete() {
    await this.deleteConfirmButton.click()
    await this.waitForDialogHidden()
  }

  /**
   * Cancel deletion.
   */
  async cancelDelete() {
    await this.deleteCancelButton.click()
    await expect(this.deleteDialog).toBeHidden()
  }

  /**
   * Delete the transaction.
   */
  async deleteTransaction() {
    await this.openDeleteDialog()
    await this.confirmDelete()
  }

  /**
   * Check if we're in edit mode.
   */
  async isEditMode(): Promise<boolean> {
    return await this.deleteButton.isVisible()
  }

  /**
   * Get the dialog title text.
   */
  async getDialogTitle(): Promise<string> {
    return await this.dialogTitle.textContent() || ''
  }

  /**
   * Check if the Envelope label is visible (for budget accounts including CC).
   */
  async expectEnvelopeLabelVisible() {
    const envelopeLabel = this.dialog.locator('.text-subtitle-1').filter({ hasText: 'Envelope' })
    await expect(envelopeLabel).toBeVisible({ timeout: 10000 })
  }

  /**
   * Check if the income allocation mode selector is visible.
   * This appears for new income transactions in budget accounts.
   */
  async isIncomeAllocationModeVisible(): Promise<boolean> {
    return await this.incomeAllocationModeGroup.isVisible({ timeout: 2000 }).catch(() => false)
  }

  /**
   * Select income allocation mode.
   */
  async selectIncomeAllocationMode(mode: 'auto-distribute' | 'envelope' | 'none') {
    switch (mode) {
      case 'auto-distribute':
        await this.autoDistributeRadio.click()
        break
      case 'envelope':
        await this.envelopeModeRadio.click()
        break
      case 'none':
        await this.noneModeRadio.click()
        break
    }
  }

  /**
   * Get the currently selected income allocation mode.
   */
  async getSelectedIncomeAllocationMode(): Promise<'auto-distribute' | 'envelope' | 'none' | null> {
    if (await this.autoDistributeRadio.isChecked()) return 'auto-distribute'
    if (await this.envelopeModeRadio.isChecked()) return 'envelope'
    if (await this.noneModeRadio.isChecked()) return 'none'
    return null
  }

  /**
   * Wait for the allocation preview dialog to be visible.
   */
  async waitForPreviewDialog() {
    await expect(this.previewDialog).toBeVisible({ timeout: 5000 })
  }

  /**
   * Check if the allocation preview dialog is visible.
   */
  async isPreviewDialogVisible(): Promise<boolean> {
    return await this.previewDialog.isVisible()
  }

  /**
   * Confirm the allocation preview and save the transaction.
   */
  async confirmPreview() {
    await this.previewConfirmButton.click()
    await expect(this.previewDialog).toBeHidden({ timeout: 5000 })
  }

  /**
   * Cancel the allocation preview.
   */
  async cancelPreview() {
    await this.previewCancelButton.click()
    await expect(this.previewDialog).toBeHidden({ timeout: 5000 })
  }

  /**
   * Get the allocations shown in the preview dialog.
   * Returns an array of { envelope: string, amount: string } objects.
   */
  async getPreviewAllocations(): Promise<{ envelope: string; amount: string }[]> {
    const rows = this.previewDialog.locator('.v-card-text .d-flex.justify-space-between')
    const count = await rows.count()
    const allocations: { envelope: string; amount: string }[] = []

    for (let i = 0; i < count - 1; i++) { // Exclude the "Total" row
      const row = rows.nth(i)
      const envelope = (await row.locator('span').first().textContent()) || ''
      const amount = (await row.locator('span').last().textContent()) || ''
      allocations.push({ envelope: envelope.trim(), amount: amount.trim() })
    }

    return allocations
  }
}
