import { type Page, type Locator, expect } from '@playwright/test'
import { BasePage } from './base.page'
import type { AccountType } from '../fixtures/test-data'

/**
 * Page object for the Accounts list view.
 */
export class AccountsPage extends BasePage {
  // Header elements
  readonly addAccountButton: Locator
  readonly editOrderButton: Locator

  // Account list sections
  readonly allAccountsRow: Locator
  readonly budgetSectionHeader: Locator
  readonly trackingSectionHeader: Locator
  readonly budgetAccountItems: Locator
  readonly trackingAccountItems: Locator
  readonly loadingSpinner: Locator
  readonly emptyState: Locator
  readonly emptyStateAddButton: Locator

  // Create dialog elements
  readonly createDialog: Locator
  readonly nameInput: Locator
  readonly accountTypeSelect: Locator
  readonly iconChips: Locator
  readonly customIconInput: Locator
  readonly useDefaultIconButton: Locator
  readonly descriptionInput: Locator
  readonly startingBalanceInput: Locator
  readonly includeInBudgetSwitch: Locator
  readonly createButton: Locator
  readonly cancelButton: Locator

  constructor(page: Page) {
    super(page)

    // Header buttons
    this.addAccountButton = page.locator('[data-testid="add-account-button"]')
    this.editOrderButton = page.locator('[data-testid="edit-order-button"]')

    // Account list sections (scoped to main content to avoid matching sidebar)
    const mainContent = page.locator('main, [role="main"]')
    this.allAccountsRow = mainContent.locator('[data-testid="all-accounts-row"]')
    this.budgetSectionHeader = mainContent.locator('[data-testid="budget-section-header"]')
    this.trackingSectionHeader = mainContent.locator('[data-testid="tracking-section-header"]')
    this.budgetAccountItems = mainContent.locator('[data-testid="budget-account-item"]')
    this.trackingAccountItems = mainContent.locator('[data-testid="tracking-account-item"]')
    this.loadingSpinner = page.locator('.v-progress-circular')
    this.emptyState = page.locator('text=No accounts yet')
    this.emptyStateAddButton = page.locator('.v-card').filter({ hasText: 'No accounts yet' }).getByRole('button', { name: 'Add Account' })

    // Create dialog
    this.createDialog = page.locator('.v-dialog').filter({ hasText: 'Create Account' })
    this.nameInput = this.createDialog.locator('input').first()
    this.accountTypeSelect = this.createDialog.locator('.v-select')
    this.iconChips = this.createDialog.locator('[data-testid="icon-chip"]')
    this.customIconInput = this.createDialog.locator('[data-testid="custom-icon-input"] input')
    this.useDefaultIconButton = this.createDialog.locator('[data-testid="use-default-icon-button"]')
    this.descriptionInput = this.createDialog.locator('textarea')
    this.startingBalanceInput = this.createDialog.locator('input[type="number"]')
    this.includeInBudgetSwitch = this.createDialog.locator('.v-switch').filter({ hasText: 'Include in budget' })
    this.createButton = this.createDialog.getByRole('button', { name: 'Create' })
    this.cancelButton = this.createDialog.getByRole('button', { name: 'Cancel' })
  }

  async goto() {
    await this.page.goto('/accounts')
    await this.waitForPageLoad()
  }

  /**
   * Open the create account dialog.
   */
  async openCreateDialog() {
    await this.addAccountButton.click()
    await expect(this.createDialog).toBeVisible()
  }

  /**
   * Fill the create account form.
   */
  async fillAccountForm(data: {
    name: string
    accountType?: AccountType
    icon?: string
    customIcon?: string
    description?: string
    startingBalance?: string
    includeInBudget?: boolean
  }) {
    await this.nameInput.fill(data.name)

    if (data.accountType) {
      await this.accountTypeSelect.click()
      // Map account type to display name
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

    if (data.icon) {
      // Select an icon from the predefined chips
      await this.iconChips.filter({ hasText: data.icon }).click()
    }

    if (data.customIcon) {
      // Enter a custom icon name
      await this.customIconInput.fill(data.customIcon)
    }

    if (data.description) {
      await this.descriptionInput.fill(data.description)
    }

    if (data.startingBalance !== undefined) {
      await this.startingBalanceInput.fill(data.startingBalance)
    }

    if (data.includeInBudget !== undefined) {
      const switchInput = this.includeInBudgetSwitch.locator('input[type="checkbox"]')
      const isChecked = await switchInput.isChecked()
      if (isChecked !== data.includeInBudget) {
        // For Vuetify switches, use the label or force click on the input
        await switchInput.click({ force: true })
        await expect(switchInput).toBeChecked({ checked: data.includeInBudget })
      }
    }
  }

  /**
   * Submit the create account form.
   */
  async submitCreateForm() {
    // Wait for create button to be visible and enabled
    await expect(this.createButton).toBeVisible()
    await expect(this.createButton).toBeEnabled()
    // Wait for any pending API requests to complete with a generous timeout
    const responsePromise = this.page.waitForResponse(
      (response) => response.url().includes('/accounts') && response.request().method() === 'POST',
      { timeout: 30000 }
    )
    await this.createButton.click()
    const response = await responsePromise
    if (response.status() >= 400) {
      const body = await response.text().catch(() => 'no body')
      throw new Error(`Account creation failed (${response.status()}): ${body}`)
    }
  }

  /**
   * Cancel the create account form.
   */
  async cancelCreateForm() {
    await this.cancelButton.click()
    await expect(this.createDialog).toBeHidden()
  }

  /**
   * Create a new account with the given data.
   */
  async createAccount(data: {
    name: string
    accountType?: AccountType
    icon?: string
    customIcon?: string
    description?: string
    startingBalance?: string
    includeInBudget?: boolean
  }) {
    await this.openCreateDialog()
    await this.fillAccountForm(data)
    await this.submitCreateForm()
    await expect(this.createDialog).toBeHidden({ timeout: 10000 })
  }

  /**
   * Click the "Use default icon" button to clear any selected icon.
   */
  async clearIcon() {
    await this.useDefaultIconButton.click()
  }

  /**
   * Get an account list item by name (only in the main content area, not sidebar).
   */
  getAccountListItem(name: string): Locator {
    // Scope to main content area to avoid matching sidebar items
    return this.page.locator('main .v-list-item, [role="main"] .v-list-item').filter({ hasText: name })
  }

  /**
   * Get an account card by name (alias for getAccountListItem for backwards compatibility).
   */
  getAccountCard(name: string): Locator {
    return this.getAccountListItem(name)
  }

  /**
   * Click on an account to navigate to its detail page.
   */
  async clickAccount(name: string) {
    const item = this.getAccountListItem(name)
    await item.click()
  }

  /**
   * Get the total balance displayed in the All Accounts row.
   */
  async getTotalBalance(): Promise<string> {
    const moneyDisplay = this.allAccountsRow.locator('.money-display, [class*="text-"]').first()
    return (await moneyDisplay.textContent()) || ''
  }

  /**
   * Assert the empty state is shown.
   */
  async expectEmptyState() {
    await expect(this.emptyState).toBeVisible()
    await expect(this.emptyStateAddButton).toBeVisible()
  }

  /**
   * Assert an account exists in the list.
   */
  async expectAccountExists(name: string) {
    await expect(this.getAccountListItem(name)).toBeVisible()
  }

  /**
   * Assert an account does not exist in the list.
   */
  async expectAccountNotExists(name: string) {
    await expect(this.getAccountListItem(name)).not.toBeVisible()
  }

  /**
   * Toggle the Budget section collapse.
   */
  async toggleBudgetSection() {
    await this.budgetSectionHeader.click()
  }

  /**
   * Toggle the Tracking section collapse.
   */
  async toggleTrackingSection() {
    await this.trackingSectionHeader.click()
  }

  /**
   * Click on All Accounts row to navigate to transactions.
   */
  async clickAllAccounts() {
    await this.allAccountsRow.click()
  }

  // ==================== Edit Mode / Reordering ====================

  /**
   * Check if currently in edit mode.
   */
  async isInEditMode(): Promise<boolean> {
    const buttonText = await this.editOrderButton.textContent()
    return buttonText?.includes('Done') ?? false
  }

  /**
   * Enter edit mode by clicking the Edit Order button.
   */
  async enterEditMode() {
    if (await this.isInEditMode()) return
    // Ensure accounts are loaded before entering edit mode
    // (initializeSortOrders needs accounts in the store to assign sort orders)
    await this.page
      .locator('[data-testid="budget-account-item"], [data-testid="tracking-account-item"]')
      .first()
      .waitFor({ state: 'visible', timeout: 10000 })
    await this.editOrderButton.click()
    await expect(this.editOrderButton).toContainText('Done')
  }

  /**
   * Exit edit mode by clicking the Done button.
   */
  async exitEditMode() {
    if (!(await this.isInEditMode())) return
    await this.editOrderButton.click()
    await expect(this.editOrderButton).toContainText('Edit Order')
  }

  /**
   * Assert we are in edit mode.
   */
  async expectInEditMode() {
    await expect(this.editOrderButton).toContainText('Done')
    await expect(this.addAccountButton).toBeHidden()
  }

  /**
   * Assert we are not in edit mode.
   */
  async expectNotInEditMode() {
    await expect(this.editOrderButton).toContainText('Edit Order')
    await expect(this.addAccountButton).toBeVisible()
  }

  /**
   * Get the up button for an account.
   */
  getAccountUpButton(accountName: string): Locator {
    const account = this.getAccountListItem(accountName)
    return account.locator('[data-testid="move-up-button"]')
  }

  /**
   * Get the down button for an account.
   */
  getAccountDownButton(accountName: string): Locator {
    const account = this.getAccountListItem(accountName)
    return account.locator('[data-testid="move-down-button"]')
  }

  /**
   * Move an account up within its section.
   */
  async moveAccountUp(accountName: string) {
    const upButton = this.getAccountUpButton(accountName)
    await expect(upButton).toBeVisible()
    // Get the current up button disabled state - if disabled, it means we're already at top
    const isDisabled = await upButton.isDisabled()
    if (isDisabled) return

    // Ensure the button is not disabled due to an in-progress reorder
    await expect(upButton).toBeEnabled()

    // swapAccountSortOrders makes 2 sequential PATCH requests
    let patchCount = 0
    const responsePromise = this.page.waitForResponse((r) => {
      if (r.url().includes('/accounts/') && r.request().method() === 'PATCH') {
        patchCount++
        return patchCount >= 2
      }
      return false
    })
    await upButton.click()
    await responsePromise
    // Wait for the button to be enabled again (UI has re-rendered after reorder)
    await expect(upButton).toBeEnabled({ timeout: 5000 }).catch(() => {
      // Button may be disabled if now at top - that's ok
    })
  }

  /**
   * Move an account down within its section.
   */
  async moveAccountDown(accountName: string) {
    const downButton = this.getAccountDownButton(accountName)
    // Get the current down button disabled state
    const isDisabled = await downButton.isDisabled()
    if (isDisabled) return

    // Ensure the button is not disabled due to an in-progress reorder
    await expect(downButton).toBeEnabled()

    // swapAccountSortOrders makes 2 sequential PATCH requests
    let patchCount = 0
    const responsePromise = this.page.waitForResponse((r) => {
      if (r.url().includes('/accounts/') && r.request().method() === 'PATCH') {
        patchCount++
        return patchCount >= 2
      }
      return false
    })
    await downButton.click()
    await responsePromise
    // Wait for the button to be enabled again (UI has re-rendered after reorder)
    await expect(downButton).toBeEnabled({ timeout: 5000 }).catch(() => {
      // Button may be disabled if now at bottom - that's ok
    })
  }

  /**
   * Get the order of account names in a section.
   */
  async getAccountOrderInSection(section: 'budget' | 'tracking'): Promise<string[]> {
    const items = section === 'budget' ? this.budgetAccountItems : this.trackingAccountItems
    const count = await items.count()
    const names: string[] = []

    for (let i = 0; i < count; i++) {
      // Get just the account name from the list item title
      const title = items.nth(i).locator('.v-list-item-title, [class*="v-list-item__content"] span')
      const text = await title.first().textContent()
      if (text) {
        names.push(text.trim())
      }
    }

    return names
  }

  /**
   * Assert the order of specific accounts in a section.
   * Filters to only the accounts in expectedOrder and checks their relative order.
   */
  async expectAccountOrderInSection(section: 'budget' | 'tracking', expectedOrder: string[]) {
    // Wait for the expected order to be reflected in the DOM (polling)
    // Use a longer timeout to handle slow re-renders after reordering
    await expect(async () => {
      const allAccounts = await this.getAccountOrderInSection(section)
      // Filter to only the accounts we care about, preserving their order
      const relevantAccounts = allAccounts.filter((name) => expectedOrder.includes(name))
      expect(relevantAccounts).toEqual(expectedOrder)
    }).toPass({ timeout: 10000 })
  }
}
