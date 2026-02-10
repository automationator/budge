import { type Page, type Locator, expect } from '@playwright/test'
import { BasePage } from './base.page'

/**
 * Page object for the Notification Settings view.
 */
export class NotificationSettingsPage extends BasePage {
  // Header
  readonly backButton: Locator
  readonly pageTitle: Locator

  // Main Card
  readonly notificationsCard: Locator
  readonly loadingSpinner: Locator

  // About Card
  readonly aboutCard: Locator

  constructor(page: Page) {
    super(page)

    // Header
    this.backButton = page.getByRole('button', { name: 'Back to Settings' })
    this.pageTitle = page.locator('h1').filter({ hasText: 'Notification Preferences' })

    // Main Card
    this.notificationsCard = page.locator('.v-card').filter({ has: page.locator('.v-list') }).first()
    this.loadingSpinner = page.locator('.v-progress-circular')

    // About Card
    this.aboutCard = page.locator('.v-card').filter({ hasText: 'About Notifications' })
  }

  async goto() {
    await this.page.goto('/settings/notifications')
    await this.waitForPageLoad()
  }

  /**
   * Get a notification item by title.
   */
  getNotificationItem(title: string): Locator {
    return this.notificationsCard.locator('.v-list-item').filter({ hasText: title })
  }

  /**
   * Get the switch for a notification type.
   */
  getNotificationSwitch(title: string): Locator {
    return this.getNotificationItem(title).locator('.v-switch input')
  }

  /**
   * Check if a notification is enabled.
   */
  async isNotificationEnabled(title: string): Promise<boolean> {
    const switchElement = this.getNotificationSwitch(title)
    return await switchElement.isChecked()
  }

  /**
   * Toggle a notification on/off.
   */
  async toggleNotification(title: string) {
    const switchElement = this.getNotificationSwitch(title)
    const wasChecked = await switchElement.isChecked()
    await switchElement.click({ force: true })
    await expect(switchElement).toBeChecked({ checked: !wasChecked })
  }

  /**
   * Enable a notification.
   */
  async enableNotification(title: string) {
    const isEnabled = await this.isNotificationEnabled(title)
    if (!isEnabled) {
      await this.toggleNotification(title)
    }
  }

  /**
   * Disable a notification.
   */
  async disableNotification(title: string) {
    const isEnabled = await this.isNotificationEnabled(title)
    if (isEnabled) {
      await this.toggleNotification(title)
    }
  }

  /**
   * Get the threshold input for low balance alerts.
   */
  getLowBalanceThresholdInput(): Locator {
    return this.page.locator('.v-text-field').filter({ hasText: '$' }).locator('input').first()
  }

  /**
   * Set the low balance threshold.
   */
  async setLowBalanceThreshold(amount: string) {
    const input = this.getLowBalanceThresholdInput()
    const responsePromise = this.page.waitForResponse(
      (r) => r.url().includes('/notification-preferences') && r.request().method() === 'PATCH'
    )
    await input.clear()
    await input.fill(amount)
    await input.blur()
    await responsePromise
  }

  /**
   * Get the days input for upcoming expense alerts.
   */
  getUpcomingExpenseDaysInput(): Locator {
    return this.page.locator('.v-text-field').filter({ hasText: 'days before' }).locator('input')
  }

  /**
   * Set the upcoming expense days.
   */
  async setUpcomingExpenseDays(days: string) {
    const input = this.getUpcomingExpenseDaysInput()
    const responsePromise = this.page.waitForResponse(
      (r) => r.url().includes('/notification-preferences') && r.request().method() === 'PATCH'
    )
    await input.clear()
    await input.fill(days)
    await input.blur()
    await responsePromise
  }

  /**
   * Go back to settings.
   */
  async goBackToSettings() {
    await this.backButton.click()
    await expect(this.page).toHaveURL('/settings')
  }

  /**
   * Assert page title is visible.
   */
  async expectPageTitle() {
    await expect(this.pageTitle).toBeVisible()
  }

  /**
   * Assert notifications card is visible.
   */
  async expectNotificationsCardVisible() {
    await expect(this.notificationsCard).toBeVisible()
  }

  /**
   * Assert about card is visible.
   */
  async expectAboutCardVisible() {
    await expect(this.aboutCard).toBeVisible()
  }

  /**
   * Assert all notification types are visible.
   */
  async expectAllNotificationTypesVisible() {
    await expect(this.getNotificationItem('Low Balance Alerts')).toBeVisible()
    await expect(this.getNotificationItem('Upcoming Expenses')).toBeVisible()
    await expect(this.getNotificationItem('Recurring Not Funded')).toBeVisible()
    await expect(this.getNotificationItem('Goal Reached')).toBeVisible()
  }
}
