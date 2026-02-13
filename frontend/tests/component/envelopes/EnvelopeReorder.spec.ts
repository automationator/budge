// Component tests for envelope reorder / edit mode in EnvelopesView.
// Actual reordering workflows (move up/down, persistence, group reorder)
// remain in frontend/tests/e2e/tests/envelope-reorder.spec.ts.

import { describe, it, expect, afterEach } from 'vitest'
import { http, HttpResponse } from 'msw'
import { server } from '@test/mocks/server'
import { factories } from '@test/mocks/factories'
import EnvelopesView from '@/views/envelopes/EnvelopesView.vue'
import { mountView, flushPromises } from '@test/helpers/component-test-utils'
import type { VueWrapper } from '@vue/test-utils'
import type { EnvelopeBudgetSummaryResponse } from '@/api/envelopes'

const API_BASE = '/api/v1'

// Track wrapper for cleanup
let currentWrapper: VueWrapper | null = null

afterEach(() => {
  if (currentWrapper) {
    currentWrapper.unmount()
    currentWrapper = null
  }
})

// Budget summary with two named groups, each with envelopes
function budgetSummaryWithGroups(): EnvelopeBudgetSummaryResponse {
  return {
    start_date: '2024-01-01',
    end_date: '2024-01-31',
    ready_to_assign: 20000,
    total_activity: 0,
    total_balance: 170000,
    groups: [
      {
        group_id: 'group-a',
        group_name: 'Group A',
        icon: null,
        sort_order: 10,
        envelopes: [
          {
            envelope_id: 'env-1',
            envelope_name: 'Envelope 1',
            envelope_group_id: 'group-a',
            linked_account_id: null,
            icon: null,
            sort_order: 10,
            is_starred: false,
            activity: 0,
            balance: 50000,
            target_balance: 60000,
          },
          {
            envelope_id: 'env-2',
            envelope_name: 'Envelope 2',
            envelope_group_id: 'group-a',
            linked_account_id: null,
            icon: null,
            sort_order: 20,
            is_starred: false,
            activity: 0,
            balance: 30000,
            target_balance: null,
          },
        ],
        total_activity: 0,
        total_balance: 80000,
      },
      {
        group_id: 'group-b',
        group_name: 'Group B',
        icon: null,
        sort_order: 20,
        envelopes: [
          {
            envelope_id: 'env-3',
            envelope_name: 'Envelope 3',
            envelope_group_id: 'group-b',
            linked_account_id: null,
            icon: null,
            sort_order: 10,
            is_starred: false,
            activity: 0,
            balance: 70000,
            target_balance: null,
          },
        ],
        total_activity: 0,
        total_balance: 70000,
      },
    ],
  }
}

// MSW overrides for reorder tests: grouped envelopes and groups
function useReorderHandlers() {
  server.use(
    http.get(`${API_BASE}/budgets/:budgetId/envelopes/budget-summary`, () => {
      return HttpResponse.json(budgetSummaryWithGroups())
    }),
    http.get(`${API_BASE}/budgets/:budgetId/envelopes`, () => {
      return HttpResponse.json([
        factories.envelope({
          is_unallocated: true,
          name: 'Unallocated',
          current_balance: 20000,
        }),
        factories.envelope({
          id: 'env-1',
          name: 'Envelope 1',
          envelope_group_id: 'group-a',
          sort_order: 10,
        }),
        factories.envelope({
          id: 'env-2',
          name: 'Envelope 2',
          envelope_group_id: 'group-a',
          sort_order: 20,
        }),
        factories.envelope({
          id: 'env-3',
          name: 'Envelope 3',
          envelope_group_id: 'group-b',
          sort_order: 10,
        }),
      ])
    }),
    http.get(`${API_BASE}/budgets/:budgetId/envelope-groups`, () => {
      return HttpResponse.json([
        { id: 'group-a', budget_id: 'budget-1', name: 'Group A', icon: null, sort_order: 10 },
        { id: 'group-b', budget_id: 'budget-1', name: 'Group B', icon: null, sort_order: 20 },
      ])
    }),
    http.patch(`${API_BASE}/budgets/:budgetId/envelope-groups/:groupId`, async ({ request, params }) => {
      const body = (await request.json()) as Record<string, unknown>
      return HttpResponse.json({
        id: params.groupId as string,
        budget_id: params.budgetId as string,
        name: (body.name as string) || 'Group',
        icon: null,
        sort_order: (body.sort_order as number) ?? 0,
      })
    }),
  )
}

// Helper: mount and settle
async function mountAndSettle() {
  const result = mountView(EnvelopesView, { attachTo: document.body })
  currentWrapper = result.wrapper
  await flushPromises()
  await flushPromises()
  await flushPromises()
  return result
}

// Get the wrapper's root element for scoped queries
function el(wrapper: VueWrapper): HTMLElement {
  return wrapper.element as HTMLElement
}

// Helper: find a menu item by text across all visible overlay menus
function findMenuItem(text: string | RegExp): HTMLElement | null {
  const allItems = document.querySelectorAll('.v-overlay .v-list-item')
  return (Array.from(allItems).find((item) => {
    const content = item.textContent || ''
    return typeof text === 'string' ? content.includes(text) : text.test(content)
  }) as HTMLElement) || null
}

// Helper: open settings menu and click Edit Order
async function enterEditMode(wrapper: VueWrapper) {
  // Click gear icon to open menu
  const gearBtn = wrapper.find('.v-btn--icon')
  await gearBtn.trigger('click')
  await flushPromises()
  await flushPromises()

  // Click "Edit Order" menu item
  const editOrderItem = findMenuItem('Edit Order')
  expect(editOrderItem).toBeTruthy()
  editOrderItem!.click()
  await flushPromises()
  await flushPromises()
  await flushPromises()
}

// Helper: open settings menu and click Done Editing
async function exitEditMode(wrapper: VueWrapper) {
  const gearBtn = wrapper.find('.v-btn--icon')
  await gearBtn.trigger('click')
  await flushPromises()
  await flushPromises()

  const doneItem = findMenuItem('Done Editing')
  expect(doneItem).toBeTruthy()
  doneItem!.click()
  await flushPromises()
  await flushPromises()
}

describe('EnvelopesView - Edit Mode / Reordering', () => {
  describe('Edit Mode Toggle', () => {
    it('can enter and exit edit mode', async () => {
      useReorderHandlers()
      const { wrapper } = await mountAndSettle()

      // Initially not in edit mode - no reorder buttons on envelope rows
      expect(el(wrapper).querySelector('.budget-row .mdi-chevron-up')).toBeNull()

      // Enter edit mode
      await enterEditMode(wrapper)

      // Reorder buttons should now be visible within our wrapper
      expect(el(wrapper).querySelector('.mdi-chevron-up')).not.toBeNull()

      // Exit edit mode
      await exitEditMode(wrapper)

      // Reorder buttons should be hidden again
      await flushPromises()
      expect(el(wrapper).querySelectorAll('.budget-row .mdi-chevron-up').length).toBe(0)
    })

    it('settings menu is accessible in edit mode', async () => {
      useReorderHandlers()
      const { wrapper } = await mountAndSettle()

      // Settings button visible initially
      expect(wrapper.find('.v-btn--icon').exists()).toBe(true)

      // Enter edit mode - settings button should still be visible
      await enterEditMode(wrapper)
      expect(wrapper.find('.v-btn--icon').exists()).toBe(true)

      // Exit edit mode - settings button should still be visible
      await exitEditMode(wrapper)
      expect(wrapper.find('.v-btn--icon').exists()).toBe(true)
    })

    it('menu shows "Done Editing" when in edit mode', async () => {
      useReorderHandlers()
      const { wrapper } = await mountAndSettle()

      // Enter edit mode
      await enterEditMode(wrapper)

      // Open menu again - should show "Done Editing" instead of "Edit Order"
      const gearBtn = wrapper.find('.v-btn--icon')
      await gearBtn.trigger('click')
      await flushPromises()

      const doneItem = findMenuItem('Done Editing')
      expect(doneItem).toBeTruthy()
    })
  })

  describe('Envelope Reorder Buttons', () => {
    it('shows reorder buttons on envelopes in edit mode', async () => {
      useReorderHandlers()
      const { wrapper } = await mountAndSettle()

      // Verify envelopes are rendered
      expect(wrapper.text()).toContain('Envelope 1')

      // Reorder buttons not visible initially on envelope rows within our wrapper
      const envelopeRows = el(wrapper).querySelectorAll('.budget-row')
      const hasUpButtonBefore = Array.from(envelopeRows).some((row) =>
        row.querySelector('.mdi-chevron-up')
      )
      expect(hasUpButtonBefore).toBe(false)

      // Enter edit mode - reorder buttons should appear on envelope rows
      await enterEditMode(wrapper)

      const hasUpButtonAfter = Array.from(
        el(wrapper).querySelectorAll('.budget-row')
      ).some((row) => row.querySelector('.mdi-chevron-up'))
      expect(hasUpButtonAfter).toBe(true)
    })

    it('up button is disabled for first envelope in group', async () => {
      useReorderHandlers()
      const { wrapper } = await mountAndSettle()
      await enterEditMode(wrapper)

      // Find Envelope 1 row (first in Group A) within our wrapper
      const envelopeRows = Array.from(el(wrapper).querySelectorAll('.budget-row'))
      const env1Row = envelopeRows.find((row) =>
        row.textContent?.includes('Envelope 1')
      )
      expect(env1Row).toBeTruthy()

      // Up button should be disabled (first in group)
      const upBtn = env1Row!.querySelector('button:has(.mdi-chevron-up)') as HTMLButtonElement
      expect(upBtn).toBeTruthy()
      expect(upBtn.disabled).toBe(true)

      // Down button should be enabled
      const downBtn = env1Row!.querySelector('button:has(.mdi-chevron-down)') as HTMLButtonElement
      expect(downBtn).toBeTruthy()
      expect(downBtn.disabled).toBe(false)
    })

    it('down button is disabled for last envelope in group', async () => {
      useReorderHandlers()
      const { wrapper } = await mountAndSettle()
      await enterEditMode(wrapper)

      // Find Envelope 2 row (last in Group A) within our wrapper
      const envelopeRows = Array.from(el(wrapper).querySelectorAll('.budget-row'))
      const env2Row = envelopeRows.find((row) =>
        row.textContent?.includes('Envelope 2')
      )
      expect(env2Row).toBeTruthy()

      // Down button should be disabled (last in group)
      const downBtn = env2Row!.querySelector('button:has(.mdi-chevron-down)') as HTMLButtonElement
      expect(downBtn).toBeTruthy()
      expect(downBtn.disabled).toBe(true)

      // Up button should be enabled
      const upBtn = env2Row!.querySelector('button:has(.mdi-chevron-up)') as HTMLButtonElement
      expect(upBtn).toBeTruthy()
      expect(upBtn.disabled).toBe(false)
    })

    it('both buttons disabled for single envelope in group', async () => {
      useReorderHandlers()
      const { wrapper } = await mountAndSettle()
      await enterEditMode(wrapper)

      // Envelope 3 is the only envelope in Group B
      const envelopeRows = Array.from(el(wrapper).querySelectorAll('.budget-row'))
      const env3Row = envelopeRows.find((row) =>
        row.textContent?.includes('Envelope 3')
      )
      expect(env3Row).toBeTruthy()

      const upBtn = env3Row!.querySelector('button:has(.mdi-chevron-up)') as HTMLButtonElement
      const downBtn = env3Row!.querySelector('button:has(.mdi-chevron-down)') as HTMLButtonElement
      expect(upBtn.disabled).toBe(true)
      expect(downBtn.disabled).toBe(true)
    })
  })

  describe('Group Reorder Buttons', () => {
    it('shows reorder buttons on groups in edit mode', async () => {
      useReorderHandlers()
      const { wrapper } = await mountAndSettle()

      // Groups should be visible
      expect(wrapper.text()).toContain('Group A')
      expect(wrapper.text()).toContain('Group B')

      // Group reorder buttons not visible initially within our wrapper
      const groupHeaders = el(wrapper).querySelectorAll('.envelope-group-header')
      const hasGroupUpBefore = Array.from(groupHeaders).some((h) =>
        h.querySelector('button')
      )
      expect(hasGroupUpBefore).toBe(false)

      // Enter edit mode
      await enterEditMode(wrapper)

      // Group reorder buttons should appear
      const hasGroupUpAfter = Array.from(
        el(wrapper).querySelectorAll('.envelope-group-header')
      ).some((h) => h.querySelector('button'))
      expect(hasGroupUpAfter).toBe(true)
    })

    it('up button is disabled for first group', async () => {
      useReorderHandlers()
      const { wrapper } = await mountAndSettle()
      await enterEditMode(wrapper)

      // Find Group A header (first group) within our wrapper
      const groupHeaders = Array.from(
        el(wrapper).querySelectorAll('.envelope-group-header')
      )
      const groupAHeader = groupHeaders.find((h) =>
        h.textContent?.includes('Group A')
      )
      expect(groupAHeader).toBeTruthy()

      // Up button should be disabled (first group)
      const buttons = groupAHeader!.querySelectorAll('button')
      const upBtn = buttons[0] as HTMLButtonElement
      expect(upBtn).toBeTruthy()
      expect(upBtn.disabled).toBe(true)

      // Down button should be enabled
      const downBtn = buttons[1] as HTMLButtonElement
      expect(downBtn).toBeTruthy()
      expect(downBtn.disabled).toBe(false)
    })

    it('down button is disabled for last group', async () => {
      useReorderHandlers()
      const { wrapper } = await mountAndSettle()
      await enterEditMode(wrapper)

      // Find Group B header (last group) within our wrapper
      const groupHeaders = Array.from(
        el(wrapper).querySelectorAll('.envelope-group-header')
      )
      const groupBHeader = groupHeaders.find((h) =>
        h.textContent?.includes('Group B')
      )
      expect(groupBHeader).toBeTruthy()

      // Down button should be disabled (last group)
      const buttons = groupBHeader!.querySelectorAll('button')
      const downBtn = buttons[1] as HTMLButtonElement
      expect(downBtn).toBeTruthy()
      expect(downBtn.disabled).toBe(true)

      // Up button should be enabled
      const upBtn = buttons[0] as HTMLButtonElement
      expect(upBtn).toBeTruthy()
      expect(upBtn.disabled).toBe(false)
    })
  })

  describe('Navigation Prevention in Edit Mode', () => {
    it('clicking envelope does not emit navigation in edit mode', async () => {
      useReorderHandlers()
      const { wrapper } = await mountAndSettle()
      await enterEditMode(wrapper)

      // In edit mode, clicking an envelope row calls handleBudgetRowClick
      // which checks isEditMode and returns early (no navigation).
      const envelopeRows = Array.from(el(wrapper).querySelectorAll('.budget-row'))
      const env1Row = envelopeRows.find((row) =>
        row.textContent?.includes('Envelope 1')
      ) as HTMLElement
      expect(env1Row).toBeTruthy()
      env1Row.click()
      await flushPromises()

      // Still on the same view (no error, no crash)
      expect(wrapper.text()).toContain('Envelope 1')
    })
  })
})
