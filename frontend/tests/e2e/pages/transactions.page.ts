import { type Page, type Locator, expect } from '@playwright/test'
import { BasePage } from './base.page'
import { TransactionFormPage } from './transaction-form.page'

/**
 * Page object for the Transactions list view.
 * Supports both mobile (list) and desktop (table) layouts.
 */
export class TransactionsPage extends BasePage {
  // Header elements
  readonly addTransactionButton: Locator
  readonly pageTitle: Locator

  // Transaction form dialog
  readonly formDialog: TransactionFormPage

  // Filter elements
  readonly accountFilter: Locator
  readonly filtersButton: Locator

  // Filter drawer elements
  readonly filterDrawer: Locator
  readonly filterDrawerPayeeAutocomplete: Locator
  readonly filterDrawerLocationAutocomplete: Locator
  readonly filterDrawerEnvelopeAutocomplete: Locator
  readonly filterDrawerHideReconciledSwitch: Locator
  readonly filterDrawerAccountTypeAll: Locator
  readonly filterDrawerAccountTypeBudget: Locator
  readonly filterDrawerAccountTypeTracking: Locator
  readonly filterDrawerApplyButton: Locator
  readonly filterDrawerClearButton: Locator
  readonly filterDrawerCloseButton: Locator

  // Transaction list (mobile) / table (desktop)
  readonly transactionGroups: Locator
  readonly transactionListItems: Locator // Mobile: v-list-item
  readonly transactionTableRows: Locator // Desktop: tr.transaction-row
  readonly loadMoreButton: Locator
  readonly loadingSpinner: Locator

  // Empty state
  readonly emptyState: Locator
  readonly emptyStateAddButton: Locator

  constructor(page: Page) {
    super(page)

    // Header
    this.pageTitle = page.locator('h1').filter({ hasText: 'Transactions' })
    this.addTransactionButton = page.getByRole('button', { name: 'Add Transaction' }).first()

    // Transaction form dialog
    this.formDialog = new TransactionFormPage(page)

    // Main page filters
    this.accountFilter = page.locator('.v-select').filter({ hasText: 'Account' })
    this.filtersButton = page.getByRole('button', { name: 'Filters' })

    // Filter drawer (VBottomSheet)
    this.filterDrawer = page.locator('.v-bottom-sheet')
    this.filterDrawerPayeeAutocomplete = this.filterDrawer.locator('.v-autocomplete').filter({ hasText: 'Payee' })
    this.filterDrawerLocationAutocomplete = this.filterDrawer.locator('.v-autocomplete').filter({ hasText: 'Location' })
    this.filterDrawerEnvelopeAutocomplete = this.filterDrawer.locator('.v-autocomplete').filter({ hasText: 'Envelope' })
    this.filterDrawerHideReconciledSwitch = this.filterDrawer.locator('.v-switch').filter({ hasText: 'Hide Reconciled' })
    this.filterDrawerAccountTypeAll = this.filterDrawer.getByLabel('All Accounts')
    this.filterDrawerAccountTypeBudget = this.filterDrawer.getByLabel('Budget Accounts Only')
    this.filterDrawerAccountTypeTracking = this.filterDrawer.getByLabel('Tracking Accounts Only')
    this.filterDrawerApplyButton = this.filterDrawer.getByRole('button', { name: 'Apply Filters' })
    this.filterDrawerClearButton = this.filterDrawer.getByRole('button', { name: 'Clear All' })
    this.filterDrawerCloseButton = this.filterDrawer.locator('.v-btn--icon').first()

    // Transaction list (mobile) and table (desktop)
    this.transactionGroups = page.locator('.date-header-row, h3.text-subtitle-2')
    this.transactionListItems = page.locator('.v-list-item') // Mobile layout
    this.transactionTableRows = page.locator('tr.transaction-row') // Desktop table layout
    this.loadMoreButton = page.getByRole('button', { name: 'Load More' })
    this.loadingSpinner = page.locator('.v-progress-circular')

    // Empty state
    this.emptyState = page.locator('text=No transactions yet')
    this.emptyStateAddButton = page.locator('.v-card').filter({ hasText: 'No transactions yet' }).getByRole('button', { name: 'Add Transaction' })
  }

  /**
   * Check if the page is showing the desktop table layout.
   * Waits for transactions to load before determining layout.
   */
  async isTableLayout(): Promise<boolean> {
    // Wait for either a transaction table row or a list item in the main content
    await this.page.locator('main tr.transaction-row, main .v-list-item').first()
      .waitFor({ state: 'visible', timeout: 10000 }).catch(() => {})
    return await this.page.locator('.v-table').isVisible({ timeout: 500 }).catch(() => false)
  }

  /**
   * Get the transaction items locator appropriate for the current layout.
   */
  get transactionItems(): Locator {
    // This getter returns the mobile list items for backwards compatibility
    // Use getTransactionLocator() for layout-aware selection
    return this.transactionListItems
  }

  async goto() {
    await this.page.goto('/transactions')
    await this.waitForPageLoad()
  }

  /**
   * Click the add transaction button to open the dialog.
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
   * Filter transactions by account.
   */
  async filterByAccount(accountName: string) {
    await this.accountFilter.click()
    // Wait for dropdown menu to appear and target only items within the overlay menu
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
        await this.waitForPageLoad()
        return
      }
    }
    // Fallback to first match if exact not found
    await menu.locator('.v-list-item').filter({ hasText: accountName }).first().click()
    await this.waitForPageLoad()
  }

  /**
   * Clear account filter (show all accounts).
   */
  async clearAccountFilter() {
    await this.filterByAccount('All Accounts')
  }

  /**
   * Open the filters drawer.
   */
  async openFiltersDrawer() {
    await this.filtersButton.click()
    await expect(this.filterDrawer).toBeVisible({ timeout: 5000 })
  }

  /**
   * Close the filters drawer without applying.
   */
  async closeFiltersDrawer() {
    await this.filterDrawerCloseButton.click()
    await expect(this.filterDrawer).toBeHidden({ timeout: 5000 })
  }

  /**
   * Apply filters and close the drawer.
   */
  async applyFilters() {
    const responsePromise = this.page.waitForResponse(
      (response) =>
        response.url().includes('/transactions') &&
        response.request().method() === 'GET' &&
        !response.url().includes('/unallocated-count')
    )
    await this.filterDrawerApplyButton.click()
    await responsePromise
    await expect(this.filterDrawer).toBeHidden({ timeout: 5000 })
    await this.waitForPageLoad()
  }

  /**
   * Clear all filters and close the drawer.
   */
  async clearAllFilters() {
    const responsePromise = this.page.waitForResponse(
      (response) =>
        response.url().includes('/transactions') &&
        response.request().method() === 'GET' &&
        !response.url().includes('/unallocated-count')
    )
    await this.filterDrawerClearButton.click()
    await responsePromise
    await expect(this.filterDrawer).toBeHidden({ timeout: 5000 })
    await this.waitForPageLoad()
  }

  /**
   * Filter by budget accounts only via the filter drawer.
   */
  async filterByBudgetAccounts() {
    await this.openFiltersDrawer()
    await this.filterDrawerAccountTypeBudget.click()
    await this.applyFilters()
  }

  /**
   * Filter by tracking accounts only via the filter drawer.
   */
  async filterByTrackingAccounts() {
    await this.openFiltersDrawer()
    await this.filterDrawerAccountTypeTracking.click()
    await this.applyFilters()
  }

  /**
   * Filter transactions by envelope name.
   */
  async filterByEnvelope(envelopeName: string) {
    await this.openFiltersDrawer()
    // Click to open the envelope autocomplete dropdown
    await this.filterDrawerEnvelopeAutocomplete.click()
    // Wait for dropdown to appear and select the envelope
    const menu = this.page.locator('.v-overlay--active .v-list')
    await menu.waitFor({ state: 'visible', timeout: 5000 })
    await menu.locator('.v-list-item').filter({ hasText: envelopeName }).first().click()
    await this.applyFilters()
  }

  /**
   * Filter transactions by location name.
   */
  async filterByLocation(locationName: string) {
    await this.openFiltersDrawer()
    // Click to open the location autocomplete dropdown
    await this.filterDrawerLocationAutocomplete.click()
    // Type the location name to filter/search
    const locationInput = this.filterDrawerLocationAutocomplete.locator('input')
    await locationInput.fill(locationName)
    // Wait for dropdown to appear and select the location
    const menu = this.page.locator('.v-overlay--active .v-list')
    await menu.waitFor({ state: 'visible', timeout: 5000 })
    await menu.locator('.v-list-item').filter({ hasText: locationName }).first().click()
    await this.applyFilters()
  }

  /**
   * Filter to hide reconciled transactions.
   */
  async filterByHideReconciled() {
    await this.openFiltersDrawer()
    const switchInput = this.filterDrawerHideReconciledSwitch.locator('input[type="checkbox"]')
    const wasChecked = await switchInput.isChecked()
    await switchInput.evaluate((el: HTMLInputElement) => el.click())
    await expect(switchInput).toBeChecked({ checked: !wasChecked })
    await this.applyFilters()
  }

  /**
   * Get the active filter count from the badge on the Filters button.
   */
  async getActiveFilterCount(): Promise<number> {
    // The badge is rendered as a status element near the Filters button
    const badgeWrapper = this.filtersButton.locator('..').locator('role=status')
    if (await badgeWrapper.isVisible({ timeout: 1000 }).catch(() => false)) {
      const text = await badgeWrapper.textContent()
      return parseInt(text || '0', 10)
    }
    return 0
  }

  /**
   * Check if a transaction shows the unallocated warning icon.
   */
  async transactionHasUnallocatedWarning(payeeName: string): Promise<boolean> {
    const isTable = await this.isTableLayout()
    if (isTable) {
      const row = this.page.locator('tr.transaction-row').filter({
        has: this.page.locator('td span.font-weight-medium', { hasText: payeeName }),
      }).first()
      const warningIcon = row.locator('.mdi-alert-circle-outline')
      return await warningIcon.isVisible({ timeout: 1000 }).catch(() => false)
    } else {
      const item = this.page.locator('.v-list-item').filter({ hasText: payeeName }).first()
      const warningIcon = item.locator('.mdi-alert-circle-outline')
      return await warningIcon.isVisible({ timeout: 1000 }).catch(() => false)
    }
  }

  /**
   * Get the envelope name displayed for a transaction.
   */
  async getTransactionEnvelope(payeeName: string): Promise<string | null> {
    const isTable = await this.isTableLayout()
    if (isTable) {
      // In table layout, envelope is in the 3rd column (index 2)
      const row = this.page.locator('tr.transaction-row').filter({
        has: this.page.locator('td span.font-weight-medium', { hasText: payeeName }),
      }).first()
      const cells = row.locator('td')
      const envelopeCell = cells.nth(2)
      const text = await envelopeCell.textContent()
      return text?.trim() === '-' ? null : text?.trim() || null
    } else {
      const item = this.page.locator('.v-list-item').filter({ hasText: payeeName }).first()
      const subtitle = item.locator('.v-list-item-subtitle')
      const text = await subtitle.textContent()
      // Parse envelope from subtitle (format: "Date · Account · Envelope [chip]")
      // The envelope may be followed by status chips like "Scheduled", "Pending", etc.
      const parts = text?.split('·').map((p) => p.trim()) || []
      if (parts.length >= 3) {
        // The envelope part may contain extra text from chips, so extract just the envelope name
        let envelopePart = parts[2] || ''
        // Remove any chip text that might be appended (status chips appear after envelope)
        const chipKeywords = ['Scheduled', 'Pending', 'Split']
        for (const keyword of chipKeywords) {
          if (envelopePart.includes(keyword)) {
            envelopePart = envelopePart.replace(keyword, '').trim()
          }
        }
        return envelopePart || null
      }
      return null
    }
  }

  /**
   * Click on a transaction to open the edit dialog.
   */
  async clickTransaction(payeeName: string) {
    const isTable = await this.isTableLayout()
    if (isTable) {
      const row = this.page.locator('tr.transaction-row').filter({
        has: this.page.locator('td span.font-weight-medium', { hasText: payeeName }),
      }).first()
      await row.click()
    } else {
      const item = this.page
        .locator('.v-main .v-list-item')
        .filter({ has: this.page.locator('.v-list-item-title', { hasText: new RegExp(`^${payeeName}$`) }) })
        .first()
      await item.click()
    }
    await this.formDialog.waitForDialog()
  }

  /**
   * Load more transactions if available.
   */
  async loadMore() {
    if (await this.loadMoreButton.isVisible()) {
      await this.loadMoreButton.click()
      await this.waitForPageLoad()
    }
  }

  /**
   * Get the number of transaction groups (dates).
   */
  async getGroupCount(): Promise<number> {
    return await this.transactionGroups.count()
  }

  /**
   * Get the number of visible transactions.
   */
  async getTransactionCount(): Promise<number> {
    const isTable = await this.isTableLayout()
    if (isTable) {
      return await this.transactionTableRows.count()
    } else {
      return await this.transactionListItems.count()
    }
  }

  /**
   * Assert empty state is shown.
   */
  async expectEmptyState() {
    await expect(this.emptyState).toBeVisible()
    await expect(this.emptyStateAddButton).toBeVisible()
  }

  /**
   * Assert transactions are shown.
   */
  async expectTransactionsVisible() {
    await expect(this.emptyState).not.toBeVisible()
    const count = await this.getTransactionCount()
    expect(count).toBeGreaterThan(0)
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
      // Mobile list: find list item with exact payee name in the title
      const item = this.page
        .locator('.v-main .v-list-item')
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
      // Mobile list: verify no list item with exact payee name in the title
      const item = this.page
        .locator('.v-main .v-list-item')
        .filter({ has: this.page.locator('.v-list-item-title', { hasText: new RegExp(`^${payeeName}$`) }) })
        .first()
      await expect(item).not.toBeVisible()
    }
  }

  /**
   * Check if a transaction shows the reconciled checkmark icon.
   */
  async transactionHasReconciledIcon(payeeName: string): Promise<boolean> {
    const isTable = await this.isTableLayout()
    if (isTable) {
      const row = this.page.locator('tr.transaction-row').filter({
        has: this.page.locator('td span.font-weight-medium', { hasText: payeeName }),
      }).first()
      const reconciledIcon = row.locator('i.mdi-check-decagram')
      return await reconciledIcon.isVisible({ timeout: 2000 }).catch(() => false)
    } else {
      const item = this.page.locator('.v-list-item').filter({ hasText: payeeName }).first()
      // Vuetify renders icons with the icon name as a class on the i element
      const reconciledIcon = item.locator('i.mdi-check-decagram')
      return await reconciledIcon.isVisible({ timeout: 2000 }).catch(() => false)
    }
  }

  /**
   * Check if a transaction shows the cleared checkmark icon.
   */
  async transactionHasClearedIcon(payeeName: string): Promise<boolean> {
    const isTable = await this.isTableLayout()
    if (isTable) {
      const row = this.page.locator('tr.transaction-row').filter({
        has: this.page.locator('td span.font-weight-medium', { hasText: payeeName }),
      }).first()
      const clearedIcon = row.locator('i.mdi-check-circle')
      return await clearedIcon.isVisible({ timeout: 2000 }).catch(() => false)
    } else {
      const item = this.page.locator('.v-list-item').filter({ hasText: payeeName }).first()
      // Cleared transactions show mdi-check-circle (filled)
      const clearedIcon = item.locator('i.mdi-check-circle')
      return await clearedIcon.isVisible({ timeout: 2000 }).catch(() => false)
    }
  }

  /**
   * Toggle the hide reconciled filter.
   * Opens the filter drawer, toggles the switch, and applies the filter.
   */
  async toggleHideReconciledFilter() {
    await this.openFiltersDrawer()
    // Click the switch input directly for reliable toggling in Vuetify 3
    const switchInput = this.filterDrawerHideReconciledSwitch.locator('input')
    await switchInput.scrollIntoViewIfNeeded()
    await switchInput.click({ force: true })
    await this.applyFilters()
  }

  /**
   * Check if the hide reconciled filter is currently active.
   * Note: This re-opens the drawer which may reset local state,
   * so it's better to verify filter behavior directly.
   */
  async isHideReconciledFilterActive(): Promise<boolean> {
    await this.openFiltersDrawer()
    // Check if the switch input is checked
    const switchInput = this.filterDrawerHideReconciledSwitch.locator('input')
    const isChecked = await switchInput.isChecked()
    await this.closeFiltersDrawer()
    return isChecked
  }
}
