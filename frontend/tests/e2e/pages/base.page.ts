import { type Page, type Locator, expect } from '@playwright/test'
import { SnackbarComponent } from '../components/snackbar.component'
import { DialogComponent } from '../components/dialog.component'

/**
 * Base page class with common operations shared across all page objects.
 */
export class BasePage {
  readonly page: Page
  readonly snackbar: SnackbarComponent
  readonly dialog: DialogComponent
  readonly loadingSpinner: Locator
  readonly pageHeading: Locator

  constructor(page: Page) {
    this.page = page
    this.snackbar = new SnackbarComponent(page)
    this.dialog = new DialogComponent(page)
    this.loadingSpinner = page.locator('.v-progress-circular')
    this.pageHeading = page.locator('h1')
  }

  /**
   * Wait for the page to finish loading (DOM ready + Vue mounted + no spinners).
   * Uses element-based waiting instead of 'networkidle' for reliability with parallel tests.
   */
  async waitForPageLoad() {
    // Wait for DOM to be interactive (fast, reliable)
    await this.page.waitForLoadState('domcontentloaded')

    // Wait for Vue app to mount (main container visible)
    await this.page.locator('.v-main, .v-application').first().waitFor({
      state: 'visible',
      timeout: 20000,
    })

    // Wait for loading spinners to disappear
    await this.waitForNoSpinners()
  }

  /**
   * Wait for any visible loading spinners to disappear.
   */
  private async waitForNoSpinners() {
    const spinner = this.page.locator('.v-progress-circular').first()
    // Only wait if spinner is currently visible
    const hasSpinner = await spinner.isVisible().catch(() => false)
    if (hasSpinner) {
      await spinner.waitFor({ state: 'hidden', timeout: 15000 }).catch(() => {
        // Spinner might have already been removed
      })
    }
  }

  /**
   * Wait for an API response matching the given URL pattern.
   */
  async waitForApiResponse(urlPattern: string | RegExp) {
    return this.page.waitForResponse((response) => {
      if (typeof urlPattern === 'string') {
        return response.url().includes(urlPattern)
      }
      return urlPattern.test(response.url())
    })
  }

  /**
   * Assert no loading spinners are visible.
   */
  async expectNoLoadingSpinner() {
    await expect(this.loadingSpinner).toBeHidden({ timeout: 10000 })
  }

  /**
   * Get the page title/heading text.
   */
  async getPageTitle(): Promise<string> {
    return await this.pageHeading.textContent() || ''
  }

  /**
   * Assert the page has a specific heading.
   */
  async expectHeading(text: string) {
    await expect(this.pageHeading).toContainText(text)
  }

  /**
   * Click a button by its text content.
   */
  async clickButton(text: string) {
    await this.page.getByRole('button', { name: text }).click()
  }

  /**
   * Click a link by its text content.
   */
  async clickLink(text: string) {
    await this.page.getByRole('link', { name: text }).click()
  }

  /**
   * Navigate using the main navigation.
   */
  async navigateTo(path: 'Accounts' | 'Transactions' | 'Envelopes' | 'Recurring' | 'Reports' | 'Settings') {
    // Try to find in navigation rail/drawer
    const navItem = this.page.locator('.v-navigation-drawer, .v-bottom-navigation').getByText(path)
    if (await navItem.isVisible({ timeout: 1000 }).catch(() => false)) {
      await navItem.click()
    } else {
      // Fallback to direct navigation
      const routes: Record<string, string> = {
        Accounts: '/accounts',
        Transactions: '/transactions',
        Envelopes: '/',
        Recurring: '/recurring',
        Reports: '/reports',
        Settings: '/settings',
      }
      await this.page.goto(routes[path])
    }
    await this.waitForPageLoad()
  }
}
