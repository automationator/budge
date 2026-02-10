import { test, expect } from '../fixtures/test-setup'
import { RecurringPage } from '../pages/recurring.page'
import { AccountsPage } from '../pages/accounts.page'

// Test context is set up automatically via fixtures
// - Database is reset per worker
// - User is created once per file

// Generate unique ID for test-created data
const testId = Date.now()

test.describe('Recurring Transactions', () => {
  test.describe('Create Recurring', () => {
    test('creates a recurring expense', async ({ authenticatedPage, testApi, testContext }) => {
      const recurringPage = new RecurringPage(authenticatedPage)
      const accountsPage = new AccountsPage(authenticatedPage)

      // Create an account first
      const accountName = `Recurring Checking ${testId}`
      await accountsPage.goto()
      await accountsPage.createAccount({
        name: accountName,
        accountType: 'checking',
        includeInBudget: false,
      })

      // Create a payee via API (recurring form uses v-select, not autocomplete)
      const payeeName = `Expense Payee ${testId}`
      await testApi.createPayee(testContext.user.budgetId, payeeName)

      await recurringPage.goto()
      await recurringPage.createRecurringExpense({
        account: accountName,
        payee: payeeName,
        amount: '50.00',
      })

      await recurringPage.expectRecurringExists(payeeName)
    })

    test('creates a recurring income', async ({ authenticatedPage, testApi, testContext }) => {
      const recurringPage = new RecurringPage(authenticatedPage)
      const accountsPage = new AccountsPage(authenticatedPage)

      // Create an account first
      const accountName = `Income Checking ${testId}`
      await accountsPage.goto()
      await accountsPage.createAccount({
        name: accountName,
        accountType: 'checking',
        includeInBudget: false,
      })

      // Create a payee via API (recurring form uses v-select, not autocomplete)
      const payeeName = `Income Payee ${testId}`
      await testApi.createPayee(testContext.user.budgetId, payeeName)

      await recurringPage.goto()
      await recurringPage.createRecurringIncome({
        account: accountName,
        payee: payeeName,
        amount: '2000.00',
      })

      await recurringPage.expectRecurringExists(payeeName)
    })

    test('creates a recurring transfer', async ({ authenticatedPage }) => {
      const recurringPage = new RecurringPage(authenticatedPage)
      const accountsPage = new AccountsPage(authenticatedPage)

      // Create two accounts
      const fromAccount = `Transfer From ${testId}`
      const toAccount = `Transfer To ${testId}`

      await accountsPage.goto()
      await accountsPage.createAccount({
        name: fromAccount,
        accountType: 'checking',
        includeInBudget: false,
      })

      await accountsPage.createAccount({
        name: toAccount,
        accountType: 'savings',
        includeInBudget: false,
      })

      await recurringPage.goto()
      await recurringPage.createRecurringTransfer({
        fromAccount: fromAccount,
        toAccount: toAccount,
        amount: '100.00',
      })

      // Transfer shows as "Transfer to [account]"
      await recurringPage.expectRecurringExists(`Transfer to ${toAccount}`)
    })

    test('creates recurring with custom frequency', async ({ authenticatedPage, testApi, testContext }) => {
      const recurringPage = new RecurringPage(authenticatedPage)
      const accountsPage = new AccountsPage(authenticatedPage)

      // Create an account first
      const accountName = `Weekly Account ${testId}`
      await accountsPage.goto()
      await accountsPage.createAccount({
        name: accountName,
        accountType: 'checking',
        includeInBudget: false,
      })

      // Create a payee via API (recurring form uses v-select, not autocomplete)
      const payeeName = `Weekly Bill ${testId}`
      await testApi.createPayee(testContext.user.budgetId, payeeName)

      await recurringPage.goto()

      // Create recurring with custom frequency
      await recurringPage.openCreateDialog()
      await recurringPage.transactionButton.click()
      await expect(recurringPage.accountSelect).toBeVisible()
      await recurringPage.selectAccount(accountName)

      // Select the payee
      await recurringPage.selectPayee(payeeName)
      await recurringPage.expenseButton.click()
      await recurringPage.amountInput.fill('25.00')
      await recurringPage.frequencyValueInput.fill('2')
      await recurringPage.selectFrequencyUnit('weeks')
      await recurringPage.createButton.click()

      await expect(recurringPage.formDialog).toBeHidden({ timeout: 10000 })
    })

    test('creates recurring expense on budget account with envelope', async ({
      authenticatedPage,
      testApi,
      testContext,
    }) => {
      const recurringPage = new RecurringPage(authenticatedPage)

      // Create a budget account via API
      const accountName = `Budget Account ${testId}`
      await testApi.createAccount(testContext.user.budgetId, {
        name: accountName,
        accountType: 'checking',
        includeInBudget: true,
      })

      // Create an envelope via API
      const envelope = await testApi.createEnvelope(testContext.user.budgetId, {
        name: `Test Envelope ${testId}`,
      })

      // Create a payee via API
      const payeeName = `Budget Expense Payee ${testId}`
      await testApi.createPayee(testContext.user.budgetId, payeeName)

      await recurringPage.goto()
      await recurringPage.createRecurringExpense({
        account: accountName,
        payee: payeeName,
        amount: '75.00',
        envelope: envelope.name,
      })

      await recurringPage.expectRecurringExists(payeeName)
    })

    test('creates recurring transfer from budget to tracking with envelope', async ({
      authenticatedPage,
      testApi,
      testContext,
    }) => {
      const recurringPage = new RecurringPage(authenticatedPage)

      // Create a budget account via API
      const budgetAccountName = `Budget Transfer From ${testId}`
      await testApi.createAccount(testContext.user.budgetId, {
        name: budgetAccountName,
        accountType: 'checking',
        includeInBudget: true,
      })

      // Create a tracking account via API
      const trackingAccountName = `Tracking Transfer To ${testId}`
      await testApi.createAccount(testContext.user.budgetId, {
        name: trackingAccountName,
        accountType: 'savings',
        includeInBudget: false,
      })

      // Create an envelope via API
      const envelope = await testApi.createEnvelope(testContext.user.budgetId, {
        name: `Transfer Envelope ${testId}`,
      })

      await recurringPage.goto()
      await recurringPage.createRecurringTransfer({
        fromAccount: budgetAccountName,
        toAccount: trackingAccountName,
        amount: '200.00',
        envelope: envelope.name,
      })

      await recurringPage.expectRecurringExists(`Transfer to ${trackingAccountName}`)
    })
  })

  test.describe('Edit Recurring', () => {
    test('edits recurring transaction amount', async ({ authenticatedPage, testApi, testContext }) => {
      const recurringPage = new RecurringPage(authenticatedPage)
      const accountsPage = new AccountsPage(authenticatedPage)

      // Create an account first
      const accountName = `Edit Account ${testId}`
      await accountsPage.goto()
      await accountsPage.createAccount({
        name: accountName,
        accountType: 'checking',
        includeInBudget: false,
      })

      // Create a payee via API (recurring form uses v-select, not autocomplete)
      const payeeName = `Edit Payee ${testId}`
      await testApi.createPayee(testContext.user.budgetId, payeeName)

      await recurringPage.goto()

      // Create a recurring to edit
      await recurringPage.createRecurringExpense({
        account: accountName,
        payee: payeeName,
        amount: '30.00',
      })

      // Edit it
      await recurringPage.openEditDialog(payeeName)

      // Change the amount
      await recurringPage.amountInput.clear()
      await recurringPage.amountInput.fill('45.00')
      await recurringPage.saveButton.click()

      await expect(recurringPage.formDialog).toBeHidden({ timeout: 10000 })
    })
  })

  test.describe('Pause/Resume', () => {
    test('pauses and resumes recurring transaction', async ({ authenticatedPage, testApi, testContext }) => {
      const recurringPage = new RecurringPage(authenticatedPage)
      const accountsPage = new AccountsPage(authenticatedPage)

      // Create an account first
      const accountName = `Pause Account ${testId}`
      await accountsPage.goto()
      await accountsPage.createAccount({
        name: accountName,
        accountType: 'checking',
        includeInBudget: false,
      })

      // Create a payee via API (recurring form uses v-select, not autocomplete)
      const payeeName = `Pause Payee ${testId}`
      await testApi.createPayee(testContext.user.budgetId, payeeName)

      await recurringPage.goto()

      // Create a recurring to pause
      await recurringPage.createRecurringExpense({
        account: accountName,
        payee: payeeName,
        amount: '20.00',
      })

      // Pause it
      await recurringPage.pauseRecurring(payeeName)

      // Enable "Show inactive" to see the paused item
      await recurringPage.toggleShowInactive()

      // Check it shows as paused
      const isPaused = await recurringPage.isRecurringPaused(payeeName)
      expect(isPaused).toBe(true)

      // Resume it
      await recurringPage.resumeRecurring(payeeName)
    })
  })

  test.describe('Delete Recurring', () => {
    test('deletes recurring transaction', async ({ authenticatedPage, testApi, testContext }) => {
      const recurringPage = new RecurringPage(authenticatedPage)
      const accountsPage = new AccountsPage(authenticatedPage)

      // Create an account first
      const accountName = `Delete Account ${testId}`
      await accountsPage.goto()
      await accountsPage.createAccount({
        name: accountName,
        accountType: 'checking',
        includeInBudget: false,
      })

      // Create a payee via API (recurring form uses v-select, not autocomplete)
      const payeeName = `Delete Payee ${testId}`
      await testApi.createPayee(testContext.user.budgetId, payeeName)

      await recurringPage.goto()

      // Create a recurring to delete
      await recurringPage.createRecurringExpense({
        account: accountName,
        payee: payeeName,
        amount: '15.00',
      })

      // Delete it
      await recurringPage.deleteRecurring(payeeName, true)
    })

    test('cancel delete does not delete', async ({ authenticatedPage, testApi, testContext }) => {
      const recurringPage = new RecurringPage(authenticatedPage)
      const accountsPage = new AccountsPage(authenticatedPage)

      // Create an account first
      const accountName = `Cancel Del Account ${testId}`
      await accountsPage.goto()
      await accountsPage.createAccount({
        name: accountName,
        accountType: 'checking',
        includeInBudget: false,
      })

      // Create a payee via API (recurring form uses v-select, not autocomplete)
      const payeeName = `Cancel Del Payee ${testId}`
      await testApi.createPayee(testContext.user.budgetId, payeeName)

      await recurringPage.goto()

      // Create a recurring
      await recurringPage.createRecurringExpense({
        account: accountName,
        payee: payeeName,
        amount: '10.00',
      })

      // Open delete dialog then cancel
      await recurringPage.openDeleteDialog(payeeName)
      await recurringPage.cancelDeleteButton.click()

      await expect(recurringPage.deleteDialog).toBeHidden()
      // Item should still exist
      await recurringPage.expectRecurringExists(payeeName)
    })
  })

  test.describe('Summary Cards', () => {
    test('active rules count updates', async ({ authenticatedPage, testApi, testContext }) => {
      const recurringPage = new RecurringPage(authenticatedPage)
      const accountsPage = new AccountsPage(authenticatedPage)

      // Create an account first
      const accountName = `Count Account ${testId}`
      await accountsPage.goto()
      await accountsPage.createAccount({
        name: accountName,
        accountType: 'checking',
        includeInBudget: false,
      })

      // Create a payee via API (recurring form uses v-select, not autocomplete)
      const payeeName = `Count Payee ${testId}`
      await testApi.createPayee(testContext.user.budgetId, payeeName)

      await recurringPage.goto()

      const initialCount = await recurringPage.getActiveRulesCount()

      // Create a recurring
      await recurringPage.createRecurringExpense({
        account: accountName,
        payee: payeeName,
        amount: '5.00',
      })

      // Count should increase
      const newCount = await recurringPage.getActiveRulesCount()
      expect(parseInt(newCount)).toBeGreaterThan(parseInt(initialCount))
    })
  })

  test.describe('Filtering', () => {
    test('toggle show inactive shows paused items', async ({ authenticatedPage, testApi, testContext }) => {
      const recurringPage = new RecurringPage(authenticatedPage)
      const accountsPage = new AccountsPage(authenticatedPage)

      // Create an account first
      const accountName = `Inactive Account ${testId}`
      await accountsPage.goto()
      await accountsPage.createAccount({
        name: accountName,
        accountType: 'checking',
        includeInBudget: false,
      })

      // Create a payee via API (recurring form uses v-select, not autocomplete)
      const payeeName = `Inactive Payee ${testId}`
      await testApi.createPayee(testContext.user.budgetId, payeeName)

      // Use a unique amount to identify this specific recurring item
      const uniqueAmount = '8.88'

      await recurringPage.goto()

      // Create and pause a recurring with unique amount
      await recurringPage.createRecurringExpense({
        account: accountName,
        payee: payeeName,
        amount: uniqueAmount,
      })

      // Find by payee name to ensure we get the right item
      await recurringPage.pauseRecurring(payeeName)

      // By default, paused items may be hidden if there are active items too
      // Toggle show inactive
      await recurringPage.toggleShowInactive()

      // Paused item should now be visible with "Paused" chip
      const isPaused = await recurringPage.isRecurringPaused(payeeName)
      expect(isPaused).toBe(true)
    })
  })

})
