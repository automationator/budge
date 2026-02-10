import { type Page, type Locator, expect } from '@playwright/test'

/**
 * Page object for the BudgetMenu component.
 * This component appears in both the NavDrawer (desktop) and BottomNav (mobile).
 */
export class BudgetMenuPage {
  readonly page: Page

  // Budget menu header (activates dropdown)
  readonly menuHeader: Locator
  readonly budgetNameDisplay: Locator
  readonly usernameDisplay: Locator

  // Dropdown menu
  readonly dropdownMenu: Locator
  readonly budgetsSubheader: Locator

  // Create budget dialog
  readonly createBudgetDialog: Locator
  readonly budgetNameInput: Locator
  readonly createButton: Locator
  readonly cancelButton: Locator

  constructor(page: Page) {
    this.page = page

    // The budget menu header with the budget name and dropdown chevron
    this.menuHeader = page.locator('.budget-selector-header')
    this.budgetNameDisplay = this.menuHeader.locator('.v-list-item-title')
    this.usernameDisplay = this.menuHeader.locator('.v-list-item-subtitle')

    // The dropdown menu that appears when clicking the header
    this.dropdownMenu = page.locator('.v-overlay__content .v-list')
    this.budgetsSubheader = this.dropdownMenu.locator('.v-list-subheader', { hasText: 'Budgets' })

    // Create budget dialog
    this.createBudgetDialog = page.locator('.v-dialog .v-card', { hasText: 'Create New Budget' })
    this.budgetNameInput = this.createBudgetDialog.locator('input')
    this.createButton = this.createBudgetDialog.getByRole('button', { name: 'Create' })
    this.cancelButton = this.createBudgetDialog.getByRole('button', { name: 'Cancel' })
  }

  /**
   * Wait for the budget menu header to be visible.
   */
  async waitForVisible() {
    // Wait for page to finish loading first (Vue app mounted)
    await this.page.waitForLoadState('domcontentloaded')
    await this.page.locator('.v-main, .v-application').first().waitFor({
      state: 'visible',
      timeout: 20000,
    })
    // Now wait for the budget menu header specifically
    await expect(this.menuHeader).toBeVisible({ timeout: 15000 })
  }

  /**
   * Open the budget dropdown menu.
   */
  async openMenu() {
    await this.menuHeader.click()
    await expect(this.dropdownMenu).toBeVisible()
  }

  /**
   * Close the dropdown menu if open.
   */
  async closeMenu() {
    // Click outside the menu to close it
    await this.page.keyboard.press('Escape')
    await expect(this.dropdownMenu).not.toBeVisible()
  }

  /**
   * Get the current budget name displayed in the header.
   */
  async getCurrentBudgetName(): Promise<string> {
    return (await this.budgetNameDisplay.textContent()) ?? ''
  }

  /**
   * Get the username displayed in the header.
   */
  async getUsername(): Promise<string> {
    const text = (await this.usernameDisplay.textContent()) ?? ''
    // Remove the @ prefix if present
    return text.startsWith('@') ? text.slice(1) : text
  }

  /**
   * Get all budget names from the dropdown.
   */
  async getBudgetNames(): Promise<string[]> {
    await this.openMenu()
    const budgetItems = this.dropdownMenu.locator('.v-list-item:has(.mdi-account-group-outline)')
    const count = await budgetItems.count()
    const names: string[] = []
    for (let i = 0; i < count; i++) {
      const name = await budgetItems.nth(i).locator('.v-list-item-title').textContent()
      if (name) names.push(name)
    }
    return names
  }

  /**
   * Check if a specific budget has the active checkmark.
   */
  async isBudgetActive(budgetName: string): Promise<boolean> {
    const budgetItem = this.dropdownMenu.locator('.v-list-item', { hasText: budgetName })
    const checkIcon = budgetItem.locator('.mdi-check')
    return checkIcon.isVisible()
  }

  /**
   * Switch to a different budget by name.
   */
  async selectBudget(budgetName: string) {
    await this.openMenu()
    const budgetItem = this.dropdownMenu.locator('.v-list-item', { hasText: budgetName })
    await budgetItem.click()
    await expect(this.dropdownMenu).not.toBeVisible()
  }

  /**
   * Open the create budget dialog.
   */
  async openCreateBudgetDialog() {
    await this.openMenu()
    const createItem = this.dropdownMenu.locator('.v-list-item', { hasText: 'Create New Budget' })
    await createItem.click()
    await expect(this.createBudgetDialog).toBeVisible()
  }

  /**
   * Create a new budget using the dialog.
   */
  async createBudget(name: string) {
    await this.openCreateBudgetDialog()
    await this.budgetNameInput.fill(name)
    await this.createButton.click()
    await expect(this.createBudgetDialog).not.toBeVisible()
  }

  /**
   * Navigate to Settings via the dropdown menu.
   */
  async goToSettings() {
    await this.openMenu()
    const settingsItem = this.dropdownMenu.locator('.v-list-item:has(.mdi-cog)')
    await settingsItem.click()
    await expect(this.page).toHaveURL(/\/settings/)
  }

  /**
   * Navigate to Manage Payees via the dropdown menu.
   */
  async goToManagePayees() {
    await this.openMenu()
    const payeesItem = this.dropdownMenu.locator('.v-list-item:has(.mdi-account-cash)')
    await payeesItem.click()
    await expect(this.page).toHaveURL(/\/settings\/payees/)
  }

  /**
   * Navigate to Budget Settings via the dropdown menu.
   */
  async goToBudgetSettings() {
    await this.openMenu()
    const settingsItem = this.dropdownMenu.locator('.v-list-item:has(.mdi-cog-outline)')
    await settingsItem.click()
    await expect(this.page).toHaveURL(/\/settings\/budget-settings/)
  }

  /**
   * Log out via the dropdown menu.
   */
  async logout() {
    await this.openMenu()
    const logoutItem = this.dropdownMenu.locator('.v-list-item:has(.mdi-logout)')
    await logoutItem.click()
    await expect(this.page).toHaveURL(/\/login/)
  }
}
