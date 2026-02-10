import { type Page, type Locator, expect } from '@playwright/test'

/**
 * Page object for the NavDrawer component.
 * This is not a standalone page but a component that appears on desktop screens.
 */
export class NavDrawerPage {
  readonly page: Page
  readonly drawer: Locator

  // Main navigation items
  readonly envelopesLink: Locator
  readonly transactionsLink: Locator
  readonly reportsLink: Locator

  // More section
  readonly moreSection: Locator
  readonly allocationRulesLink: Locator
  readonly recurringTransactionsLink: Locator

  // Accounts section
  readonly allAccountsLink: Locator
  readonly budgetSection: Locator
  readonly trackingSection: Locator

  // Add Account button
  readonly addAccountButton: Locator

  constructor(page: Page) {
    this.page = page
    // Use the left-side drawer specifically (not the notifications drawer on the right)
    this.drawer = page.locator('.v-navigation-drawer--left')

    // Main navigation items
    this.envelopesLink = this.drawer.getByRole('link', { name: 'Envelopes' })
    this.transactionsLink = this.drawer.getByRole('link', { name: 'Transactions' })
    this.reportsLink = this.drawer.getByRole('link', { name: 'Reports' })

    // More section
    this.moreSection = this.drawer.locator('.v-list-item', { hasText: 'More' })
    this.allocationRulesLink = this.drawer.getByRole('link', { name: 'Allocation Rules' })
    this.recurringTransactionsLink = this.drawer.getByRole('link', { name: 'Recurring Transactions' })

    // Accounts section - use role-based selectors to find the section headers
    this.allAccountsLink = this.drawer.getByRole('link', { name: 'All Accounts' })
    // Budget section header is a listitem (not a link) with text starting with "Budget"
    this.budgetSection = this.drawer.getByRole('listitem').filter({ hasText: /^Budget/ })
    // Tracking section header is a listitem (not a link) with text starting with "Tracking"
    this.trackingSection = this.drawer.getByRole('listitem').filter({ hasText: /^Tracking/ })

    // Add Account button (opens dialog, not a link)
    this.addAccountButton = this.drawer.getByRole('button', { name: 'Add Account' })
  }

  /**
   * Wait for the nav drawer to be visible.
   */
  async waitForVisible() {
    await expect(this.drawer).toBeVisible({ timeout: 10000 })
  }

  /**
   * Expand the "More" collapsible section.
   */
  async expandMore() {
    // Check if already expanded (child items are visible)
    const isExpanded = await this.allocationRulesLink.isVisible().catch(() => false)
    if (!isExpanded) {
      await this.moreSection.click()
      await expect(this.allocationRulesLink).toBeVisible()
    }
  }

  /**
   * Expand the Budget accounts section by clicking the header if collapsed.
   */
  async expandBudget() {
    await this.budgetSection.waitFor({ state: 'visible' })
    // Check for down chevron class indicating collapsed state
    const downIcon = this.budgetSection.locator('.v-icon.mdi-chevron-down')
    // Only click if section is collapsed
    if (await downIcon.isVisible().catch(() => false)) {
      await this.budgetSection.click()
    }
    // Wait for expanded state (up chevron class)
    await expect(this.budgetSection.locator('.v-icon.mdi-chevron-up')).toBeVisible({ timeout: 5000 })
  }

  /**
   * Collapse the Budget accounts section by clicking the header if expanded.
   */
  async collapseBudget() {
    await this.budgetSection.waitFor({ state: 'visible' })
    // Check for up chevron class indicating expanded state
    const upIcon = this.budgetSection.locator('.v-icon.mdi-chevron-up')
    // Only click if section is expanded
    if (await upIcon.isVisible().catch(() => false)) {
      await this.budgetSection.click()
    }
    // Wait for collapsed state (down chevron class)
    await expect(this.budgetSection.locator('.v-icon.mdi-chevron-down')).toBeVisible({ timeout: 5000 })
  }

  /**
   * Expand the Tracking accounts section by clicking the header if collapsed.
   */
  async expandTracking() {
    await this.trackingSection.waitFor({ state: 'visible' })
    // Check for down chevron class indicating collapsed state
    const downIcon = this.trackingSection.locator('.v-icon.mdi-chevron-down')
    // Only click if section is collapsed
    if (await downIcon.isVisible().catch(() => false)) {
      await this.trackingSection.click()
    }
    // Wait for expanded state (up chevron class)
    await expect(this.trackingSection.locator('.v-icon.mdi-chevron-up')).toBeVisible({ timeout: 5000 })
  }

  /**
   * Collapse the Tracking accounts section by clicking the header if expanded.
   */
  async collapseTracking() {
    await this.trackingSection.waitFor({ state: 'visible' })
    // Check for up chevron class indicating expanded state
    const upIcon = this.trackingSection.locator('.v-icon.mdi-chevron-up')
    // Only click if section is expanded
    if (await upIcon.isVisible().catch(() => false)) {
      await this.trackingSection.click()
    }
    // Wait for collapsed state (down chevron class)
    await expect(this.trackingSection.locator('.v-icon.mdi-chevron-down')).toBeVisible({ timeout: 5000 })
  }

  /**
   * Click on a specific account in the sidebar by name.
   */
  async clickAccount(accountName: string) {
    await this.drawer.getByRole('link', { name: accountName }).click()
  }

  /**
   * Assert the main navigation items are visible.
   */
  async expectMainNavVisible() {
    await expect(this.envelopesLink).toBeVisible()
    await expect(this.transactionsLink).toBeVisible()
    await expect(this.reportsLink).toBeVisible()
  }

  /**
   * Assert the Budget section is visible.
   */
  async expectBudgetSectionVisible() {
    await expect(this.budgetSection).toBeVisible()
  }

  /**
   * Assert the Tracking section is visible (only if tracking accounts exist).
   */
  async expectTrackingSectionVisible() {
    await expect(this.trackingSection).toBeVisible()
  }

  /**
   * Assert the Tracking section is not visible.
   */
  async expectTrackingSectionHidden() {
    await expect(this.trackingSection).not.toBeVisible()
  }

  /**
   * Assert an account is visible in the sidebar.
   * Waits for accounts to load and appear in the nav drawer.
   */
  async expectAccountVisible(accountName: string, timeout = 15000) {
    // Wait for the account to appear - it may take time to load
    const accountLocator = this.drawer.getByText(accountName, { exact: false })
    await expect(accountLocator).toBeVisible({ timeout })
  }

  /**
   * Navigate to Envelopes via sidebar.
   */
  async goToEnvelopes() {
    await this.envelopesLink.click()
  }

  /**
   * Navigate to Transactions via sidebar.
   */
  async goToTransactions() {
    await this.transactionsLink.click()
  }

  /**
   * Navigate to Reports via sidebar.
   */
  async goToReports() {
    await this.reportsLink.click()
  }

  /**
   * Navigate to All Accounts transactions.
   */
  async goToAllAccountsTransactions() {
    await this.allAccountsLink.click()
  }

  /**
   * Open the Add Account dialog.
   */
  async openAddAccountDialog() {
    await this.addAccountButton.click()
  }
}
