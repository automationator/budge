import { test, expect } from '../fixtures/test-setup'
import { BottomNavPage } from '../pages/bottom-nav.page'
import { TransactionFormPage } from '../pages/transaction-form.page'

// This file runs in the mobile project (430x715 viewport)
// UI rendering tests (visibility, active states, dialog open, bottom sheet open/close)
// have been migrated to frontend/tests/unit/components/layout/BottomNav.spec.ts

test.describe('Bottom Navigation', () => {
  test.describe('Tab Navigation', () => {
    test('Envelopes tab navigates to home', async ({ authenticatedPage }) => {
      const bottomNav = new BottomNavPage(authenticatedPage)

      await authenticatedPage.goto('/accounts')
      await bottomNav.waitForVisible()

      await bottomNav.goToEnvelopes()
      await expect(authenticatedPage).toHaveURL('/')
    })

    test('Accounts tab navigates to accounts', async ({ authenticatedPage }) => {
      const bottomNav = new BottomNavPage(authenticatedPage)

      await authenticatedPage.goto('/')
      await bottomNav.waitForVisible()

      await bottomNav.goToAccounts()
      await expect(authenticatedPage).toHaveURL('/accounts')
    })

    test('Reports tab navigates to reports', async ({ authenticatedPage }) => {
      const bottomNav = new BottomNavPage(authenticatedPage)

      await authenticatedPage.goto('/')
      await bottomNav.waitForVisible()

      await bottomNav.goToReports()
      await expect(authenticatedPage).toHaveURL('/reports')
    })
  })

  test.describe('Add Transaction Button', () => {
    test('Add button works from different pages', async ({ authenticatedPage }) => {
      const bottomNav = new BottomNavPage(authenticatedPage)
      const formPage = new TransactionFormPage(authenticatedPage)

      await authenticatedPage.goto('/reports')
      await bottomNav.waitForVisible()

      await bottomNav.openAddTransaction()

      await formPage.waitForDialog()

      // Close dialog
      await formPage.cancelButton.click()
      await formPage.waitForDialogHidden()

      // Should still be on reports page
      await expect(authenticatedPage).toHaveURL(/\/reports/)
    })
  })

  test.describe('More Menu (Bottom Sheet)', () => {
    test('Transactions link navigates and closes sheet', async ({ authenticatedPage }) => {
      const bottomNav = new BottomNavPage(authenticatedPage)

      await authenticatedPage.goto('/')
      await bottomNav.waitForVisible()

      await bottomNav.openMoreMenu()
      await bottomNav.clickMoreMenuItem('Transactions')

      await expect(authenticatedPage).toHaveURL('/transactions')
      await bottomNav.expectMoreMenuHidden()
    })

    test('Recurring link navigates correctly', async ({ authenticatedPage }) => {
      const bottomNav = new BottomNavPage(authenticatedPage)

      await authenticatedPage.goto('/')
      await bottomNav.waitForVisible()

      await bottomNav.openMoreMenu()
      await bottomNav.clickMoreMenuItem('Recurring')

      await expect(authenticatedPage).toHaveURL('/recurring')
    })

    test('Allocation Rules link navigates correctly', async ({ authenticatedPage }) => {
      const bottomNav = new BottomNavPage(authenticatedPage)

      await authenticatedPage.goto('/')
      await bottomNav.waitForVisible()

      await bottomNav.openMoreMenu()
      await bottomNav.clickMoreMenuItem('Allocation Rules')

      await expect(authenticatedPage).toHaveURL('/allocation-rules')
    })

    test('Notifications link navigates to settings', async ({ authenticatedPage }) => {
      const bottomNav = new BottomNavPage(authenticatedPage)

      await authenticatedPage.goto('/')
      await bottomNav.waitForVisible()

      await bottomNav.openMoreMenu()
      await bottomNav.clickMoreMenuItem('Notifications')

      await expect(authenticatedPage).toHaveURL('/settings/notifications')
    })
  })
})
