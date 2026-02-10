import { test, expect } from '../fixtures/test-setup'
import { EnvelopesPage } from '../pages/envelopes.page'

// Note: Basic visibility and content tests are covered by component tests in
// tests/unit/components/envelopes/OverspentAlert.spec.ts
// This file only contains E2E tests for integration behavior that requires real API calls.

test.describe('Overspent Envelopes Alert', () => {
  test.describe('Envelopes Page', () => {
    test('clicking CTA opens transfer dialog with amount pre-filled', async ({
      authenticatedPage,
      testApi,
      testContext,
    }) => {
      const testId = Date.now()

      // Create an overspent envelope
      const account = await testApi.createAccount(testContext.user.budgetId, {
        name: `Checking ${testId}`,
        startingBalance: 10000,
      })

      const envelope = await testApi.createEnvelope(testContext.user.budgetId, {
        name: `Overspent ${testId}`,
      })

      // Overspend by $50
      await testApi.createTransaction(testContext.user.budgetId, {
        accountId: account.id,
        envelopeId: envelope.id,
        amount: -5000, // -$50
      })

      const envelopesPage = new EnvelopesPage(authenticatedPage)
      await envelopesPage.goto()

      await envelopesPage.expectOverspentAlertVisible()

      // Click the CTA button - should open transfer dialog
      await envelopesPage.clickCoverOverspending()

      // Transfer dialog should be visible
      await expect(envelopesPage.transferDialog).toBeVisible()

      // The dialog should show "Cover overspending" context
      await expect(envelopesPage.transferDialog).toContainText('Cover overspending')

      // The amount should be pre-filled with the overspent amount ($50.00)
      await expect(envelopesPage.transferAmountInput).toHaveValue('50.00')
    })
  })
})
