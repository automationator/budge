import { type Page, type Locator, expect } from '@playwright/test'
import { BasePage } from './base.page'

/**
 * Page object for the Recurring Transactions view.
 */
export class RecurringPage extends BasePage {
  // Header elements
  readonly pageTitle: Locator
  readonly addRecurringButton: Locator

  // Summary cards
  readonly monthlyExpensesCard: Locator
  readonly monthlyIncomeCard: Locator
  readonly netMonthlyCard: Locator
  readonly activeRulesCard: Locator

  // Filters
  readonly showInactiveSwitch: Locator

  // List
  readonly recurringList: Locator
  readonly recurringItems: Locator
  readonly loadingSpinner: Locator
  readonly emptyState: Locator
  readonly emptyStateAddButton: Locator

  // Form Dialog
  readonly formDialog: Locator
  readonly formDialogTitle: Locator
  readonly transactionTypeToggle: Locator
  readonly transactionButton: Locator
  readonly transferButton: Locator
  readonly accountSelect: Locator
  readonly destinationAccountSelect: Locator
  readonly payeeSelect: Locator
  readonly expenseButton: Locator
  readonly incomeButton: Locator
  readonly amountInput: Locator
  readonly frequencyValueInput: Locator
  readonly frequencyUnitSelect: Locator
  readonly startDateInput: Locator
  readonly endDateInput: Locator
  readonly envelopeSelect: Locator
  readonly memoInput: Locator
  readonly createButton: Locator
  readonly saveButton: Locator
  readonly cancelFormButton: Locator

  // Delete Dialog
  readonly deleteDialog: Locator
  readonly deleteScheduledCheckbox: Locator
  readonly confirmDeleteButton: Locator
  readonly cancelDeleteButton: Locator

  constructor(page: Page) {
    super(page)

    // Header
    this.pageTitle = page.locator('h1').filter({ hasText: 'Recurring Transactions' })
    this.addRecurringButton = page.getByRole('button', { name: 'Add Recurring', exact: true })

    // Summary cards
    this.monthlyExpensesCard = page.locator('.v-card').filter({ hasText: 'Monthly Expenses' })
    this.monthlyIncomeCard = page.locator('.v-card').filter({ hasText: 'Monthly Income' })
    this.netMonthlyCard = page.locator('.v-card').filter({ hasText: 'Net Monthly' })
    this.activeRulesCard = page.locator('.v-card').filter({ hasText: 'Active Rules' })

    // Filters
    this.showInactiveSwitch = page.locator('.v-switch').filter({ hasText: 'Show inactive' })

    // List
    this.recurringList = page.locator('.v-list')
    this.recurringItems = page.locator('.v-list-item')
    this.loadingSpinner = page.locator('.v-progress-circular')
    this.emptyState = page.locator('text=No recurring transactions yet')
    this.emptyStateAddButton = page.getByRole('button', { name: 'Add Recurring Transaction' })

    // Form Dialog - use page-level locators since only one dialog is open at a time
    this.formDialog = page.locator('.v-dialog').filter({ has: page.locator('.v-btn-toggle') })
    this.formDialogTitle = this.formDialog.locator('.v-card-title')
    this.transactionTypeToggle = this.formDialog.locator('.v-btn-toggle').first()
    this.transactionButton = this.formDialog.getByRole('button', { name: 'Transaction', exact: true })
    this.transferButton = this.formDialog.getByRole('button', { name: 'Transfer', exact: true })
    // Use page-level selectors with label matching (same approach as transaction-form.page.ts)
    this.accountSelect = page.locator('.v-dialog .v-select').filter({ hasText: 'Account' }).first()
    this.destinationAccountSelect = page.locator('.v-dialog .v-select').filter({ hasText: 'To Account' })
    this.payeeSelect = page.locator('.v-dialog .v-autocomplete').filter({ hasText: 'Payee' })
    this.expenseButton = this.formDialog.getByRole('button', { name: 'Expense' })
    this.incomeButton = this.formDialog.getByRole('button', { name: 'Income' })
    this.amountInput = this.formDialog.getByLabel('Amount')
    this.frequencyValueInput = this.formDialog.getByLabel('Every')
    this.frequencyUnitSelect = page.locator('.v-dialog .v-select').filter({ hasText: 'Period' })
    this.startDateInput = page.locator('.v-dialog input[type="date"]').first()
    this.endDateInput = page.locator('.v-dialog input[type="date"]').nth(1)
    this.envelopeSelect = page.locator('.v-dialog .v-autocomplete').filter({ hasText: 'Envelope' })
    this.memoInput = page.locator('.v-dialog .v-text-field').filter({ hasText: 'Memo' }).locator('input')
    this.createButton = this.formDialog.getByRole('button', { name: 'Create' })
    this.saveButton = this.formDialog.getByRole('button', { name: 'Save' })
    this.cancelFormButton = this.formDialog.getByRole('button', { name: 'Cancel' })

    // Delete Dialog
    this.deleteDialog = page.locator('.v-dialog').filter({ hasText: 'Delete Recurring Transaction' })
    this.deleteScheduledCheckbox = this.deleteDialog.locator('.v-checkbox')
    this.confirmDeleteButton = this.deleteDialog.getByRole('button', { name: 'Delete' })
    this.cancelDeleteButton = this.deleteDialog.getByRole('button', { name: 'Cancel' })
  }

  async goto() {
    // Set up promise to wait for payees API response BEFORE navigation
    const payeesResponsePromise = this.page.waitForResponse(
      (response) => response.url().includes('/payees') && response.status() === 200,
      { timeout: 15000 }
    )
    await this.page.goto('/recurring')
    await this.waitForPageLoad()
    // Wait for payees to be loaded (the page fetches them on mount)
    await payeesResponsePromise.catch(() => {
      // Payees may have been cached, ignore timeout
    })
  }

  /**
   * Open the create recurring dialog.
   */
  async openCreateDialog() {
    await this.addRecurringButton.click()
    await expect(this.formDialog).toBeVisible()
  }

  /**
   * Select an account in the form.
   */
  async selectAccount(accountName: string) {
    // Click the select to open the dropdown
    await this.accountSelect.click()
    // Wait specifically for the target item (not just any item)
    const menu = this.page.locator('.v-menu .v-list-item')
    const targetItem = menu.filter({ hasText: accountName }).first()
    await targetItem.waitFor({ state: 'visible', timeout: 10000 })
    await targetItem.click()
  }

  /**
   * Select a destination account for transfer.
   */
  async selectDestinationAccount(accountName: string) {
    await this.destinationAccountSelect.click()
    // Wait specifically for the target item (not just any item)
    const menu = this.page.locator('.v-menu .v-list-item')
    const targetItem = menu.filter({ hasText: accountName }).first()
    await targetItem.waitFor({ state: 'visible', timeout: 10000 })
    await targetItem.click()
  }

  /**
   * Select a payee from the dropdown.
   * Note: Payees must be created beforehand (via API or transaction).
   * Now uses v-autocomplete via PayeeSelect component.
   */
  async selectPayee(payeeName: string) {
    // Click to open the autocomplete dropdown first
    await this.payeeSelect.click()

    // Fill the input to filter payees
    await this.payeeSelect.locator('input').fill(payeeName)

    // Wait for menu to appear with increased timeout
    const menu = this.page.locator('.v-overlay--active .v-list')
    await menu.waitFor({ state: 'visible', timeout: 10000 })

    // Select the payee with increased timeout
    const option = menu.locator('.v-list-item').filter({ hasText: payeeName }).first()
    await option.waitFor({ state: 'visible', timeout: 10000 })
    await option.click()

    // Wait for selection to be reflected in the input
    await expect(this.payeeSelect).toContainText(payeeName, { timeout: 5000 })
  }

  /**
   * Select an envelope from the dropdown.
   */
  async selectEnvelope(envelopeName: string) {
    await this.envelopeSelect.click()
    const menu = this.page.locator('.v-menu .v-list-item')
    const targetItem = menu.filter({ hasText: envelopeName }).first()
    await targetItem.waitFor({ state: 'visible', timeout: 10000 })
    await targetItem.click()
  }

  /**
   * Select frequency unit.
   */
  async selectFrequencyUnit(unit: 'days' | 'weeks' | 'months' | 'years') {
    // Map backend values to display text
    const displayMap: Record<string, string> = {
      days: 'Day(s)',
      weeks: 'Week(s)',
      months: 'Month(s)',
      years: 'Year(s)',
    }
    const displayText = displayMap[unit]
    await this.frequencyUnitSelect.click()
    // Wait specifically for the target item (not just any item)
    const menu = this.page.locator('.v-menu .v-list-item')
    const targetItem = menu.filter({ hasText: displayText }).first()
    await targetItem.waitFor({ state: 'visible', timeout: 10000 })
    await targetItem.click()
  }

  /**
   * Create a recurring expense transaction.
   */
  async createRecurringExpense(data: {
    account: string
    payee: string
    amount: string
    envelope?: string // Required for budget accounts
    frequencyValue?: string
    frequencyUnit?: 'Day(s)' | 'Week(s)' | 'Month(s)' | 'Year(s)'
    memo?: string
  }) {
    await this.openCreateDialog()

    // Ensure Transaction mode is selected
    await this.transactionButton.click()
    await expect(this.accountSelect).toBeVisible()

    await this.selectAccount(data.account)
    await this.selectPayee(data.payee)

    // Set expense (default)
    await this.expenseButton.click()

    await this.amountInput.fill(data.amount)

    if (data.envelope) {
      await this.selectEnvelope(data.envelope)
    }

    if (data.frequencyValue) {
      await this.frequencyValueInput.fill(data.frequencyValue)
    }

    if (data.frequencyUnit) {
      await this.selectFrequencyUnit(data.frequencyUnit)
    }

    if (data.memo) {
      await this.memoInput.fill(data.memo)
    }

    // Ensure the button is enabled
    await expect(this.createButton).toBeEnabled({ timeout: 5000 })

    // Click the button and wait for API response
    const responsePromise = this.page.waitForResponse(
      (response) => response.url().includes('/recurring-transactions') && response.request().method() === 'POST'
    )
    await this.createButton.click()
    await responsePromise

    // Wait for dialog to close
    await expect(this.formDialog).toBeHidden({ timeout: 10000 })
  }

  /**
   * Create a recurring income transaction.
   */
  async createRecurringIncome(data: {
    account: string
    payee: string
    amount: string
    frequencyValue?: string
    frequencyUnit?: 'Day(s)' | 'Week(s)' | 'Month(s)' | 'Year(s)'
    memo?: string
  }) {
    await this.openCreateDialog()

    await this.transactionButton.click()
    await expect(this.accountSelect).toBeVisible()

    await this.selectAccount(data.account)
    await this.selectPayee(data.payee)

    // Set income
    await this.incomeButton.click()

    await this.amountInput.fill(data.amount)

    if (data.frequencyValue) {
      await this.frequencyValueInput.fill(data.frequencyValue)
    }

    if (data.frequencyUnit) {
      await this.selectFrequencyUnit(data.frequencyUnit)
    }

    if (data.memo) {
      await this.memoInput.fill(data.memo)
    }

    // Ensure the button is enabled
    await expect(this.createButton).toBeEnabled({ timeout: 5000 })

    // Click the button and wait for API response
    const responsePromise = this.page.waitForResponse(
      (response) => response.url().includes('/recurring-transactions') && response.request().method() === 'POST'
    )
    await this.createButton.click()
    await responsePromise

    // Wait for dialog to close
    await expect(this.formDialog).toBeHidden({ timeout: 10000 })
  }

  /**
   * Create a recurring transfer.
   */
  async createRecurringTransfer(data: {
    fromAccount: string
    toAccount: string
    amount: string
    envelope?: string // Required for budget->tracking transfers
    frequencyValue?: string
    frequencyUnit?: 'Day(s)' | 'Week(s)' | 'Month(s)' | 'Year(s)'
    memo?: string
  }) {
    await this.openCreateDialog()

    // Switch to Transfer mode
    await this.transferButton.click()
    await expect(this.accountSelect).toBeVisible()

    await this.selectAccount(data.fromAccount)
    await this.selectDestinationAccount(data.toAccount)

    if (data.envelope) {
      await this.selectEnvelope(data.envelope)
    }

    await this.amountInput.fill(data.amount)

    if (data.frequencyValue) {
      await this.frequencyValueInput.fill(data.frequencyValue)
    }

    if (data.frequencyUnit) {
      await this.selectFrequencyUnit(data.frequencyUnit)
    }

    if (data.memo) {
      await this.memoInput.fill(data.memo)
    }

    // Ensure the button is enabled
    await expect(this.createButton).toBeEnabled({ timeout: 5000 })

    // Click the button and wait for API response
    const responsePromise = this.page.waitForResponse(
      (response) => response.url().includes('/recurring-transactions') && response.request().method() === 'POST'
    )
    await this.createButton.click()
    await responsePromise

    // Wait for dialog to close
    await expect(this.formDialog).toBeHidden({ timeout: 10000 })
  }

  /**
   * Get a recurring item by payee/description text.
   */
  getRecurringItem(text: string): Locator {
    return this.page.locator('.v-list-item').filter({ hasText: text }).first()
  }

  /**
   * Open the menu for a recurring item.
   */
  async openItemMenu(text: string) {
    const item = this.getRecurringItem(text)
    await item.locator('button').filter({ has: this.page.locator('[class*="mdi-dots-vertical"]') }).click()
    const menu = this.page.locator('.v-overlay--active .v-list')
    await menu.waitFor({ state: 'visible', timeout: 5000 })
    return menu
  }

  /**
   * Edit a recurring item.
   */
  async openEditDialog(text: string) {
    const menu = await this.openItemMenu(text)
    await menu.locator('.v-list-item').filter({ hasText: 'Edit' }).click()
    await expect(this.formDialog).toBeVisible()
  }

  /**
   * Pause a recurring item.
   */
  async pauseRecurring(text: string) {
    const menu = await this.openItemMenu(text)
    // Wait for the PATCH API call to complete
    const responsePromise = this.page.waitForResponse(
      (response) =>
        response.url().includes('/recurring-transactions/') && response.request().method() === 'PATCH'
    )
    await menu.locator('.v-list-item').filter({ hasText: 'Pause' }).click()
    await responsePromise
  }

  /**
   * Resume a recurring item.
   */
  async resumeRecurring(text: string) {
    const menu = await this.openItemMenu(text)
    await menu.locator('.v-list-item').filter({ hasText: 'Resume' }).click()
  }

  /**
   * Open delete dialog for a recurring item.
   */
  async openDeleteDialog(text: string) {
    const menu = await this.openItemMenu(text)
    await menu.locator('.v-list-item').filter({ hasText: 'Delete' }).click()
    await expect(this.deleteDialog).toBeVisible()
  }

  /**
   * Delete a recurring item.
   */
  async deleteRecurring(text: string, deleteScheduled = true) {
    await this.openDeleteDialog(text)

    // Toggle checkbox if needed
    const checkbox = this.deleteScheduledCheckbox.locator('input[type="checkbox"]')
    const isChecked = await checkbox.isChecked()
    if (isChecked !== deleteScheduled) {
      await checkbox.click({ force: true })
    }

    await this.confirmDeleteButton.click()
    await expect(this.deleteDialog).toBeHidden({ timeout: 10000 })
  }

  /**
   * Toggle show inactive filter.
   */
  async toggleShowInactive() {
    // Set up response listener before clicking
    const responsePromise = this.page.waitForResponse((response) =>
      response.url().includes('/recurring-transactions') && response.request().method() === 'GET'
    )
    // Click the input directly with force to bypass intercepting elements
    const switchInput = this.showInactiveSwitch.locator('input[type="checkbox"]')
    await switchInput.click({ force: true })
    // Wait for the API response
    await responsePromise
  }

  /**
   * Assert recurring item exists.
   */
  async expectRecurringExists(text: string) {
    await expect(this.getRecurringItem(text)).toBeVisible()
  }

  /**
   * Assert recurring item does not exist.
   */
  async expectRecurringNotExists(text: string) {
    await expect(this.getRecurringItem(text)).not.toBeVisible()
  }

  /**
   * Assert empty state is shown.
   */
  async expectEmptyState() {
    await expect(this.emptyState).toBeVisible()
    await expect(this.emptyStateAddButton).toBeVisible()
  }

  /**
   * Get active rules count.
   */
  async getActiveRulesCount(): Promise<string> {
    return await this.activeRulesCard.locator('.text-h6').textContent() || '0'
  }

  /**
   * Check if an item is paused.
   */
  async isRecurringPaused(text: string): Promise<boolean> {
    const item = this.getRecurringItem(text)
    const pausedChip = item.locator('.v-chip').filter({ hasText: 'Paused' })
    try {
      await expect(pausedChip).toBeVisible({ timeout: 5000 })
      return true
    } catch {
      return false
    }
  }
}
