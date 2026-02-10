import { test, expect } from '../fixtures/test-setup'
import { AllocationRulesPage } from '../pages/allocation-rules.page'
import { EnvelopesPage } from '../pages/envelopes.page'

// Test context is set up automatically via fixtures
// - Database is reset per worker
// - User is created once per file

// Generate unique ID for test-created data
const testId = Date.now()

test.describe('Allocation Rules', () => {
  test.describe('Create Rules', () => {
    test('creates a fixed amount rule', async ({ authenticatedPage }) => {
      const allocationRulesPage = new AllocationRulesPage(authenticatedPage)
      const envelopesPage = new EnvelopesPage(authenticatedPage)

      // Create an envelope first
      const envelopeName = `Fixed Envelope ${testId}`
      await envelopesPage.goto()
      await envelopesPage.createEnvelope({ name: envelopeName })

      const ruleName = `Fixed Rule ${testId}`

      await allocationRulesPage.goto()
      await allocationRulesPage.createFixedRule({
        envelope: envelopeName,
        amount: '100.00',
        name: ruleName,
      })

      await allocationRulesPage.expectRuleExists(ruleName)
    })

    test('creates a percentage rule', async ({ authenticatedPage }) => {
      const allocationRulesPage = new AllocationRulesPage(authenticatedPage)
      const envelopesPage = new EnvelopesPage(authenticatedPage)

      // Create an envelope first
      const envelopeName = `Pct Envelope ${testId}`
      await envelopesPage.goto()
      await envelopesPage.createEnvelope({ name: envelopeName })

      const ruleName = `Percentage Rule ${testId}`

      await allocationRulesPage.goto()
      await allocationRulesPage.createPercentageRule({
        envelope: envelopeName,
        percentage: '10',
        name: ruleName,
      })

      await allocationRulesPage.expectRuleExists(ruleName)
    })

    test('creates a remainder rule', async ({ authenticatedPage }) => {
      const allocationRulesPage = new AllocationRulesPage(authenticatedPage)
      const envelopesPage = new EnvelopesPage(authenticatedPage)

      // Create an envelope first
      const envelopeName = `Remainder Envelope ${testId}`
      await envelopesPage.goto()
      await envelopesPage.createEnvelope({ name: envelopeName })

      const ruleName = `Remainder Rule ${testId}`

      await allocationRulesPage.goto()
      await allocationRulesPage.createRemainderRule({
        envelope: envelopeName,
        weight: '1',
        name: ruleName,
      })

      await allocationRulesPage.expectRuleExists(ruleName)
    })

    test('creates a period cap rule', async ({ authenticatedPage }) => {
      const allocationRulesPage = new AllocationRulesPage(authenticatedPage)
      const envelopesPage = new EnvelopesPage(authenticatedPage)

      // Create an envelope first
      const envelopeName = `Cap Envelope ${testId}`
      await envelopesPage.goto()
      await envelopesPage.createEnvelope({ name: envelopeName })

      const ruleName = `Period Cap Rule ${testId}`

      await allocationRulesPage.goto()
      await allocationRulesPage.createPeriodCapRule({
        envelope: envelopeName,
        amount: '200.00',
        periodUnit: 'Month(s)',
        name: ruleName,
      })

      await allocationRulesPage.expectRuleExists(ruleName)
      // Verify it shows the period cap format
      const ruleItem = allocationRulesPage.getRuleItem(ruleName)
      await expect(ruleItem).toContainText('Period Cap')
      await expect(ruleItem).toContainText('$200.00')
    })

  })

  test.describe('Edit Rules', () => {
    test('edits rule amount', async ({ authenticatedPage }) => {
      const allocationRulesPage = new AllocationRulesPage(authenticatedPage)
      const envelopesPage = new EnvelopesPage(authenticatedPage)

      // Create an envelope first
      const envelopeName = `Edit Envelope ${testId}`
      await envelopesPage.goto()
      await envelopesPage.createEnvelope({ name: envelopeName })

      const ruleName = `Edit Test ${testId}`

      await allocationRulesPage.goto()

      // Create a rule to edit
      await allocationRulesPage.createFixedRule({
        envelope: envelopeName,
        amount: '50.00',
        name: ruleName,
      })

      // Edit it
      await allocationRulesPage.openEditDialog(ruleName)
      await allocationRulesPage.amountInput.clear()
      await allocationRulesPage.amountInput.fill('75.00')
      await allocationRulesPage.saveButton.click()

      await expect(allocationRulesPage.formDialog).toBeHidden({ timeout: 10000 })
    })
  })

  test.describe('Delete Rules', () => {
    test('deletes a rule', async ({ authenticatedPage }) => {
      const allocationRulesPage = new AllocationRulesPage(authenticatedPage)
      const envelopesPage = new EnvelopesPage(authenticatedPage)

      // Create an envelope first
      const envelopeName = `Delete Envelope ${testId}`
      await envelopesPage.goto()
      await envelopesPage.createEnvelope({ name: envelopeName })

      const ruleName = `Delete Test ${testId}`

      await allocationRulesPage.goto()

      // Create a rule to delete
      await allocationRulesPage.createFixedRule({
        envelope: envelopeName,
        amount: '25.00',
        name: ruleName,
      })

      // Delete it
      await allocationRulesPage.deleteRule(ruleName)
    })

    test('cancel delete does not delete', async ({ authenticatedPage }) => {
      const allocationRulesPage = new AllocationRulesPage(authenticatedPage)
      const envelopesPage = new EnvelopesPage(authenticatedPage)

      // Create an envelope first
      const envelopeName = `Cancel Del Envelope ${testId}`
      await envelopesPage.goto()
      await envelopesPage.createEnvelope({ name: envelopeName })

      const ruleName = `Cancel Delete ${testId}`

      await allocationRulesPage.goto()

      // Create a rule
      await allocationRulesPage.createFixedRule({
        envelope: envelopeName,
        amount: '15.00',
        name: ruleName,
      })

      // Open delete dialog then cancel
      await allocationRulesPage.openDeleteDialog(ruleName)
      await allocationRulesPage.cancelDeleteButton.click()

      await expect(allocationRulesPage.deleteDialog).toBeHidden()
      // Item should still exist
      await allocationRulesPage.expectRuleExists(ruleName)
    })
  })

  test.describe('Activate/Deactivate', () => {
    test('deactivates and activates a rule', async ({ authenticatedPage }) => {
      const allocationRulesPage = new AllocationRulesPage(authenticatedPage)
      const envelopesPage = new EnvelopesPage(authenticatedPage)

      // Create an envelope first
      const envelopeName = `Toggle Envelope ${testId}`
      await envelopesPage.goto()
      await envelopesPage.createEnvelope({ name: envelopeName })

      const ruleName = `Toggle Test ${testId}`

      await allocationRulesPage.goto()

      // Create a rule
      await allocationRulesPage.createFixedRule({
        envelope: envelopeName,
        amount: '30.00',
        name: ruleName,
      })

      // Deactivate it
      await allocationRulesPage.toggleRuleActive(ruleName)

      // Enable "Show inactive" to see the paused item
      await allocationRulesPage.toggleShowInactive()

      // Check it shows as inactive
      const isInactive = await allocationRulesPage.isRuleInactive(ruleName)
      expect(isInactive).toBe(true)

      // Activate it
      await allocationRulesPage.toggleRuleActive(ruleName)
    })
  })

  test.describe('Summary Cards', () => {
    test('active rules count updates', async ({ authenticatedPage }) => {
      const allocationRulesPage = new AllocationRulesPage(authenticatedPage)
      const envelopesPage = new EnvelopesPage(authenticatedPage)

      // Create an envelope first
      const envelopeName = `Count Envelope ${testId}`
      await envelopesPage.goto()
      await envelopesPage.createEnvelope({ name: envelopeName })

      const ruleName = `Count Test ${testId}`

      await allocationRulesPage.goto()

      const initialCount = await allocationRulesPage.getActiveRulesCount()

      // Create a rule
      await allocationRulesPage.createFixedRule({
        envelope: envelopeName,
        amount: '5.00',
        name: ruleName,
      })

      // Count should increase
      const newCount = await allocationRulesPage.getActiveRulesCount()
      expect(parseInt(newCount)).toBeGreaterThan(parseInt(initialCount))
    })
  })

  test.describe('Filtering', () => {
    test('toggle show inactive shows deactivated rules', async ({ authenticatedPage }) => {
      const allocationRulesPage = new AllocationRulesPage(authenticatedPage)
      const envelopesPage = new EnvelopesPage(authenticatedPage)

      // Create an envelope first
      const envelopeName = `Inactive Envelope ${testId}`
      await envelopesPage.goto()
      await envelopesPage.createEnvelope({ name: envelopeName })

      const ruleName = `Filter Inactive ${testId}`

      await allocationRulesPage.goto()

      // Create and deactivate a rule
      await allocationRulesPage.createFixedRule({
        envelope: envelopeName,
        amount: '10.00',
        name: ruleName,
      })

      await allocationRulesPage.toggleRuleActive(ruleName)

      // Toggle show inactive
      await allocationRulesPage.toggleShowInactive()

      // Inactive item should be visible
      const isInactive = await allocationRulesPage.isRuleInactive(ruleName)
      expect(isInactive).toBe(true)
    })

    test('filter by envelope shows only matching rules', async ({ authenticatedPage }) => {
      const allocationRulesPage = new AllocationRulesPage(authenticatedPage)
      const envelopesPage = new EnvelopesPage(authenticatedPage)

      // Create two envelopes
      const envelope1 = `Filter Env1 ${testId}`
      const envelope2 = `Filter Env2 ${testId}`

      await envelopesPage.goto()
      await envelopesPage.createEnvelope({ name: envelope1 })
      await envelopesPage.createEnvelope({ name: envelope2 })

      const ruleForEnv1 = `Env1 Rule ${testId}`
      const ruleForEnv2 = `Env2 Rule ${testId}`

      await allocationRulesPage.goto()

      // Create rules for different envelopes
      await allocationRulesPage.createFixedRule({
        envelope: envelope1,
        amount: '20.00',
        name: ruleForEnv1,
      })

      await allocationRulesPage.createFixedRule({
        envelope: envelope2,
        amount: '30.00',
        name: ruleForEnv2,
      })

      // Filter by envelope 1
      await allocationRulesPage.filterByEnvelope(envelope1)

      // Only rule for envelope 1 should be visible
      await allocationRulesPage.expectRuleExists(ruleForEnv1)
      await allocationRulesPage.expectRuleNotExists(ruleForEnv2)

      // Clear filter
      await allocationRulesPage.filterByEnvelope(null)

      // Both rules should be visible
      await allocationRulesPage.expectRuleExists(ruleForEnv1)
      await allocationRulesPage.expectRuleExists(ruleForEnv2)
    })
  })

  test.describe('Preview', () => {
    test('preview shows allocation distribution', async ({ authenticatedPage }) => {
      const allocationRulesPage = new AllocationRulesPage(authenticatedPage)
      const envelopesPage = new EnvelopesPage(authenticatedPage)

      // Create an envelope first
      const envelopeName = `Preview Envelope ${testId}`
      await envelopesPage.goto()
      await envelopesPage.createEnvelope({ name: envelopeName })

      const ruleName = `Preview Test ${testId}`

      await allocationRulesPage.goto()

      // Create a rule
      await allocationRulesPage.createFixedRule({
        envelope: envelopeName,
        amount: '100.00',
        name: ruleName,
      })

      // Run preview
      await allocationRulesPage.runPreview('1000.00')

      // Preview table should be visible with results
      await expect(allocationRulesPage.previewTable).toBeVisible()
    })
  })

  test.describe('Respect Target Balance', () => {
    test('creates a fixed rule with respect target enabled', async ({ authenticatedPage }) => {
      const allocationRulesPage = new AllocationRulesPage(authenticatedPage)
      const envelopesPage = new EnvelopesPage(authenticatedPage)

      // Create an envelope with target balance
      const envelopeName = `Target Fixed Env ${testId}`
      await envelopesPage.goto()
      await envelopesPage.createEnvelope({
        name: envelopeName,
        targetBalance: '500.00',
      })

      const ruleName = `Respect Target Fixed ${testId}`

      await allocationRulesPage.goto()
      await allocationRulesPage.createFixedRule({
        envelope: envelopeName,
        amount: '200.00',
        name: ruleName,
        respectTarget: true,
      })

      await allocationRulesPage.expectRuleExists(ruleName)
    })

    test('creates a percentage rule with respect target enabled', async ({ authenticatedPage }) => {
      const allocationRulesPage = new AllocationRulesPage(authenticatedPage)
      const envelopesPage = new EnvelopesPage(authenticatedPage)

      // Create an envelope with target balance
      const envelopeName = `Target Pct Env ${testId}`
      await envelopesPage.goto()
      await envelopesPage.createEnvelope({
        name: envelopeName,
        targetBalance: '1000.00',
      })

      const ruleName = `Respect Target Pct ${testId}`

      await allocationRulesPage.goto()
      await allocationRulesPage.createPercentageRule({
        envelope: envelopeName,
        percentage: '15',
        name: ruleName,
        respectTarget: true,
      })

      await allocationRulesPage.expectRuleExists(ruleName)
    })

    test('creates a remainder rule with respect target enabled', async ({ authenticatedPage }) => {
      const allocationRulesPage = new AllocationRulesPage(authenticatedPage)
      const envelopesPage = new EnvelopesPage(authenticatedPage)

      // Create an envelope with target balance
      const envelopeName = `Target Rem Env ${testId}`
      await envelopesPage.goto()
      await envelopesPage.createEnvelope({
        name: envelopeName,
        targetBalance: '2000.00',
      })

      const ruleName = `Respect Target Rem ${testId}`

      await allocationRulesPage.goto()
      await allocationRulesPage.createRemainderRule({
        envelope: envelopeName,
        weight: '1',
        name: ruleName,
        respectTarget: true,
      })

      await allocationRulesPage.expectRuleExists(ruleName)
    })

  })
})
