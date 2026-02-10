import { test, expect } from '../fixtures/test-setup'
import { AccountsPage } from '../pages/accounts.page'
import { EnvelopesPage } from '../pages/envelopes.page'
import { TransactionsPage } from '../pages/transactions.page'
import { TransactionFormPage } from '../pages/transaction-form.page'

// Test context is set up automatically via fixtures
// - Database is reset per worker
// - User is created once per file

const testId = Date.now()

test.describe('Credit Card Envelopes', () => {
  // CC account creation tests remain as E2E because they test API mutations
  // and cross-page navigation (account creation → envelope verification → deletion).
  //
  // CC transaction form tests (envelope label, dropdown filtering) are covered by
  // component tests in tests/unit/components/transactions/TransactionFormDialog.spec.ts.
  // CC envelope rendering tests (section display, disabled features) are covered by
  // component tests in tests/unit/components/envelopes/EnvelopesView.spec.ts.

  test.describe('Credit Card Account Creation', () => {
    test('creates linked envelope when creating CC account', async ({ authenticatedPage }) => {
      const accountsPage = new AccountsPage(authenticatedPage)
      const envelopesPage = new EnvelopesPage(authenticatedPage)

      // Create a credit card account
      const ccName = `Test CC ${testId}`
      await accountsPage.goto()
      await accountsPage.createAccount({
        name: ccName,
        accountType: 'credit_card',
      })

      // Navigate to envelopes and verify CC envelope was created
      await envelopesPage.goto()
      await envelopesPage.expectCreditCardsSectionVisible()
      await envelopesPage.expectCreditCardEnvelopeExists(ccName)
    })

    test('deleting CC account also deletes linked envelope', async ({ authenticatedPage }) => {
      const accountsPage = new AccountsPage(authenticatedPage)
      const envelopesPage = new EnvelopesPage(authenticatedPage)
      const { AccountDetailPage } = await import('../pages/account-detail.page')

      // Create a credit card account
      const ccName = `Delete CC ${testId}`
      await accountsPage.goto()
      await accountsPage.createAccount({
        name: ccName,
        accountType: 'credit_card',
      })

      // Verify envelope exists
      await envelopesPage.goto()
      await envelopesPage.expectCreditCardEnvelopeExists(ccName)

      // Delete the account
      await accountsPage.goto()
      await accountsPage.clickAccount(ccName)
      const detailPage = new AccountDetailPage(authenticatedPage)
      await detailPage.deleteAccount()

      // Verify envelope is gone
      await envelopesPage.goto()
      // CC section should not be visible if no CC envelopes exist
      // (or the specific envelope should not exist)
      const ccEnvelope = authenticatedPage.locator('.v-list-item').filter({ hasText: ccName })
      await expect(ccEnvelope).toBeHidden()
    })
  })

  test.describe('CC Spending Behavior', () => {
    test('spending on CC moves money from category to CC envelope', async ({
      authenticatedPage,
    }) => {
      const accountsPage = new AccountsPage(authenticatedPage)
      const envelopesPage = new EnvelopesPage(authenticatedPage)
      const transactionsPage = new TransactionsPage(authenticatedPage)
      const formPage = new TransactionFormPage(authenticatedPage)

      // Create a checking account with starting balance
      const checkingName = `CC Test Checking ${testId}`
      await accountsPage.goto()
      await accountsPage.createAccount({
        name: checkingName,
        accountType: 'checking',
        startingBalance: '500.00',
        includeInBudget: true,
      })

      // Create a CC account
      const ccName = `Spending CC ${testId}`
      await accountsPage.createAccount({
        name: ccName,
        accountType: 'credit_card',
      })

      // Create a Groceries envelope
      const groceriesName = `CC Groceries ${testId}`
      await envelopesPage.goto()
      await envelopesPage.createEnvelope({ name: groceriesName })

      // Transfer $200 to Groceries envelope
      await envelopesPage.openAssignMoneyDialog()
      await envelopesPage.completeTransfer(groceriesName, '200.00')

      // Create a CC expense in Groceries category
      await transactionsPage.goto()
      await transactionsPage.clickAddTransaction()
      await formPage.selectAccount(ccName)
      await formPage.createNewPayee(`Store ${testId}`)
      await formPage.setAsExpense()
      await formPage.fillAmount('50.00')
      await formPage.selectEnvelope(groceriesName)
      await formPage.submit()

      // Go to envelopes and check balances
      await envelopesPage.goto()

      // Groceries should be reduced by $50 (from $200 to $150)
      await envelopesPage.clickEnvelope(groceriesName)
      const { EnvelopeDetailPage } = await import('../pages/envelope-detail.page')
      const detailPage = new EnvelopeDetailPage(authenticatedPage)
      const groceriesBalance = await detailPage.getCurrentBalance()
      expect(groceriesBalance).toContain('150')

      // CC envelope should have $50
      await envelopesPage.goto()
      const ccBalance = await envelopesPage.getCreditCardEnvelopeBalance(ccName)
      expect(ccBalance).toContain('50')
    })

    test('CC spending does not affect Ready to Assign', async ({
      authenticatedPage,
    }) => {
      const accountsPage = new AccountsPage(authenticatedPage)
      const envelopesPage = new EnvelopesPage(authenticatedPage)
      const transactionsPage = new TransactionsPage(authenticatedPage)
      const formPage = new TransactionFormPage(authenticatedPage)

      // Create a checking account with starting balance
      const checkingName = `RTA Test Checking ${testId}`
      await accountsPage.goto()
      await accountsPage.createAccount({
        name: checkingName,
        accountType: 'checking',
        startingBalance: '500.00',
        includeInBudget: true,
      })

      // Create a CC account
      const ccName = `RTA Test CC ${testId}`
      await accountsPage.createAccount({
        name: ccName,
        accountType: 'credit_card',
      })

      // Create a Groceries envelope
      const groceriesName = `RTA Groceries ${testId}`
      await envelopesPage.goto()
      await envelopesPage.createEnvelope({ name: groceriesName })

      // Transfer all $500 to Groceries envelope
      await envelopesPage.openAssignMoneyDialog()
      await envelopesPage.completeTransfer(groceriesName, '500.00')

      // Capture Ready to Assign before CC spending
      await envelopesPage.goto()
      const initialReadyToAssign = await envelopesPage.readyToAssignAmount.textContent()

      // Create a CC expense in Groceries category
      await transactionsPage.goto()
      await transactionsPage.clickAddTransaction()
      await formPage.selectAccount(ccName)
      await formPage.createNewPayee(`RTA Store ${testId}`)
      await formPage.setAsExpense()
      await formPage.fillAmount('50.00')
      await formPage.selectEnvelope(groceriesName)
      await formPage.submit()

      // Navigate back to envelopes and verify Ready to Assign is unchanged
      await envelopesPage.goto()
      const afterSpendingReadyToAssign = await envelopesPage.readyToAssignAmount.textContent()
      expect(afterSpendingReadyToAssign).toBe(initialReadyToAssign)
    })
  })

  test.describe('CC Payment Behavior', () => {
    test('paying CC reduces CC envelope balance', async ({ authenticatedPage }) => {
      const accountsPage = new AccountsPage(authenticatedPage)
      const envelopesPage = new EnvelopesPage(authenticatedPage)
      const transactionsPage = new TransactionsPage(authenticatedPage)
      const formPage = new TransactionFormPage(authenticatedPage)

      // Create a checking account with starting balance
      const checkingName = `Payment Checking ${testId}`
      await accountsPage.goto()
      await accountsPage.createAccount({
        name: checkingName,
        accountType: 'checking',
        startingBalance: '1000.00',
        includeInBudget: true,
      })

      // Create a CC account
      const ccName = `Payment CC ${testId}`
      await accountsPage.createAccount({
        name: ccName,
        accountType: 'credit_card',
      })

      // Create Groceries envelope and transfer money
      const groceriesName = `Payment Groceries ${testId}`
      await envelopesPage.goto()
      await envelopesPage.createEnvelope({ name: groceriesName })

      await envelopesPage.openAssignMoneyDialog()
      await envelopesPage.completeTransfer(groceriesName, '300.00')

      // Spend $100 on CC to build up CC envelope balance
      await transactionsPage.goto()
      await transactionsPage.clickAddTransaction()
      await formPage.selectAccount(ccName)
      await formPage.createNewPayee(`Payment Store ${testId}`)
      await formPage.setAsExpense()
      await formPage.fillAmount('100.00')
      await formPage.selectEnvelope(groceriesName)
      await formPage.submit()

      // Verify CC envelope has $100
      await envelopesPage.goto()
      let ccBalance = await envelopesPage.getCreditCardEnvelopeBalance(ccName)
      expect(ccBalance).toContain('100')

      // Make a CC payment (transfer from checking to CC)
      await transactionsPage.goto()
      await transactionsPage.clickAddTransaction()
      await formPage.createTransfer({
        fromAccount: checkingName,
        toAccount: ccName,
        amount: '50.00',
      })

      // CC envelope should be reduced to $50
      await envelopesPage.goto()
      ccBalance = await envelopesPage.getCreditCardEnvelopeBalance(ccName)
      expect(ccBalance).toContain('50')
    })
  })
})
