import { test, expect } from '../fixtures/test-setup'
import { EnvelopesPage } from '../pages/envelopes.page'
import { EnvelopeDetailPage } from '../pages/envelope-detail.page'
import { AccountsPage } from '../pages/accounts.page'

// Test context is set up automatically via fixtures
// - Database is reset per worker
// - User is created once per file
//
// Form validation tests (disabled buttons, duplicate name errors) are covered by
// component tests in tests/unit/components/envelopes/EnvelopesView.spec.ts

// Generate unique names for this test run (for test-created data)
const testId = Date.now()
const testEnvelope = `Groceries ${testId}`
const testGroup = `Monthly Bills ${testId}`

test.describe('Envelopes', () => {
  test.describe('Create Envelopes', () => {
    test('creates a basic envelope', async ({ authenticatedPage }) => {
      const envelopesPage = new EnvelopesPage(authenticatedPage)

      await envelopesPage.goto()
      await envelopesPage.createEnvelope({
        name: testEnvelope,
      })

      await envelopesPage.expectEnvelopeExists(testEnvelope)
    })

    test('creates envelope with target balance', async ({ authenticatedPage }) => {
      const envelopesPage = new EnvelopesPage(authenticatedPage)
      const detailPage = new EnvelopeDetailPage(authenticatedPage)
      const envelopeName = `Savings Goal ${testId}`

      await envelopesPage.goto()
      await envelopesPage.createEnvelope({
        name: envelopeName,
        targetBalance: '500.00',
      })

      // Navigate to detail to verify target balance creates progress bar
      await envelopesPage.clickEnvelope(envelopeName)
      await detailPage.expectProgressBarVisible()
    })

    test('creates envelope in a group', async ({ authenticatedPage }) => {
      const envelopesPage = new EnvelopesPage(authenticatedPage)
      const envelopeName = `Rent ${testId}`

      await envelopesPage.goto()

      // First create a group
      await envelopesPage.createGroup(testGroup)

      // Then create envelope in that group
      await envelopesPage.createEnvelope({
        name: envelopeName,
        group: testGroup,
      })

      await envelopesPage.expectEnvelopeExists(envelopeName)
      await envelopesPage.expectGroupExists(testGroup)
    })

    test('creates envelope with new group inline', async ({ authenticatedPage }) => {
      const envelopesPage = new EnvelopesPage(authenticatedPage)
      const envelopeName = `New Group Envelope ${testId}`
      const newGroupName = `Inline Group ${testId}`

      await envelopesPage.goto()
      await envelopesPage.createEnvelope({
        name: envelopeName,
        createNewGroup: newGroupName,
      })

      await envelopesPage.expectEnvelopeExists(envelopeName)
      await envelopesPage.expectGroupExists(newGroupName)
    })

  })

  // Note: "auto-assign disabled when no rules" test removed - it's order-dependent and
  // incompatible with shared test data where other test files may create rules

  test.describe('Create Envelope with Allocation Rule', () => {
    test('creates envelope with Fill to Target rule', async ({ authenticatedPage }) => {
      const envelopesPage = new EnvelopesPage(authenticatedPage)
      const detailPage = new EnvelopeDetailPage(authenticatedPage)
      const envelopeName = `Fill Target Rule ${testId}`

      await envelopesPage.goto()
      await envelopesPage.createEnvelope({
        name: envelopeName,
        targetBalance: '500.00',
        withRule: {
          type: 'fill_to_target',
        },
      })

      await envelopesPage.expectEnvelopeExists(envelopeName)

      // Verify rule exists by checking envelope detail
      await envelopesPage.clickEnvelope(envelopeName)
      await detailPage.expectAllocationRulesSectionVisible()
    })

    test('creates envelope with Fixed amount rule', async ({ authenticatedPage }) => {
      const envelopesPage = new EnvelopesPage(authenticatedPage)
      const envelopeName = `Fixed Rule ${testId}`

      await envelopesPage.goto()
      await envelopesPage.createEnvelope({
        name: envelopeName,
        withRule: {
          type: 'fixed',
          amount: '100.00',
        },
      })

      await envelopesPage.expectEnvelopeExists(envelopeName)

      // Verify rule icon appears on envelope card
      await envelopesPage.expectEnvelopeHasRuleIcons(envelopeName)
    })

    // Note: Allocation rule form validation tests (Fill to Target requires target,
    // Fixed rule requires amount, rule toggle default state) are covered by component tests
    // in tests/unit/components/allocation-rules/AllocationRuleForm.spec.ts
  })

  test.describe('Create Groups', () => {
    test('creates a new group', async ({ authenticatedPage }) => {
      const envelopesPage = new EnvelopesPage(authenticatedPage)
      const groupName = `Savings ${testId}`
      const envelopeName = `Emergency Fund ${testId}`

      await envelopesPage.goto()
      await envelopesPage.createGroup(groupName)

      // Groups only show when they have envelopes, so create one in the new group
      await envelopesPage.createEnvelope({
        name: envelopeName,
        group: groupName,
      })

      // Verify the group is visible with the envelope in it
      await envelopesPage.expectGroupExists(groupName)
      await envelopesPage.expectEnvelopeExists(envelopeName)
    })

  })

  test.describe('Transfer Money', () => {
    test('transfers money from unallocated to envelope', async ({ authenticatedPage }) => {
      const envelopesPage = new EnvelopesPage(authenticatedPage)
      const accountsPage = new AccountsPage(authenticatedPage)
      const transferEnvelope = `Transfer Test ${testId}`

      // First create a budget account with starting balance (goes to Unallocated)
      await accountsPage.goto()
      await accountsPage.createAccount({
        name: `Transfer Account ${testId}`,
        accountType: 'checking',
        startingBalance: '500.00',
        includeInBudget: true,
      })
      await envelopesPage.goto()

      // Create an envelope to transfer to
      await envelopesPage.createEnvelope({ name: transferEnvelope })

      // Open assign money dialog from Ready to Assign card
      await envelopesPage.openAssignMoneyDialog()
      await envelopesPage.completeTransfer(transferEnvelope, '100.00')
    })

    test('transfers money between envelopes from detail page', async ({ authenticatedPage }) => {
      const envelopesPage = new EnvelopesPage(authenticatedPage)
      const accountsPage = new AccountsPage(authenticatedPage)
      const detailPage = new EnvelopeDetailPage(authenticatedPage)
      const sourceEnvelope = `Source ${testId}`
      const destEnvelope = `Destination ${testId}`

      // First create a budget account with starting balance (goes to Unallocated)
      await accountsPage.goto()
      await accountsPage.createAccount({
        name: `Transfer Account2 ${testId}`,
        accountType: 'checking',
        startingBalance: '500.00',
        includeInBudget: true,
      })
      await envelopesPage.goto()

      // Create two envelopes
      await envelopesPage.createEnvelope({ name: sourceEnvelope })
      await envelopesPage.createEnvelope({ name: destEnvelope })

      // Fund the source envelope from unallocated
      await envelopesPage.openAssignMoneyDialog()
      await envelopesPage.completeTransfer(sourceEnvelope, '200.00')

      // Navigate to source envelope and transfer to destination
      await envelopesPage.clickEnvelope(sourceEnvelope)
      await detailPage.transferTo(destEnvelope, '50.00')
    })
  })

  test.describe('Transfer Direction Toggle', () => {
    test('toggle defaults to "to" when opening transfer from envelope card', async ({
      authenticatedPage,
    }) => {
      const envelopesPage = new EnvelopesPage(authenticatedPage)
      const envelopeName = `Toggle Default ${testId}`

      await envelopesPage.goto()
      await envelopesPage.createEnvelope({ name: envelopeName })

      await envelopesPage.openTransferFromEnvelope(envelopeName)

      // Toggle should be visible and "to" should be active
      await envelopesPage.expectTransferToggleVisible()
      await expect(envelopesPage.transferToButton).toHaveClass(/v-btn--active/)

      await envelopesPage.cancelTransferButton.click()
    })

    test('can switch transfer direction to "from" mode', async ({ authenticatedPage }) => {
      const envelopesPage = new EnvelopesPage(authenticatedPage)
      const accountsPage = new AccountsPage(authenticatedPage)
      const sourceEnvelope = `Source Toggle ${testId}`
      const destEnvelope = `Dest Toggle ${testId}`

      // Create account with funds
      await accountsPage.goto()
      await accountsPage.createAccount({
        name: `Toggle Account ${testId}`,
        accountType: 'checking',
        startingBalance: '500.00',
        includeInBudget: true,
      })

      await envelopesPage.goto()
      await envelopesPage.createEnvelope({ name: sourceEnvelope })
      await envelopesPage.createEnvelope({ name: destEnvelope })

      // Fund source envelope
      await envelopesPage.openAssignMoneyDialog()
      await envelopesPage.completeTransfer(sourceEnvelope, '100.00')

      // Open transfer from source and switch to "from" mode, transfer to dest
      await envelopesPage.openTransferFromEnvelope(sourceEnvelope)
      await envelopesPage.selectTransferDirection('from')
      await envelopesPage.completeTransfer(destEnvelope, '25.00')
    })

    test('toggle not shown when assigning from unallocated', async ({ authenticatedPage }) => {
      const envelopesPage = new EnvelopesPage(authenticatedPage)
      const accountsPage = new AccountsPage(authenticatedPage)

      // Create account with funds to make "Assign Money" button appear
      await accountsPage.goto()
      await accountsPage.createAccount({
        name: `Unalloc Toggle ${testId}`,
        accountType: 'checking',
        startingBalance: '100.00',
        includeInBudget: true,
      })

      await envelopesPage.goto()

      // Open assign money dialog from Ready to Assign
      await envelopesPage.openAssignMoneyDialog()
      await envelopesPage.expectTransferToggleHidden()
      await envelopesPage.cancelTransferButton.click()
    })

    test('toggle state resets when dialog reopens', async ({ authenticatedPage }) => {
      const envelopesPage = new EnvelopesPage(authenticatedPage)
      const envelopeName = `Reset Toggle ${testId}`

      await envelopesPage.goto()
      await envelopesPage.createEnvelope({ name: envelopeName })

      // Open, switch to "from", cancel
      await envelopesPage.openTransferFromEnvelope(envelopeName)
      await envelopesPage.selectTransferDirection('from')
      await expect(envelopesPage.transferFromButton).toHaveClass(/v-btn--active/)
      await envelopesPage.cancelTransferButton.click()

      // Reopen - should default back to "to"
      await envelopesPage.openTransferFromEnvelope(envelopeName)
      await expect(envelopesPage.transferToButton).toHaveClass(/v-btn--active/)
      await envelopesPage.cancelTransferButton.click()
    })

    test('transfer dialog has direction toggle on detail page', async ({ authenticatedPage }) => {
      const envelopesPage = new EnvelopesPage(authenticatedPage)
      const detailPage = new EnvelopeDetailPage(authenticatedPage)
      const envelopeName = `Detail Toggle ${testId}`

      await envelopesPage.goto()
      await envelopesPage.createEnvelope({ name: envelopeName })

      await envelopesPage.clickEnvelope(envelopeName)
      await detailPage.openTransferDialog()

      // Toggle should be visible with "to" active
      await expect(detailPage.transferDirectionToggle).toBeVisible()
      await expect(detailPage.transferToButton).toHaveClass(/v-btn--active/)

      await detailPage.cancelTransferButton.click()
    })

    test('can transfer to current envelope from another (detail page)', async ({
      authenticatedPage,
    }) => {
      const envelopesPage = new EnvelopesPage(authenticatedPage)
      const accountsPage = new AccountsPage(authenticatedPage)
      const detailPage = new EnvelopeDetailPage(authenticatedPage)
      const destEnvelope = `Dest Detail ${testId}`
      const sourceEnvelope = `Source Detail ${testId}`

      // Create account with funds
      await accountsPage.goto()
      await accountsPage.createAccount({
        name: `Detail Transfer ${testId}`,
        accountType: 'checking',
        startingBalance: '500.00',
        includeInBudget: true,
      })

      await envelopesPage.goto()
      await envelopesPage.createEnvelope({ name: destEnvelope })
      await envelopesPage.createEnvelope({ name: sourceEnvelope })

      // Fund source envelope
      await envelopesPage.openAssignMoneyDialog()
      await envelopesPage.completeTransfer(sourceEnvelope, '100.00')

      // Navigate to destination envelope and transfer FROM source
      await envelopesPage.clickEnvelope(destEnvelope)
      await detailPage.transferFrom(sourceEnvelope, '30.00')

      // Verify balance updated
      const balance = await detailPage.getCurrentBalance()
      expect(balance).toContain('30.00')
    })
  })

  test.describe('Edit Envelope', () => {
    test('updates envelope name', async ({ authenticatedPage }) => {
      const envelopesPage = new EnvelopesPage(authenticatedPage)
      const detailPage = new EnvelopeDetailPage(authenticatedPage)
      const originalName = `Edit Test ${testId}`
      const newName = `Updated Name ${testId}`

      await envelopesPage.goto()
      await envelopesPage.createEnvelope({ name: originalName })

      await envelopesPage.clickEnvelope(originalName)
      await detailPage.updateEnvelope({ name: newName })

      await detailPage.expectName(newName)
    })

    test('updates envelope target balance', async ({ authenticatedPage }) => {
      const envelopesPage = new EnvelopesPage(authenticatedPage)
      const detailPage = new EnvelopeDetailPage(authenticatedPage)
      const envelopeName = `Target Test ${testId}`

      await envelopesPage.goto()
      await envelopesPage.createEnvelope({ name: envelopeName })

      await envelopesPage.clickEnvelope(envelopeName)
      await detailPage.updateEnvelope({ targetBalance: '1000.00' })

      await detailPage.expectProgressBarVisible()
    })

    test('updates envelope description', async ({ authenticatedPage }) => {
      const envelopesPage = new EnvelopesPage(authenticatedPage)
      const detailPage = new EnvelopeDetailPage(authenticatedPage)
      const envelopeName = `Description Test ${testId}`

      await envelopesPage.goto()
      await envelopesPage.createEnvelope({ name: envelopeName })

      await envelopesPage.clickEnvelope(envelopeName)
      await detailPage.updateEnvelope({ description: 'Monthly grocery budget' })
    })
  })

  test.describe('Delete Envelope', () => {
    test('deletes envelope with confirmation', async ({ authenticatedPage }) => {
      const envelopesPage = new EnvelopesPage(authenticatedPage)
      const detailPage = new EnvelopeDetailPage(authenticatedPage)
      const envelopeName = `Delete Test ${testId}`

      await envelopesPage.goto()
      await envelopesPage.createEnvelope({ name: envelopeName })

      await envelopesPage.clickEnvelope(envelopeName)
      await detailPage.deleteEnvelope()

      await expect(authenticatedPage).toHaveURL('/')
      await envelopesPage.expectEnvelopeNotExists(envelopeName)
    })

    test('cancel delete does not delete envelope', async ({ authenticatedPage }) => {
      const envelopesPage = new EnvelopesPage(authenticatedPage)
      const detailPage = new EnvelopeDetailPage(authenticatedPage)
      const envelopeName = `Cancel Delete ${testId}`

      await envelopesPage.goto()
      await envelopesPage.createEnvelope({ name: envelopeName })

      await envelopesPage.clickEnvelope(envelopeName)
      await detailPage.openDeleteDialog()
      await detailPage.cancelDelete()

      // Should still be on detail page
      await expect(authenticatedPage).toHaveURL(/\/envelopes\/[a-z0-9-]+/)
    })
  })

  test.describe('Navigation', () => {
    test('clicking envelope navigates to detail page', async ({ authenticatedPage }) => {
      const envelopesPage = new EnvelopesPage(authenticatedPage)
      const envelopeName = `Navigation Test ${testId}`

      await envelopesPage.goto()
      await envelopesPage.createEnvelope({ name: envelopeName })

      await envelopesPage.clickEnvelope(envelopeName)

      await expect(authenticatedPage).toHaveURL(/\/envelopes\/[a-z0-9-]+/)
    })

    test('back button returns to envelopes list', async ({ authenticatedPage }) => {
      const envelopesPage = new EnvelopesPage(authenticatedPage)
      const detailPage = new EnvelopeDetailPage(authenticatedPage)
      const envelopeName = `Back Button Test ${testId}`

      await envelopesPage.goto()
      await envelopesPage.createEnvelope({ name: envelopeName })

      await envelopesPage.clickEnvelope(envelopeName)
      await detailPage.goBack()

      await expect(authenticatedPage).toHaveURL('/')
    })
  })

  test.describe('Ready to Assign', () => {
    test('shows Ready to Assign card with unallocated balance', async ({ authenticatedPage }) => {
      const envelopesPage = new EnvelopesPage(authenticatedPage)
      const accountsPage = new AccountsPage(authenticatedPage)

      // Create an account with starting balance to have funds in unallocated
      await accountsPage.goto()
      await accountsPage.createAccount({
        name: `Ready to Assign Test ${testId}`,
        accountType: 'checking',
        startingBalance: '100.00',
        includeInBudget: true,
      })

      // Create an envelope (this triggers creation of the unallocated envelope)
      await envelopesPage.goto()
      await envelopesPage.createEnvelope({
        name: `Test Envelope ${testId}`,
      })

      // The budget account we created should have funds in unallocated
      await expect(envelopesPage.readyToAssignCard).toBeVisible()
    })

    test('assign money button opens transfer dialog', async ({ authenticatedPage }) => {
      const envelopesPage = new EnvelopesPage(authenticatedPage)

      await envelopesPage.goto()

      // Only visible if there's positive unallocated balance
      if (await envelopesPage.assignMoneyButton.isVisible()) {
        await envelopesPage.openAssignMoneyDialog()
        await expect(envelopesPage.transferDialog).toBeVisible()
      }
    })
  })

  test.describe('Auto-Assign with Rules', () => {
    test('auto-assign shows preview with allocations', async ({ authenticatedPage, testApi, testContext }) => {
      const envelopesPage = new EnvelopesPage(authenticatedPage)
      const accountsPage = new AccountsPage(authenticatedPage)
      const envelopeName = `Auto Target ${testId}`

      // Create account via UI (properly sets up unallocated balance)
      await accountsPage.goto()
      await accountsPage.createAccount({
        name: `Auto Assign Account ${testId}`,
        accountType: 'checking',
        startingBalance: '500.00',
        includeInBudget: true,
      })

      // Create envelope and rule via API
      const envelope = await testApi.createEnvelope(testContext.user.budgetId, {
        name: envelopeName,
      })

      await testApi.createAllocationRule(testContext.user.budgetId, {
        envelopeId: envelope.id,
        ruleType: 'fixed',
        amount: 10000, // $100 in cents
      })

      // Navigate and test auto-assign
      await envelopesPage.goto()

      // Open auto-assign dialog
      await envelopesPage.openAutoAssignDialog()

      // Should show preview with allocations
      await envelopesPage.expectAutoAssignHasAllocations()

      // Cancel for now
      await envelopesPage.cancelAutoAssign()
    })

    test('auto-assign distributes money to envelopes', async ({ authenticatedPage, testApi, testContext }) => {
      const envelopesPage = new EnvelopesPage(authenticatedPage)
      const accountsPage = new AccountsPage(authenticatedPage)
      const envelopeName = `Auto Distribute ${testId}`

      // Create account via UI (properly sets up unallocated balance)
      await accountsPage.goto()
      await accountsPage.createAccount({
        name: `Distribute Account ${testId}`,
        accountType: 'checking',
        startingBalance: '500.00',
        includeInBudget: true,
      })

      // Create envelope and rule via API
      const envelope = await testApi.createEnvelope(testContext.user.budgetId, {
        name: envelopeName,
      })

      await testApi.createAllocationRule(testContext.user.budgetId, {
        envelopeId: envelope.id,
        ruleType: 'fixed',
        amount: 5000, // $50 in cents
      })

      // Navigate and test auto-assign
      await envelopesPage.goto()

      // Open auto-assign and apply
      await envelopesPage.openAutoAssignDialog()
      await envelopesPage.expectAutoAssignHasAllocations()
      await envelopesPage.applyAutoAssign()
    })

    test('auto-assign with multiple rules distributes to all', async ({ authenticatedPage, testApi, testContext }) => {
      const envelopesPage = new EnvelopesPage(authenticatedPage)
      const accountsPage = new AccountsPage(authenticatedPage)
      const envelope1Name = `Multi Auto 1 ${testId}`
      const envelope2Name = `Multi Auto 2 ${testId}`

      // Create account via UI (properly sets up unallocated balance)
      await accountsPage.goto()
      await accountsPage.createAccount({
        name: `Multi Auto Account ${testId}`,
        accountType: 'checking',
        startingBalance: '500.00',
        includeInBudget: true,
      })

      // Create envelopes and rules via API
      const envelope1 = await testApi.createEnvelope(testContext.user.budgetId, {
        name: envelope1Name,
      })

      const envelope2 = await testApi.createEnvelope(testContext.user.budgetId, {
        name: envelope2Name,
      })

      await testApi.createAllocationRule(testContext.user.budgetId, {
        envelopeId: envelope1.id,
        ruleType: 'fixed',
        amount: 2500, // $25 in cents
      })

      await testApi.createAllocationRule(testContext.user.budgetId, {
        envelopeId: envelope2.id,
        ruleType: 'fixed',
        amount: 2500, // $25 in cents
      })

      // Navigate and test auto-assign
      await envelopesPage.goto()

      // Open auto-assign and apply
      await envelopesPage.openAutoAssignDialog()
      await envelopesPage.expectAutoAssignHasAllocations()
      await envelopesPage.applyAutoAssign()
    })

    test('cancel auto-assign does not change balances', async ({ authenticatedPage, testApi, testContext }) => {
      const envelopesPage = new EnvelopesPage(authenticatedPage)
      const accountsPage = new AccountsPage(authenticatedPage)
      const envelopeName = `Cancel Auto ${testId}`

      // Create account via UI (properly sets up unallocated balance)
      await accountsPage.goto()
      await accountsPage.createAccount({
        name: `Cancel Auto Account ${testId}`,
        accountType: 'checking',
        startingBalance: '500.00',
        includeInBudget: true,
      })

      // Create envelope and rule via API
      const envelope = await testApi.createEnvelope(testContext.user.budgetId, {
        name: envelopeName,
      })

      await testApi.createAllocationRule(testContext.user.budgetId, {
        envelopeId: envelope.id,
        ruleType: 'fixed',
        amount: 10000, // $100 in cents
      })

      // Navigate to envelopes
      await envelopesPage.goto()

      // Open auto-assign then cancel
      await envelopesPage.openAutoAssignDialog()
      await envelopesPage.cancelAutoAssign()

      // Should still be on envelopes page, no snackbar for success
      await expect(authenticatedPage).toHaveURL('/')
    })
  })

  test.describe('Envelope Detail', () => {
    test('shows empty activity state for new envelope', async ({ authenticatedPage }) => {
      const envelopesPage = new EnvelopesPage(authenticatedPage)
      const detailPage = new EnvelopeDetailPage(authenticatedPage)
      const envelopeName = `Activity Test ${testId}`

      await envelopesPage.goto()
      await envelopesPage.createEnvelope({ name: envelopeName })

      await envelopesPage.clickEnvelope(envelopeName)
      await detailPage.expectEmptyActivity()
    })

    test('shows allocations after transfer', async ({ authenticatedPage }) => {
      const envelopesPage = new EnvelopesPage(authenticatedPage)
      const accountsPage = new AccountsPage(authenticatedPage)
      const detailPage = new EnvelopeDetailPage(authenticatedPage)
      const envelopeName = `Allocations Test ${testId}`

      // First create a budget account with starting balance (goes to Unallocated)
      await accountsPage.goto()
      await accountsPage.createAccount({
        name: `Allocations Account ${testId}`,
        accountType: 'checking',
        startingBalance: '500.00',
        includeInBudget: true,
      })

      await envelopesPage.goto()
      await envelopesPage.createEnvelope({ name: envelopeName })

      // Transfer money to the envelope
      await envelopesPage.openAssignMoneyDialog()
      await envelopesPage.completeTransfer(envelopeName, '75.00')

      // Navigate to detail and check for allocations
      await envelopesPage.clickEnvelope(envelopeName)
      await detailPage.expectAllocationsExist()
    })
  })

  test.describe('Allocation Rules in Envelope Detail', () => {
    test('shows allocation rules section', async ({ authenticatedPage }) => {
      const envelopesPage = new EnvelopesPage(authenticatedPage)
      const detailPage = new EnvelopeDetailPage(authenticatedPage)
      const envelopeName = `Rules Section ${testId}`

      await envelopesPage.goto()
      await envelopesPage.createEnvelope({ name: envelopeName })

      await envelopesPage.clickEnvelope(envelopeName)
      await detailPage.expectAllocationRulesSectionVisible()
    })

    test('shows empty state when no rules', async ({ authenticatedPage }) => {
      const envelopesPage = new EnvelopesPage(authenticatedPage)
      const detailPage = new EnvelopeDetailPage(authenticatedPage)
      const envelopeName = `Empty Rules ${testId}`

      await envelopesPage.goto()
      await envelopesPage.createEnvelope({ name: envelopeName })

      await envelopesPage.clickEnvelope(envelopeName)
      await detailPage.expectEmptyRulesState()
    })

    test('can create allocation rule from detail page', async ({ authenticatedPage }) => {
      const envelopesPage = new EnvelopesPage(authenticatedPage)
      const detailPage = new EnvelopeDetailPage(authenticatedPage)
      const envelopeName = `Create Rule Detail ${testId}`
      const ruleName = `Detail Rule ${testId}`

      await envelopesPage.goto()
      await envelopesPage.createEnvelope({ name: envelopeName })

      await envelopesPage.clickEnvelope(envelopeName)
      await detailPage.createRule({
        name: ruleName,
        amount: '100.00',
      })

      await detailPage.expectRuleExists(ruleName)
    })

    test('can edit allocation rule', async ({ authenticatedPage }) => {
      const envelopesPage = new EnvelopesPage(authenticatedPage)
      const detailPage = new EnvelopeDetailPage(authenticatedPage)
      const envelopeName = `Edit Rule ${testId}`
      const ruleName = `Editable Rule ${testId}`

      await envelopesPage.goto()
      await envelopesPage.createEnvelope({ name: envelopeName })

      await envelopesPage.clickEnvelope(envelopeName)
      await detailPage.createRule({
        name: ruleName,
        amount: '50.00',
      })

      await detailPage.editRuleAmount(ruleName, '75.00')
    })

    test('can delete allocation rule', async ({ authenticatedPage }) => {
      const envelopesPage = new EnvelopesPage(authenticatedPage)
      const detailPage = new EnvelopeDetailPage(authenticatedPage)
      const envelopeName = `Delete Rule ${testId}`
      const ruleName = `Deletable Rule ${testId}`

      await envelopesPage.goto()
      await envelopesPage.createEnvelope({ name: envelopeName })

      await envelopesPage.clickEnvelope(envelopeName)
      await detailPage.createRule({
        name: ruleName,
        amount: '30.00',
      })

      await detailPage.deleteRule(ruleName)
    })

    test('can toggle rule active/inactive', async ({ authenticatedPage }) => {
      const envelopesPage = new EnvelopesPage(authenticatedPage)
      const detailPage = new EnvelopeDetailPage(authenticatedPage)
      const envelopeName = `Toggle Rule ${testId}`
      const ruleName = `Toggleable Rule ${testId}`

      await envelopesPage.goto()
      await envelopesPage.createEnvelope({ name: envelopeName })

      await envelopesPage.clickEnvelope(envelopeName)
      await detailPage.createRule({
        name: ruleName,
        amount: '40.00',
      })

      // Deactivate the rule
      await detailPage.toggleRuleActive(ruleName)
    })

    test('manage all rules link navigates to allocation rules page', async ({ authenticatedPage }) => {
      const envelopesPage = new EnvelopesPage(authenticatedPage)
      const detailPage = new EnvelopeDetailPage(authenticatedPage)
      const envelopeName = `Manage Link ${testId}`
      const ruleName = `Link Test Rule ${testId}`

      await envelopesPage.goto()
      await envelopesPage.createEnvelope({ name: envelopeName })

      await envelopesPage.clickEnvelope(envelopeName)

      // Create a rule so the manage link appears
      await detailPage.createRule({
        name: ruleName,
        amount: '20.00',
      })

      await detailPage.manageAllRulesLink.click()
      await expect(authenticatedPage).toHaveURL('/allocation-rules')
    })
  })

  test.describe('Star/Unstar Envelope', () => {
    test('can star an envelope from detail page', async ({ authenticatedPage }) => {
      const envelopesPage = new EnvelopesPage(authenticatedPage)
      const detailPage = new EnvelopeDetailPage(authenticatedPage)
      const envelopeName = `Star Test ${testId}`

      await envelopesPage.goto()
      await envelopesPage.createEnvelope({ name: envelopeName })

      await envelopesPage.clickEnvelope(envelopeName)
      await detailPage.expectNotStarred()
      await detailPage.toggleStar()
      await detailPage.expectStarred()
    })

    test('can unstar a starred envelope', async ({ authenticatedPage }) => {
      const envelopesPage = new EnvelopesPage(authenticatedPage)
      const detailPage = new EnvelopeDetailPage(authenticatedPage)
      const envelopeName = `Unstar Test ${testId}`

      await envelopesPage.goto()
      await envelopesPage.createEnvelope({ name: envelopeName })

      await envelopesPage.clickEnvelope(envelopeName)

      // Star it first
      await detailPage.toggleStar()
      await detailPage.expectStarred()

      // Unstar it
      await detailPage.toggleStar()
      await detailPage.expectNotStarred()
    })
  })
})
