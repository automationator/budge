import { type Page, type Locator, expect } from '@playwright/test'
import { BasePage } from './base.page'

/**
 * Page object for the Envelope detail view.
 */
export class EnvelopeDetailPage extends BasePage {
  // Navigation
  readonly backButton: Locator

  // Header
  readonly envelopeName: Locator
  readonly groupName: Locator
  readonly starButton: Locator
  readonly editButton: Locator

  // Balance card
  readonly balanceCard: Locator
  readonly currentBalance: Locator
  readonly transferButton: Locator
  readonly progressBar: Locator
  readonly targetBalance: Locator
  readonly description: Locator

  // Activity section
  readonly activitySection: Locator
  readonly allocationsCount: Locator
  readonly allocationItems: Locator
  readonly emptyActivityState: Locator

  // Delete button
  readonly deleteButton: Locator

  // Edit Dialog
  readonly editDialog: Locator
  readonly editNameInput: Locator
  readonly editGroupSelect: Locator
  readonly editTargetBalanceInput: Locator
  readonly editDescriptionInput: Locator
  readonly saveButton: Locator
  readonly cancelEditButton: Locator

  // Transfer Dialog
  readonly transferDialog: Locator
  readonly transferDirectionToggle: Locator
  readonly transferToButton: Locator
  readonly transferFromButton: Locator
  readonly transferToSelect: Locator
  readonly transferAmountInput: Locator
  readonly confirmTransferButton: Locator
  readonly cancelTransferButton: Locator

  // Delete Dialog
  readonly deleteDialog: Locator
  readonly confirmDeleteButton: Locator
  readonly cancelDeleteButton: Locator

  // Allocation Rules Section
  readonly allocationRulesSection: Locator
  readonly addRuleButton: Locator
  readonly ruleItems: Locator
  readonly emptyRulesState: Locator
  readonly manageAllRulesLink: Locator

  // Allocation Rule Dialog
  readonly ruleDialog: Locator
  readonly ruleNameInput: Locator
  readonly ruleTypeSelect: Locator
  readonly ruleAmountInput: Locator
  readonly rulePriorityInput: Locator
  readonly ruleRespectTargetSwitch: Locator
  readonly ruleActiveSwitch: Locator
  readonly saveRuleButton: Locator
  readonly cancelRuleButton: Locator

  // Delete Rule Dialog
  readonly deleteRuleDialog: Locator
  readonly confirmDeleteRuleButton: Locator
  readonly cancelDeleteRuleButton: Locator

  constructor(page: Page) {
    super(page)

    // Navigation
    this.backButton = page.getByRole('link', { name: 'Back to Envelopes' })

    // Header
    this.envelopeName = page.locator('h1')
    this.groupName = page.locator('.text-body-2.text-grey')
    this.starButton = page.locator('button').filter({ has: page.locator('[class*="mdi-star"]') }).first()
    this.editButton = page.locator('button').filter({ has: page.locator('[class*="mdi-pencil"]') })

    // Balance card
    this.balanceCard = page.locator('.v-card').filter({ hasText: 'Current Balance' })
    this.currentBalance = this.balanceCard.locator('.text-h4')
    this.transferButton = this.balanceCard.getByRole('button', { name: 'Transfer' })
    // Use the active progress bar with rounded style (the visible one, not the loading indicator)
    this.progressBar = this.balanceCard.locator('.v-progress-linear--rounded')
    this.targetBalance = this.balanceCard.locator('text=Target:').locator('..')
    this.description = this.balanceCard.locator('.text-body-2.text-medium-emphasis').last()

    // Activity section
    this.activitySection = page.locator('.v-card').filter({ hasText: 'Recent Activity' })
    this.allocationsCount = this.activitySection.locator('.v-chip')
    this.allocationItems = this.activitySection.locator('.v-list-item')
    this.emptyActivityState = this.activitySection.locator('text=No allocation history yet')

    // Delete button
    this.deleteButton = page.getByRole('button', { name: 'Delete Envelope' })

    // Edit Dialog
    this.editDialog = page.locator('.v-dialog').filter({ hasText: 'Edit Envelope' })
    this.editNameInput = this.editDialog.locator('input').first()
    this.editGroupSelect = this.editDialog.locator('.v-select')
    this.editTargetBalanceInput = this.editDialog.getByLabel('Target Balance (optional)')
    this.editDescriptionInput = this.editDialog.locator('textarea')
    this.saveButton = this.editDialog.getByRole('button', { name: 'Save' })
    this.cancelEditButton = this.editDialog.getByRole('button', { name: 'Cancel' })

    // Transfer Dialog
    this.transferDialog = page.locator('.v-dialog').filter({ hasText: 'Transfer Money' })
    this.transferDirectionToggle = this.transferDialog.locator('.v-btn-toggle')
    this.transferToButton = this.transferDirectionToggle.locator('.v-btn').first()
    this.transferFromButton = this.transferDirectionToggle.locator('.v-btn').last()
    this.transferToSelect = this.transferDialog.locator('.v-select')
    this.transferAmountInput = this.transferDialog.getByLabel('Amount')
    this.confirmTransferButton = this.transferDialog.getByRole('button', { name: 'Transfer' })
    this.cancelTransferButton = this.transferDialog.getByRole('button', { name: 'Cancel' })

    // Delete Dialog
    this.deleteDialog = page.locator('.v-dialog').filter({ hasText: 'Delete Envelope' }).filter({ has: page.locator('text=Are you sure') })
    this.confirmDeleteButton = this.deleteDialog.getByRole('button', { name: 'Delete' })
    this.cancelDeleteButton = this.deleteDialog.getByRole('button', { name: 'Cancel' })

    // Allocation Rules Section
    this.allocationRulesSection = page.locator('.v-card').filter({ hasText: 'Allocation Rules' })
    this.addRuleButton = this.allocationRulesSection.getByRole('button', { name: 'Add Rule' })
    this.ruleItems = this.allocationRulesSection.locator('.v-list-item')
    this.emptyRulesState = this.allocationRulesSection.locator('text=No allocation rules for this envelope')
    this.manageAllRulesLink = this.allocationRulesSection.getByRole('link', { name: 'Manage All Rules' })

    // Allocation Rule Dialog (handles both create and edit)
    this.ruleDialog = page.locator('.v-dialog').filter({ hasText: /Allocation Rule/ })
    this.ruleNameInput = this.ruleDialog.locator('input').first()
    this.ruleTypeSelect = this.ruleDialog.locator('.v-select')
    this.ruleAmountInput = this.ruleDialog.locator('input[type="number"]').first()
    this.rulePriorityInput = this.ruleDialog.locator('input[type="number"]').nth(1)
    this.ruleRespectTargetSwitch = this.ruleDialog.locator('.v-switch').filter({ hasText: 'Stop at target' })
    this.ruleActiveSwitch = this.ruleDialog.locator('.v-switch').filter({ hasText: 'Active' })
    this.saveRuleButton = this.ruleDialog.getByRole('button', { name: /Create|Save/ })
    this.cancelRuleButton = this.ruleDialog.getByRole('button', { name: 'Cancel' })

    // Delete Rule Dialog
    this.deleteRuleDialog = page.locator('.v-dialog').filter({ hasText: 'Delete Allocation Rule' })
    this.confirmDeleteRuleButton = this.deleteRuleDialog.getByRole('button', { name: 'Delete' })
    this.cancelDeleteRuleButton = this.deleteRuleDialog.getByRole('button', { name: 'Cancel' })
  }

  /**
   * Navigate back to the envelopes list.
   */
  async goBack() {
    await this.backButton.click()
    await expect(this.page).toHaveURL('/')
  }

  /**
   * Open the edit dialog.
   */
  async openEditDialog() {
    await this.editButton.click()
    await expect(this.editDialog).toBeVisible()
  }

  /**
   * Update envelope details.
   */
  async updateEnvelope(data: {
    name?: string
    group?: string
    targetBalance?: string
    description?: string
  }) {
    await this.openEditDialog()

    if (data.name !== undefined) {
      await this.editNameInput.clear()
      await this.editNameInput.fill(data.name)
    }

    if (data.group !== undefined) {
      await this.editGroupSelect.click()
      const menu = this.page.locator('.v-overlay--active .v-list')
      await menu.waitFor({ state: 'visible', timeout: 5000 })
      await menu.locator('.v-list-item').filter({ hasText: data.group }).first().click()
    }

    if (data.targetBalance !== undefined) {
      await this.editTargetBalanceInput.clear()
      await this.editTargetBalanceInput.fill(data.targetBalance)
    }

    if (data.description !== undefined) {
      await this.editDescriptionInput.clear()
      await this.editDescriptionInput.fill(data.description)
    }

    await this.saveButton.click()
    await expect(this.editDialog).toBeHidden({ timeout: 10000 })
  }

  /**
   * Open the transfer dialog.
   */
  async openTransferDialog() {
    await this.transferButton.click()
    await expect(this.transferDialog).toBeVisible()
  }

  /**
   * Transfer money to another envelope (FROM current envelope).
   * Uses the "from" direction mode.
   */
  async transferTo(toEnvelope: string, amount: string) {
    await this.openTransferDialog()
    // Switch to "from" mode since we want to transfer OUT
    await this.selectTransferDirection('from')

    await this.transferToSelect.click()
    const menu = this.page.locator('.v-overlay--active .v-list')
    await menu.waitFor({ state: 'visible', timeout: 5000 })
    await menu.locator('.v-list-item').filter({ hasText: toEnvelope }).first().click()
    // Wait for menu to close
    await menu.waitFor({ state: 'hidden', timeout: 5000 }).catch(() => {})

    await this.transferAmountInput.fill(amount)

    // Verify button is enabled before clicking
    await expect(this.confirmTransferButton).toBeEnabled({ timeout: 5000 })
    await this.confirmTransferButton.click()
    await expect(this.transferDialog).toBeHidden({ timeout: 15000 })
  }

  /**
   * Transfer money from another envelope (TO current envelope).
   * Uses the default "to" direction mode.
   */
  async transferFrom(fromEnvelope: string, amount: string) {
    await this.openTransferDialog()
    // Default is "to" mode, so we're transferring INTO current envelope

    await this.transferToSelect.click()
    const menu = this.page.locator('.v-overlay--active .v-list')
    await menu.waitFor({ state: 'visible', timeout: 5000 })
    await menu.locator('.v-list-item').filter({ hasText: fromEnvelope }).first().click()
    // Wait for menu to close
    await menu.waitFor({ state: 'hidden', timeout: 5000 }).catch(() => {})

    await this.transferAmountInput.fill(amount)

    // Verify button is enabled before clicking
    await expect(this.confirmTransferButton).toBeEnabled({ timeout: 5000 })
    await this.confirmTransferButton.click()
    await expect(this.transferDialog).toBeHidden({ timeout: 15000 })
  }

  /**
   * Select transfer direction in the dialog.
   */
  async selectTransferDirection(direction: 'from' | 'to') {
    if (direction === 'to') {
      await this.transferToButton.click()
    } else {
      await this.transferFromButton.click()
    }
  }

  /**
   * Open the delete confirmation dialog.
   */
  async openDeleteDialog() {
    await this.deleteButton.click()
    await expect(this.deleteDialog).toBeVisible()
  }

  /**
   * Delete the envelope.
   */
  async deleteEnvelope() {
    await this.openDeleteDialog()
    await this.confirmDeleteButton.click()
    await expect(this.page).toHaveURL('/', { timeout: 10000 })
  }

  /**
   * Cancel delete operation.
   */
  async cancelDelete() {
    await this.cancelDeleteButton.click()
    await expect(this.deleteDialog).toBeHidden()
  }

  /**
   * Get the envelope name displayed.
   */
  async getName(): Promise<string> {
    return await this.envelopeName.textContent() || ''
  }

  /**
   * Assert envelope has a specific name.
   */
  async expectName(name: string) {
    await expect(this.envelopeName).toHaveText(name)
  }

  /**
   * Assert envelope has progress bar visible (has target balance).
   */
  async expectProgressBarVisible() {
    await expect(this.progressBar).toBeVisible()
  }

  /**
   * Assert empty activity state.
   */
  async expectEmptyActivity() {
    await expect(this.emptyActivityState).toBeVisible()
  }

  /**
   * Assert allocations exist.
   */
  async expectAllocationsExist() {
    await expect(this.allocationItems.first()).toBeVisible()
  }

  // =========== Allocation Rules Methods ===========

  /**
   * Assert the allocation rules section is visible.
   */
  async expectAllocationRulesSectionVisible() {
    await expect(this.allocationRulesSection).toBeVisible()
  }

  /**
   * Assert empty rules state is shown.
   */
  async expectEmptyRulesState() {
    await expect(this.emptyRulesState).toBeVisible()
  }

  /**
   * Open the create rule dialog.
   */
  async openCreateRuleDialog() {
    await this.addRuleButton.click()
    await expect(this.ruleDialog).toBeVisible()
  }

  /**
   * Create an allocation rule from the envelope detail page.
   */
  async createRule(data: {
    name?: string
    ruleType?: string
    amount: string
  }) {
    await this.openCreateRuleDialog()

    if (data.name) {
      await this.ruleNameInput.fill(data.name)
    }

    if (data.ruleType) {
      await this.ruleTypeSelect.click()
      const menu = this.page.locator('.v-overlay--active .v-list')
      await menu.waitFor({ state: 'visible', timeout: 5000 })
      await menu.locator('.v-list-item').filter({ hasText: data.ruleType }).first().click()
    }

    await this.ruleAmountInput.fill(data.amount)

    await this.saveRuleButton.click()
    await expect(this.ruleDialog).toBeHidden({ timeout: 10000 })
  }

  /**
   * Get a rule item by name.
   */
  getRuleItem(name: string): Locator {
    return this.allocationRulesSection.locator('.v-list-item').filter({ hasText: name })
  }

  /**
   * Assert a rule exists in the rules section.
   */
  async expectRuleExists(name: string) {
    await expect(this.getRuleItem(name)).toBeVisible()
  }

  /**
   * Assert a rule does not exist.
   */
  async expectRuleNotExists(name: string) {
    await expect(this.getRuleItem(name)).not.toBeVisible()
  }

  /**
   * Open the menu for a rule.
   */
  async openRuleMenu(name: string) {
    const ruleItem = this.getRuleItem(name)
    await ruleItem.locator('button').filter({ has: this.page.locator('[class*="mdi-dots-vertical"]') }).click()
    await expect(this.page.locator('.v-overlay--active .v-list')).toBeVisible()
  }

  /**
   * Open edit dialog for a rule.
   */
  async openEditRuleDialog(name: string) {
    await this.openRuleMenu(name)
    await this.page.locator('.v-overlay--active .v-list-item').filter({ hasText: 'Edit' }).click()
    await expect(this.ruleDialog).toBeVisible()
  }

  /**
   * Edit a rule's amount.
   */
  async editRuleAmount(name: string, newAmount: string) {
    await this.openEditRuleDialog(name)
    await this.ruleAmountInput.clear()
    await this.ruleAmountInput.fill(newAmount)
    await this.saveRuleButton.click()
    await expect(this.ruleDialog).toBeHidden({ timeout: 10000 })
  }

  /**
   * Delete a rule.
   */
  async deleteRule(name: string) {
    await this.openRuleMenu(name)
    await this.page.locator('.v-overlay--active .v-list-item').filter({ hasText: 'Delete' }).click()
    await expect(this.deleteRuleDialog).toBeVisible()
    await this.confirmDeleteRuleButton.click()
    await expect(this.deleteRuleDialog).toBeHidden({ timeout: 10000 })
  }

  /**
   * Toggle a rule's active state.
   */
  async toggleRuleActive(name: string) {
    await this.openRuleMenu(name)
    const menuItems = this.page.locator('.v-overlay--active .v-list-item')
    // Click either "Deactivate" or "Activate"
    await menuItems.filter({ hasText: /Deactivate|Activate/ }).click()
  }

  /**
   * Get the current balance displayed on the envelope detail page.
   */
  async getCurrentBalance(): Promise<string> {
    return (await this.currentBalance.textContent()) || ''
  }

  // =========== Star/Favorite Methods ===========

  /**
   * Toggle the star status of the envelope.
   */
  async toggleStar() {
    await this.starButton.click()
    // Wait for the API request to complete
    await this.page.waitForResponse((resp) => resp.url().includes('/envelopes/') && resp.request().method() === 'PATCH')
  }

  /**
   * Assert the envelope is starred.
   */
  async expectStarred() {
    await expect(this.starButton.locator('[class*="mdi-star"]:not([class*="mdi-star-outline"])')).toBeVisible()
  }

  /**
   * Assert the envelope is not starred.
   */
  async expectNotStarred() {
    await expect(this.starButton.locator('[class*="mdi-star-outline"]')).toBeVisible()
  }
}
