import { type Page, type Locator, expect } from '@playwright/test'
import { BasePage } from './base.page'

/**
 * Page object for the Team Members settings view.
 */
export class TeamMembersPage extends BasePage {
  // Header
  readonly backButton: Locator
  readonly pageTitle: Locator
  readonly addMemberButton: Locator

  // Members List
  readonly membersCard: Locator
  readonly membersList: Locator
  readonly loadingSpinner: Locator

  // Add Member Dialog
  readonly addMemberDialog: Locator
  readonly usernameInput: Locator
  readonly roleSelect: Locator
  readonly addMemberSubmitButton: Locator
  readonly cancelAddButton: Locator

  // Change Role Dialog
  readonly changeRoleDialog: Locator
  readonly roleSelectInDialog: Locator
  readonly updateRoleButton: Locator
  readonly cancelRoleButton: Locator

  // Remove Member Dialog
  readonly removeDialog: Locator
  readonly confirmRemoveButton: Locator
  readonly cancelRemoveButton: Locator

  constructor(page: Page) {
    super(page)

    // Header
    this.backButton = page.getByRole('button', { name: 'Back' })
    this.pageTitle = page.locator('h1').filter({ hasText: 'Budget Settings' })
    this.addMemberButton = page.getByRole('button', { name: 'Add Member' })

    // Members List
    this.membersCard = page.locator('.v-card').filter({ has: page.locator('.v-list') })
    this.membersList = this.membersCard.locator('.v-list')
    this.loadingSpinner = page.locator('.v-progress-circular')

    // Add Member Dialog
    this.addMemberDialog = page.locator('.v-dialog').filter({ hasText: 'Add Budget Member' })
    this.usernameInput = this.addMemberDialog.locator('.v-text-field').filter({ hasText: 'Username' }).locator('input')
    this.roleSelect = this.addMemberDialog.locator('.v-select').filter({ hasText: 'Role' })
    this.addMemberSubmitButton = this.addMemberDialog.getByRole('button', { name: 'Add Member' })
    this.cancelAddButton = this.addMemberDialog.getByRole('button', { name: 'Cancel' })

    // Change Role Dialog
    this.changeRoleDialog = page.locator('.v-dialog').filter({ hasText: 'Change Role' })
    this.roleSelectInDialog = this.changeRoleDialog.locator('.v-select')
    this.updateRoleButton = this.changeRoleDialog.getByRole('button', { name: 'Update Role' })
    this.cancelRoleButton = this.changeRoleDialog.getByRole('button', { name: 'Cancel' })

    // Remove Member Dialog
    this.removeDialog = page.locator('.v-dialog').filter({ hasText: 'Remove Member' })
    this.confirmRemoveButton = this.removeDialog.getByRole('button', { name: 'Remove' })
    this.cancelRemoveButton = this.removeDialog.getByRole('button', { name: 'Cancel' })
  }

  async goto() {
    await this.page.goto('/settings/budget-settings')
    await this.waitForPageLoad()
  }

  /**
   * Get a member list item by username.
   */
  getMemberItem(username: string): Locator {
    return this.membersList.locator('.v-list-item').filter({ hasText: `@${username}` })
  }

  /**
   * Get the role chip for a member (excludes "You" chip).
   */
  getMemberRole(username: string): Locator {
    return this.getMemberItem(username).locator('.v-chip').filter({ hasNotText: 'You' })
  }

  /**
   * Open the menu for a member.
   */
  async openMemberMenu(username: string) {
    const item = this.getMemberItem(username)
    await item.locator('button').filter({ has: this.page.locator('[class*="mdi-dots-vertical"]') }).click()
    const menu = this.page.locator('.v-overlay--active .v-list')
    await menu.waitFor({ state: 'visible', timeout: 5000 })
    return menu
  }

  /**
   * Open the add member dialog.
   */
  async openAddMemberDialog() {
    await this.addMemberButton.click()
    await expect(this.addMemberDialog).toBeVisible()
  }

  /**
   * Add a new team member.
   */
  async addMember(username: string, role: 'owner' | 'admin' | 'member' | 'viewer' = 'member') {
    await this.openAddMemberDialog()
    await this.usernameInput.fill(username)

    // Select role
    await this.roleSelect.click()
    const menu = this.page.locator('.v-menu .v-list-item')
    const roleTitle = role.charAt(0).toUpperCase() + role.slice(1)
    // Wait specifically for the target item (not just any item)
    const targetItem = menu.filter({ hasText: roleTitle }).first()
    await targetItem.waitFor({ state: 'visible', timeout: 10000 })
    await targetItem.click()

    await this.addMemberSubmitButton.click()
    await expect(this.addMemberDialog).toBeHidden({ timeout: 10000 })
  }

  /**
   * Open change role dialog for a member.
   */
  async openChangeRoleDialog(username: string) {
    const menu = await this.openMemberMenu(username)
    await menu.locator('.v-list-item').filter({ hasText: 'Change Role' }).click()
    await expect(this.changeRoleDialog).toBeVisible()
  }

  /**
   * Change a member's role.
   */
  async changeMemberRole(username: string, newRole: 'owner' | 'admin' | 'member' | 'viewer') {
    await this.openChangeRoleDialog(username)

    await this.roleSelectInDialog.click()
    const menu = this.page.locator('.v-menu .v-list-item')
    const roleTitle = newRole.charAt(0).toUpperCase() + newRole.slice(1)
    // Wait specifically for the target item (not just any item)
    const targetItem = menu.filter({ hasText: roleTitle }).first()
    await targetItem.waitFor({ state: 'visible', timeout: 10000 })
    await targetItem.click()

    await this.updateRoleButton.click()
    await expect(this.changeRoleDialog).toBeHidden({ timeout: 10000 })
  }

  /**
   * Open remove member dialog.
   */
  async openRemoveDialog(username: string) {
    const menu = await this.openMemberMenu(username)
    await menu.locator('.v-list-item').filter({ hasText: 'Remove' }).click()
    await expect(this.removeDialog).toBeVisible()
  }

  /**
   * Remove a member.
   */
  async removeMember(username: string) {
    await this.openRemoveDialog(username)
    await this.confirmRemoveButton.click()
    await expect(this.removeDialog).toBeHidden({ timeout: 10000 })
  }

  /**
   * Go back to settings.
   */
  async goBackToSettings() {
    await this.backButton.click()
    await expect(this.page).toHaveURL('/settings')
  }

  /**
   * Get member count.
   */
  async getMemberCount(): Promise<number> {
    return await this.membersList.locator('.v-list-item').count()
  }

  /**
   * Check if a member exists (waits for the item to appear).
   */
  async memberExists(username: string): Promise<boolean> {
    try {
      await expect(this.getMemberItem(username)).toBeVisible({ timeout: 10000 })
      return true
    } catch {
      return false
    }
  }

  /**
   * Assert page title is visible.
   */
  async expectPageTitle() {
    await expect(this.pageTitle).toBeVisible()
  }

  /**
   * Assert member list is visible.
   */
  async expectMemberListVisible() {
    await expect(this.membersCard).toBeVisible()
  }
}
