import { type Page, type Locator, expect } from '@playwright/test'
import { BasePage } from './base.page'

/**
 * Page object for the Allocation Rules view.
 */
export class AllocationRulesPage extends BasePage {
  // Header elements
  readonly pageTitle: Locator
  readonly addRuleButton: Locator

  // Summary cards
  readonly activeRulesCard: Locator
  readonly totalRulesCard: Locator
  readonly envelopesCoveredCard: Locator
  readonly remainderRulesCard: Locator

  // Preview section
  readonly previewPanel: Locator
  readonly previewAmountInput: Locator
  readonly previewButton: Locator
  readonly previewTable: Locator

  // Filters
  readonly envelopeFilterSelect: Locator
  readonly showInactiveSwitch: Locator

  // List
  readonly rulesList: Locator
  readonly ruleItems: Locator
  readonly emptyState: Locator
  readonly emptyStateAddButton: Locator

  // Form Dialog
  readonly formDialog: Locator
  readonly formDialogTitle: Locator
  readonly nameInput: Locator
  readonly envelopeSelect: Locator
  readonly ruleTypeSelect: Locator
  readonly amountInput: Locator
  readonly capPeriodValueInput: Locator
  readonly capPeriodUnitSelect: Locator
  readonly priorityInput: Locator
  readonly isActiveSwitch: Locator
  readonly respectTargetSwitch: Locator
  readonly createButton: Locator
  readonly saveButton: Locator
  readonly cancelFormButton: Locator

  // Delete Dialog
  readonly deleteDialog: Locator
  readonly confirmDeleteButton: Locator
  readonly cancelDeleteButton: Locator

  constructor(page: Page) {
    super(page)

    // Header
    this.pageTitle = page.locator('h1').filter({ hasText: 'Allocation Rules' })
    this.addRuleButton = page.getByRole('button', { name: 'Add Rule', exact: true })

    // Summary cards
    this.activeRulesCard = page.locator('.v-card').filter({ hasText: 'Active Rules' }).first()
    this.totalRulesCard = page.locator('.v-card').filter({ hasText: 'Total Rules' })
    this.envelopesCoveredCard = page.locator('.v-card').filter({ hasText: 'Envelopes Covered' })
    this.remainderRulesCard = page.locator('.v-card').filter({ hasText: 'Remainder Rules' })

    // Preview section
    this.previewPanel = page.locator('.v-expansion-panel').filter({ hasText: 'Preview Income Distribution' })
    this.previewAmountInput = page.locator('.v-expansion-panel input[type="number"]')
    this.previewButton = page.locator('.v-expansion-panel').getByRole('button', { name: 'Preview', exact: true })
    this.previewTable = page.locator('.v-expansion-panel .v-table')

    // Filters
    this.envelopeFilterSelect = page.locator('.v-select').filter({ hasText: 'Filter by Envelope' })
    this.showInactiveSwitch = page.locator('.v-switch').filter({ hasText: 'Show inactive' })

    // List
    this.rulesList = page.locator('.v-card .v-list').last()
    this.ruleItems = page.locator('.v-list-item')
    this.emptyState = page.locator('text=No allocation rules yet')
    this.emptyStateAddButton = page.getByRole('button', { name: 'Create Your First Rule' })

    // Form Dialog
    this.formDialog = page.locator('.v-dialog').filter({ hasText: /Allocation Rule/ })
    this.formDialogTitle = this.formDialog.locator('.v-card-title')
    this.nameInput = page.locator('.v-dialog .v-text-field').filter({ hasText: 'Name' }).locator('input')
    this.envelopeSelect = page.locator('.v-dialog .v-autocomplete').filter({ hasText: 'Envelope' }).first()
    this.ruleTypeSelect = page.locator('.v-dialog .v-select').filter({ hasText: 'Rule Type' })
    this.amountInput = page.locator('.v-dialog input[type="number"]').first()
    this.capPeriodValueInput = page.locator('.v-dialog .v-text-field').filter({ hasText: 'Every' }).locator('input')
    this.capPeriodUnitSelect = page.locator('.v-dialog .v-select:has(.v-label:text-is("Period"))')
    this.priorityInput = page.locator('.v-dialog .v-text-field').filter({ hasText: 'Priority' }).locator('input')
    this.isActiveSwitch = page.locator('.v-dialog .v-switch').filter({ hasText: 'Active' })
    this.respectTargetSwitch = page.locator('.v-dialog .v-switch').filter({ hasText: 'Stop at target balance' })
    this.createButton = this.formDialog.getByRole('button', { name: 'Create' })
    this.saveButton = this.formDialog.getByRole('button', { name: 'Save' })
    this.cancelFormButton = this.formDialog.getByRole('button', { name: 'Cancel' })

    // Delete Dialog
    this.deleteDialog = page.locator('.v-dialog').filter({ hasText: 'Delete Allocation Rule' })
    this.confirmDeleteButton = this.deleteDialog.getByRole('button', { name: 'Delete' })
    this.cancelDeleteButton = this.deleteDialog.getByRole('button', { name: 'Cancel' })
  }

  async goto() {
    // Set up response waiter BEFORE navigation so we don't miss the response
    const envelopesResponsePromise = this.page.waitForResponse(
      (response) =>
        response.url().includes('/api/v1/teams/') &&
        response.url().endsWith('/envelopes') &&
        response.status() === 200,
      { timeout: 15000 }
    ).catch(() => {
      // Envelopes API may not be called if there are no envelopes
    })

    await this.page.goto('/allocation-rules')
    await this.waitForPageLoad()

    // Wait for the envelopes API to complete (needed for dropdown data)
    await envelopesResponsePromise
  }

  /**
   * Open the create rule dialog.
   */
  async openCreateDialog() {
    await this.addRuleButton.click()
    await expect(this.formDialog).toBeVisible()
  }

  /**
   * Select an envelope in the form.
   */
  async selectEnvelope(envelopeName: string) {
    await this.envelopeSelect.click()
    // Wait specifically for the target item (not just any item)
    const menu = this.page.locator('.v-menu .v-list-item')
    const targetItem = menu.filter({ hasText: envelopeName }).first()
    await targetItem.waitFor({ state: 'visible', timeout: 10000 })
    await targetItem.click()
  }

  /**
   * Select a rule type in the form.
   */
  async selectRuleType(ruleType: 'Fill to Target' | 'Fixed Amount' | 'Percentage' | 'Remainder' | 'Period Cap') {
    await this.ruleTypeSelect.click()
    // Wait specifically for the target item (not just any item)
    const menu = this.page.locator('.v-menu .v-list-item')
    const targetItem = menu.filter({ hasText: ruleType }).first()
    await targetItem.waitFor({ state: 'visible', timeout: 10000 })
    await targetItem.click()
  }

  /**
   * Toggle the "Stop at target balance" switch.
   */
  async toggleRespectTarget() {
    const switchInput = this.respectTargetSwitch.locator('input[type="checkbox"]')
    const wasChecked = await switchInput.isChecked()
    await switchInput.click({ force: true })
    await expect(switchInput).toBeChecked({ checked: !wasChecked })
  }

  /**
   * Create a fixed amount rule.
   */
  async createFixedRule(data: {
    envelope: string
    amount: string
    name?: string
    priority?: string
    respectTarget?: boolean
  }) {
    await this.openCreateDialog()

    await this.selectEnvelope(data.envelope)
    await this.selectRuleType('Fixed Amount')
    await this.amountInput.fill(data.amount)

    if (data.name) {
      await this.nameInput.fill(data.name)
    }

    if (data.priority) {
      await this.priorityInput.clear()
      await this.priorityInput.fill(data.priority)
    }

    if (data.respectTarget) {
      await this.toggleRespectTarget()
    }

    await expect(this.createButton).toBeEnabled({ timeout: 5000 })

    const responsePromise = this.page.waitForResponse(
      (response) => response.url().includes('/allocation-rules') && response.request().method() === 'POST'
    )
    await this.createButton.click()
    await responsePromise

    await expect(this.formDialog).toBeHidden({ timeout: 10000 })
  }

  /**
   * Create a percentage rule.
   */
  async createPercentageRule(data: {
    envelope: string
    percentage: string
    name?: string
    priority?: string
    respectTarget?: boolean
  }) {
    await this.openCreateDialog()

    await this.selectEnvelope(data.envelope)
    await this.selectRuleType('Percentage')
    await this.amountInput.fill(data.percentage)

    if (data.name) {
      await this.nameInput.fill(data.name)
    }

    if (data.priority) {
      await this.priorityInput.clear()
      await this.priorityInput.fill(data.priority)
    }

    if (data.respectTarget) {
      await this.toggleRespectTarget()
    }

    await expect(this.createButton).toBeEnabled({ timeout: 5000 })

    const responsePromise = this.page.waitForResponse(
      (response) => response.url().includes('/allocation-rules') && response.request().method() === 'POST'
    )
    await this.createButton.click()
    await responsePromise

    await expect(this.formDialog).toBeHidden({ timeout: 10000 })
  }

  /**
   * Create a remainder rule.
   */
  async createRemainderRule(data: {
    envelope: string
    weight: string
    name?: string
    priority?: string
    respectTarget?: boolean
  }) {
    await this.openCreateDialog()

    await this.selectEnvelope(data.envelope)
    await this.selectRuleType('Remainder')
    await this.amountInput.fill(data.weight)

    if (data.name) {
      await this.nameInput.fill(data.name)
    }

    if (data.priority) {
      await this.priorityInput.clear()
      await this.priorityInput.fill(data.priority)
    }

    if (data.respectTarget) {
      await this.toggleRespectTarget()
    }

    await expect(this.createButton).toBeEnabled({ timeout: 5000 })

    const responsePromise = this.page.waitForResponse(
      (response) => response.url().includes('/allocation-rules') && response.request().method() === 'POST'
    )
    await this.createButton.click()
    await responsePromise

    await expect(this.formDialog).toBeHidden({ timeout: 10000 })
  }

  /**
   * Create a period cap rule.
   */
  async createPeriodCapRule(data: {
    envelope: string
    amount: string
    periodValue?: string
    periodUnit: 'Week(s)' | 'Month(s)' | 'Year(s)'
    name?: string
  }) {
    await this.openCreateDialog()

    await this.selectEnvelope(data.envelope)
    await this.selectRuleType('Period Cap')
    await this.amountInput.fill(data.amount)

    if (data.name) {
      await this.nameInput.fill(data.name)
    }

    if (data.periodValue) {
      await this.capPeriodValueInput.clear()
      await this.capPeriodValueInput.fill(data.periodValue)
    }

    // Select period unit
    await this.capPeriodUnitSelect.click()
    const menu = this.page.locator('.v-menu .v-list-item')
    const targetItem = menu.filter({ hasText: data.periodUnit }).first()
    await targetItem.waitFor({ state: 'visible', timeout: 10000 })
    await targetItem.click()

    await expect(this.createButton).toBeEnabled({ timeout: 5000 })

    const responsePromise = this.page.waitForResponse(
      (response) => response.url().includes('/allocation-rules') && response.request().method() === 'POST'
    )
    await this.createButton.click()
    await responsePromise

    await expect(this.formDialog).toBeHidden({ timeout: 10000 })
  }

  /**
   * Get a rule item by name/description text.
   */
  getRuleItem(text: string): Locator {
    return this.page.locator('.v-list-item').filter({ hasText: text }).first()
  }

  /**
   * Open the menu for a rule item.
   */
  async openItemMenu(text: string) {
    const item = this.getRuleItem(text)
    await expect(item).toBeVisible()
    const menuButton = item.locator('button').filter({ has: this.page.locator('[class*="mdi-dots-vertical"]') })
    await expect(menuButton).toBeVisible()
    await menuButton.click()
    // Wait for the menu to appear - use a more specific locator for the v-menu overlay
    const menu = this.page.locator('.v-menu > .v-overlay__content > .v-list')
    await menu.waitFor({ state: 'visible', timeout: 5000 })
    return menu
  }

  /**
   * Open edit dialog for a rule.
   */
  async openEditDialog(text: string) {
    const menu = await this.openItemMenu(text)
    await menu.locator('.v-list-item').filter({ hasText: 'Edit' }).click()
    await expect(this.formDialog).toBeVisible()
  }

  /**
   * Toggle active/inactive status of a rule.
   */
  async toggleRuleActive(text: string) {
    const menu = await this.openItemMenu(text)
    const toggleItem = menu.locator('.v-list-item').filter({ hasText: /Activate|Deactivate/ })
    // Wait for the PATCH request to complete
    const responsePromise = this.page.waitForResponse(
      (r) => r.url().includes('/allocation-rules/') && r.request().method() === 'PATCH'
    )
    await toggleItem.click()
    await responsePromise
    // Wait for menu to close
    await expect(menu).toBeHidden({ timeout: 5000 }).catch(() => {})
  }

  /**
   * Open delete dialog for a rule.
   */
  async openDeleteDialog(text: string) {
    const menu = await this.openItemMenu(text)
    await menu.locator('.v-list-item').filter({ hasText: 'Delete' }).click()
    await expect(this.deleteDialog).toBeVisible()
  }

  /**
   * Delete a rule.
   */
  async deleteRule(text: string) {
    await this.openDeleteDialog(text)
    await this.confirmDeleteButton.click()
    await expect(this.deleteDialog).toBeHidden({ timeout: 10000 })
  }

  /**
   * Move rule priority up.
   */
  async movePriorityUp(text: string) {
    const item = this.getRuleItem(text)
    const upButton = item.locator('button[class*="mdi-chevron-up"]')
    const responsePromise = this.page.waitForResponse(
      (r) => r.url().includes('/allocation-rules/') && r.request().method() === 'PATCH'
    )
    await upButton.click()
    await responsePromise
    // Wait for the button to be enabled again (UI has re-rendered after reorder)
    await expect(upButton).toBeEnabled({ timeout: 5000 }).catch(() => {
      // Button may be disabled if now at top - that's ok
    })
  }

  /**
   * Move rule priority down.
   */
  async movePriorityDown(text: string) {
    const item = this.getRuleItem(text)
    const downButton = item.locator('button[class*="mdi-chevron-down"]')
    const responsePromise = this.page.waitForResponse(
      (r) => r.url().includes('/allocation-rules/') && r.request().method() === 'PATCH'
    )
    await downButton.click()
    await responsePromise
    // Wait for the button to be enabled again (UI has re-rendered after reorder)
    await expect(downButton).toBeEnabled({ timeout: 5000 }).catch(() => {
      // Button may be disabled if now at bottom - that's ok
    })
  }

  /**
   * Toggle show inactive filter.
   */
  async toggleShowInactive() {
    const switchInput = this.showInactiveSwitch.locator('input[type="checkbox"]')
    const wasChecked = await switchInput.isChecked()
    await switchInput.evaluate((el: HTMLInputElement) => el.click())
    await expect(switchInput).toBeChecked({ checked: !wasChecked })
  }

  /**
   * Filter by envelope.
   */
  async filterByEnvelope(envelopeName: string | null) {
    await this.envelopeFilterSelect.click()
    // Wait specifically for the target item (not just any item)
    const menu = this.page.locator('.v-menu .v-list-item')
    const filterText = envelopeName || 'All Envelopes'
    const targetItem = menu.filter({ hasText: filterText }).first()
    await targetItem.waitFor({ state: 'visible', timeout: 10000 })
    await targetItem.click()
  }

  /**
   * Expand preview panel and run preview.
   */
  async runPreview(amount: string) {
    await this.previewPanel.click()
    await this.previewAmountInput.waitFor({ state: 'visible', timeout: 5000 })
    await this.previewAmountInput.fill(amount)
    await this.previewButton.click()
    await expect(this.previewTable).toBeVisible()
  }

  /**
   * Assert rule exists.
   */
  async expectRuleExists(text: string) {
    await expect(this.getRuleItem(text)).toBeVisible()
  }

  /**
   * Assert rule does not exist.
   */
  async expectRuleNotExists(text: string) {
    await expect(this.getRuleItem(text)).not.toBeVisible()
  }

  /**
   * Assert empty state is shown.
   */
  async expectEmptyState() {
    await expect(this.emptyState).toBeVisible()
    await expect(this.emptyStateAddButton).toBeVisible()
  }

  /**
   * Get active rules count from summary card.
   */
  async getActiveRulesCount(): Promise<string> {
    return (await this.activeRulesCard.locator('.text-h6').textContent()) || '0'
  }

  /**
   * Check if a rule is inactive (waits for the Inactive chip to appear).
   */
  async isRuleInactive(text: string): Promise<boolean> {
    const item = this.getRuleItem(text)
    await expect(item).toBeVisible({ timeout: 5000 })
    const inactiveChip = item.locator('.v-chip').filter({ hasText: 'Inactive' })
    // Wait a bit for the chip to appear after filtering
    try {
      await expect(inactiveChip).toBeVisible({ timeout: 3000 })
      return true
    } catch {
      return false
    }
  }
}
