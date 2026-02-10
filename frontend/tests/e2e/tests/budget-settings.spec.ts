import { test, expect } from '../fixtures/test-setup'
import { BudgetSettingsPage } from '../pages/budget-settings.page'
import { BudgetMenuPage } from '../pages/budget-menu.page'
import * as fs from 'fs'
import * as path from 'path'
import * as os from 'os'

test.describe('BudgetSettings', () => {
  test.describe('Budget Name', () => {
    test('allows owner to rename budget', async ({ authenticatedPage }) => {
      const budgetSettings = new BudgetSettingsPage(authenticatedPage)
      await budgetSettings.goto()

      const newName = `Renamed Budget ${Date.now()}`
      await budgetSettings.renameBudget(newName)

      // Verify name changed in display
      const displayedName = await budgetSettings.getBudgetName()
      expect(displayedName).toBe(newName)
    })
  })

  test.describe('Delete Budget', () => {
    test('successfully deletes budget with correct password', async ({
      authenticatedPage,
      testApi,
      testContext,
    }) => {
      // Create a second budget to delete (can't test deleting last budget easily)
      const newBudget = await testApi.createBudget(testContext.user.userId, 'Budget To Delete')

      // Navigate to home first and switch to new budget
      await authenticatedPage.goto('/')
      const budgetMenu = new BudgetMenuPage(authenticatedPage)
      await budgetMenu.waitForVisible()

      // Open menu and select budget
      await budgetMenu.openMenu()
      const budgetItem = authenticatedPage.locator('.v-overlay__content .v-list-item', {
        hasText: newBudget.name,
      })
      await budgetItem.click()

      // Wait for budget switch
      await expect(budgetMenu.budgetNameDisplay).toHaveText(newBudget.name)

      // Navigate to budget settings
      const budgetSettings = new BudgetSettingsPage(authenticatedPage)
      await budgetSettings.goto()

      // Delete the budget with correct password (same password used in test fixture)
      await budgetSettings.deleteBudget('TestPassword123!')

      // Should redirect to home (when there are other budgets) or settings
      await expect(authenticatedPage).toHaveURL(/\/$|\/settings/)
    })
  })

  test.describe('Navigation', () => {
    test('navigates to budget settings from budget menu', async ({ authenticatedPage }) => {
      await authenticatedPage.goto('/')
      const budgetMenu = new BudgetMenuPage(authenticatedPage)
      await budgetMenu.waitForVisible()

      // Click header to open menu
      await budgetMenu.menuHeader.click()

      // Wait for dropdown to open
      const dropdown = authenticatedPage.locator('.v-overlay__content .v-list')
      await expect(dropdown).toBeVisible()

      // Click budget settings item
      const settingsItem = dropdown.locator('.v-list-item:has(.mdi-cog-outline)')
      await settingsItem.click()

      // Verify navigation
      await expect(authenticatedPage).toHaveURL(/\/settings\/budget-settings/)
    })

    test('back button returns to previous page', async ({ authenticatedPage }) => {
      // First go to settings, then to budget settings
      await authenticatedPage.goto('/settings')
      await expect(authenticatedPage).toHaveURL(/\/settings$/)

      // Navigate to budget settings from settings page
      const budgetSettingsLink = authenticatedPage.locator('a[href="/settings/budget-settings"]')
      await budgetSettingsLink.click()

      await expect(authenticatedPage).toHaveURL(/\/settings\/budget-settings/)

      // Now click back
      const budgetSettings = new BudgetSettingsPage(authenticatedPage)
      await budgetSettings.backButton.click()

      // Should go back to settings
      await expect(authenticatedPage).toHaveURL(/\/settings$/)
    })
  })

  test.describe('Data Management', () => {
    test('exports budget data as JSON file', async ({ authenticatedPage, testApi, testContext }) => {
      // Create some test data to export
      await testApi.createAccount(testContext.user.budgetId, {
        name: 'Export Test Account',
        accountType: 'checking',
      })

      const budgetSettings = new BudgetSettingsPage(authenticatedPage)
      await budgetSettings.goto()

      // Export and verify file download
      const filePath = await budgetSettings.exportBudget()
      expect(filePath).toBeTruthy()

      // Verify file contains valid JSON with expected structure
      const content = fs.readFileSync(filePath, 'utf-8')
      const data = JSON.parse(content)

      expect(data.version).toBe('1.0')
      expect(data.budget).toBeDefined()
      expect(Array.isArray(data.accounts)).toBe(true)
      expect(Array.isArray(data.envelopes)).toBe(true)
    })

    test('validates import file format', async ({ authenticatedPage }) => {
      const budgetSettings = new BudgetSettingsPage(authenticatedPage)
      await budgetSettings.goto()
      await budgetSettings.openImportDialog()

      // Create an invalid JSON file
      const invalidFile = path.join(os.tmpdir(), 'invalid-import.json')
      fs.writeFileSync(invalidFile, '{ invalid json }')

      await budgetSettings.selectImportFile(invalidFile)

      // Should show error message
      const errorMessage = authenticatedPage.locator('.v-messages__message')
      await expect(errorMessage.first()).toBeVisible({ timeout: 5000 })

      // Cleanup
      fs.unlinkSync(invalidFile)
    })

    test('shows file preview when valid file selected', async ({
      authenticatedPage,
      testApi,
      testContext,
    }) => {
      // Create some test data
      await testApi.createAccount(testContext.user.budgetId, {
        name: 'Preview Test Account',
        accountType: 'checking',
      })

      const budgetSettings = new BudgetSettingsPage(authenticatedPage)
      await budgetSettings.goto()

      // First export to get a valid file
      const exportPath = await budgetSettings.exportBudget()

      // Open import dialog and select the file
      await budgetSettings.openImportDialog()
      await budgetSettings.selectImportFile(exportPath)

      // Wait for preview to appear
      await budgetSettings.waitForImportPreview()

      // Verify preview shows expected content
      await expect(budgetSettings.importPreview).toContainText('accounts')
    })

    test('shows replace mode warning', async ({ authenticatedPage, testApi, testContext }) => {
      // Create some test data
      await testApi.createAccount(testContext.user.budgetId, {
        name: 'Warning Test Account',
        accountType: 'checking',
      })

      const budgetSettings = new BudgetSettingsPage(authenticatedPage)
      await budgetSettings.goto()

      // Export to get a valid file
      const exportPath = await budgetSettings.exportBudget()

      // Open import dialog and select file
      await budgetSettings.openImportDialog()
      await budgetSettings.selectImportFile(exportPath)
      await budgetSettings.waitForImportPreview()

      // Select replace mode
      await budgetSettings.selectReplaceMode()

      // Warning should appear
      const warning = authenticatedPage.locator('.v-alert', { hasText: 'permanently delete' })
      await expect(warning).toBeVisible()
    })

    test('requires password for import', async ({ authenticatedPage, testApi, testContext }) => {
      // Create some test data
      await testApi.createAccount(testContext.user.budgetId, {
        name: 'Password Test Account',
        accountType: 'checking',
      })

      const budgetSettings = new BudgetSettingsPage(authenticatedPage)
      await budgetSettings.goto()

      // Export
      const exportPath = await budgetSettings.exportBudget()

      // Open import dialog and select file
      await budgetSettings.openImportDialog()
      await budgetSettings.selectImportFile(exportPath)
      await budgetSettings.waitForImportPreview()

      // Try with wrong password
      await budgetSettings.confirmImport('wrongpassword')

      // Should show password error
      const errorMessage = authenticatedPage.locator('.v-dialog .v-messages__message')
      await expect(errorMessage.first()).toContainText(/invalid/i)
    })

    test('successfully imports budget data with merge mode', async ({
      authenticatedPage,
      testApi,
      testContext,
    }) => {
      // Create some test data
      await testApi.createAccount(testContext.user.budgetId, {
        name: 'Merge Test Account',
        accountType: 'checking',
      })

      const budgetSettings = new BudgetSettingsPage(authenticatedPage)
      await budgetSettings.goto()

      // Export the budget
      const exportPath = await budgetSettings.exportBudget()

      // Open import dialog and select file
      await budgetSettings.openImportDialog()
      await budgetSettings.selectImportFile(exportPath)
      await budgetSettings.waitForImportPreview()

      // Merge mode is default, confirm import with correct password
      await budgetSettings.confirmImport('TestPassword123!')

      // Wait for result dialog
      await budgetSettings.waitForImportResult()

      // Verify result shows accounts imported
      await expect(budgetSettings.importResultDialog).toContainText('account')

      // Close result dialog
      await budgetSettings.closeImportResult()
    })

    test('successfully imports budget data with replace mode', async ({
      authenticatedPage,
      testApi,
      testContext,
    }) => {
      // Create some test data
      await testApi.createAccount(testContext.user.budgetId, {
        name: 'Replace Test Account',
        accountType: 'savings',
      })

      const budgetSettings = new BudgetSettingsPage(authenticatedPage)
      await budgetSettings.goto()

      // Export the budget
      const exportPath = await budgetSettings.exportBudget()

      // Open import dialog and select file
      await budgetSettings.openImportDialog()
      await budgetSettings.selectImportFile(exportPath)
      await budgetSettings.waitForImportPreview()

      // Select replace mode
      await budgetSettings.selectReplaceMode()

      // Confirm import with correct password
      await budgetSettings.confirmImport('TestPassword123!')

      // Wait for result dialog
      await budgetSettings.waitForImportResult()

      // Close result dialog
      await budgetSettings.closeImportResult()
    })
  })
})
