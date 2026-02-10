// Action sheet tests (tapping, options, transitions, dismissal) have been migrated to
// frontend/tests/unit/components/envelopes/EnvelopesMobile.spec.ts
// These remaining tests verify CSS @media behavior which requires a real layout engine.

import { test } from '../fixtures/test-setup'
import { EnvelopesPage } from '../pages/envelopes.page'

// Generate unique names for this test run
const testId = Date.now()

test.describe('Envelopes Mobile', () => {
  test.describe('Mobile Layout', () => {
    test('activity column is hidden on mobile', async ({ authenticatedPage, testApi, testContext }) => {
      // Create an envelope via API to ensure we have data to display
      await testApi.createEnvelope(testContext.user.budgetId, {
        name: `Layout Test ${testId}`,
      })

      const envelopesPage = new EnvelopesPage(authenticatedPage)
      await envelopesPage.goto()

      // Verify activity column is hidden on mobile viewport
      await envelopesPage.expectActivityColumnHidden()
    })

    test('action buttons are hidden on mobile', async ({ authenticatedPage, testApi, testContext }) => {
      await testApi.createEnvelope(testContext.user.budgetId, {
        name: `Action Buttons Test ${testId}`,
      })

      const envelopesPage = new EnvelopesPage(authenticatedPage)
      await envelopesPage.goto()

      // Verify action buttons are hidden on mobile viewport
      await envelopesPage.expectActionButtonsHidden()
    })

    test('balance column remains visible', async ({ authenticatedPage, testApi, testContext }) => {
      await testApi.createEnvelope(testContext.user.budgetId, {
        name: `Columns Test ${testId}`,
      })

      const envelopesPage = new EnvelopesPage(authenticatedPage)
      await envelopesPage.goto()

      // Verify balance column is visible
      await envelopesPage.expectBalanceColumnVisible()
    })
  })
})
