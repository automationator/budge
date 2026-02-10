// UI rendering tests migrated to component tests:
// frontend/tests/unit/components/layout/BudgetMenu.spec.ts

import { test, expect } from '../fixtures/test-setup'
import { BudgetMenuPage } from '../pages/budget-menu.page'

test.describe('BudgetMenu', () => {
  test.describe('Desktop (NavDrawer)', () => {
    test('switches to a different budget', async ({ authenticatedPage, testApi, testContext }) => {
      // Create a second budget
      const newBudget = await testApi.createBudget(testContext.user.userId, 'Test Second Budget')

      await authenticatedPage.goto('/')
      const budgetMenu = new BudgetMenuPage(authenticatedPage)
      await budgetMenu.waitForVisible()

      // Switch to the new budget
      await budgetMenu.selectBudget(newBudget.name)

      // Verify budget name changed
      await expect(budgetMenu.budgetNameDisplay).toHaveText(newBudget.name)
    })

    test('creates a new budget via dialog', async ({ authenticatedPage }) => {
      await authenticatedPage.goto('/')
      const budgetMenu = new BudgetMenuPage(authenticatedPage)
      await budgetMenu.waitForVisible()

      const newBudgetName = `New Budget ${Date.now()}`
      await budgetMenu.createBudget(newBudgetName)

      // Verify budget is now selected
      await expect(budgetMenu.budgetNameDisplay).toHaveText(newBudgetName)
    })

    test('navigates to Settings from menu', async ({ authenticatedPage }) => {
      await authenticatedPage.goto('/')
      const budgetMenu = new BudgetMenuPage(authenticatedPage)
      await budgetMenu.waitForVisible()

      await budgetMenu.goToSettings()
      // URL check is done inside goToSettings
    })

    test('navigates to Budget Settings from menu', async ({ authenticatedPage }) => {
      await authenticatedPage.goto('/')
      const budgetMenu = new BudgetMenuPage(authenticatedPage)
      await budgetMenu.waitForVisible()

      await budgetMenu.goToBudgetSettings()
      // URL check is done inside goToBudgetSettings
    })

    test('logs out user', async ({ authenticatedPage }) => {
      await authenticatedPage.goto('/')
      const budgetMenu = new BudgetMenuPage(authenticatedPage)
      await budgetMenu.waitForVisible()

      await budgetMenu.logout()
      // URL check is done inside logout - should redirect to /login
    })
  })
})
