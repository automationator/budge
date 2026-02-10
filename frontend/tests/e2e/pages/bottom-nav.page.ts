import { type Page, type Locator, expect } from '@playwright/test'

/**
 * Page object for the BottomNav component (mobile only).
 * The bottom navigation appears on mobile viewports (< 960px width).
 */
export class BottomNavPage {
  readonly page: Page
  readonly bottomNav: Locator
  readonly envelopesButton: Locator
  readonly accountsButton: Locator
  readonly addButton: Locator
  readonly reportsButton: Locator
  readonly moreButton: Locator
  readonly bottomSheet: Locator

  constructor(page: Page) {
    this.page = page
    this.bottomNav = page.locator('.v-bottom-navigation')
    this.envelopesButton = this.bottomNav.locator('.v-btn').filter({ hasText: 'Envelopes' })
    this.accountsButton = this.bottomNav.locator('.v-btn').filter({ hasText: 'Accounts' })
    this.addButton = this.bottomNav.locator('.v-btn').filter({ hasText: 'Add' })
    this.reportsButton = this.bottomNav.locator('.v-btn').filter({ hasText: 'Reports' })
    this.moreButton = this.bottomNav.locator('.v-btn').filter({ hasText: 'More' })
    this.bottomSheet = page.locator('.v-bottom-sheet')
  }

  async waitForVisible() {
    await expect(this.bottomNav).toBeVisible({ timeout: 10000 })
  }

  async expectVisible() {
    await expect(this.bottomNav).toBeVisible()
  }

  async expectHidden() {
    await expect(this.bottomNav).toBeHidden()
  }

  async goToEnvelopes() {
    await this.envelopesButton.click()
  }

  async goToAccounts() {
    await this.accountsButton.click()
  }

  async openAddTransaction() {
    await this.addButton.click()
  }

  async goToReports() {
    await this.reportsButton.click()
  }

  async openMoreMenu() {
    await this.moreButton.click()
    await expect(this.bottomSheet).toBeVisible()
  }

  async expectMoreMenuVisible() {
    await expect(this.bottomSheet).toBeVisible()
  }

  async expectMoreMenuHidden() {
    await expect(this.bottomSheet).toBeHidden()
  }

  async closeMoreMenu() {
    await this.page.keyboard.press('Escape')
    await expect(this.bottomSheet).toBeHidden()
  }

  async clickMoreMenuItem(itemName: string) {
    await this.bottomSheet.getByText(itemName, { exact: true }).click()
  }

  async goToTransactions() {
    await this.openMoreMenu()
    await this.clickMoreMenuItem('Transactions')
  }

  async goToRecurring() {
    await this.openMoreMenu()
    await this.clickMoreMenuItem('Recurring')
  }

  async goToAllocationRules() {
    await this.openMoreMenu()
    await this.clickMoreMenuItem('Allocation Rules')
  }

  async goToNotifications() {
    await this.openMoreMenu()
    await this.clickMoreMenuItem('Notifications')
  }

  async expectEnvelopesActive() {
    await expect(this.envelopesButton).toHaveClass(/v-btn--active/)
  }

  async expectAccountsActive() {
    await expect(this.accountsButton).toHaveClass(/v-btn--active/)
  }

  async expectReportsActive() {
    await expect(this.reportsButton).toHaveClass(/v-btn--active/)
  }

  async expectMoreActive() {
    await expect(this.moreButton).toHaveClass(/v-btn--active/)
  }
}
