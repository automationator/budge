import { type Page, type Locator, expect } from '@playwright/test'
import { BasePage } from './base.page'
import type { AccountType } from '../fixtures/test-data'
import { TransactionFormPage } from './transaction-form.page'

/**
 * Page object for the Account Detail view.
 */
export class AccountDetailPage extends BasePage {
  // Back navigation
  readonly backButton: Locator

  // Account header card
  readonly accountName: Locator
  readonly accountType: Locator
  readonly accountBalance: Locator
  readonly offBudgetLabel: Locator
  readonly descriptionText: Locator

  // Action buttons
  readonly editButton: Locator
  readonly reconcileButton: Locator
  readonly deleteButton: Locator
  readonly lastReconciledText: Locator

  // Transactions section
  readonly transactionsCard: Locator
  readonly transactionsList: Locator
  readonly transactionsTable: Locator
  readonly transactionTableRows: Locator
  readonly loadMoreButton: Locator
  readonly noTransactionsMessage: Locator
  readonly addTransactionButton: Locator
  readonly hideReconciledFilterChip: Locator

  // Transaction form dialog
  readonly formDialog: TransactionFormPage

  // Edit dialog
  readonly editDialog: Locator
  readonly editNameInput: Locator
  readonly editAccountTypeSelect: Locator
  readonly editIconChips: Locator
  readonly editCustomIconInput: Locator
  readonly editUseDefaultIconButton: Locator
  readonly editDescriptionInput: Locator
  readonly editIncludeInBudgetSwitch: Locator
  readonly editActiveSwitch: Locator
  readonly editSaveButton: Locator
  readonly editCancelButton: Locator

  // Delete confirmation dialog
  readonly deleteDialog: Locator
  readonly deleteConfirmButton: Locator
  readonly deleteCancelButton: Locator

  // Reconcile dialog
  readonly reconcileDialog: Locator
  // Step 1: Confirmation
  readonly reconcileDisplayedBalance: Locator
  readonly reconcileYesButton: Locator
  readonly reconcileNoButton: Locator
  // Step 2: Balance entry
  readonly reconcileBalanceInput: Locator
  readonly reconcileSignToggle: Locator
  readonly reconcileBackButton: Locator
  readonly reconcileConfirmButton: Locator
  readonly reconcileCancelButton: Locator

  constructor(page: Page) {
    super(page)

    // Back navigation
    this.backButton = page.getByRole('link', { name: 'Back to Accounts' })

    // Account header
    this.accountName = page.locator('.v-card-title').first()
    this.accountType = page.locator('.v-card-subtitle').first()
    // Target the MoneyDisplay span which has font-weight-medium and starts with $ or -$
    this.accountBalance = page.locator('.v-card').first().locator('span.font-weight-medium').filter({ hasText: /^-?\$/ }).first()
    this.offBudgetLabel = page.locator('.v-card').first().locator('text=Off-budget').first()
    this.descriptionText = page.locator('.v-card-text').first()

    // Action buttons
    this.editButton = page.getByRole('button', { name: 'Edit' })
    this.reconcileButton = page.getByRole('button', { name: 'Reconcile' })
    this.deleteButton = page.getByRole('button', { name: 'Delete' })
    this.lastReconciledText = page.getByTestId('last-reconciled-text')

    // Transactions section - supports both mobile (list) and desktop (table) layouts
    // The toolbar with filter chip and add button is now separate from the transaction cards
    this.transactionsCard = page.locator('.v-card').filter({ has: page.locator('.v-list, .v-table') })
    this.transactionsList = page.locator('.v-list')
    this.transactionsTable = page.locator('.v-table')
    this.transactionTableRows = page.locator('tr.transaction-row')
    this.loadMoreButton = page.getByRole('button', { name: 'Load More' })
    this.noTransactionsMessage = page.locator('text=No transactions yet')
    this.addTransactionButton = page.getByRole('button', { name: 'Add Transaction' })
    this.hideReconciledFilterChip = page.locator('.v-chip').filter({ hasText: /Hide Reconciled|Hide/ })

    // Transaction form dialog
    this.formDialog = new TransactionFormPage(page)

    // Edit dialog
    this.editDialog = page.locator('.v-dialog').filter({ hasText: 'Edit Account' })
    this.editNameInput = this.editDialog.locator('input').first()
    this.editAccountTypeSelect = this.editDialog.locator('.v-select')
    this.editIconChips = this.editDialog.locator('[data-testid="icon-chip"]')
    this.editCustomIconInput = this.editDialog.locator('[data-testid="custom-icon-input"] input')
    this.editUseDefaultIconButton = this.editDialog.locator('[data-testid="use-default-icon-button"]')
    this.editDescriptionInput = this.editDialog.locator('textarea')
    this.editIncludeInBudgetSwitch = this.editDialog.locator('.v-switch').filter({ hasText: 'Include in budget' })
    this.editActiveSwitch = this.editDialog.locator('.v-switch').filter({ hasText: 'Active' })
    this.editSaveButton = this.editDialog.getByRole('button', { name: 'Save' })
    this.editCancelButton = this.editDialog.getByRole('button', { name: 'Cancel' })

    // Delete dialog
    this.deleteDialog = page.locator('.v-dialog').filter({ hasText: 'Delete Account' })
    this.deleteConfirmButton = this.deleteDialog.getByRole('button', { name: 'Delete' })
    this.deleteCancelButton = this.deleteDialog.getByRole('button', { name: 'Cancel' })

    // Reconcile dialog
    this.reconcileDialog = page.locator('.v-dialog').filter({ hasText: 'Reconcile Account' })
    // Step 1: Confirmation
    this.reconcileDisplayedBalance = this.reconcileDialog.locator('span.font-weight-medium').filter({ hasText: /^\$/ })
    this.reconcileYesButton = this.reconcileDialog.getByRole('button', { name: 'Yes' })
    this.reconcileNoButton = this.reconcileDialog.getByRole('button', { name: 'No' })
    // Step 2: Balance entry
    this.reconcileBalanceInput = this.reconcileDialog.locator('input')
    this.reconcileSignToggle = this.reconcileDialog.getByTestId('amount-sign-toggle')
    this.reconcileBackButton = this.reconcileDialog.getByRole('button', { name: 'Back' })
    this.reconcileConfirmButton = this.reconcileDialog.getByRole('button', { name: 'Reconcile' })
    this.reconcileCancelButton = this.reconcileDialog.getByRole('button', { name: 'Cancel' })
  }

  async goto(accountId: string) {
    await this.page.goto(`/accounts/${accountId}`)
    await this.waitForPageLoad()
  }

  /**
   * Navigate back to accounts list.
   */
  async goBack() {
    await this.backButton.click()
    await expect(this.page).toHaveURL(/\/accounts$/)
  }

  /**
   * Get the account name displayed.
   */
  async getAccountName(): Promise<string> {
    return await this.accountName.textContent() || ''
  }

  /**
   * Get the account balance displayed.
   */
  async getAccountBalance(): Promise<string> {
    return await this.accountBalance.textContent() || ''
  }

  /**
   * Get the last reconciled text displayed.
   */
  async getLastReconciledText(): Promise<string> {
    return (await this.lastReconciledText.textContent()) || ''
  }

  // ============ Edit Actions ============

  /**
   * Open the edit dialog.
   */
  async openEditDialog() {
    // Wait for the page to fully load first
    await this.waitForPageLoad()
    // Wait for the edit button to be visible and enabled
    await expect(this.editButton).toBeVisible({ timeout: 15000 })
    await expect(this.editButton).toBeEnabled({ timeout: 5000 })
    // Click and wait for dialog - retry click if dialog doesn't appear
    await expect(async () => {
      await this.editButton.click()
      await expect(this.editDialog).toBeVisible({ timeout: 3000 })
    }).toPass({ timeout: 15000 })
  }

  /**
   * Fill the edit form.
   */
  async fillEditForm(data: {
    name?: string
    accountType?: AccountType
    icon?: string
    customIcon?: string
    clearIcon?: boolean
    description?: string
    includeInBudget?: boolean
    isActive?: boolean
  }) {
    if (data.name !== undefined) {
      await this.editNameInput.clear()
      await this.editNameInput.fill(data.name)
    }

    if (data.accountType) {
      await this.editAccountTypeSelect.click()
      const typeNames: Record<AccountType, string> = {
        checking: 'Checking',
        savings: 'Savings',
        credit_card: 'Credit Card',
        cash: 'Cash',
        investment: 'Investment',
        loan: 'Loan',
        other: 'Other',
      }
      // Use the overlay container for dropdown items to avoid matching sidebar items
      await this.page.locator('.v-overlay__content .v-list-item').filter({ hasText: typeNames[data.accountType] }).click()
    }

    if (data.clearIcon) {
      // Click "Use default icon" button to clear any selected icon
      await this.editUseDefaultIconButton.click()
    }

    if (data.icon) {
      // Select an icon from the predefined chips
      await this.editIconChips.filter({ hasText: data.icon }).click()
    }

    if (data.customIcon) {
      // Enter a custom icon name
      await this.editCustomIconInput.clear()
      await this.editCustomIconInput.fill(data.customIcon)
    }

    if (data.description !== undefined) {
      await this.editDescriptionInput.clear()
      await this.editDescriptionInput.fill(data.description)
    }

    if (data.includeInBudget !== undefined) {
      const isChecked = await this.editIncludeInBudgetSwitch.locator('input').isChecked()
      if (isChecked !== data.includeInBudget) {
        await this.editIncludeInBudgetSwitch.locator('input').click({ force: true })
      }
    }

    if (data.isActive !== undefined) {
      const isChecked = await this.editActiveSwitch.locator('input').isChecked()
      if (isChecked !== data.isActive) {
        await this.editActiveSwitch.locator('input').click({ force: true })
      }
    }
  }

  /**
   * Save the edit form.
   */
  async saveEdit() {
    await this.editSaveButton.click()
    await expect(this.editDialog).toBeHidden({ timeout: 10000 })
  }

  /**
   * Cancel the edit form.
   */
  async cancelEdit() {
    await this.editCancelButton.click()
    await expect(this.editDialog).toBeHidden()
  }

  /**
   * Edit the account with given data.
   */
  async editAccount(data: {
    name?: string
    accountType?: AccountType
    icon?: string
    customIcon?: string
    clearIcon?: boolean
    description?: string
    includeInBudget?: boolean
    isActive?: boolean
  }) {
    await this.openEditDialog()
    await this.fillEditForm(data)
    await this.saveEdit()
  }

  // ============ Delete Actions ============

  /**
   * Open the delete confirmation dialog.
   */
  async openDeleteDialog() {
    await this.deleteButton.click()
    await expect(this.deleteDialog).toBeVisible()
  }

  /**
   * Confirm account deletion.
   */
  async confirmDelete() {
    await this.deleteConfirmButton.click()
    // Should redirect to accounts list
    await expect(this.page).toHaveURL(/\/accounts$/, { timeout: 10000 })
  }

  /**
   * Cancel account deletion.
   */
  async cancelDelete() {
    await this.deleteCancelButton.click()
    await expect(this.deleteDialog).toBeHidden()
  }

  /**
   * Delete the account.
   */
  async deleteAccount() {
    await this.openDeleteDialog()
    await this.confirmDelete()
  }

  // ============ Reconcile Actions ============

  /**
   * Open the reconcile dialog. Opens to Step 1 (confirmation).
   */
  async openReconcileDialog() {
    await this.reconcileButton.click()
    await expect(this.reconcileDialog).toBeVisible()
    await this.waitForStep1()
  }

  /**
   * Wait for Step 1 (confirmation) to be visible.
   */
  async waitForStep1() {
    await expect(this.reconcileYesButton).toBeVisible()
    await expect(this.reconcileNoButton).toBeVisible()
  }

  /**
   * Wait for Step 2 (balance entry) to be visible.
   */
  async waitForStep2() {
    await expect(this.reconcileBalanceInput).toBeVisible()
    await expect(this.reconcileBackButton).toBeVisible()
  }

  /**
   * Get the balance displayed in Step 1 (confirmation).
   */
  async getReconcileDisplayedBalance(): Promise<string> {
    return (await this.reconcileDisplayedBalance.textContent()) || ''
  }

  /**
   * Get the balance in the input field (Step 2).
   */
  async getReconcileInputBalance(): Promise<string> {
    return await this.reconcileBalanceInput.inputValue()
  }

  /**
   * Click "Yes" on Step 1 to confirm balance is correct.
   * Waits for dialog to close.
   */
  async confirmBalanceCorrect() {
    await this.reconcileYesButton.click()
    await expect(this.reconcileDialog).toBeHidden({ timeout: 10000 })
  }

  /**
   * Click "No" on Step 1 to proceed to balance entry (Step 2).
   */
  async proceedToBalanceEntry() {
    await this.reconcileNoButton.click()
    await this.waitForStep2()
  }

  /**
   * Click "Back" from Step 2 to return to Step 1.
   */
  async goBackToStep1() {
    await this.reconcileBackButton.click()
    await this.waitForStep1()
  }

  /**
   * Fill the reconcile balance (Step 2).
   */
  async fillReconcileBalance(balance: string) {
    await this.reconcileBalanceInput.clear()
    await this.reconcileBalanceInput.fill(balance)
  }

  /**
   * Toggle the balance sign (Step 2).
   */
  async toggleReconcileSign() {
    await this.reconcileSignToggle.click()
  }

  /**
   * Check if the balance sign is negative (Step 2).
   */
  async isReconcileSignNegative(): Promise<boolean> {
    const text = await this.reconcileSignToggle.textContent()
    return text?.includes('−') ?? false
  }

  /**
   * Set the balance sign to negative if it's not already (Step 2).
   */
  async setReconcileSignNegative() {
    if (!(await this.isReconcileSignNegative())) {
      await this.toggleReconcileSign()
    }
  }

  /**
   * Set the balance sign to positive if it's not already (Step 2).
   */
  async setReconcileSignPositive() {
    if (await this.isReconcileSignNegative()) {
      await this.toggleReconcileSign()
    }
  }

  /**
   * Confirm reconciliation (Step 2).
   */
  async confirmReconcile() {
    await this.reconcileConfirmButton.click()
    await expect(this.reconcileDialog).toBeHidden({ timeout: 10000 })
  }

  /**
   * Cancel reconciliation (works from either step).
   */
  async cancelReconcile() {
    await this.reconcileCancelButton.click()
    await expect(this.reconcileDialog).toBeHidden()
  }

  /**
   * Reconcile by confirming the current balance is correct (Step 1 Yes path).
   */
  async reconcileAccountConfirm() {
    await this.openReconcileDialog()
    await this.confirmBalanceCorrect()
  }

  /**
   * Reconcile by entering a new balance (Step 1 No -> Step 2 path).
   * @param newBalance The balance amount (always positive)
   * @param isNegative Whether to set the balance as negative (for credit cards/loans)
   */
  async reconcileAccountWithBalance(newBalance: string, isNegative = false) {
    await this.openReconcileDialog()
    await this.proceedToBalanceEntry()
    await this.fillReconcileBalance(newBalance)
    if (isNegative) {
      await this.setReconcileSignNegative()
    } else {
      await this.setReconcileSignPositive()
    }
    await this.confirmReconcile()
  }

  // ============ Transactions ============

  /**
   * Open the transaction form dialog by clicking Add Transaction.
   */
  async clickAddTransaction() {
    await this.addTransactionButton.click()
    await this.formDialog.waitForDialog()
  }

  /**
   * Check if the transaction form dialog is visible.
   */
  async isFormDialogVisible(): Promise<boolean> {
    return await this.formDialog.dialog.isVisible({ timeout: 1000 }).catch(() => false)
  }

  /**
   * Assert no transactions are shown.
   */
  async expectNoTransactions() {
    await expect(this.noTransactionsMessage).toBeVisible()
  }

  /**
   * Check if the page is showing the desktop table layout.
   * Waits for transactions to load before determining layout.
   */
  async isTableLayout(): Promise<boolean> {
    // Wait for either a transaction table row or a list item in the main content
    await this.page.locator('main tr.transaction-row, main .v-list-item').first()
      .waitFor({ state: 'visible', timeout: 10000 }).catch(() => {})
    return await this.transactionsTable.isVisible({ timeout: 500 }).catch(() => false)
  }

  /**
   * Assert transactions are shown.
   */
  async expectTransactionsVisible() {
    const isTable = await this.isTableLayout()
    if (isTable) {
      await expect(this.transactionsTable).toBeVisible()
    } else {
      await expect(this.transactionsList).toBeVisible()
    }
  }

  /**
   * Get the transaction count displayed.
   */
  async getTransactionCount(): Promise<number> {
    const isTable = await this.isTableLayout()
    if (isTable) {
      return await this.transactionTableRows.count()
    } else {
      const items = this.transactionsList.locator('.v-list-item')
      return await items.count()
    }
  }

  /**
   * Click load more button if visible.
   */
  async loadMoreTransactions() {
    if (await this.loadMoreButton.isVisible()) {
      await this.loadMoreButton.click()
      await this.waitForPageLoad()
    }
  }

  /**
   * Create a transaction using the form dialog.
   * Opens the dialog first if not already visible.
   */
  async createTransaction(options: {
    payee: string
    amount: string
    isExpense?: boolean
    envelope?: string
    memo?: string
    cleared?: boolean
  }) {
    // Open the dialog if not visible
    if (!(await this.isFormDialogVisible())) {
      await this.clickAddTransaction()
    }

    // Use the form dialog to create the transaction
    // Account is pre-filled since we're on the account detail page
    await this.formDialog.createTransaction({
      payee: options.payee,
      amount: options.amount,
      isExpense: options.isExpense,
      envelope: options.envelope,
      memo: options.memo,
      cleared: options.cleared,
    })
  }

  /**
   * Create a transfer using the form dialog.
   * Opens the dialog first if not already visible.
   */
  async createTransfer(options: {
    toAccount: string
    amount: string
    isOutflow?: boolean
    memo?: string
    cleared?: boolean
  }) {
    // Open the dialog if not visible
    if (!(await this.isFormDialogVisible())) {
      await this.clickAddTransaction()
    }

    // Switch to transfer mode and create the transfer
    // For transfers from account detail, the current account is the source
    await this.formDialog.switchToTransfer()
    await this.formDialog.selectToAccount(options.toAccount)
    await this.formDialog.fillAmount(options.amount)

    if (options.memo) {
      await this.formDialog.fillMemo(options.memo)
    }

    if (options.cleared) {
      await this.formDialog.toggleCleared()
    }

    await this.formDialog.createButton.click()
  }

  // ============ Reconciled Filter ============

  /**
   * Toggle the hide reconciled filter chip.
   */
  async toggleHideReconciledFilter() {
    const responsePromise = this.page.waitForResponse(
      (response) =>
        response.url().includes('/transactions') &&
        response.request().method() === 'GET'
    )
    await this.hideReconciledFilterChip.click()
    await responsePromise
    await this.waitForPageLoad()
  }

  /**
   * Check if hide reconciled filter is active.
   */
  async isHideReconciledFilterActive(): Promise<boolean> {
    const classes = await this.hideReconciledFilterChip.getAttribute('class')
    return classes?.includes('v-chip--variant-elevated') ?? false
  }

  /**
   * Check if a transaction with given payee name exists.
   */
  async expectTransactionExists(payeeName: string) {
    const isTable = await this.isTableLayout()
    if (isTable) {
      // Desktop table: find row with matching payee
      const row = this.page.locator('tr.transaction-row').filter({
        has: this.page.locator('td span.font-weight-medium', { hasText: payeeName }),
      }).first()
      await expect(row).toBeVisible()
    } else {
      // Mobile list
      const item = this.transactionsList
        .locator('.v-list-item')
        .filter({ has: this.page.locator('.v-list-item-title', { hasText: new RegExp(`^${payeeName}$`) }) })
        .first()
      await expect(item).toBeVisible()
    }
  }

  /**
   * Check if a transaction with given payee name does not exist.
   */
  async expectTransactionNotExists(payeeName: string) {
    const isTable = await this.isTableLayout()
    if (isTable) {
      // Desktop table: verify no row with matching payee
      const row = this.page.locator('tr.transaction-row').filter({
        has: this.page.locator('td span.font-weight-medium', { hasText: payeeName }),
      }).first()
      await expect(row).not.toBeVisible()
    } else {
      // Mobile list
      const item = this.transactionsList
        .locator('.v-list-item')
        .filter({ has: this.page.locator('.v-list-item-title', { hasText: new RegExp(`^${payeeName}$`) }) })
        .first()
      await expect(item).not.toBeVisible()
    }
  }
}
