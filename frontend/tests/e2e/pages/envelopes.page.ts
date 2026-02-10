import { type Page, type Locator, expect } from '@playwright/test'
import { BasePage } from './base.page'

/**
 * Page object for the Envelopes list view.
 */
export class EnvelopesPage extends BasePage {
  // Header elements
  readonly pageTitle: Locator
  readonly settingsButton: Locator
  readonly settingsMenu: Locator
  readonly addEnvelopeMenuItem: Locator
  readonly addGroupMenuItem: Locator
  readonly editOrderMenuItem: Locator

  // Ready to Assign (Unallocated) card
  readonly readyToAssignCard: Locator
  readonly readyToAssignAmount: Locator
  readonly assignMoneyButton: Locator

  // Envelope list
  readonly envelopeCards: Locator
  readonly loadingSpinner: Locator
  readonly emptyState: Locator
  readonly emptyStateCreateButton: Locator

  // Group sections
  readonly groupSections: Locator

  // Credit Cards section
  readonly creditCardsSection: Locator
  readonly creditCardEnvelopes: Locator

  // Create Envelope Dialog
  readonly createEnvelopeDialog: Locator
  readonly envelopeNameInput: Locator
  readonly envelopeGroupSelect: Locator
  readonly inlineNewGroupNameInput: Locator
  readonly envelopeTargetBalanceInput: Locator
  readonly createEnvelopeButton: Locator
  readonly cancelCreateEnvelopeButton: Locator
  // Allocation rule fields in create envelope dialog
  readonly addRuleToggle: Locator
  readonly ruleTypeSelectInCreate: Locator
  readonly ruleAmountInputInCreate: Locator
  readonly fillToTargetWarning: Locator

  // Create Group Dialog
  readonly createGroupDialog: Locator
  readonly groupNameInput: Locator
  readonly createGroupButton: Locator
  readonly cancelCreateGroupButton: Locator

  // Transfer Dialog
  readonly transferDialog: Locator
  readonly transferDirectionToggle: Locator
  readonly transferToButton: Locator
  readonly transferFromButton: Locator
  readonly transferToSelect: Locator
  readonly transferAmountInput: Locator
  readonly transferButton: Locator
  readonly cancelTransferButton: Locator

  // Assign Money Menu (dropdown)
  readonly assignMoneyMenu: Locator
  readonly assignManuallyMenuItem: Locator
  readonly autoAssignMenuItem: Locator

  // Auto-Assign Dialog
  readonly autoAssignDialog: Locator
  readonly autoAssignApplyButton: Locator
  readonly autoAssignCancelButton: Locator
  readonly autoAssignAllocationsList: Locator
  readonly autoAssignNoAllocationsMessage: Locator

  // Create Allocation Rule Dialog
  readonly createRuleDialog: Locator
  readonly ruleNameInput: Locator
  readonly ruleTypeSelect: Locator
  readonly ruleAmountInput: Locator
  readonly rulePriorityInput: Locator
  readonly ruleRespectTargetSwitch: Locator
  readonly ruleActiveSwitch: Locator
  readonly createRuleButton: Locator
  readonly cancelCreateRuleButton: Locator

  // Overspent alert
  readonly overspentAlert: Locator

  // Action sheet (mobile)
  readonly actionSheet: Locator
  readonly actionSheetTransfer: Locator
  readonly actionSheetAddTransaction: Locator
  readonly actionSheetViewActivity: Locator
  readonly actionSheetViewDetails: Locator

  // Activity dialog
  readonly activityDialog: Locator

  constructor(page: Page) {
    super(page)

    // Header
    this.pageTitle = page.locator('h1').filter({ hasText: 'Envelopes' })
    // Gear icon button next to the title
    this.settingsButton = page.locator('button:has(.mdi-cog)')
    this.settingsMenu = page.locator('.v-list').filter({ hasText: 'Add Envelope' })
    this.addEnvelopeMenuItem = this.settingsMenu.locator('.v-list-item').filter({ hasText: /^Add Envelope$/ })
    this.addGroupMenuItem = this.settingsMenu.locator('.v-list-item').filter({ hasText: 'Add Envelope Group' })
    this.editOrderMenuItem = this.settingsMenu.locator('.v-list-item').filter({ hasText: /Edit Order|Done Editing/ })

    // Ready to Assign card (the standalone card, not the summary panel which has class budget-summary-panel)
    this.readyToAssignCard = page.locator('.v-card.mb-4').filter({ hasText: 'Ready to Assign' }).first()
    this.readyToAssignAmount = this.readyToAssignCard.locator('.money-display, .text-h5').first()
    this.assignMoneyButton = this.readyToAssignCard.getByRole('button', { name: 'Assign Money' })

    // Envelope list
    this.envelopeCards = page.locator('.v-list-item')
    this.loadingSpinner = page.locator('.v-progress-circular')
    this.emptyState = page.locator('text=No envelopes yet')
    this.emptyStateCreateButton = page.getByRole('button', { name: 'Create Envelope' })

    // Group sections
    this.groupSections = page.locator('.text-subtitle-2.text-grey')

    // Credit Cards section - scope to main content area to avoid matching sidebar
    // The wrapper div contains both the "Credit Cards" header and list items
    this.creditCardsSection = page
      .locator('main')
      .locator('div')
      .filter({ has: page.locator('span.text-grey:has-text("Credit Cards")') })
      .filter({ has: page.locator('.v-list-item') })
      .first()
    this.creditCardEnvelopes = this.creditCardsSection.locator('.v-list-item')

    // Create Envelope Dialog
    this.createEnvelopeDialog = page.locator('.v-dialog').filter({ hasText: 'Create Envelope' })
    this.envelopeNameInput = this.createEnvelopeDialog.locator('input').first()
    this.envelopeGroupSelect = this.createEnvelopeDialog.locator('.v-select').first()
    this.inlineNewGroupNameInput = this.createEnvelopeDialog.getByLabel('New Group Name')
    this.envelopeTargetBalanceInput = this.createEnvelopeDialog.locator('input[type="number"]').first()
    this.createEnvelopeButton = this.createEnvelopeDialog.getByRole('button', { name: 'Create' })
    this.cancelCreateEnvelopeButton = this.createEnvelopeDialog.getByRole('button', { name: 'Cancel' })
    // Allocation rule fields in create envelope dialog
    this.addRuleToggle = this.createEnvelopeDialog
      .locator('.v-switch')
      .filter({ hasText: 'Add allocation rule' })
    this.ruleTypeSelectInCreate = this.createEnvelopeDialog
      .locator('.v-select')
      .filter({ hasText: 'Rule Type' })
    this.ruleAmountInputInCreate = this.createEnvelopeDialog.getByRole('spinbutton', {
      name: 'Amount',
    })
    this.fillToTargetWarning = this.createEnvelopeDialog.locator('.v-alert')

    // Create Group Dialog
    this.createGroupDialog = page.locator('.v-dialog').filter({ hasText: 'Create Group' })
    this.groupNameInput = this.createGroupDialog.locator('input')
    this.createGroupButton = this.createGroupDialog.getByRole('button', { name: 'Create' })
    this.cancelCreateGroupButton = this.createGroupDialog.getByRole('button', { name: 'Cancel' })

    // Transfer Dialog
    this.transferDialog = page.locator('.v-dialog').filter({ hasText: 'Transfer Money' })
    this.transferDirectionToggle = this.transferDialog.locator('.v-btn-toggle')
    this.transferToButton = this.transferDirectionToggle.locator('.v-btn').first()
    this.transferFromButton = this.transferDirectionToggle.locator('.v-btn').last()
    this.transferToSelect = this.transferDialog.locator('.v-autocomplete')
    this.transferAmountInput = this.transferDialog.getByLabel('Amount')
    this.transferButton = this.transferDialog.getByRole('button', { name: 'Transfer' })
    this.cancelTransferButton = this.transferDialog.getByRole('button', { name: 'Cancel' })

    // Assign Money Menu (dropdown)
    this.assignMoneyMenu = page.locator('.v-list').filter({ hasText: 'Assign Manually' })
    this.assignManuallyMenuItem = page.locator('.v-list-item').filter({ hasText: 'Assign Manually' })
    this.autoAssignMenuItem = page.locator('.v-list-item').filter({ hasText: 'Auto-Assign with Rules' })

    // Auto-Assign Dialog
    this.autoAssignDialog = page.locator('.v-dialog').filter({ hasText: 'Auto-Assign Money' })
    this.autoAssignApplyButton = this.autoAssignDialog.getByRole('button', { name: 'Apply' })
    this.autoAssignCancelButton = this.autoAssignDialog.getByRole('button', { name: 'Cancel' })
    this.autoAssignAllocationsList = this.autoAssignDialog.locator('.v-list')
    this.autoAssignNoAllocationsMessage = this.autoAssignDialog.locator('text=No allocations would be made')

    // Create Allocation Rule Dialog
    this.createRuleDialog = page.locator('.v-dialog').filter({ hasText: 'New Allocation Rule' })
    this.ruleNameInput = this.createRuleDialog.locator('input').first()
    this.ruleTypeSelect = this.createRuleDialog.locator('.v-select')
    this.ruleAmountInput = this.createRuleDialog.locator('input[type="number"]').first()
    this.rulePriorityInput = this.createRuleDialog.locator('input[type="number"]').nth(1)
    this.ruleRespectTargetSwitch = this.createRuleDialog.locator('.v-switch').filter({ hasText: 'Stop at target' })
    this.ruleActiveSwitch = this.createRuleDialog.locator('.v-switch').filter({ hasText: 'Active' })
    this.createRuleButton = this.createRuleDialog.getByRole('button', { name: 'Create' })
    this.cancelCreateRuleButton = this.createRuleDialog.getByRole('button', { name: 'Cancel' })

    // Overspent alert
    this.overspentAlert = page.locator('[data-testid="overspent-alert"]')

    // Action sheet (mobile)
    this.actionSheet = page.locator('.v-bottom-sheet')
    this.actionSheetTransfer = this.actionSheet.getByText('Transfer Money')
    this.actionSheetAddTransaction = this.actionSheet.getByText('Add Transaction')
    this.actionSheetViewActivity = this.actionSheet.getByText('View Activity')
    this.actionSheetViewDetails = this.actionSheet.getByText('View Details')

    // Activity dialog
    this.activityDialog = page.locator('.v-dialog').filter({ hasText: 'Activity' })
  }

  async goto() {
    await this.page.goto('/')
    await this.waitForPageLoad()
  }

  /**
   * Open the settings menu (gear icon).
   */
  async openSettingsMenu() {
    await this.settingsButton.click()
    await expect(this.settingsMenu).toBeVisible()
  }

  /**
   * Open the Create Envelope dialog from the settings menu.
   */
  async openCreateEnvelopeDialog() {
    await this.openSettingsMenu()
    await this.addEnvelopeMenuItem.click()
    await expect(this.createEnvelopeDialog).toBeVisible()
  }

  /**
   * Open the Create Group dialog from the settings menu.
   */
  async openCreateGroupDialog() {
    await this.openSettingsMenu()
    await this.addGroupMenuItem.click()
    await expect(this.createGroupDialog).toBeVisible()
  }

  /**
   * Create a new envelope.
   */
  async createEnvelope(data: {
    name: string
    group?: string
    createNewGroup?: string // Create a new group inline with this name
    targetBalance?: string
    withRule?: {
      type: 'fill_to_target' | 'fixed'
      amount?: string // Required for 'fixed'
    }
  }) {
    await this.openCreateEnvelopeDialog()
    await this.envelopeNameInput.fill(data.name)

    if (data.createNewGroup) {
      // Select "+ Create New Group" option and fill in the new group name
      await this.envelopeGroupSelect.click()
      const menu = this.page.locator('.v-overlay--active .v-list')
      await menu.waitFor({ state: 'visible', timeout: 5000 })
      // Wait specifically for the target item (not just any item)
      const createNewGroupItem = menu.locator('.v-list-item').filter({ hasText: '+ Create New Group' }).first()
      await createNewGroupItem.waitFor({ state: 'visible', timeout: 10000 })
      await createNewGroupItem.click()
      await menu.waitFor({ state: 'hidden', timeout: 5000 }).catch(() => {})
      await this.inlineNewGroupNameInput.waitFor({ state: 'visible' })
      await this.inlineNewGroupNameInput.fill(data.createNewGroup)
    } else if (data.group) {
      await this.envelopeGroupSelect.click()
      const menu = this.page.locator('.v-overlay--active .v-list')
      await menu.waitFor({ state: 'visible', timeout: 5000 })
      // Wait specifically for the target item (not just any item)
      const targetItem = menu.locator('.v-list-item').filter({ hasText: data.group }).first()
      await targetItem.waitFor({ state: 'visible', timeout: 10000 })
      await targetItem.click()
    }

    if (data.targetBalance) {
      await this.envelopeTargetBalanceInput.fill(data.targetBalance)
    }

    if (data.withRule) {
      // Enable the allocation rule toggle
      await this.addRuleToggle.click()

      // Select rule type
      await this.ruleTypeSelectInCreate.click()
      const menu = this.page.locator('.v-overlay--active .v-list')
      await menu.waitFor({ state: 'visible', timeout: 5000 })
      const ruleTypeLabel = data.withRule.type === 'fill_to_target' ? 'Fill to Target' : 'Fixed Amount'
      await menu.locator('.v-list-item').filter({ hasText: ruleTypeLabel }).first().click()
      // Wait for menu to close
      await menu.waitFor({ state: 'hidden', timeout: 5000 }).catch(() => {})

      // Fill amount for fixed rules
      if (data.withRule.type === 'fixed' && data.withRule.amount) {
        await this.ruleAmountInputInCreate.fill(data.withRule.amount)
      }
    }

    await this.createEnvelopeButton.click()
    await expect(this.createEnvelopeDialog).toBeHidden({ timeout: 10000 })
  }

  /**
   * Create a new group.
   */
  async createGroup(name: string) {
    await this.openCreateGroupDialog()
    await this.groupNameInput.fill(name)
    await this.createGroupButton.click()
    await expect(this.createGroupDialog).toBeHidden({ timeout: 10000 })
  }

  /**
   * Click on an envelope to navigate to detail page.
   */
  async clickEnvelope(name: string) {
    const envelope = this.page.locator('.v-list-item').filter({ hasText: name }).first()
    await envelope.click()
    await expect(this.page).toHaveURL(/\/envelopes\/[a-z0-9-]+/)
  }

  /**
   * Open transfer dialog from an envelope's transfer button.
   */
  async openTransferFromEnvelope(name: string) {
    // Hover over the envelope to show transfer button, then click it
    const envelope = this.page.locator('.v-list-item').filter({ hasText: name }).first()
    await envelope.hover()
    // The transfer button uses mdi-swap-horizontal icon
    const transferBtn = envelope.locator('button:has(.mdi-swap-horizontal)')
    await transferBtn.click()
    await expect(this.transferDialog).toBeVisible()
  }

  /**
   * Open the Assign Money dropdown menu.
   */
  async openAssignMoneyMenu() {
    await this.assignMoneyButton.click()
    await expect(this.assignMoneyMenu).toBeVisible()
  }

  /**
   * Open transfer dialog from the Ready to Assign card (via menu).
   */
  async openAssignMoneyDialog() {
    await this.openAssignMoneyMenu()
    await this.assignManuallyMenuItem.click()
    await expect(this.transferDialog).toBeVisible()
  }

  /**
   * Open the Auto-Assign dialog from the Assign Money menu.
   */
  async openAutoAssignDialog() {
    await this.openAssignMoneyMenu()
    await this.autoAssignMenuItem.click()
    await expect(this.autoAssignDialog).toBeVisible()
  }

  /**
   * Apply auto-assign and wait for completion.
   */
  async applyAutoAssign() {
    await this.autoAssignApplyButton.click()
    await expect(this.autoAssignDialog).toBeHidden({ timeout: 15000 })
  }

  /**
   * Cancel auto-assign dialog.
   */
  async cancelAutoAssign() {
    await this.autoAssignCancelButton.click()
    await expect(this.autoAssignDialog).toBeHidden({ timeout: 5000 })
  }

  /**
   * Check if auto-assign shows allocations preview.
   */
  async expectAutoAssignHasAllocations() {
    await expect(this.autoAssignAllocationsList).toBeVisible()
    // Should have at least one allocation item
    const items = this.autoAssignAllocationsList.locator('.v-list-item')
    await expect(items.first()).toBeVisible()
  }

  /**
   * Check if auto-assign shows no allocations message.
   */
  async expectAutoAssignNoAllocations() {
    await expect(this.autoAssignNoAllocationsMessage).toBeVisible()
  }

  /**
   * Check if auto-assign menu item is disabled.
   */
  async expectAutoAssignDisabled() {
    await this.openAssignMoneyMenu()
    // Vuetify uses CSS class for disabled state, not aria-disabled attribute
    await expect(this.autoAssignMenuItem).toHaveClass(/v-list-item--disabled/)
    // Close the menu
    await this.page.keyboard.press('Escape')
  }

  /**
   * Complete a transfer in the transfer dialog.
   */
  async completeTransfer(toEnvelope: string, amount: string) {
    await this.transferToSelect.click()
    const menu = this.page.locator('.v-overlay--active .v-list')
    await menu.waitFor({ state: 'visible', timeout: 5000 })
    // Wait specifically for the target item (not just any item)
    const targetItem = menu.locator('.v-list-item').filter({ hasText: toEnvelope }).first()
    await targetItem.waitFor({ state: 'visible', timeout: 10000 })
    await targetItem.click()
    // Wait for menu to close
    await menu.waitFor({ state: 'hidden', timeout: 5000 }).catch(() => {})

    await this.transferAmountInput.fill(amount)

    // Verify button is enabled before clicking
    await expect(this.transferButton).toBeEnabled({ timeout: 5000 })

    // Click and wait for dialog to close (confirms transfer completed)
    await this.transferButton.click()
    await expect(this.transferDialog).toBeHidden({ timeout: 5000 })
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
   * Assert the transfer direction toggle is visible.
   */
  async expectTransferToggleVisible() {
    await expect(this.transferDirectionToggle).toBeVisible()
  }

  /**
   * Assert the transfer direction toggle is not visible.
   */
  async expectTransferToggleHidden() {
    await expect(this.transferDirectionToggle).not.toBeVisible()
  }

  /**
   * Get an envelope card by name.
   */
  getEnvelopeCard(name: string): Locator {
    return this.page.locator('.v-list-item').filter({ hasText: name }).first()
  }

  /**
   * Check if an envelope exists.
   */
  async expectEnvelopeExists(name: string) {
    await expect(this.getEnvelopeCard(name)).toBeVisible()
  }

  /**
   * Check if an envelope does not exist.
   */
  async expectEnvelopeNotExists(name: string) {
    await expect(this.getEnvelopeCard(name)).not.toBeVisible()
  }

  /**
   * Check if a group exists.
   */
  async expectGroupExists(name: string) {
    const group = this.page.locator('.text-subtitle-2').filter({ hasText: name })
    await expect(group).toBeVisible()
  }

  /**
   * Assert empty state is shown.
   */
  async expectEmptyState() {
    await expect(this.emptyState).toBeVisible()
    await expect(this.emptyStateCreateButton).toBeVisible()
  }

  /**
   * Check if an envelope has rule icons visible.
   */
  async expectEnvelopeHasRuleIcons(name: string) {
    const envelope = this.getEnvelopeCard(name)
    // Rule type icons are rendered inside the list-item-title, look for the icons directly
    const ruleIcons = envelope.locator(
      '.v-icon[class*="mdi-target"], .v-icon[class*="mdi-currency-usd"], .v-icon[class*="mdi-percent"], .v-icon[class*="mdi-scale-balance"]'
    )
    await expect(ruleIcons.first()).toBeVisible({ timeout: 10000 })
  }

  /**
   * Check if the Credit Cards section is visible.
   */
  async expectCreditCardsSectionVisible() {
    await expect(this.creditCardsSection).toBeVisible({ timeout: 10000 })
  }

  /**
   * Check if a credit card envelope exists in the CC section.
   */
  async expectCreditCardEnvelopeExists(name: string) {
    const ccEnvelope = this.creditCardEnvelopes.filter({ hasText: name })
    await expect(ccEnvelope).toBeVisible({ timeout: 10000 })
  }

  /**
   * Get the balance displayed for a credit card envelope.
   */
  async getCreditCardEnvelopeBalance(name: string): Promise<string> {
    const ccEnvelope = this.creditCardEnvelopes.filter({ hasText: name })
    // Use the balance column's display-value to avoid matching the activity column
    const balance = ccEnvelope.locator('.balance-column .display-value')
    return (await balance.textContent()) || ''
  }

  // ==================== Edit Mode / Reordering ====================

  /**
   * Enter edit mode via the settings menu.
   */
  async enterEditMode() {
    await this.openSettingsMenu()
    // Wait for Edit Order menu item to be visible
    const menuItem = this.page.locator('.v-list-item').filter({ hasText: /Edit Order/ }).first()
    await expect(menuItem).toBeVisible({ timeout: 5000 })
    // Use JavaScript click to bypass DOM detachment issues during Vuetify menu transitions
    await menuItem.evaluate((el) => (el as HTMLElement).click())
    // Wait for reorder buttons to appear on envelope rows or group headers
    await expect(
      this.page.locator('.envelope-group-header button:has(.mdi-chevron-up), .v-list-item button:has(.mdi-chevron-up)').first()
    ).toBeVisible({ timeout: 5000 })
  }

  /**
   * Exit edit mode via the settings menu.
   */
  async exitEditMode() {
    await this.openSettingsMenu()
    // The menu text changes to "Done Editing" in edit mode - wait for it to stabilize
    const menuItem = this.page.locator('.v-list-item').filter({ hasText: /Done Editing/ }).first()
    await expect(menuItem).toBeVisible({ timeout: 5000 })
    // Use JavaScript click to bypass DOM detachment issues during Vuetify menu transitions
    await menuItem.evaluate((el) => (el as HTMLElement).click())
    // Wait for reorder buttons to disappear from group headers and envelope rows
    await expect(
      this.page.locator('.envelope-group-header button:has(.mdi-chevron-up)').first()
    ).toBeHidden({ timeout: 5000 })
  }

  /**
   * Check if in edit mode (reorder buttons are visible).
   */
  async expectInEditMode() {
    // Check for reorder buttons on groups or envelope rows
    await expect(
      this.page.locator('.envelope-group-header button:has(.mdi-chevron-up), .v-list-item button:has(.mdi-chevron-up)').first()
    ).toBeVisible({ timeout: 5000 })
  }

  /**
   * Check if not in edit mode (reorder buttons are hidden).
   */
  async expectNotInEditMode() {
    // Check that reorder buttons are not visible on group headers or envelope rows
    await expect(
      this.page.locator('.envelope-group-header button:has(.mdi-chevron-up)').first()
    ).toBeHidden({ timeout: 5000 })
    await expect(
      this.page.locator('.v-list-item button:has(.mdi-chevron-up)').first()
    ).toBeHidden({ timeout: 5000 })
  }

  /**
   * Get the up button for a group.
   */
  getGroupUpButton(groupName: string): Locator {
    // Use the specific group header class and find the first button (up)
    const groupHeader = this.page.locator('.envelope-group-header').filter({ hasText: groupName }).first()
    // First button is up, second is down
    return groupHeader.locator('button').first()
  }

  /**
   * Get the down button for a group.
   */
  getGroupDownButton(groupName: string): Locator {
    // Use the specific group header class and find the second button (down)
    const groupHeader = this.page.locator('.envelope-group-header').filter({ hasText: groupName }).first()
    // First button is up, second is down
    return groupHeader.locator('button').nth(1)
  }

  /**
   * Move a group up.
   */
  async moveGroupUp(groupName: string) {
    const upButton = this.getGroupUpButton(groupName)
    // Wait for the PATCH request to complete when clicking
    const responsePromise = this.page.waitForResponse(
      (r) => r.url().includes('/envelope-groups/') && r.request().method() === 'PATCH'
    )
    await upButton.click()
    await responsePromise
    // Wait for the button to be enabled again (UI has re-rendered after reorder)
    await expect(upButton).toBeEnabled({ timeout: 5000 }).catch(() => {
      // Button may be disabled if now at top - that's ok
    })
  }

  /**
   * Move a group down.
   */
  async moveGroupDown(groupName: string) {
    const downButton = this.getGroupDownButton(groupName)
    // Wait for the PATCH request to complete when clicking
    const responsePromise = this.page.waitForResponse(
      (r) => r.url().includes('/envelope-groups/') && r.request().method() === 'PATCH'
    )
    await downButton.click()
    await responsePromise
    // Wait for the button to be enabled again (UI has re-rendered after reorder)
    await expect(downButton).toBeEnabled({ timeout: 5000 }).catch(() => {
      // Button may be disabled if now at bottom - that's ok
    })
  }

  /**
   * Get the up button for an envelope.
   */
  getEnvelopeUpButton(envelopeName: string): Locator {
    const envelope = this.page.locator('.v-list-item').filter({ hasText: envelopeName }).first()
    return envelope.locator('button:has(.mdi-chevron-up)')
  }

  /**
   * Get the down button for an envelope.
   */
  getEnvelopeDownButton(envelopeName: string): Locator {
    const envelope = this.page.locator('.v-list-item').filter({ hasText: envelopeName }).first()
    return envelope.locator('button:has(.mdi-chevron-down)')
  }

  /**
   * Move an envelope up within its group.
   */
  async moveEnvelopeUp(envelopeName: string) {
    const upButton = this.getEnvelopeUpButton(envelopeName)
    // Wait for the PATCH request to complete when clicking
    const responsePromise = this.page.waitForResponse(
      (r) => r.url().includes('/envelopes/') && r.request().method() === 'PATCH'
    )
    await upButton.click()
    await responsePromise
    // Wait for the button to be enabled again (UI has re-rendered after reorder)
    await expect(upButton).toBeEnabled({ timeout: 5000 }).catch(() => {
      // Button may be disabled if now at top - that's ok
    })
  }

  /**
   * Move an envelope down within its group.
   */
  async moveEnvelopeDown(envelopeName: string) {
    const downButton = this.getEnvelopeDownButton(envelopeName)
    // Wait for the PATCH request to complete when clicking
    const responsePromise = this.page.waitForResponse(
      (r) => r.url().includes('/envelopes/') && r.request().method() === 'PATCH'
    )
    await downButton.click()
    await responsePromise
    // Wait for the button to be enabled again (UI has re-rendered after reorder)
    await expect(downButton).toBeEnabled({ timeout: 5000 }).catch(() => {
      // Button may be disabled if now at bottom - that's ok
    })
  }

  /**
   * Assert the order of groups on the page.
   * @param expectedOrder Array of group names in expected order
   */
  async expectGroupOrder(expectedOrder: string[]) {
    const groupHeaders = this.page.locator('.text-subtitle-2.text-grey')
    const count = await groupHeaders.count()

    // Filter to only the groups in expectedOrder (exclude "Other", "Credit Cards", etc. if not in list)
    const actualOrder: string[] = []
    for (let i = 0; i < count; i++) {
      const text = await groupHeaders.nth(i).textContent()
      if (text && expectedOrder.includes(text.trim())) {
        actualOrder.push(text.trim())
      }
    }

    expect(actualOrder).toEqual(expectedOrder)
  }

  /**
   * Assert that the specified groups appear in the given order relative to each other.
   * Other groups may exist in between them.
   * @param expectedOrder Array of group names in expected relative order
   */
  async expectGroupContains(expectedOrder: string[]) {
    // Use the specific class for group name spans within envelope-group-header
    const groupNameSpans = this.page.locator('.envelope-group-header .text-subtitle-2.text-grey')
    await expect(groupNameSpans.first()).toBeVisible({ timeout: 10000 })

    // Wait for the expected order to be reflected in the DOM (polling)
    await expect(async () => {
      const count = await groupNameSpans.count()

      // Collect all group names in order
      const allGroups: string[] = []
      for (let i = 0; i < count; i++) {
        const text = await groupNameSpans.nth(i).textContent()
        if (text) {
          allGroups.push(text.trim())
        }
      }

      // Filter to only the groups we care about, preserving order
      const actualOrder = allGroups.filter((g) => expectedOrder.includes(g))

      expect(actualOrder).toEqual(expectedOrder)
    }).toPass({ timeout: 5000 })
  }

  /**
   * Assert the order of envelopes within a group section.
   * @param groupName The name of the group (or "Other" for ungrouped)
   * @param expectedOrder Array of envelope names in expected order
   */
  async expectEnvelopeOrderInGroup(groupName: string, expectedOrder: string[]) {
    // Find the group section and wait for it to be visible (ensures page is loaded)
    const groupHeader = this.page.locator('.envelope-group-header').filter({ hasText: groupName }).first()
    await expect(groupHeader).toBeVisible({ timeout: 10000 })

    // The list follows the header - find the next sibling list
    const envelopeList = groupHeader.locator('~ .v-list, ~ * .v-list').first()
    const envelopeItems = envelopeList.locator('.v-list-item')

    // Wait for the expected order to be reflected in the DOM (polling)
    await expect(async () => {
      const actualOrder: string[] = []
      const count = await envelopeItems.count()
      for (let i = 0; i < count; i++) {
        const title = envelopeItems.nth(i).locator('.v-list-item-title')
        const text = await title.textContent()
        if (text) {
          // Extract just the envelope name (may have rule icons after)
          const name = text.trim().split('\n')[0].trim()
          actualOrder.push(name)
        }
      }

      expect(actualOrder).toEqual(expectedOrder)
    }).toPass({ timeout: 5000 })
  }

  // ==================== Collapse/Expand ====================

  /**
   * Get the group header element by name.
   */
  getGroupHeader(groupName: string): Locator {
    return this.page.locator('.envelope-group-header').filter({ hasText: groupName }).first()
  }

  /**
   * Toggle collapse for a section by clicking its header.
   */
  async toggleGroupCollapse(groupName: string) {
    await this.getGroupHeader(groupName).click()
  }

  /**
   * Assert that a section is collapsed (chevron rotated).
   */
  async expectGroupCollapsed(groupName: string) {
    const header = this.getGroupHeader(groupName)
    const chevron = header.locator('.collapse-chevron')
    await expect(chevron).toHaveClass(/rotate-collapsed/)
  }

  /**
   * Assert that a section is expanded (chevron not rotated).
   */
  async expectGroupExpanded(groupName: string) {
    const header = this.getGroupHeader(groupName)
    const chevron = header.locator('.collapse-chevron')
    await expect(chevron).not.toHaveClass(/rotate-collapsed/)
  }

  /**
   * Assert that the content card for a section is visible.
   */
  async expectGroupContentVisible(groupName: string) {
    const header = this.getGroupHeader(groupName)
    // The v-card follows the header in the DOM
    const card = header.locator('+ .v-expand-transition .v-card, ~ .v-expand-transition .v-card').first()
    await expect(card).toBeVisible()
  }

  /**
   * Assert that the content card for a section is hidden.
   */
  async expectGroupContentHidden(groupName: string) {
    const header = this.getGroupHeader(groupName)
    // The v-card follows the header in the DOM
    const card = header.locator('+ .v-expand-transition .v-card, ~ .v-expand-transition .v-card').first()
    await expect(card).toBeHidden()
  }

  // ==================== Overspent Alert ====================

  /**
   * Assert the overspent alert is visible.
   */
  async expectOverspentAlertVisible() {
    await expect(this.overspentAlert).toBeVisible()
  }

  /**
   * Assert the overspent alert is not visible.
   */
  async expectNoOverspentAlert() {
    await expect(this.overspentAlert).not.toBeVisible()
  }

  /**
   * Assert a specific envelope is listed in the overspent alert.
   */
  async expectOverspentEnvelopeListed(envelopeName: string) {
    await expect(this.overspentAlert).toContainText(envelopeName)
  }

  /**
   * Click the Cover button for an overspent envelope to open the transfer dialog.
   */
  async clickCoverOverspending(envelopeName?: string) {
    await expect(this.overspentAlert).toBeVisible()
    // Click the Cover button within the list item
    const listItems = this.overspentAlert.locator('.v-list-item')
    if (envelopeName) {
      await listItems
        .filter({ hasText: envelopeName })
        .getByRole('button', { name: 'Cover' })
        .click()
    } else {
      await listItems.first().getByRole('button', { name: 'Cover' }).click()
    }
    await expect(this.transferDialog).toBeVisible()
  }

  // ==================== Mobile Action Sheet ====================

  /**
   * Assert the action sheet is visible.
   */
  async expectActionSheetVisible() {
    await expect(this.actionSheet).toBeVisible()
  }

  /**
   * Assert the action sheet is hidden.
   */
  async expectActionSheetHidden() {
    await expect(this.actionSheet).toBeHidden()
  }

  /**
   * Assert the activity column is hidden (mobile layout).
   */
  async expectActivityColumnHidden() {
    const activityCol = this.page.locator('.activity-column')
    // Check that either it doesn't exist or isn't visible
    const count = await activityCol.count()
    if (count > 0) {
      await expect(activityCol.first()).toBeHidden()
    }
  }

  /**
   * Assert the activity column is visible (desktop layout).
   */
  async expectActivityColumnVisible() {
    const activityCol = this.page.locator('.activity-column')
    await expect(activityCol.first()).toBeVisible()
  }

  /**
   * Assert the action buttons are hidden (mobile layout).
   */
  async expectActionButtonsHidden() {
    const actionButtons = this.page.locator('.action-buttons')
    const count = await actionButtons.count()
    if (count > 0) {
      await expect(actionButtons.first()).toBeHidden()
    }
  }

  /**
   * Assert the balance column is visible.
   */
  async expectBalanceColumnVisible() {
    const balanceCol = this.page.locator('.balance-column')
    await expect(balanceCol.first()).toBeVisible()
  }

  /**
   * Assert the activity dialog is visible.
   */
  async expectActivityDialogVisible() {
    await expect(this.activityDialog).toBeVisible()
  }

  /**
   * Assert the activity dialog is hidden.
   */
  async expectActivityDialogHidden() {
    await expect(this.activityDialog).toBeHidden()
  }
}
