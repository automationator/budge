// UI rendering tests (profile display, security card, nav links, dialog open/close,
// empty states, form visibility) are in component tests:
// frontend/tests/unit/components/settings/SettingsViews.spec.ts

import { test, expect } from '../fixtures/test-setup'
import { SettingsPage } from '../pages/settings.page'
import { TeamMembersPage } from '../pages/team-members.page'
import { NotificationSettingsPage } from '../pages/notification-settings.page'
import { PayeesSettingsPage } from '../pages/payees-settings.page'
import { LocationsSettingsPage } from '../pages/locations-settings.page'
import { StartFreshPage } from '../pages/start-fresh.page'

// Password used by test factory
const TEST_PASSWORD = 'TestPassword123!'

// Test context is set up automatically via fixtures
// - Database is reset per worker
// - User is created once per file

test.describe('Settings', () => {
  test.describe('Main Settings Page', () => {
    test('can navigate to settings page', async ({ authenticatedPage }) => {
      const settingsPage = new SettingsPage(authenticatedPage)

      await settingsPage.goto()

      await settingsPage.expectPageTitle()
      await expect(authenticatedPage).toHaveURL('/settings')
    })

    test('can update profile', async ({ authenticatedPage, testContext }) => {
      const settingsPage = new SettingsPage(authenticatedPage)
      const newUsername = `updated_${testContext.workerId}_${Date.now()}`

      await settingsPage.goto()
      await settingsPage.updateProfile({
        username: newUsername,
      })

      // Verify the username was updated in the display
      await expect(settingsPage.usernameDisplay).toContainText(newUsername)
    })

    test('can navigate to budget settings', async ({ authenticatedPage }) => {
      const settingsPage = new SettingsPage(authenticatedPage)

      await settingsPage.goto()
      await settingsPage.goToBudgetSettings()

      await expect(authenticatedPage).toHaveURL('/settings/budget-settings')
    })

    test('can navigate to notification preferences', async ({ authenticatedPage }) => {
      const settingsPage = new SettingsPage(authenticatedPage)

      await settingsPage.goto()
      await settingsPage.goToNotificationPreferences()

      await expect(authenticatedPage).toHaveURL('/settings/notifications')
    })

    test('can navigate to manage payees', async ({ authenticatedPage }) => {
      const settingsPage = new SettingsPage(authenticatedPage)

      await settingsPage.goto()
      await settingsPage.goToManagePayees()

      await expect(authenticatedPage).toHaveURL('/settings/payees')
    })

    test('can navigate to start fresh', async ({ authenticatedPage }) => {
      const settingsPage = new SettingsPage(authenticatedPage)

      await settingsPage.goto()
      await settingsPage.goToStartFresh()

      await expect(authenticatedPage).toHaveURL('/settings/start-fresh')
    })
  })

  test.describe('Budget Settings Page', () => {
    test('can navigate to budget settings page', async ({ authenticatedPage }) => {
      const teamPage = new TeamMembersPage(authenticatedPage)

      await teamPage.goto()

      await teamPage.expectPageTitle()
      await expect(authenticatedPage).toHaveURL('/settings/budget-settings')
    })

    test('shows current user in member list', async ({ authenticatedPage }) => {
      const teamPage = new TeamMembersPage(authenticatedPage)

      await teamPage.goto()

      // Verify the member list is visible
      await expect(teamPage.membersList).toBeVisible()

      // Just verify that at least one member exists (the current user)
      const memberCount = await teamPage.membersList.locator('.v-list-item').count()
      expect(memberCount).toBeGreaterThan(0)
    })

    test('current user has owner role', async ({ authenticatedPage }) => {
      const teamPage = new TeamMembersPage(authenticatedPage)

      await teamPage.goto()

      // Look for any member with owner role
      const ownerChip = authenticatedPage.locator('.v-chip').filter({ hasText: 'owner' })
      await expect(ownerChip.first()).toBeVisible()
    })

    test('can go back to settings', async ({ authenticatedPage }) => {
      const settingsPage = new SettingsPage(authenticatedPage)
      const teamPage = new TeamMembersPage(authenticatedPage)

      // Navigate from settings to budget settings, then back
      await settingsPage.goto()
      await settingsPage.goToBudgetSettings()
      await teamPage.goBackToSettings()

      await expect(authenticatedPage).toHaveURL('/settings')
    })
  })

  test.describe('Notification Settings Page', () => {
    test('can navigate to notification settings', async ({ authenticatedPage }) => {
      const notifPage = new NotificationSettingsPage(authenticatedPage)

      await notifPage.goto()

      await notifPage.expectPageTitle()
      await expect(authenticatedPage).toHaveURL('/settings/notifications')
    })

    test('can toggle notification', async ({ authenticatedPage }) => {
      const notifPage = new NotificationSettingsPage(authenticatedPage)

      await notifPage.goto()

      // Toggle Goal Reached notification (simple one without extra settings)
      const initialState = await notifPage.isNotificationEnabled('Goal Reached')
      await notifPage.toggleNotification('Goal Reached')

      // State should have changed
      const newState = await notifPage.isNotificationEnabled('Goal Reached')
      expect(newState).toBe(!initialState)
    })

    test('can go back to settings', async ({ authenticatedPage }) => {
      const settingsPage = new SettingsPage(authenticatedPage)
      const notifPage = new NotificationSettingsPage(authenticatedPage)

      // Navigate from settings to notifications, then back
      await settingsPage.goto()
      await settingsPage.goToNotificationPreferences()
      await notifPage.goBackToSettings()

      await expect(authenticatedPage).toHaveURL('/settings')
    })
  })

  test.describe('Payees Settings Page', () => {
    test('can navigate to payees settings', async ({ authenticatedPage }) => {
      const payeesPage = new PayeesSettingsPage(authenticatedPage)

      await payeesPage.goto()

      await payeesPage.expectPageTitle()
      await expect(authenticatedPage).toHaveURL('/settings/payees')
    })

    test('can create a new payee', async ({ authenticatedPage }) => {
      const payeesPage = new PayeesSettingsPage(authenticatedPage)
      const payeeName = `Test Payee ${Date.now()}`

      await payeesPage.goto()
      await payeesPage.createPayee({ name: payeeName })

      await expect(payeesPage.getPayeeItem(payeeName)).toBeVisible()
    })

    test('can create payee with all fields', async ({ authenticatedPage, testApi, testContext }) => {
      const payeesPage = new PayeesSettingsPage(authenticatedPage)
      const payeeName = `Full Payee ${Date.now()}`

      // Create an envelope for the default envelope selection
      const envelope = await testApi.createEnvelope(testContext.user.budgetId, {
        name: `Test Envelope ${Date.now()}`,
      })

      await payeesPage.goto()
      await payeesPage.createPayee({
        name: payeeName,
        icon: '🏪',
        description: 'Test description',
        defaultEnvelope: envelope.name,
      })

      const payeeItem = payeesPage.getPayeeItem(payeeName)
      await expect(payeeItem).toBeVisible()
      // Check default envelope is shown
      const defaultEnvelope = await payeesPage.getPayeeDefaultEnvelope(payeeName)
      expect(defaultEnvelope).toBe(envelope.name)
    })

    test('can edit existing payee', async ({ authenticatedPage, testApi, testContext }) => {
      const payeesPage = new PayeesSettingsPage(authenticatedPage)

      // Create a payee via API
      const originalName = `Original Payee ${Date.now()}`
      await testApi.createPayee(testContext.user.budgetId, originalName)

      await payeesPage.goto()
      await expect(payeesPage.getPayeeItem(originalName)).toBeVisible()

      // Edit the payee
      const newName = `Updated Payee ${Date.now()}`
      await payeesPage.editPayee(originalName, { name: newName })

      await expect(payeesPage.getPayeeItem(newName)).toBeVisible()
      await expect(payeesPage.getPayeeItem(originalName)).toBeHidden()
    })

    test('can set default envelope on existing payee', async ({
      authenticatedPage,
      testApi,
      testContext,
    }) => {
      const payeesPage = new PayeesSettingsPage(authenticatedPage)

      // Create a payee and envelope via API
      const payeeName = `Payee with Envelope ${Date.now()}`
      await testApi.createPayee(testContext.user.budgetId, payeeName)
      const envelope = await testApi.createEnvelope(testContext.user.budgetId, {
        name: `Groceries Envelope ${Date.now()}`,
      })

      await payeesPage.goto()

      // Edit to set default envelope
      await payeesPage.editPayee(payeeName, { defaultEnvelope: envelope.name })

      const defaultEnvelope = await payeesPage.getPayeeDefaultEnvelope(payeeName)
      expect(defaultEnvelope).toBe(envelope.name)
    })

    test('can open delete confirmation dialog', async ({
      authenticatedPage,
      testApi,
      testContext,
    }) => {
      const payeesPage = new PayeesSettingsPage(authenticatedPage)

      // Create a payee via API
      const payeeName = `Payee to Delete ${Date.now()}`
      await testApi.createPayee(testContext.user.budgetId, payeeName)

      await payeesPage.goto()
      await payeesPage.clickDeleteButton(payeeName)

      await expect(payeesPage.deleteDialog).toBeVisible()
      await expect(payeesPage.deleteDialog).toContainText(payeeName)
    })

    test('can cancel delete confirmation', async ({ authenticatedPage, testApi, testContext }) => {
      const payeesPage = new PayeesSettingsPage(authenticatedPage)

      // Create a payee via API
      const payeeName = `Payee Cancel Delete ${Date.now()}`
      await testApi.createPayee(testContext.user.budgetId, payeeName)

      await payeesPage.goto()
      await payeesPage.clickDeleteButton(payeeName)
      await payeesPage.cancelDelete()

      await expect(payeesPage.deleteDialog).toBeHidden()
      // Payee should still exist
      await expect(payeesPage.getPayeeItem(payeeName)).toBeVisible()
    })

    test('can delete a payee', async ({ authenticatedPage, testApi, testContext }) => {
      const payeesPage = new PayeesSettingsPage(authenticatedPage)

      // Create a payee via API
      const payeeName = `Payee to Remove ${Date.now()}`
      await testApi.createPayee(testContext.user.budgetId, payeeName)

      await payeesPage.goto()
      await expect(payeesPage.getPayeeItem(payeeName)).toBeVisible()

      await payeesPage.deletePayee(payeeName)

      await expect(payeesPage.getPayeeItem(payeeName)).toBeHidden()
    })

    test('can go back to settings', async ({ authenticatedPage }) => {
      const settingsPage = new SettingsPage(authenticatedPage)
      const payeesPage = new PayeesSettingsPage(authenticatedPage)

      // Navigate from settings to payees, then back
      await settingsPage.goto()
      await settingsPage.goToManagePayees()
      await payeesPage.goBackToSettings()

      await expect(authenticatedPage).toHaveURL('/settings')
    })
  })

  test.describe('Locations Settings Page', () => {
    test('can navigate to locations settings', async ({ authenticatedPage }) => {
      const locationsPage = new LocationsSettingsPage(authenticatedPage)

      await locationsPage.goto()

      await locationsPage.expectPageTitle()
      await expect(authenticatedPage).toHaveURL('/settings/locations')
    })

    test('can create a new location', async ({ authenticatedPage }) => {
      const locationsPage = new LocationsSettingsPage(authenticatedPage)
      const locationName = `Test Location ${Date.now()}`

      await locationsPage.goto()
      await locationsPage.createLocation({ name: locationName })

      await expect(locationsPage.getLocationItem(locationName)).toBeVisible()
    })

    test('can create location with all fields', async ({ authenticatedPage }) => {
      const locationsPage = new LocationsSettingsPage(authenticatedPage)
      const locationName = `Full Location ${Date.now()}`

      await locationsPage.goto()
      await locationsPage.createLocation({
        name: locationName,
        icon: '📍',
        description: 'A test location',
      })

      const locationItem = locationsPage.getLocationItem(locationName)
      await expect(locationItem).toBeVisible()
      // Check description is shown
      await expect(locationItem).toContainText('A test location')
    })

    test('can edit existing location', async ({ authenticatedPage, testApi, testContext }) => {
      const locationsPage = new LocationsSettingsPage(authenticatedPage)

      // Create a location via API
      const originalName = `Original Location ${Date.now()}`
      await testApi.createLocation(testContext.user.budgetId, originalName)

      await locationsPage.goto()
      await expect(locationsPage.getLocationItem(originalName)).toBeVisible()

      // Edit the location
      const newName = `Updated Location ${Date.now()}`
      await locationsPage.editLocation(originalName, { name: newName })

      await expect(locationsPage.getLocationItem(newName)).toBeVisible()
      await expect(locationsPage.getLocationItem(originalName)).toBeHidden()
    })

    test('can open delete confirmation dialog', async ({
      authenticatedPage,
      testApi,
      testContext,
    }) => {
      const locationsPage = new LocationsSettingsPage(authenticatedPage)

      // Create a location via API
      const locationName = `Location to Delete ${Date.now()}`
      await testApi.createLocation(testContext.user.budgetId, locationName)

      await locationsPage.goto()
      await locationsPage.clickDeleteButton(locationName)

      await expect(locationsPage.deleteDialog).toBeVisible()
      await expect(locationsPage.deleteDialog).toContainText(locationName)
    })

    test('can cancel delete confirmation', async ({ authenticatedPage, testApi, testContext }) => {
      const locationsPage = new LocationsSettingsPage(authenticatedPage)

      // Create a location via API
      const locationName = `Location Cancel Delete ${Date.now()}`
      await testApi.createLocation(testContext.user.budgetId, locationName)

      await locationsPage.goto()
      await locationsPage.clickDeleteButton(locationName)
      await locationsPage.cancelDelete()

      await expect(locationsPage.deleteDialog).toBeHidden()
      // Location should still exist
      await expect(locationsPage.getLocationItem(locationName)).toBeVisible()
    })

    test('can delete a location', async ({ authenticatedPage, testApi, testContext }) => {
      const locationsPage = new LocationsSettingsPage(authenticatedPage)

      // Create a location via API
      const locationName = `Location to Remove ${Date.now()}`
      await testApi.createLocation(testContext.user.budgetId, locationName)

      await locationsPage.goto()
      await expect(locationsPage.getLocationItem(locationName)).toBeVisible()

      await locationsPage.deleteLocation(locationName)

      await expect(locationsPage.getLocationItem(locationName)).toBeHidden()
    })

    test('can go back to settings', async ({ authenticatedPage }) => {
      const settingsPage = new SettingsPage(authenticatedPage)
      const locationsPage = new LocationsSettingsPage(authenticatedPage)

      // Navigate from settings to locations, then back
      await settingsPage.goto()
      await authenticatedPage.click('text=Manage Locations')
      await locationsPage.goBackToSettings()

      await expect(authenticatedPage).toHaveURL('/settings')
    })
  })

  test.describe('Start Fresh Page', () => {
    test('can navigate to start fresh page', async ({ authenticatedPage }) => {
      const startFreshPage = new StartFreshPage(authenticatedPage)

      await startFreshPage.goto()

      await startFreshPage.expectPageTitle()
      await expect(authenticatedPage).toHaveURL('/settings/start-fresh')
    })

    test('shows preview when delete all is selected', async ({
      authenticatedPage,
      testApi,
      testContext,
    }) => {
      // Create some data first
      await testApi.createAccount(testContext.user.budgetId, { name: `Account Preview ${Date.now()}` })

      const startFreshPage = new StartFreshPage(authenticatedPage)

      await startFreshPage.goto()
      await startFreshPage.selectDeleteAll()

      await startFreshPage.expectPreviewVisible()
    })

    test('can open and cancel confirmation dialog', async ({
      authenticatedPage,
      testApi,
      testContext,
    }) => {
      // Create some data first
      await testApi.createAccount(testContext.user.budgetId, { name: `Account Dialog ${Date.now()}` })

      const startFreshPage = new StartFreshPage(authenticatedPage)

      await startFreshPage.goto()
      await startFreshPage.selectDeleteAll()
      await startFreshPage.openConfirmDialog()

      await expect(startFreshPage.confirmDialog).toBeVisible()
      await expect(startFreshPage.passwordInput).toBeVisible()

      await startFreshPage.cancelDeletion()
      await expect(startFreshPage.confirmDialog).toBeHidden()
    })

    test('shows password error for wrong password', async ({
      authenticatedPage,
      testApi,
      testContext,
    }) => {
      // Create some data first
      await testApi.createAccount(testContext.user.budgetId, { name: `Account Password ${Date.now()}` })

      const startFreshPage = new StartFreshPage(authenticatedPage)

      await startFreshPage.goto()
      await startFreshPage.selectDeleteAll()
      await startFreshPage.openConfirmDialog()
      await startFreshPage.confirmDeletion('wrongpassword')

      // Password error should be visible
      await expect(startFreshPage.confirmDialog.locator('.v-messages')).toContainText('Invalid')
    })

    test('can delete all data with correct password', async ({
      authenticatedPage,
      testApi,
      testContext,
    }) => {
      // Create some data first
      await testApi.createAccount(testContext.user.budgetId, { name: 'Account to Delete' })

      const startFreshPage = new StartFreshPage(authenticatedPage)

      await startFreshPage.goto()
      await startFreshPage.selectDeleteAll()
      await startFreshPage.deleteData(TEST_PASSWORD)

      // Should redirect to settings
      await expect(authenticatedPage).toHaveURL('/settings')
    })

    test('can go back to settings', async ({ authenticatedPage }) => {
      const settingsPage = new SettingsPage(authenticatedPage)
      const startFreshPage = new StartFreshPage(authenticatedPage)

      // Navigate from settings to start fresh, then back
      await settingsPage.goto()
      await settingsPage.goToStartFresh()
      await startFreshPage.goBackToSettings()

      await expect(authenticatedPage).toHaveURL('/settings')
    })

    test('can clear allocations and reset envelope balances', async ({
      authenticatedPage,
      testApi,
      testContext,
    }) => {
      // Create account with starting balance
      const account = await testApi.createAccount(testContext.user.budgetId, {
        name: `Account Allocations ${Date.now()}`,
        startingBalance: 10000, // $100.00
      })

      // Create envelope and allocate money to it
      const envelope = await testApi.createEnvelope(testContext.user.budgetId, {
        name: `Envelope Allocations ${Date.now()}`,
      })

      // Create a transaction allocated to the envelope
      await testApi.createTransaction(testContext.user.budgetId, {
        accountId: account.id,
        amount: -5000, // -$50.00 expense
        envelopeId: envelope.id,
        isCleared: true,
      })

      const startFreshPage = new StartFreshPage(authenticatedPage)

      await startFreshPage.goto()
      await startFreshPage.selectSelective()
      await startFreshPage.toggleCategory('allocations')

      // Should show preview with allocations and envelopes to clear
      await startFreshPage.expectPreviewVisible()

      // Delete with correct password
      await startFreshPage.deleteData(TEST_PASSWORD)

      // Should redirect
      await expect(authenticatedPage).toHaveURL('/settings')
    })

    test('clearing allocations preserves envelopes', async ({
      authenticatedPage,
      testApi,
      testContext,
    }) => {
      // Create account and envelope with allocation
      const account = await testApi.createAccount(testContext.user.budgetId, {
        name: `Account Preserve ${Date.now()}`,
        startingBalance: 10000,
      })

      const envelopeName = `Envelope Preserve ${Date.now()}`
      const envelope = await testApi.createEnvelope(testContext.user.budgetId, {
        name: envelopeName,
      })

      await testApi.createTransaction(testContext.user.budgetId, {
        accountId: account.id,
        amount: -5000,
        envelopeId: envelope.id,
        isCleared: true,
      })

      const startFreshPage = new StartFreshPage(authenticatedPage)

      await startFreshPage.goto()
      await startFreshPage.selectSelective()
      await startFreshPage.toggleCategory('allocations')
      await startFreshPage.deleteData(TEST_PASSWORD)

      // Navigate to envelopes page and verify envelope still exists
      await authenticatedPage.goto('/')
      await expect(authenticatedPage.locator('text=' + envelopeName)).toBeVisible()
    })
  })
})
