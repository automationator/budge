import { type Page, type Locator, expect } from '@playwright/test'
import { BasePage } from './base.page'

/**
 * Page object for the Settings view.
 */
export class SettingsPage extends BasePage {
  // Header
  readonly pageTitle: Locator

  // Profile Card - View Mode
  readonly profileCard: Locator
  readonly displayName: Locator
  readonly usernameDisplay: Locator
  readonly editProfileButton: Locator

  // Profile Card - Edit Mode
  readonly usernameInput: Locator
  readonly saveChangesButton: Locator
  readonly cancelEditButton: Locator

  // Security Card
  readonly securityCard: Locator
  readonly changePasswordButton: Locator

  // Password Dialog
  readonly passwordDialog: Locator
  readonly newPasswordInput: Locator
  readonly confirmPasswordInput: Locator
  readonly updatePasswordButton: Locator
  readonly cancelPasswordButton: Locator

  // Navigation Links
  readonly budgetSettingsLink: Locator
  readonly notificationPreferencesLink: Locator
  readonly managePayeesLink: Locator
  readonly startFreshLink: Locator

  // Admin Settings Card
  readonly adminSettingsCard: Locator
  readonly registrationSwitch: Locator

  constructor(page: Page) {
    super(page)

    // Header
    this.pageTitle = page.locator('h1').filter({ hasText: 'Settings' })

    // Profile Card
    this.profileCard = page.locator('.v-card').filter({ has: page.locator('.v-avatar') }).first()
    this.displayName = this.profileCard.locator('.text-h6')
    this.usernameDisplay = this.profileCard.locator('.text-body-2')
    this.editProfileButton = page.getByRole('button', { name: 'Edit Profile' })

    // Edit Mode Fields
    this.usernameInput = page.locator('.v-text-field').filter({ hasText: 'Username' }).locator('input')
    this.saveChangesButton = page.getByRole('button', { name: 'Save Changes' })
    this.cancelEditButton = page.getByRole('button', { name: 'Cancel' })

    // Security Card
    this.securityCard = page.locator('.v-card').filter({ hasText: 'Security' })
    this.changePasswordButton = page.getByRole('button', { name: 'Change Password' })

    // Password Dialog
    this.passwordDialog = page.locator('.v-dialog').filter({ hasText: 'Change Password' })
    this.newPasswordInput = this.passwordDialog.locator('.v-text-field').filter({ hasText: 'New Password' }).locator('input')
    this.confirmPasswordInput = this.passwordDialog.locator('.v-text-field').filter({ hasText: 'Confirm Password' }).locator('input')
    this.updatePasswordButton = this.passwordDialog.getByRole('button', { name: 'Update Password' })
    this.cancelPasswordButton = this.passwordDialog.getByRole('button', { name: 'Cancel' })

    // Navigation Links
    this.budgetSettingsLink = page.locator('.v-list-item').filter({ hasText: 'Budget Settings' })
    this.notificationPreferencesLink = page.locator('.v-list-item').filter({ hasText: 'Notification Preferences' })
    this.managePayeesLink = page.locator('.v-list-item').filter({ hasText: 'Manage Payees' })
    this.startFreshLink = page.locator('.v-list-item').filter({ hasText: 'Start Fresh' })

    // Admin Settings Card
    this.adminSettingsCard = page.locator('.v-card').filter({ hasText: 'Admin Settings' })
    this.registrationSwitch = this.adminSettingsCard.locator('.v-switch')
  }

  async goto() {
    await this.page.goto('/settings')
    await this.waitForPageLoad()
    await this.waitForUserLoaded()
  }

  /**
   * Wait for user data to be loaded from the auth store.
   * The settings page renders admin card conditionally based on user data,
   * which may not be available immediately after navigation.
   */
  async waitForUserLoaded() {
    await expect(this.displayName).not.toBeEmpty({ timeout: 10000 })
  }

  /**
   * Start editing the profile.
   */
  async startEditing() {
    await this.editProfileButton.click()
    await expect(this.saveChangesButton).toBeVisible()
  }

  /**
   * Update profile fields.
   */
  async updateProfile(data: { username: string }) {
    await this.startEditing()

    await this.usernameInput.clear()
    await this.usernameInput.fill(data.username)

    await this.saveChangesButton.click()
  }

  /**
   * Cancel profile editing.
   */
  async cancelEditing() {
    await this.cancelEditButton.click()
    await expect(this.editProfileButton).toBeVisible()
  }

  /**
   * Open the change password dialog.
   */
  async openPasswordDialog() {
    await this.changePasswordButton.click()
    await expect(this.passwordDialog).toBeVisible()
  }

  /**
   * Change the password.
   */
  async changePassword(newPassword: string, confirmPassword: string) {
    await this.openPasswordDialog()
    await this.newPasswordInput.fill(newPassword)
    await this.confirmPasswordInput.fill(confirmPassword)
    await this.updatePasswordButton.click()
  }

  /**
   * Navigate to budget settings page.
   */
  async goToBudgetSettings() {
    await this.budgetSettingsLink.click()
    await expect(this.page).toHaveURL('/settings/budget-settings')
  }

  /**
   * Navigate to notification preferences page.
   */
  async goToNotificationPreferences() {
    await this.notificationPreferencesLink.click()
    await expect(this.page).toHaveURL('/settings/notifications')
  }

  /**
   * Navigate to manage payees page.
   */
  async goToManagePayees() {
    await this.managePayeesLink.click()
    await expect(this.page).toHaveURL('/settings/payees')
  }

  /**
   * Navigate to start fresh page.
   */
  async goToStartFresh() {
    await this.startFreshLink.click()
    await expect(this.page).toHaveURL('/settings/start-fresh')
  }

  /**
   * Assert page title is visible.
   */
  async expectPageTitle() {
    await expect(this.pageTitle).toBeVisible()
  }

  /**
   * Assert profile card shows user info.
   */
  async expectProfileVisible() {
    await expect(this.profileCard).toBeVisible()
    await expect(this.displayName).toBeVisible()
  }

  /**
   * Assert security card is visible.
   */
  async expectSecurityCardVisible() {
    await expect(this.securityCard).toBeVisible()
    await expect(this.changePasswordButton).toBeVisible()
  }

  /**
   * Assert navigation links are visible.
   */
  async expectNavigationLinksVisible() {
    await expect(this.budgetSettingsLink).toBeVisible()
    await expect(this.notificationPreferencesLink).toBeVisible()
    await expect(this.managePayeesLink).toBeVisible()
    await expect(this.startFreshLink).toBeVisible()
  }

  /**
   * Assert admin settings card is visible.
   */
  async expectAdminCardVisible() {
    await this.waitForUserLoaded()
    await expect(this.adminSettingsCard).toBeVisible({ timeout: 10000 })
  }

  /**
   * Assert admin settings card is not visible.
   */
  async expectAdminCardHidden() {
    await expect(this.adminSettingsCard).toBeHidden()
  }

  /**
   * Check if registration is currently enabled.
   */
  async isRegistrationEnabled(): Promise<boolean> {
    const input = this.registrationSwitch.locator('input')
    return await input.isChecked()
  }

  /**
   * Toggle the registration setting.
   */
  async toggleRegistration() {
    const switchInput = this.registrationSwitch.locator('input[type="checkbox"]')

    // Wait for admin settings to finish loading (switch is disabled while loading)
    await expect(switchInput).toBeEnabled()
    const wasChecked = await switchInput.isChecked()

    // Click the input directly via JS to reliably toggle the Vuetify v-switch
    await switchInput.evaluate((el: HTMLInputElement) => el.click())

    // Wait for the save cycle to complete (switch becomes disabled then enabled again)
    await expect(switchInput).toBeEnabled()
    await expect(switchInput).toBeChecked({ checked: !wasChecked })
  }
}
