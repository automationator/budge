import { type Page, type Locator, expect } from '@playwright/test'
import { BasePage } from './base.page'

/**
 * Page object for the Manage Locations settings view.
 */
export class LocationsSettingsPage extends BasePage {
  // Header
  readonly backButton: Locator
  readonly pageTitle: Locator
  readonly addLocationButton: Locator

  // Locations List
  readonly locationsCard: Locator
  readonly locationsList: Locator

  // Create/Edit Dialog
  readonly editDialog: Locator
  readonly nameInput: Locator
  readonly iconInput: Locator
  readonly descriptionInput: Locator
  readonly saveButton: Locator
  readonly cancelButton: Locator

  // Delete Dialog
  readonly deleteDialog: Locator
  readonly confirmDeleteButton: Locator
  readonly cancelDeleteButton: Locator

  constructor(page: Page) {
    super(page)

    // Header
    this.backButton = page.getByRole('button', { name: 'Back to Settings' })
    this.pageTitle = page.locator('h1').filter({ hasText: 'Manage Locations' })
    this.addLocationButton = page.getByRole('button', { name: 'Add Location' })

    // Locations List
    this.locationsCard = page.locator('.v-card').filter({ has: page.locator('.v-list') })
    this.locationsList = this.locationsCard.locator('.v-list')

    // Create/Edit Dialog (title changes based on mode)
    this.editDialog = page.locator('.v-dialog').filter({
      has: page.locator('.v-card-title').filter({ hasText: /Add Location|Edit Location/ }),
    })
    this.nameInput = this.editDialog
      .locator('.v-text-field')
      .filter({ hasText: 'Name' })
      .locator('input')
    this.iconInput = this.editDialog
      .locator('.v-text-field')
      .filter({ hasText: 'Icon' })
      .locator('input')
    this.descriptionInput = this.editDialog.locator('.v-textarea').locator('textarea')
    this.saveButton = this.editDialog.getByRole('button', { name: /Save|Create/ })
    this.cancelButton = this.editDialog.getByRole('button', { name: 'Cancel' })

    // Delete Dialog
    this.deleteDialog = page.locator('.v-dialog').filter({ hasText: 'Delete Location' })
    this.confirmDeleteButton = this.deleteDialog.getByRole('button', { name: 'Delete' })
    this.cancelDeleteButton = this.deleteDialog.getByRole('button', { name: 'Cancel' })
  }

  async goto() {
    await this.page.goto('/settings/locations')
    await this.waitForPageLoad()
  }

  /**
   * Get a location list item by name.
   */
  getLocationItem(name: string): Locator {
    return this.locationsList.locator('.v-list-item').filter({ hasText: name })
  }

  /**
   * Open the add location dialog.
   */
  async openAddDialog() {
    await this.addLocationButton.click()
    await expect(this.editDialog).toBeVisible()
  }

  /**
   * Open the edit dialog for a location.
   */
  async openEditDialog(locationName: string) {
    await this.getLocationItem(locationName).click()
    await expect(this.editDialog).toBeVisible()
  }

  /**
   * Create a new location.
   */
  async createLocation(data: { name: string; icon?: string; description?: string }) {
    await this.openAddDialog()
    await this.fillLocationForm(data)
    await this.saveButton.click()
    await expect(this.editDialog).toBeHidden({ timeout: 10000 })
  }

  /**
   * Edit an existing location.
   */
  async editLocation(
    locationName: string,
    data: {
      name?: string
      icon?: string
      description?: string
    }
  ) {
    await this.openEditDialog(locationName)
    await this.fillLocationForm(data)
    await this.saveButton.click()
    await expect(this.editDialog).toBeHidden({ timeout: 10000 })
  }

  /**
   * Fill the location form fields.
   */
  private async fillLocationForm(data: { name?: string; icon?: string; description?: string }) {
    if (data.name !== undefined) {
      await this.nameInput.clear()
      await this.nameInput.fill(data.name)
    }
    if (data.icon !== undefined) {
      await this.iconInput.clear()
      await this.iconInput.fill(data.icon)
    }
    if (data.description !== undefined) {
      await this.descriptionInput.clear()
      await this.descriptionInput.fill(data.description)
    }
  }

  /**
   * Click the delete button for a location.
   */
  async clickDeleteButton(locationName: string) {
    const item = this.getLocationItem(locationName)
    await item.locator('button').filter({ has: this.page.locator('[class*="mdi-delete"]') }).click()
    await expect(this.deleteDialog).toBeVisible()
  }

  /**
   * Delete a location.
   */
  async deleteLocation(locationName: string) {
    await this.clickDeleteButton(locationName)
    await this.confirmDeleteButton.click()
    await expect(this.deleteDialog).toBeHidden({ timeout: 10000 })
  }

  /**
   * Cancel delete dialog.
   */
  async cancelDelete() {
    await this.cancelDeleteButton.click()
    await expect(this.deleteDialog).toBeHidden()
  }

  /**
   * Go back to settings.
   */
  async goBackToSettings() {
    await this.backButton.click()
    await expect(this.page).toHaveURL('/settings')
  }

  /**
   * Get location count.
   */
  async getLocationCount(): Promise<number> {
    const items = this.locationsList.locator('.v-list-item')
    const count = await items.count()
    // Check if empty state is showing
    const emptyText = await items.first().textContent()
    if (emptyText?.includes('No locations yet')) {
      return 0
    }
    return count
  }

  /**
   * Check if a location exists.
   */
  async locationExists(name: string): Promise<boolean> {
    const item = this.getLocationItem(name)
    return await item.isVisible({ timeout: 2000 }).catch(() => false)
  }

  /**
   * Assert page title is visible.
   */
  async expectPageTitle() {
    await expect(this.pageTitle).toBeVisible()
  }

  /**
   * Assert locations list is visible.
   */
  async expectLocationsListVisible() {
    await expect(this.locationsCard).toBeVisible()
  }

  /**
   * Assert empty state is shown.
   */
  async expectEmptyState() {
    const emptyMessage = this.locationsList.locator('.v-list-item').filter({ hasText: 'No locations yet' })
    await expect(emptyMessage).toBeVisible()
  }
}
