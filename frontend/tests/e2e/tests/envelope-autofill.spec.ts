import { test, expect } from '../fixtures/test-setup'
import { TransactionsPage } from '../pages/transactions.page'
import { TransactionFormPage } from '../pages/transaction-form.page'

// Test context is set up automatically via fixtures
// - Database is reset per worker
// - User is created once per file

// Auto-fill rendering tests (payee default envelope, no-default, no-override)
// are in frontend/tests/unit/components/transactions/TransactionFormDialog.spec.ts

test.describe('Envelope Auto-fill', () => {
  test.describe('Default Envelope Behavior', () => {
    test('first transaction sets the default envelope for a payee', async ({
      authenticatedPage,
      testApi,
      testContext,
    }) => {
      const transactionsPage = new TransactionsPage(authenticatedPage)
      const formPage = new TransactionFormPage(authenticatedPage)

      const teamId = testContext.user.budgetId

      // Create test data
      const account = await testApi.createAccount(teamId, {
        name: 'First Transaction Checking',
        accountType: 'checking',
        includeInBudget: true,
        startingBalance: 100000,
      })

      const groceriesEnvelope = await testApi.createEnvelope(teamId, {
        name: 'First Transaction Groceries',
      })

      const payee = await testApi.createPayee(teamId, 'First Transaction Store')

      // Go to transactions page
      await transactionsPage.goto()
      await transactionsPage.clickAddTransaction()

      // Create the first transaction with this payee and groceries envelope
      await formPage.selectAccount(account.name)
      await formPage.selectPayee(payee.name)
      await formPage.selectEnvelope(groceriesEnvelope.name)
      await formPage.fillAmount('50.00')
      await formPage.setAsExpense()
      await formPage.submit()

      // Now create another transaction with the same payee
      await transactionsPage.clickAddTransaction()
      await formPage.selectAccount(account.name)
      await formPage.selectPayee(payee.name)

      // Verify groceries envelope is auto-filled (it was set as default from first transaction)
      await formPage.waitForEnvelopeAutoFill(groceriesEnvelope.name)
      const selectedEnvelope = await formPage.getSelectedEnvelope()
      expect(selectedEnvelope).toBe(groceriesEnvelope.name)
    })
  })
})
