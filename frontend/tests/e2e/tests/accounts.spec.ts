import { test, expect } from '../fixtures/test-setup'
import { AccountsPage } from '../pages/accounts.page'
import { AccountDetailPage } from '../pages/account-detail.page'

// Test context is set up automatically via fixtures
// - Database is reset per worker
// - User is created once per file

// UI rendering, form validation, dialog open/close, empty states, and grouping
// tests have been migrated to component tests:
// - tests/unit/components/accounts/AccountsView.spec.ts
// - tests/unit/components/accounts/AccountDetailView.spec.ts

test.describe('Accounts', () => {
  test.describe('CRUD Operations', () => {
    test('creates account with starting balance', async ({ authenticatedPage }) => {
      const accountsPage = new AccountsPage(authenticatedPage)
      await accountsPage.goto()

      const accountName = `Balance Account ${Date.now()}`
      await accountsPage.createAccount({
        name: accountName,
        accountType: 'checking',
        startingBalance: '1000.00',
      })

      await accountsPage.expectAccountExists(accountName)

      // Navigate to account detail to verify balance
      await accountsPage.clickAccount(accountName)
      const detailPage = new AccountDetailPage(authenticatedPage)
      await expect(detailPage.accountBalance).toContainText('1,000', { timeout: 15000 })
    })

    test('updates account name', async ({ authenticatedPage }) => {
      const accountsPage = new AccountsPage(authenticatedPage)
      await accountsPage.goto()

      // Create an account first
      const originalName = `Original Account ${Date.now()}`
      await accountsPage.createAccount({ name: originalName })
      await accountsPage.expectAccountExists(originalName)

      // Navigate to detail page
      await accountsPage.clickAccount(originalName)
      const detailPage = new AccountDetailPage(authenticatedPage)

      // Edit account
      const newName = `Updated Account ${Date.now()}`
      await detailPage.editAccount({ name: newName })

      // Verify name changed
      const displayedName = await detailPage.getAccountName()
      expect(displayedName).toContain(newName)
    })

    test('updates account type', async ({ authenticatedPage }) => {
      const accountsPage = new AccountsPage(authenticatedPage)
      await accountsPage.goto()

      // Create an account first
      const accountName = `Type Test ${Date.now()}`
      await accountsPage.createAccount({
        name: accountName,
        accountType: 'checking',
      })
      await accountsPage.expectAccountExists(accountName)

      // Navigate to detail
      await accountsPage.clickAccount(accountName)
      const detailPage = new AccountDetailPage(authenticatedPage)

      await detailPage.editAccount({ accountType: 'savings' })
    })

    test('updates account icon', async ({ authenticatedPage }) => {
      const accountsPage = new AccountsPage(authenticatedPage)
      await accountsPage.goto()

      // Create an account first
      const accountName = `Icon Update Test ${Date.now()}`
      await accountsPage.createAccount({
        name: accountName,
        accountType: 'checking',
      })
      await accountsPage.expectAccountExists(accountName)

      // Navigate to detail
      await accountsPage.clickAccount(accountName)
      const detailPage = new AccountDetailPage(authenticatedPage)

      // Update icon (use "Food" which matches the Food chip)
      await detailPage.editAccount({ icon: 'Food' })
    })

    test('clears account icon to use default', async ({ authenticatedPage }) => {
      const accountsPage = new AccountsPage(authenticatedPage)
      await accountsPage.goto()

      // Create an account with a custom icon
      const accountName = `Clear Icon Test ${Date.now()}`
      await accountsPage.createAccount({
        name: accountName,
        accountType: 'checking',
        icon: 'Home', // Matches the Home chip
      })
      await accountsPage.expectAccountExists(accountName)

      // Navigate to detail
      await accountsPage.clickAccount(accountName)
      const detailPage = new AccountDetailPage(authenticatedPage)

      // Clear the icon
      await detailPage.editAccount({ clearIcon: true })
    })

    test('toggles include in budget setting', async ({ authenticatedPage }) => {
      const accountsPage = new AccountsPage(authenticatedPage)
      await accountsPage.goto()

      // Create an account first
      const accountName = `Budget Test ${Date.now()}`
      await accountsPage.createAccount({ name: accountName })
      await accountsPage.expectAccountExists(accountName)

      // Navigate to detail
      await accountsPage.clickAccount(accountName)
      const detailPage = new AccountDetailPage(authenticatedPage)

      // Turn off include in budget
      await detailPage.editAccount({ includeInBudget: false })

      // Reload to see the updated state (Vue may not reactively update immediately)
      await authenticatedPage.reload()
      await detailPage.waitForPageLoad()

      // Verify off-budget label appears
      await expect(detailPage.offBudgetLabel).toBeVisible()
    })

    test('deletes account with confirmation', async ({ authenticatedPage }) => {
      const accountsPage = new AccountsPage(authenticatedPage)
      await accountsPage.goto()

      // Create an account first
      const accountName = `Delete Test ${Date.now()}`
      await accountsPage.createAccount({ name: accountName })
      await accountsPage.expectAccountExists(accountName)

      // Navigate to detail
      await accountsPage.clickAccount(accountName)
      const detailPage = new AccountDetailPage(authenticatedPage)

      await detailPage.deleteAccount()

      // Should redirect to accounts list
      await expect(authenticatedPage).toHaveURL(/\/accounts$/)

      // Account should not exist in list
      await accountsPage.expectAccountNotExists(accountName)
    })
  })

  test.describe('Reconciliation', () => {
    test('reconciles account when balance is correct (Yes path)', async ({ authenticatedPage }) => {
      const accountsPage = new AccountsPage(authenticatedPage)
      await accountsPage.goto()

      // Create an account with starting balance
      const accountName = `Reconcile Confirm ${Date.now()}`
      await accountsPage.createAccount({
        name: accountName,
        startingBalance: '1000.00',
      })
      await accountsPage.expectAccountExists(accountName)

      // Navigate to detail
      await accountsPage.clickAccount(accountName)
      const detailPage = new AccountDetailPage(authenticatedPage)

      // Use the confirm path (Yes button)
      await detailPage.reconcileAccountConfirm()

      // Balance should remain unchanged
      const balance = await detailPage.getAccountBalance()
      expect(balance).toContain('1,000')
    })

    test('reconciles account with balance adjustment (No path)', async ({ authenticatedPage }) => {
      const accountsPage = new AccountsPage(authenticatedPage)
      await accountsPage.goto()

      // Create an account first
      const accountName = `Reconcile Balance ${Date.now()}`
      await accountsPage.createAccount({ name: accountName })
      await accountsPage.expectAccountExists(accountName)

      // Navigate to detail
      await accountsPage.clickAccount(accountName)
      const detailPage = new AccountDetailPage(authenticatedPage)

      // Reconcile to $500 using the No path
      await detailPage.reconcileAccountWithBalance('500.00')

      // Balance should update
      await authenticatedPage.reload()
      await detailPage.waitForPageLoad()

      const balance = await detailPage.getAccountBalance()
      expect(balance).toContain('500')
    })

    test('reconciles credit card with negative balance', async ({
      authenticatedPage,
      testApi,
      testContext,
    }) => {
      const detailPage = new AccountDetailPage(authenticatedPage)

      // Create credit card account via API
      const account = await testApi.createAccount(testContext.user.budgetId, {
        name: `Credit Card ${Date.now()}`,
        accountType: 'credit_card',
      })

      // Create expense transaction (negative amount creates debt)
      await testApi.createTransaction(testContext.user.budgetId, {
        accountId: account.id,
        amount: -10000, // $100 spent on credit card
        payeeName: 'Test Purchase',
        isCleared: true,
      })

      // Go to account detail page
      await detailPage.goto(account.id)

      // Verify initial balance is -$100.00
      const initialBalance = await detailPage.getAccountBalance()
      expect(initialBalance).toBe('-$100.00')

      // Open reconcile dialog and verify sign toggle defaults to negative
      await detailPage.openReconcileDialog()
      await detailPage.proceedToBalanceEntry()

      const isNegative = await detailPage.isReconcileSignNegative()
      expect(isNegative).toBe(true)

      // Reconcile to -$150.00 (different negative balance)
      await detailPage.fillReconcileBalance('150.00')
      await detailPage.setReconcileSignNegative()
      await detailPage.confirmReconcile()

      // Reload and verify new balance
      await authenticatedPage.reload()
      await detailPage.waitForPageLoad()

      const newBalance = await detailPage.getAccountBalance()
      expect(newBalance).toBe('-$150.00')
    })
  })

  test.describe('Account Grouping', () => {
    test('All Accounts row navigates to transactions', async ({ authenticatedPage }) => {
      const accountsPage = new AccountsPage(authenticatedPage)
      await accountsPage.goto()

      // Create an account with balance
      const accountName = `All Accounts Test ${Date.now()}`
      await accountsPage.createAccount({
        name: accountName,
        startingBalance: '500.00',
      })
      await accountsPage.expectAccountExists(accountName)

      // All Accounts row should be visible
      await expect(accountsPage.allAccountsRow).toBeVisible()

      // Click should navigate to transactions
      await accountsPage.clickAllAccounts()
      await expect(authenticatedPage).toHaveURL(/\/transactions$/)
    })
  })

  test.describe('Navigation', () => {
    test('clicking account navigates to detail page', async ({ authenticatedPage }) => {
      const accountsPage = new AccountsPage(authenticatedPage)
      await accountsPage.goto()

      // Create an account first
      const accountName = `Nav Test ${Date.now()}`
      await accountsPage.createAccount({ name: accountName })
      await accountsPage.expectAccountExists(accountName)

      await accountsPage.clickAccount(accountName)

      await expect(authenticatedPage).toHaveURL(/\/accounts\/[a-z0-9-]+/)
    })

    test('back button returns to accounts list', async ({ authenticatedPage }) => {
      const accountsPage = new AccountsPage(authenticatedPage)
      await accountsPage.goto()

      // Create an account first
      const accountName = `Back Test ${Date.now()}`
      await accountsPage.createAccount({ name: accountName })
      await accountsPage.expectAccountExists(accountName)

      await accountsPage.clickAccount(accountName)
      const detailPage = new AccountDetailPage(authenticatedPage)

      await detailPage.goBack()

      await expect(authenticatedPage).toHaveURL(/\/accounts$/)
    })
  })

  test.describe('Last Reconciled Display', () => {
    test('shows "Last reconciled today" after reconciling', async ({ authenticatedPage }) => {
      const accountsPage = new AccountsPage(authenticatedPage)
      await accountsPage.goto()

      const accountName = `Reconcile Time ${Date.now()}`
      await accountsPage.createAccount({ name: accountName })
      await accountsPage.expectAccountExists(accountName)

      await accountsPage.clickAccount(accountName)
      const detailPage = new AccountDetailPage(authenticatedPage)

      await detailPage.reconcileAccountConfirm()

      // Check for updated text (should now say "Last reconciled today")
      await expect(detailPage.lastReconciledText).toHaveText('Last reconciled today')
    })
  })

  test.describe('Reconciled Filter', () => {
    test('hide reconciled filter hides reconciled transactions on account detail page', async ({
      authenticatedPage,
      testApi,
      testContext,
    }) => {
      const accountDetailPage = new AccountDetailPage(authenticatedPage)

      // Create account via API (no starting balance to avoid extra adjustment transaction)
      const account = await testApi.createAccount(testContext.user.budgetId, {
        name: `Test Account ${Date.now()}`,
        accountType: 'checking',
      })

      // Create 2 cleared transactions that will be reconciled
      await testApi.createTransaction(testContext.user.budgetId, {
        accountId: account.id,
        amount: -5000, // $50 expense
        payeeName: 'Reconciled Payee',
        isCleared: true,
      })

      await testApi.createTransaction(testContext.user.budgetId, {
        accountId: account.id,
        amount: -3000, // $30 expense
        payeeName: 'Also Reconciled',
        isCleared: true,
      })

      // Reconcile the account - this will mark both cleared transactions as reconciled
      const result = await testApi.reconcileAccount(
        testContext.user.budgetId,
        account.id,
        -8000 // Current balance after the two expenses
      )
      expect(result.transactionsReconciled).toBe(2)

      // Create a new cleared transaction after reconciliation (not reconciled)
      await testApi.createTransaction(testContext.user.budgetId, {
        accountId: account.id,
        amount: -2000, // $20 expense
        payeeName: 'New Unreconciled',
        isCleared: true,
      })

      // Go to account detail page
      await accountDetailPage.goto(account.id)

      // Initially all transactions should be visible
      await accountDetailPage.expectTransactionExists('Reconciled Payee')
      await accountDetailPage.expectTransactionExists('Also Reconciled')
      await accountDetailPage.expectTransactionExists('New Unreconciled')

      // Toggle hide reconciled filter
      await accountDetailPage.toggleHideReconciledFilter()

      // Verify filter is active
      const isActive = await accountDetailPage.isHideReconciledFilterActive()
      expect(isActive).toBe(true)

      // Reconciled transactions should be hidden
      await accountDetailPage.expectTransactionNotExists('Reconciled Payee')
      await accountDetailPage.expectTransactionNotExists('Also Reconciled')

      // New unreconciled transaction should still be visible
      await accountDetailPage.expectTransactionExists('New Unreconciled')

      // Toggle filter off
      await accountDetailPage.toggleHideReconciledFilter()

      // All transactions should be visible again
      await accountDetailPage.expectTransactionExists('Reconciled Payee')
      await accountDetailPage.expectTransactionExists('Also Reconciled')
      await accountDetailPage.expectTransactionExists('New Unreconciled')
    })
  })
})
