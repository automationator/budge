import { test, expect } from '../fixtures/test-setup'
import { NavDrawerPage } from '../pages/nav-drawer.page'

// UI rendering tests (visibility, expand/collapse, dialog open) have been
// moved to frontend/tests/unit/components/layout/NavDrawer.spec.ts.
// Only navigation URL-verification tests remain here.

test.describe('Navigation Drawer', () => {
  test.describe('Main Navigation', () => {
    test('Envelopes link navigates to home', async ({ authenticatedPage }) => {
      const navDrawer = new NavDrawerPage(authenticatedPage)

      await authenticatedPage.goto('/accounts') // Start on different page
      await navDrawer.waitForVisible()

      await navDrawer.goToEnvelopes()

      await expect(authenticatedPage).toHaveURL('/')
    })

    test('Reports link navigates to reports', async ({ authenticatedPage }) => {
      const navDrawer = new NavDrawerPage(authenticatedPage)

      await authenticatedPage.goto('/')
      await navDrawer.waitForVisible()

      await navDrawer.goToReports()

      await expect(authenticatedPage).toHaveURL('/reports')
    })

    test('Transactions link navigates to transactions', async ({ authenticatedPage }) => {
      const navDrawer = new NavDrawerPage(authenticatedPage)

      await authenticatedPage.goto('/')
      await navDrawer.waitForVisible()

      await navDrawer.goToTransactions()

      await expect(authenticatedPage).toHaveURL('/transactions')
    })
  })

  test.describe('More Section', () => {
    test('Allocation Rules link navigates correctly', async ({ authenticatedPage }) => {
      const navDrawer = new NavDrawerPage(authenticatedPage)

      await authenticatedPage.goto('/')
      await navDrawer.waitForVisible()
      await navDrawer.expandMore()

      await navDrawer.allocationRulesLink.click()

      await expect(authenticatedPage).toHaveURL('/allocation-rules')
    })

    test('Recurring Transactions link navigates correctly', async ({ authenticatedPage }) => {
      const navDrawer = new NavDrawerPage(authenticatedPage)

      await authenticatedPage.goto('/')
      await navDrawer.waitForVisible()
      await navDrawer.expandMore()

      await navDrawer.recurringTransactionsLink.click()

      await expect(authenticatedPage).toHaveURL('/recurring')
    })
  })

  test.describe('Accounts Section', () => {
    test('All Accounts link navigates to transactions', async ({ authenticatedPage }) => {
      const navDrawer = new NavDrawerPage(authenticatedPage)

      await authenticatedPage.goto('/')
      await navDrawer.waitForVisible()

      await navDrawer.goToAllAccountsTransactions()

      await expect(authenticatedPage).toHaveURL('/transactions')
    })

    test('clicking individual account navigates to account detail', async ({
      authenticatedPage,
      testApi,
      testContext,
    }) => {
      // Create a budget account
      const accountName = `Nav Account ${Date.now()}`
      const account = await testApi.createAccount(testContext.user.budgetId, {
        name: accountName,
        accountType: 'checking',
        includeInBudget: true,
      })

      const navDrawer = new NavDrawerPage(authenticatedPage)

      await authenticatedPage.goto('/')
      await navDrawer.waitForVisible()

      // Expand Budget section to show accounts
      await navDrawer.expandBudget()

      await navDrawer.clickAccount(accountName)

      await expect(authenticatedPage).toHaveURL(new RegExp(`/accounts/${account.id}`))
    })
  })
})
