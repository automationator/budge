import { test, expect } from '../fixtures/test-setup'
import { TransactionsPage } from '../pages/transactions.page'
import { TransactionFormPage } from '../pages/transaction-form.page'
import { AccountsPage } from '../pages/accounts.page'

// Test context is set up automatically via fixtures
// - Database is reset per worker
// - User is created once per file

// Generate unique ID for test-created data
const testId = Date.now()

test.describe('Transactions', () => {
  test.describe('Create Transactions', () => {
    test('creates an expense transaction', async ({ authenticatedPage }) => {
      const transactionsPage = new TransactionsPage(authenticatedPage)
      const formPage = new TransactionFormPage(authenticatedPage)
      const accountsPage = new AccountsPage(authenticatedPage)

      // Create an account first (off-budget for simplicity)
      const accountName = `Checking ${testId}`
      await accountsPage.goto()
      await accountsPage.createAccount({
        name: accountName,
        accountType: 'checking',
        startingBalance: '1000.00',
        includeInBudget: false,
      })

      await transactionsPage.goto()
      await transactionsPage.clickAddTransaction()

      const payeeName = `Grocery Store ${testId}`
      await formPage.createTransaction({
        account: accountName,
        payee: payeeName,
        amount: '50.00',
        isExpense: true,
      })

      // Verify the dialog closed and the transaction appears
      await formPage.waitForDialogHidden()
      await transactionsPage.expectTransactionExists(payeeName)
    })

    test('creates an income transaction', async ({ authenticatedPage }) => {
      const transactionsPage = new TransactionsPage(authenticatedPage)
      const formPage = new TransactionFormPage(authenticatedPage)
      const accountsPage = new AccountsPage(authenticatedPage)

      // Create an account first
      const accountName = `Income Account ${testId}`
      await accountsPage.goto()
      await accountsPage.createAccount({
        name: accountName,
        accountType: 'checking',
        includeInBudget: false,
      })

      await transactionsPage.goto()
      await transactionsPage.clickAddTransaction()

      const payeeName = `Employer ${Date.now()}`
      await formPage.createTransaction({
        account: accountName,
        payee: payeeName,
        amount: '1000.00',
        isExpense: false,
      })

      await formPage.waitForDialogHidden()
      await transactionsPage.expectTransactionExists(payeeName)
    })

    test('creates a transfer between accounts', async ({ authenticatedPage }) => {
      const transactionsPage = new TransactionsPage(authenticatedPage)
      const formPage = new TransactionFormPage(authenticatedPage)
      const accountsPage = new AccountsPage(authenticatedPage)

      // Create two accounts
      const fromAccountName = `Transfer From ${testId}`
      const toAccountName = `Transfer To ${testId}`

      await accountsPage.goto()
      await accountsPage.createAccount({
        name: fromAccountName,
        accountType: 'checking',
        startingBalance: '500.00',
        includeInBudget: false,
      })

      await accountsPage.createAccount({
        name: toAccountName,
        accountType: 'savings',
        includeInBudget: false,
      })

      await transactionsPage.goto()
      await transactionsPage.clickAddTransaction()

      await formPage.createTransfer({
        fromAccount: fromAccountName,
        toAccount: toAccountName,
        amount: '100.00',
      })

      await formPage.waitForDialogHidden()
    })

    test('creates transaction with memo', async ({ authenticatedPage }) => {
      const transactionsPage = new TransactionsPage(authenticatedPage)
      const formPage = new TransactionFormPage(authenticatedPage)
      const accountsPage = new AccountsPage(authenticatedPage)

      // Create an account first
      const accountName = `Memo Account ${testId}`
      await accountsPage.goto()
      await accountsPage.createAccount({
        name: accountName,
        accountType: 'checking',
        includeInBudget: false,
      })

      await transactionsPage.goto()
      await transactionsPage.clickAddTransaction()

      const payeeName = `Coffee Shop ${Date.now()}`
      await formPage.createTransaction({
        account: accountName,
        payee: payeeName,
        amount: '5.50',
        memo: 'Morning coffee',
      })

      await formPage.waitForDialogHidden()
      await transactionsPage.expectTransactionExists(payeeName)
    })

    test('creates cleared transaction', async ({ authenticatedPage }) => {
      const transactionsPage = new TransactionsPage(authenticatedPage)
      const formPage = new TransactionFormPage(authenticatedPage)
      const accountsPage = new AccountsPage(authenticatedPage)

      // Create an account first
      const accountName = `Cleared Account ${testId}`
      await accountsPage.goto()
      await accountsPage.createAccount({
        name: accountName,
        accountType: 'checking',
        includeInBudget: false,
      })

      await transactionsPage.goto()
      await transactionsPage.clickAddTransaction()

      const payeeName = `Gas Station ${Date.now()}`
      await formPage.createTransaction({
        account: accountName,
        payee: payeeName,
        amount: '45.00',
        cleared: true,
      })

      await formPage.waitForDialogHidden()
      await transactionsPage.expectTransactionExists(payeeName)
    })

    test('save and add another keeps dialog open', async ({ authenticatedPage, testApi, testContext }) => {
      const transactionsPage = new TransactionsPage(authenticatedPage)
      const formPage = new TransactionFormPage(authenticatedPage)

      // Create test data via API
      const accountName = `Add Another Account ${testId}`
      const payeeName = `Add Another Payee ${testId}`
      await testApi.createAccount(testContext.user.budgetId, {
        name: accountName,
        accountType: 'checking',
        startingBalance: 100000, // $1000.00 in cents
        includeInBudget: false,
      })
      await testApi.createPayee(testContext.user.budgetId, payeeName)

      await transactionsPage.goto()
      await transactionsPage.clickAddTransaction()

      // Fill form
      await formPage.selectAccount(accountName)
      await formPage.selectPayee(payeeName)
      await formPage.fillAmount('30.00')

      // Click Save & Add Another
      await formPage.saveAndAddAnother()

      // Dialog should still be visible
      await expect(formPage.dialog).toBeVisible()

      // Amount field should be cleared
      const amountValue = await formPage.amountInput.inputValue()
      expect(amountValue).toBe('')
    })
  })

  test.describe('Edit Transaction', () => {
    test('opens edit dialog when clicking transaction', async ({ authenticatedPage }) => {
      const transactionsPage = new TransactionsPage(authenticatedPage)
      const formPage = new TransactionFormPage(authenticatedPage)
      const accountsPage = new AccountsPage(authenticatedPage)

      // Create an account first
      const accountName = `Edit Nav Account ${testId}`
      await accountsPage.goto()
      await accountsPage.createAccount({
        name: accountName,
        accountType: 'checking',
        includeInBudget: false,
      })

      // Create a transaction
      await transactionsPage.goto()
      await transactionsPage.clickAddTransaction()

      const payeeName = `Edit Test ${Date.now()}`
      await formPage.createTransaction({
        account: accountName,
        payee: payeeName,
        amount: '30.00',
      })

      await formPage.waitForDialogHidden()

      // Now click on it to edit
      await transactionsPage.clickTransaction(payeeName)

      // Should be in edit mode (dialog with Delete button visible)
      const title = await formPage.getDialogTitle()
      expect(title).toContain('Edit')
      await expect(formPage.deleteButton).toBeVisible()
    })

    test('updates transaction and shows success', async ({ authenticatedPage }) => {
      const transactionsPage = new TransactionsPage(authenticatedPage)
      const formPage = new TransactionFormPage(authenticatedPage)
      const accountsPage = new AccountsPage(authenticatedPage)

      // Create an account first
      const accountName = `Update Account ${testId}`
      await accountsPage.goto()
      await accountsPage.createAccount({
        name: accountName,
        accountType: 'checking',
        includeInBudget: false,
      })

      // Create a transaction
      await transactionsPage.goto()
      await transactionsPage.clickAddTransaction()

      const payeeName = `Update Test ${Date.now()}`
      await formPage.createTransaction({
        account: accountName,
        payee: payeeName,
        amount: '20.00',
      })

      await formPage.waitForDialogHidden()

      // Edit it
      await transactionsPage.clickTransaction(payeeName)
      await formPage.fillAmount('25.00')
      await formPage.saveButton.click()

      await formPage.waitForDialogHidden()
    })
  })

  test.describe('Delete Transaction', () => {
    test('deletes transaction with confirmation', async ({ authenticatedPage }) => {
      const transactionsPage = new TransactionsPage(authenticatedPage)
      const formPage = new TransactionFormPage(authenticatedPage)
      const accountsPage = new AccountsPage(authenticatedPage)

      // Create an account first
      const accountName = `Delete Account ${testId}`
      await accountsPage.goto()
      await accountsPage.createAccount({
        name: accountName,
        accountType: 'checking',
        includeInBudget: false,
      })

      // Create a transaction
      await transactionsPage.goto()
      await transactionsPage.clickAddTransaction()

      const payeeName = `Delete Test ${Date.now()}`
      await formPage.createTransaction({
        account: accountName,
        payee: payeeName,
        amount: '15.00',
      })

      await formPage.waitForDialogHidden()

      // Navigate to edit and delete
      await transactionsPage.clickTransaction(payeeName)
      await formPage.deleteTransaction()

      // Transaction should not exist anymore
      await transactionsPage.expectTransactionNotExists(payeeName)
    })

    test('cancel delete does not delete transaction', async ({ authenticatedPage }) => {
      const transactionsPage = new TransactionsPage(authenticatedPage)
      const formPage = new TransactionFormPage(authenticatedPage)
      const accountsPage = new AccountsPage(authenticatedPage)

      // Create an account first
      const accountName = `Cancel Del Account ${testId}`
      await accountsPage.goto()
      await accountsPage.createAccount({
        name: accountName,
        accountType: 'checking',
        includeInBudget: false,
      })

      // Create a transaction
      await transactionsPage.goto()
      await transactionsPage.clickAddTransaction()

      const payeeName = `Cancel Delete ${Date.now()}`
      await formPage.createTransaction({
        account: accountName,
        payee: payeeName,
        amount: '10.00',
      })

      await formPage.waitForDialogHidden()

      // Navigate to edit
      await transactionsPage.clickTransaction(payeeName)

      // Open delete dialog and cancel
      await formPage.openDeleteDialog()
      await formPage.cancelDelete()

      // Dialog should still be visible (edit mode)
      await expect(formPage.dialog).toBeVisible()
    })
  })

  test.describe('Budget to Tracking Transfers', () => {
    test('creates budget to tracking transfer with envelope', async ({
      authenticatedPage,
      testApi,
      testContext,
    }) => {
      const transactionsPage = new TransactionsPage(authenticatedPage)
      const formPage = new TransactionFormPage(authenticatedPage)

      // Create budget account, tracking account, and envelope via API
      const budgetAccount = await testApi.createAccount(testContext.user.budgetId, {
        name: `Budget Acct ${testId}`,
        accountType: 'checking',
        includeInBudget: true,
        startingBalance: 100000, // $1000
      })
      const trackingAccount = await testApi.createAccount(testContext.user.budgetId, {
        name: `Tracking Acct ${testId}`,
        accountType: 'investment',
        includeInBudget: false,
      })
      const envelope = await testApi.createEnvelope(testContext.user.budgetId, {
        name: `Investment ${testId}`,
      })

      await transactionsPage.goto()
      await transactionsPage.clickAddTransaction()

      // Create transfer with envelope
      await formPage.createTransfer({
        fromAccount: budgetAccount.name,
        toAccount: trackingAccount.name,
        amount: '500.00',
        envelope: envelope.name,
      })

      await formPage.waitForDialogHidden()
    })
  })

  test.describe('Filtering', () => {
    test('filter by account shows only that account transactions', async ({ authenticatedPage }) => {
      const transactionsPage = new TransactionsPage(authenticatedPage)
      const formPage = new TransactionFormPage(authenticatedPage)
      const accountsPage = new AccountsPage(authenticatedPage)

      // Create two accounts
      const checkingAccount = `Filter Checking ${testId}`
      const savingsAccount = `Filter Savings ${testId}`

      await accountsPage.goto()
      await accountsPage.createAccount({
        name: checkingAccount,
        accountType: 'checking',
        includeInBudget: false,
      })

      await accountsPage.createAccount({
        name: savingsAccount,
        accountType: 'savings',
        includeInBudget: false,
      })

      // Create transaction in checking account
      await transactionsPage.goto()
      await transactionsPage.clickAddTransaction()

      const checkingPayee = `Checking Payee ${Date.now()}`
      await formPage.createTransaction({
        account: checkingAccount,
        payee: checkingPayee,
        amount: '35.00',
      })
      await formPage.waitForDialogHidden()

      // Create transaction in savings account
      await transactionsPage.clickAddTransaction()
      const savingsPayee = `Savings Payee ${Date.now()}`
      await formPage.createTransaction({
        account: savingsAccount,
        payee: savingsPayee,
        amount: '40.00',
      })
      await formPage.waitForDialogHidden()

      // Filter by checking account
      await transactionsPage.filterByAccount(checkingAccount)

      // Should see checking transaction but not savings
      await transactionsPage.expectTransactionExists(checkingPayee)
      await transactionsPage.expectTransactionNotExists(savingsPayee)

      // Clear filter
      await transactionsPage.clearAccountFilter()

      // Should see both
      await transactionsPage.expectTransactionExists(checkingPayee)
      await transactionsPage.expectTransactionExists(savingsPayee)
    })

    test('dialog pre-populates account when filtered by account', async ({
      authenticatedPage,
      testApi,
      testContext,
    }) => {
      const transactionsPage = new TransactionsPage(authenticatedPage)
      const formPage = new TransactionFormPage(authenticatedPage)

      // Create an account
      const accountName = `Pre-populate Test ${testId}`
      const account = await testApi.createAccount(testContext.user.budgetId, {
        name: accountName,
        accountType: 'checking',
      })

      // Navigate to transactions filtered by this account
      await authenticatedPage.goto(`/transactions?account_id=${account.id}`)
      await transactionsPage.waitForPageLoad()

      // Open add transaction dialog
      await transactionsPage.clickAddTransaction()

      // Verify account is pre-populated
      const selectedAccount = await formPage.getSelectedAccount()
      expect(selectedAccount).toBe(accountName)
    })

    test('budget filter shows only budget account transactions', async ({
      authenticatedPage,
      testApi,
      testContext,
    }) => {
      const transactionsPage = new TransactionsPage(authenticatedPage)

      // Create a budget account and a tracking account with transactions
      const budgetAccount = await testApi.createAccount(testContext.user.budgetId, {
        name: `Budget Filter Account ${Date.now()}`,
        accountType: 'checking',
        includeInBudget: true,
      })

      const trackingAccount = await testApi.createAccount(testContext.user.budgetId, {
        name: `Tracking Filter Account ${Date.now()}`,
        accountType: 'investment',
        includeInBudget: false,
      })

      // Create transactions in each account
      const budgetPayee = `Budget Payee ${Date.now()}`
      const trackingPayee = `Tracking Payee ${Date.now()}`

      await testApi.createTransaction(testContext.user.budgetId, {
        accountId: budgetAccount.id,
        payeeName: budgetPayee,
        amount: -5000,
      })

      await testApi.createTransaction(testContext.user.budgetId, {
        accountId: trackingAccount.id,
        payeeName: trackingPayee,
        amount: -3000,
      })

      await transactionsPage.goto()

      // Initially both transactions should be visible
      await transactionsPage.expectTransactionExists(budgetPayee)
      await transactionsPage.expectTransactionExists(trackingPayee)

      // Apply budget filter via drawer
      await transactionsPage.filterByBudgetAccounts()

      // Should only see budget transaction
      await transactionsPage.expectTransactionExists(budgetPayee)
      await transactionsPage.expectTransactionNotExists(trackingPayee)

      // Filter count badge should show 1
      expect(await transactionsPage.getActiveFilterCount()).toBe(1)

      // Clear filters
      await transactionsPage.openFiltersDrawer()
      await transactionsPage.clearAllFilters()

      // Should see both again
      await transactionsPage.expectTransactionExists(budgetPayee)
      await transactionsPage.expectTransactionExists(trackingPayee)
    })

    test('tracking filter shows only tracking account transactions', async ({
      authenticatedPage,
      testApi,
      testContext,
    }) => {
      const transactionsPage = new TransactionsPage(authenticatedPage)

      // Create a budget account and a tracking account with transactions
      const budgetAccount = await testApi.createAccount(testContext.user.budgetId, {
        name: `Budget For Track ${Date.now()}`,
        accountType: 'checking',
        includeInBudget: true,
      })

      const trackingAccount = await testApi.createAccount(testContext.user.budgetId, {
        name: `Tracking For Track ${Date.now()}`,
        accountType: 'investment',
        includeInBudget: false,
      })

      // Create transactions in each account
      const budgetPayee = `Budget Track Payee ${Date.now()}`
      const trackingPayee = `Tracking Track Payee ${Date.now()}`

      await testApi.createTransaction(testContext.user.budgetId, {
        accountId: budgetAccount.id,
        payeeName: budgetPayee,
        amount: -5000,
      })

      await testApi.createTransaction(testContext.user.budgetId, {
        accountId: trackingAccount.id,
        payeeName: trackingPayee,
        amount: -3000,
      })

      await transactionsPage.goto()

      // Apply tracking filter via drawer
      await transactionsPage.filterByTrackingAccounts()

      // Should only see tracking transaction
      await transactionsPage.expectTransactionNotExists(budgetPayee)
      await transactionsPage.expectTransactionExists(trackingPayee)

      // Filter count badge should show 1
      expect(await transactionsPage.getActiveFilterCount()).toBe(1)
    })

    test('account type filter uses radio buttons (mutually exclusive)', async ({
      authenticatedPage,
      testApi,
      testContext,
    }) => {
      const transactionsPage = new TransactionsPage(authenticatedPage)

      // Create accounts with transactions
      const budgetAccount = await testApi.createAccount(testContext.user.budgetId, {
        name: `Radio Budget ${Date.now()}`,
        accountType: 'checking',
        includeInBudget: true,
      })

      const trackingAccount = await testApi.createAccount(testContext.user.budgetId, {
        name: `Radio Tracking ${Date.now()}`,
        accountType: 'investment',
        includeInBudget: false,
      })

      const budgetPayee = `Radio Budget Payee ${Date.now()}`
      const trackingPayee = `Radio Tracking Payee ${Date.now()}`

      await testApi.createTransaction(testContext.user.budgetId, {
        accountId: budgetAccount.id,
        payeeName: budgetPayee,
        amount: -5000,
      })

      await testApi.createTransaction(testContext.user.budgetId, {
        accountId: trackingAccount.id,
        payeeName: trackingPayee,
        amount: -3000,
      })

      await transactionsPage.goto()

      // Apply budget filter first
      await transactionsPage.filterByBudgetAccounts()
      await transactionsPage.expectTransactionExists(budgetPayee)
      await transactionsPage.expectTransactionNotExists(trackingPayee)

      // Apply tracking filter - should replace budget filter (radio buttons)
      await transactionsPage.filterByTrackingAccounts()
      await transactionsPage.expectTransactionNotExists(budgetPayee)
      await transactionsPage.expectTransactionExists(trackingPayee)

      // Still only 1 filter active (account type)
      expect(await transactionsPage.getActiveFilterCount()).toBe(1)
    })

    test('envelope filter shows only transactions for selected envelope', async ({
      authenticatedPage,
      testApi,
      testContext,
    }) => {
      const transactionsPage = new TransactionsPage(authenticatedPage)

      // Create a budget account
      const account = await testApi.createAccount(testContext.user.budgetId, {
        name: `Envelope Filter Account ${Date.now()}`,
        accountType: 'checking',
        includeInBudget: true,
      })

      // Create an envelope
      const envelopeName = `Test Envelope ${Date.now()}`
      const envelope = await testApi.createEnvelope(testContext.user.budgetId, { name: envelopeName })

      // Create a transaction allocated to the envelope
      const envelopePayee = `Envelope Payee ${Date.now()}`
      await testApi.createTransaction(testContext.user.budgetId, {
        accountId: account.id,
        payeeName: envelopePayee,
        amount: -5000,
        envelopeId: envelope.id,
      })

      // Create an unallocated transaction
      const unallocatedPayee = `Unallocated Payee ${Date.now()}`
      await testApi.createTransaction(testContext.user.budgetId, {
        accountId: account.id,
        payeeName: unallocatedPayee,
        amount: -3000,
        // No envelopeId - goes to unallocated
      })

      await transactionsPage.goto()

      // Initially both transactions should be visible
      await transactionsPage.expectTransactionExists(envelopePayee)
      await transactionsPage.expectTransactionExists(unallocatedPayee)

      // Apply envelope filter
      await transactionsPage.filterByEnvelope(envelopeName)

      // Should only see envelope transaction
      await transactionsPage.expectTransactionExists(envelopePayee)
      await transactionsPage.expectTransactionNotExists(unallocatedPayee)

      // Filter count badge should show 1
      expect(await transactionsPage.getActiveFilterCount()).toBe(1)
    })
  })

  test.describe('Envelope Selection', () => {
    test('creates transaction with specific envelope', async ({ authenticatedPage, testApi, testContext }) => {
      const transactionsPage = new TransactionsPage(authenticatedPage)
      const formPage = new TransactionFormPage(authenticatedPage)

      // Create a budget account with starting balance via API
      const budgetAccount = `Envelope Test Account ${testId}`
      await testApi.createAccount(testContext.user.budgetId, {
        name: budgetAccount,
        accountType: 'checking',
        startingBalance: 50000, // cents
        includeInBudget: true,
      })

      // Create an envelope via API
      const envelopeName = `Test Envelope ${testId}`
      await testApi.createEnvelope(testContext.user.budgetId, { name: envelopeName })

      await transactionsPage.goto()
      await transactionsPage.clickAddTransaction()

      const payeeName = `Envelope Test ${Date.now()}`
      await formPage.createTransaction({
        account: budgetAccount,
        payee: payeeName,
        amount: '25.00',
        envelope: envelopeName,
      })

      await formPage.waitForDialogHidden()
      await transactionsPage.expectTransactionExists(payeeName)

      // Verify envelope is displayed on transaction
      const envelope = await transactionsPage.getTransactionEnvelope(payeeName)
      expect(envelope).toBe(envelopeName)
    })

    test('income defaults to Unallocated when no envelope selected', async ({ authenticatedPage }) => {
      const transactionsPage = new TransactionsPage(authenticatedPage)
      const formPage = new TransactionFormPage(authenticatedPage)
      const accountsPage = new AccountsPage(authenticatedPage)

      // Create a budget account
      const budgetAccount = `Unalloc Account ${testId}`
      await accountsPage.goto()
      await accountsPage.createAccount({
        name: budgetAccount,
        accountType: 'checking',
        includeInBudget: true,
      })

      await transactionsPage.goto()
      await transactionsPage.clickAddTransaction()

      const payeeName = `Income Unallocated Test ${Date.now()}`
      await formPage.selectAccount(budgetAccount)

      // Fill payee
      const payeeInput = formPage.payeeAutocomplete.locator('input')
      await payeeInput.click()
      await payeeInput.fill(payeeName)
      const menu = authenticatedPage.locator('.v-overlay--active .v-list')
      await menu.waitFor({ state: 'visible', timeout: 5000 })
      const createOption = menu.locator('.v-list-item').filter({ hasText: `Create "${payeeName}"` }).first()
      if (await createOption.isVisible({ timeout: 1000 }).catch(() => false)) {
        // Create new payee (inline, no dialog)
        await createOption.click()
        // Wait for the payee to be selected
        await expect(formPage.payeeAutocomplete.locator('.v-field__input')).toContainText(payeeName, { timeout: 5000 })
      }

      await formPage.fillAmount('30.00')
      // Switch to income (not expense) - income does NOT require envelope
      await formPage.setAsIncome()

      // Select "None" income allocation mode to go to Unallocated
      await formPage.selectIncomeAllocationMode('none')

      // Don't select any envelope - leave it empty (income defaults to Unallocated)
      await formPage.createButton.click()

      // With "None" mode, the transaction is created directly without preview dialog
      await formPage.waitForDialogHidden()
      await transactionsPage.expectTransactionExists(payeeName)

      // Verify transaction does NOT show envelope text (unallocated is hidden in new UI)
      const envelope = await transactionsPage.getTransactionEnvelope(payeeName)
      expect(envelope).toBeNull()
    })

    test('expense requires envelope selection in budget accounts', async ({ authenticatedPage, testApi, testContext }) => {
      const transactionsPage = new TransactionsPage(authenticatedPage)
      const formPage = new TransactionFormPage(authenticatedPage)

      // Create a budget account via API
      const budgetAccount = `Expense Req Env Account ${testId}`
      await testApi.createAccount(testContext.user.budgetId, {
        name: budgetAccount,
        accountType: 'checking',
        includeInBudget: true,
      })

      await transactionsPage.goto()
      await transactionsPage.clickAddTransaction()

      await formPage.selectAccount(budgetAccount)

      // Fill payee
      const payeeName = `Expense Req Env Payee ${Date.now()}`
      await formPage.createNewPayee(payeeName)
      await formPage.fillAmount('25.00')
      // Default is expense, don't change it

      // Without envelope, the create button should be disabled (validation fails)
      await expect(formPage.createButton).toBeDisabled()

      // Verify the hint indicates envelope is required (validation message is in alert element)
      const hint = formPage.page.locator('[role="alert"]').filter({ hasText: 'Required for expenses' })
      await expect(hint).toBeVisible()
    })

    test('can switch between single and split envelope modes', async ({ authenticatedPage }) => {
      const transactionsPage = new TransactionsPage(authenticatedPage)
      const formPage = new TransactionFormPage(authenticatedPage)
      const accountsPage = new AccountsPage(authenticatedPage)

      // Create a budget account
      const budgetAccount = `Split Mode Account ${testId}`
      await accountsPage.goto()
      await accountsPage.createAccount({
        name: budgetAccount,
        accountType: 'checking',
        includeInBudget: true,
      })

      await transactionsPage.goto()
      await transactionsPage.clickAddTransaction()

      // Select budget account
      await formPage.selectAccount(budgetAccount)

      // Verify single envelope mode is default
      await expect(formPage.envelopeSelect).toBeVisible()
      await expect(formPage.splitEnvelopesButton).toBeVisible()

      // Switch to split mode
      await formPage.enableSplitMode()
      await expect(formPage.addAllocationButton).toBeVisible()
      await expect(formPage.useSingleEnvelopeButton).toBeVisible()

      // Switch back to single mode
      await formPage.disableSplitMode()
      await expect(formPage.envelopeSelect).toBeVisible()
    })
  })

  test.describe('Location', () => {
    test('creates transaction with location', async ({ authenticatedPage, testApi, testContext }) => {
      const transactionsPage = new TransactionsPage(authenticatedPage)
      const formPage = new TransactionFormPage(authenticatedPage)

      // Create an account via API
      const accountName = `Location Account ${testId}`
      await testApi.createAccount(testContext.user.budgetId, {
        name: accountName,
        accountType: 'checking',
        includeInBudget: false,
      })

      // Create a location via API
      const locationName = `Test Location ${Date.now()}`
      await testApi.createLocation(testContext.user.budgetId, locationName)

      await transactionsPage.goto()
      await transactionsPage.clickAddTransaction()

      const payeeName = `Location Test Payee ${Date.now()}`
      await formPage.createTransaction({
        account: accountName,
        payee: payeeName,
        amount: '50.00',
        location: locationName,
      })

      await formPage.waitForDialogHidden()
      await transactionsPage.expectTransactionExists(payeeName)
    })

    test('creates new location inline when selecting', async ({ authenticatedPage, testApi, testContext }) => {
      const transactionsPage = new TransactionsPage(authenticatedPage)
      const formPage = new TransactionFormPage(authenticatedPage)

      // Create an account via API
      const accountName = `Location Create Account ${testId}`
      await testApi.createAccount(testContext.user.budgetId, {
        name: accountName,
        accountType: 'checking',
        includeInBudget: false,
      })

      await transactionsPage.goto()
      await transactionsPage.clickAddTransaction()

      // Create a new location inline (not via API)
      const newLocationName = `New Location ${Date.now()}`
      const payeeName = `New Location Payee ${Date.now()}`

      await formPage.selectAccount(accountName)
      await formPage.createNewPayee(payeeName)
      await formPage.fillAmount('25.00')
      await formPage.selectLocation(newLocationName)

      await formPage.createButton.click()
      await formPage.waitForDialogHidden()
      await transactionsPage.expectTransactionExists(payeeName)
    })

    test('location persists when editing transaction', async ({ authenticatedPage, testApi, testContext }) => {
      const transactionsPage = new TransactionsPage(authenticatedPage)
      const formPage = new TransactionFormPage(authenticatedPage)

      // Create an account via API
      const accountName = `Location Edit Account ${testId}`
      await testApi.createAccount(testContext.user.budgetId, {
        name: accountName,
        accountType: 'checking',
        includeInBudget: false,
      })

      // Create a location via API
      const locationName = `Edit Location ${Date.now()}`
      await testApi.createLocation(testContext.user.budgetId, locationName)

      await transactionsPage.goto()
      await transactionsPage.clickAddTransaction()

      const payeeName = `Location Edit Payee ${Date.now()}`
      await formPage.createTransaction({
        account: accountName,
        payee: payeeName,
        amount: '35.00',
        location: locationName,
      })

      await formPage.waitForDialogHidden()

      // Open the transaction for editing
      await transactionsPage.clickTransaction(payeeName)

      // Verify location is populated
      const selectedLocation = await formPage.getSelectedLocation()
      expect(selectedLocation).toContain(locationName)
    })

    test('filter transactions by location', async ({ authenticatedPage, testApi, testContext }) => {
      const transactionsPage = new TransactionsPage(authenticatedPage)
      const formPage = new TransactionFormPage(authenticatedPage)

      // Create an account via API
      const accountName = `Location Filter Account ${testId}`
      await testApi.createAccount(testContext.user.budgetId, {
        name: accountName,
        accountType: 'checking',
        includeInBudget: false,
      })

      // Create two locations via API
      const location1 = `Filter Location A ${Date.now()}`
      const location2 = `Filter Location B ${Date.now()}`
      await testApi.createLocation(testContext.user.budgetId, location1)
      await testApi.createLocation(testContext.user.budgetId, location2)

      await transactionsPage.goto()

      // Create transaction with location 1
      await transactionsPage.clickAddTransaction()
      const payee1 = `Location Filter Payee 1 ${Date.now()}`
      await formPage.createTransaction({
        account: accountName,
        payee: payee1,
        amount: '100.00',
        location: location1,
      })
      await formPage.waitForDialogHidden()

      // Create transaction with location 2
      await transactionsPage.clickAddTransaction()
      const payee2 = `Location Filter Payee 2 ${Date.now()}`
      await formPage.createTransaction({
        account: accountName,
        payee: payee2,
        amount: '200.00',
        location: location2,
      })
      await formPage.waitForDialogHidden()

      // Initially both transactions should be visible
      await transactionsPage.expectTransactionExists(payee1)
      await transactionsPage.expectTransactionExists(payee2)

      // Filter by location 1
      await transactionsPage.filterByLocation(location1)

      // Should only see transaction with location 1
      await transactionsPage.expectTransactionExists(payee1)
      await transactionsPage.expectTransactionNotExists(payee2)

      // Filter count badge should show 1
      expect(await transactionsPage.getActiveFilterCount()).toBe(1)

      // Clear filters
      await transactionsPage.openFiltersDrawer()
      await transactionsPage.clearAllFilters()

      // Should see both again
      await transactionsPage.expectTransactionExists(payee1)
      await transactionsPage.expectTransactionExists(payee2)
    })
  })

  test.describe('Income Auto-Allocation', () => {
    test('shows auto-distribute option when allocation rules exist', async ({
      authenticatedPage,
      testApi,
      testContext,
    }) => {
      const transactionsPage = new TransactionsPage(authenticatedPage)
      const formPage = new TransactionFormPage(authenticatedPage)

      // Create a budget account and envelope via API
      const accountName = `Auto Dist Account ${testId}`
      await testApi.createAccount(testContext.user.budgetId, {
        name: accountName,
        accountType: 'checking',
        includeInBudget: true,
      })

      const envelope = await testApi.createEnvelope(testContext.user.budgetId, {
        name: `Savings ${testId}`,
      })

      // Create an allocation rule
      await testApi.createAllocationRule(testContext.user.budgetId, {
        envelopeId: envelope.id,
        ruleType: 'fixed',
        amount: 5000, // $50
        priority: 1,
      })

      await transactionsPage.goto()
      await transactionsPage.clickAddTransaction()

      await formPage.selectAccount(accountName)
      await formPage.setAsIncome()

      // Auto-distribute option should be visible because rules exist
      await expect(formPage.autoDistributeRadio).toBeVisible()
    })

    test('shows preview dialog when saving with auto-distribute mode', async ({
      authenticatedPage,
      testApi,
      testContext,
    }) => {
      const transactionsPage = new TransactionsPage(authenticatedPage)
      const formPage = new TransactionFormPage(authenticatedPage)

      // Create a budget account and envelope via API
      const accountName = `Preview Account ${testId}`
      await testApi.createAccount(testContext.user.budgetId, {
        name: accountName,
        accountType: 'checking',
        includeInBudget: true,
      })

      const envelope = await testApi.createEnvelope(testContext.user.budgetId, {
        name: `Preview Savings ${testId}`,
      })

      // Create an allocation rule: $50 fixed
      await testApi.createAllocationRule(testContext.user.budgetId, {
        envelopeId: envelope.id,
        ruleType: 'fixed',
        amount: 5000, // $50 in cents
        priority: 1,
      })

      await transactionsPage.goto()
      await transactionsPage.clickAddTransaction()

      await formPage.selectAccount(accountName)
      const payeeName = `Preview Payee ${Date.now()}`
      await formPage.createNewPayee(payeeName)
      await formPage.fillAmount('100.00')
      await formPage.setAsIncome()

      // Ensure auto-distribute is selected
      await formPage.selectIncomeAllocationMode('auto-distribute')

      // Click create - should show preview dialog
      await formPage.createButton.click()
      await formPage.waitForPreviewDialog()

      // Preview dialog should be visible with allocations
      await expect(formPage.previewDialog).toBeVisible()
    })

    test('creates income with envelope mode', async ({
      authenticatedPage,
      testApi,
      testContext,
    }) => {
      const transactionsPage = new TransactionsPage(authenticatedPage)
      const formPage = new TransactionFormPage(authenticatedPage)

      // Create a budget account and envelope via API
      const accountName = `Envelope Mode Account ${testId}`
      await testApi.createAccount(testContext.user.budgetId, {
        name: accountName,
        accountType: 'checking',
        includeInBudget: true,
      })

      const envelope = await testApi.createEnvelope(testContext.user.budgetId, {
        name: `Income Envelope ${testId}`,
      })

      await transactionsPage.goto()
      await transactionsPage.clickAddTransaction()

      await formPage.selectAccount(accountName)
      const payeeName = `Envelope Mode Payee ${Date.now()}`
      await formPage.createNewPayee(payeeName)
      await formPage.fillAmount('75.00')
      await formPage.setAsIncome()

      // Select envelope mode
      await formPage.selectIncomeAllocationMode('envelope')

      // Envelope dropdown should now be visible
      await expect(formPage.envelopeSelect).toBeVisible()

      // Select the envelope
      await formPage.selectEnvelope(envelope.name)

      // Create transaction
      await formPage.createButton.click()
      await formPage.waitForDialogHidden()

      // Transaction should be created
      await transactionsPage.expectTransactionExists(payeeName)
    })

    test('creates income with none mode (goes to Unallocated)', async ({
      authenticatedPage,
      testApi,
      testContext,
    }) => {
      const transactionsPage = new TransactionsPage(authenticatedPage)
      const formPage = new TransactionFormPage(authenticatedPage)

      // Create a budget account via API
      const accountName = `None Mode Account ${testId}`
      await testApi.createAccount(testContext.user.budgetId, {
        name: accountName,
        accountType: 'checking',
        includeInBudget: true,
      })

      await transactionsPage.goto()
      await transactionsPage.clickAddTransaction()

      await formPage.selectAccount(accountName)
      const payeeName = `None Mode Payee ${Date.now()}`
      await formPage.createNewPayee(payeeName)
      await formPage.fillAmount('50.00')
      await formPage.setAsIncome()

      // Select none mode
      await formPage.selectIncomeAllocationMode('none')

      // Create transaction - should not show preview dialog
      await formPage.createButton.click()
      await formPage.waitForDialogHidden()

      // Transaction should be created
      await transactionsPage.expectTransactionExists(payeeName)
    })

    test('confirms preview and creates transaction with auto-distribute', async ({
      authenticatedPage,
      testApi,
      testContext,
    }) => {
      const transactionsPage = new TransactionsPage(authenticatedPage)
      const formPage = new TransactionFormPage(authenticatedPage)

      // Create a budget account and envelope via API
      const accountName = `Confirm Preview Account ${testId}`
      await testApi.createAccount(testContext.user.budgetId, {
        name: accountName,
        accountType: 'checking',
        includeInBudget: true,
      })

      const envelope = await testApi.createEnvelope(testContext.user.budgetId, {
        name: `Confirm Savings ${testId}`,
      })

      // Create an allocation rule: $50 fixed
      await testApi.createAllocationRule(testContext.user.budgetId, {
        envelopeId: envelope.id,
        ruleType: 'fixed',
        amount: 5000, // $50 in cents
        priority: 1,
      })

      await transactionsPage.goto()
      await transactionsPage.clickAddTransaction()

      await formPage.selectAccount(accountName)
      const payeeName = `Confirm Payee ${Date.now()}`
      await formPage.createNewPayee(payeeName)
      await formPage.fillAmount('100.00')
      await formPage.setAsIncome()

      // Ensure auto-distribute is selected
      await formPage.selectIncomeAllocationMode('auto-distribute')

      // Click create - shows preview
      await formPage.createButton.click()
      await formPage.waitForPreviewDialog()

      // Confirm the preview
      await formPage.confirmPreview()

      // Dialog should close and transaction should be created
      await formPage.waitForDialogHidden()
      await transactionsPage.expectTransactionExists(payeeName)
    })

    test('can cancel preview and return to form', async ({
      authenticatedPage,
      testApi,
      testContext,
    }) => {
      const transactionsPage = new TransactionsPage(authenticatedPage)
      const formPage = new TransactionFormPage(authenticatedPage)

      // Create a budget account and envelope via API
      const accountName = `Cancel Preview Account ${testId}`
      await testApi.createAccount(testContext.user.budgetId, {
        name: accountName,
        accountType: 'checking',
        includeInBudget: true,
      })

      const envelope = await testApi.createEnvelope(testContext.user.budgetId, {
        name: `Cancel Savings ${testId}`,
      })

      // Create an allocation rule
      await testApi.createAllocationRule(testContext.user.budgetId, {
        envelopeId: envelope.id,
        ruleType: 'fixed',
        amount: 5000,
        priority: 1,
      })

      await transactionsPage.goto()
      await transactionsPage.clickAddTransaction()

      await formPage.selectAccount(accountName)
      const payeeName = `Cancel Preview Payee ${Date.now()}`
      await formPage.createNewPayee(payeeName)
      await formPage.fillAmount('100.00')
      await formPage.setAsIncome()

      await formPage.selectIncomeAllocationMode('auto-distribute')

      // Click create - shows preview
      await formPage.createButton.click()
      await formPage.waitForPreviewDialog()

      // Cancel the preview
      await formPage.cancelPreview()

      // Preview should close but main form should still be open
      await expect(formPage.previewDialog).not.toBeVisible()
      await expect(formPage.dialog).toBeVisible()
    })
  })
})
