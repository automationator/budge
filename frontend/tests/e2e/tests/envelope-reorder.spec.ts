import { test } from '../fixtures/test-setup'
import { EnvelopesPage } from '../pages/envelopes.page'

// Edit mode UI tests (toggle, button visibility, disabled states, navigation prevention)
// have been migrated to unit/components/envelopes/EnvelopeReorder.spec.ts

test.describe('Envelope Reordering', () => {
  test.describe('Envelope Reordering', () => {
    test('can move envelope up within a group', async ({ authenticatedPage, testApi, testContext }) => {
      // Use unique group name to avoid interference from other tests
      const groupName = 'Move Up Group'
      // Create test data: Group with 3 envelopes
      await testApi.createEnvelope(testContext.user.budgetId, {
        name: 'MoveUp A',
        groupName,
      })
      await testApi.createEnvelope(testContext.user.budgetId, {
        name: 'MoveUp B',
        groupName,
      })
      await testApi.createEnvelope(testContext.user.budgetId, {
        name: 'MoveUp C',
        groupName,
      })

      const envelopesPage = new EnvelopesPage(authenticatedPage)
      await envelopesPage.goto()

      // Enter edit mode
      await envelopesPage.enterEditMode()

      // Move MoveUp B up (should become first)
      await envelopesPage.moveEnvelopeUp('MoveUp B')

      // Verify order changed
      await envelopesPage.expectEnvelopeOrderInGroup(groupName, [
        'MoveUp B',
        'MoveUp A',
        'MoveUp C',
      ])

      // Exit and refresh to verify persistence
      await envelopesPage.exitEditMode()
      await envelopesPage.goto()
      await envelopesPage.expectEnvelopeOrderInGroup(groupName, [
        'MoveUp B',
        'MoveUp A',
        'MoveUp C',
      ])
    })

    test('can move envelope down within a group', async ({ authenticatedPage, testApi, testContext }) => {
      // Use unique group name to avoid interference from other tests
      const groupName = 'Move Down Group'
      // Create test data: Group with 3 envelopes
      await testApi.createEnvelope(testContext.user.budgetId, {
        name: 'MoveDown A',
        groupName,
      })
      await testApi.createEnvelope(testContext.user.budgetId, {
        name: 'MoveDown B',
        groupName,
      })
      await testApi.createEnvelope(testContext.user.budgetId, {
        name: 'MoveDown C',
        groupName,
      })

      const envelopesPage = new EnvelopesPage(authenticatedPage)
      await envelopesPage.goto()

      // Enter edit mode
      await envelopesPage.enterEditMode()

      // Move MoveDown A down (should become second)
      await envelopesPage.moveEnvelopeDown('MoveDown A')

      // Verify order changed
      await envelopesPage.expectEnvelopeOrderInGroup(groupName, [
        'MoveDown B',
        'MoveDown A',
        'MoveDown C',
      ])
    })
  })

  test.describe('Group Reordering', () => {
    test('can move group up', async ({ authenticatedPage, testApi, testContext }) => {
      // Create test data: 3 groups with unique names
      await testApi.createEnvelopeGroup(testContext.user.budgetId, 'GrpUp A')
      await testApi.createEnvelopeGroup(testContext.user.budgetId, 'GrpUp B')
      await testApi.createEnvelopeGroup(testContext.user.budgetId, 'GrpUp C')
      await testApi.createEnvelope(testContext.user.budgetId, {
        name: 'Envelope in GrpUp A',
        groupName: 'GrpUp A',
      })
      await testApi.createEnvelope(testContext.user.budgetId, {
        name: 'Envelope in GrpUp B',
        groupName: 'GrpUp B',
      })
      await testApi.createEnvelope(testContext.user.budgetId, {
        name: 'Envelope in GrpUp C',
        groupName: 'GrpUp C',
      })

      const envelopesPage = new EnvelopesPage(authenticatedPage)
      await envelopesPage.goto()

      // Enter edit mode
      await envelopesPage.enterEditMode()

      // Move GrpUp B up (should become first among these 3)
      await envelopesPage.moveGroupUp('GrpUp B')

      // Verify relative order changed - B should now be before A
      await envelopesPage.expectGroupContains(['GrpUp B', 'GrpUp A', 'GrpUp C'])

      // Exit and refresh to verify persistence
      await envelopesPage.exitEditMode()
      await envelopesPage.goto()
      await envelopesPage.expectGroupContains(['GrpUp B', 'GrpUp A', 'GrpUp C'])
    })

    test('can move group down', async ({ authenticatedPage, testApi, testContext }) => {
      // Create test data: 3 groups with unique names
      await testApi.createEnvelopeGroup(testContext.user.budgetId, 'GrpDn A')
      await testApi.createEnvelopeGroup(testContext.user.budgetId, 'GrpDn B')
      await testApi.createEnvelopeGroup(testContext.user.budgetId, 'GrpDn C')
      await testApi.createEnvelope(testContext.user.budgetId, {
        name: 'Envelope in GrpDn A',
        groupName: 'GrpDn A',
      })
      await testApi.createEnvelope(testContext.user.budgetId, {
        name: 'Envelope in GrpDn B',
        groupName: 'GrpDn B',
      })
      await testApi.createEnvelope(testContext.user.budgetId, {
        name: 'Envelope in GrpDn C',
        groupName: 'GrpDn C',
      })

      const envelopesPage = new EnvelopesPage(authenticatedPage)
      await envelopesPage.goto()

      // Enter edit mode
      await envelopesPage.enterEditMode()

      // Move GrpDn A down (should become second among these 3)
      await envelopesPage.moveGroupDown('GrpDn A')

      // Verify relative order changed - B should now be before A
      await envelopesPage.expectGroupContains(['GrpDn B', 'GrpDn A', 'GrpDn C'])
    })
  })
})
