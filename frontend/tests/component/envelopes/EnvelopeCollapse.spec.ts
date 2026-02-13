// Component tests for envelope group collapse/expand behavior.
// Converted from frontend/tests/e2e/tests/envelope-collapse.spec.ts.

import { describe, it, expect } from 'vitest'
import { http, HttpResponse } from 'msw'
import { server } from '@test/mocks/server'
import EnvelopesView from '@/views/envelopes/EnvelopesView.vue'
import { mountView, flushPromises } from '@test/helpers/component-test-utils'
import { useEnvelopesStore } from '@/stores/envelopes'
import type { EnvelopeBudgetSummaryResponse } from '@/api/envelopes'

const API_BASE = '/api/v1'

// Budget summary with two named groups + an ungrouped ("Other") section
function makeBudgetSummary(
  groups: Array<{
    group_id: string | null
    group_name: string | null
    envelopes: Array<{ id: string; name: string }>
  }>
): EnvelopeBudgetSummaryResponse {
  return {
    start_date: '2024-01-01',
    end_date: '2024-01-31',
    ready_to_assign: 20000,
    total_activity: 0,
    total_balance: 170000,
    groups: groups.map((g, gi) => ({
      group_id: g.group_id,
      group_name: g.group_name,
      icon: null,
      sort_order: gi * 10,
      envelopes: g.envelopes.map((e, ei) => ({
        envelope_id: e.id,
        envelope_name: e.name,
        envelope_group_id: g.group_id,
        linked_account_id: null,
        icon: null,
        sort_order: ei * 10,
        is_starred: false,
        activity: 0,
        balance: 50000,
        target_balance: null,
      })),
      total_activity: 0,
      total_balance: 50000 * g.envelopes.length,
    })),
  }
}

// Two named groups with one envelope each
const twoGroupsSummary = makeBudgetSummary([
  { group_id: 'group-1', group_name: 'Group A', envelopes: [{ id: 'env-a', name: 'Envelope A' }] },
  { group_id: 'group-2', group_name: 'Group B', envelopes: [{ id: 'env-b', name: 'Envelope B' }] },
])

// One ungrouped ("Other") section
const otherGroupSummary = makeBudgetSummary([
  { group_id: null, group_name: null, envelopes: [{ id: 'env-u', name: 'Ungrouped Envelope' }] },
])

function setupHandlers(summary: EnvelopeBudgetSummaryResponse) {
  server.use(
    http.get(`${API_BASE}/budgets/:budgetId/envelopes/budget-summary`, () => {
      return HttpResponse.json(summary)
    }),
    http.get(`${API_BASE}/budgets/:budgetId/envelope-groups`, () => {
      const groups = summary.groups
        .filter((g) => g.group_id !== null)
        .map((g) => ({
          id: g.group_id,
          budget_id: 'budget-1',
          name: g.group_name,
          icon: null,
          sort_order: g.sort_order,
        }))
      return HttpResponse.json(groups)
    })
  )
}

// Helper: mount and wait for async data
async function mountAndSettle(options?: { localStorage?: Record<string, string> }) {
  if (options?.localStorage) {
    for (const [key, value] of Object.entries(options.localStorage)) {
      window.localStorage.setItem(key, value)
    }
  }
  const result = mountView(EnvelopesView)
  await flushPromises()
  await flushPromises()
  await flushPromises()
  return result
}

// Get the group header element
function getGroupHeader(wrapper: ReturnType<typeof mountView>['wrapper'], groupName: string) {
  const headers = wrapper.findAll('.envelope-group-header')
  return headers.find((h) => h.text().includes(groupName))!
}

// Check if a group's chevron has the collapsed class
function isChevronCollapsed(wrapper: ReturnType<typeof mountView>['wrapper'], groupName: string) {
  const header = getGroupHeader(wrapper, groupName)
  const chevron = header.find('.collapse-chevron')
  return chevron.classes().includes('rotate-collapsed')
}

describe('Envelope Group Collapse', () => {
  it('groups are expanded by default', async () => {
    setupHandlers(twoGroupsSummary)
    const { wrapper } = await mountAndSettle()

    expect(isChevronCollapsed(wrapper, 'Group A')).toBe(false)
    expect(isChevronCollapsed(wrapper, 'Group B')).toBe(false)
  })

  it('can collapse and expand a named group', async () => {
    setupHandlers(twoGroupsSummary)
    const { wrapper } = await mountAndSettle()

    // Initially expanded
    expect(isChevronCollapsed(wrapper, 'Group A')).toBe(false)

    // Collapse
    await getGroupHeader(wrapper, 'Group A').trigger('click')
    await flushPromises()
    expect(isChevronCollapsed(wrapper, 'Group A')).toBe(true)

    // Expand again
    await getGroupHeader(wrapper, 'Group A').trigger('click')
    await flushPromises()
    expect(isChevronCollapsed(wrapper, 'Group A')).toBe(false)
  })

  it('collapse state persists via localStorage', async () => {
    setupHandlers(twoGroupsSummary)
    const { wrapper } = await mountAndSettle()

    // Collapse Group A
    await getGroupHeader(wrapper, 'Group A').trigger('click')
    await flushPromises()
    expect(isChevronCollapsed(wrapper, 'Group A')).toBe(true)

    // Verify localStorage was written
    expect(localStorage.setItem).toHaveBeenCalledWith(
      'budge:envelopes:collapsed',
      expect.stringContaining('group-1')
    )

    // Get the stored value for remounting
    const storedValue = localStorage.getItem('budge:envelopes:collapsed')!

    // Remount with stored localStorage value
    wrapper.unmount()
    const { wrapper: wrapper2 } = await mountAndSettle({
      localStorage: { 'budge:envelopes:collapsed': storedValue },
    })

    // Group A should still be collapsed after remount
    expect(isChevronCollapsed(wrapper2, 'Group A')).toBe(true)
    // Group B should still be expanded
    expect(isChevronCollapsed(wrapper2, 'Group B')).toBe(false)
    wrapper2.unmount()
  })

  it('can collapse Other section', async () => {
    setupHandlers(otherGroupSummary)
    const { wrapper } = await mountAndSettle()

    // Other section should be expanded by default
    expect(isChevronCollapsed(wrapper, 'Other')).toBe(false)

    // Collapse
    await getGroupHeader(wrapper, 'Other').trigger('click')
    await flushPromises()
    expect(isChevronCollapsed(wrapper, 'Other')).toBe(true)

    // Expand again
    await getGroupHeader(wrapper, 'Other').trigger('click')
    await flushPromises()
    expect(isChevronCollapsed(wrapper, 'Other')).toBe(false)
  })

  it('collapse works in edit mode', async () => {
    setupHandlers(twoGroupsSummary)

    // Add PATCH handler for envelope-groups (needed by initializeSortOrders)
    server.use(
      http.patch(`${API_BASE}/budgets/:budgetId/envelope-groups/:groupId`, async ({ request, params }) => {
        const body = (await request.json()) as Record<string, unknown>
        return HttpResponse.json({
          id: params.groupId,
          budget_id: params.budgetId,
          name: 'Group',
          icon: null,
          sort_order: body.sort_order ?? 0,
        })
      })
    )

    const { wrapper, pinia } = await mountAndSettle()
    const store = useEnvelopesStore(pinia)

    // Enter edit mode
    store.isEditMode = true
    await flushPromises()

    // Should still be able to collapse
    await getGroupHeader(wrapper, 'Group A').trigger('click')
    await flushPromises()
    expect(isChevronCollapsed(wrapper, 'Group A')).toBe(true)

    // Exit edit mode
    store.isEditMode = false
    await flushPromises()

    // Should remain collapsed
    expect(isChevronCollapsed(wrapper, 'Group A')).toBe(true)
  })

  it('reorder buttons do not trigger collapse (click.stop)', async () => {
    setupHandlers(twoGroupsSummary)

    // Add handlers needed for reorder actions
    server.use(
      http.patch(`${API_BASE}/budgets/:budgetId/envelope-groups/:groupId`, async ({ request, params }) => {
        const body = (await request.json()) as Record<string, unknown>
        return HttpResponse.json({
          id: params.groupId,
          budget_id: params.budgetId,
          name: 'Group',
          icon: null,
          sort_order: body.sort_order ?? 0,
        })
      })
    )

    const { wrapper, pinia } = await mountAndSettle()
    const store = useEnvelopesStore(pinia)

    // Enter edit mode to show reorder buttons
    store.isEditMode = true
    await flushPromises()

    // Both groups should be expanded
    expect(isChevronCollapsed(wrapper, 'Group A')).toBe(false)
    expect(isChevronCollapsed(wrapper, 'Group B')).toBe(false)

    // Find the down button on Group A's header
    const headerA = getGroupHeader(wrapper, 'Group A')
    const buttons = headerA.findAll('button')
    // In edit mode, group headers show up/down buttons - the second button is "down"
    const downButton = buttons.find((b) => b.find('.mdi-chevron-down').exists())
    expect(downButton).toBeTruthy()

    // Click the reorder button - the @click.stop should prevent collapse
    await downButton!.trigger('click')
    await flushPromises()

    // Group A should still be expanded (not collapsed by the button click)
    expect(isChevronCollapsed(wrapper, 'Group A')).toBe(false)
  })

  it('multiple groups can be collapsed independently', async () => {
    setupHandlers(twoGroupsSummary)
    const { wrapper } = await mountAndSettle()

    // Both expanded initially
    expect(isChevronCollapsed(wrapper, 'Group A')).toBe(false)
    expect(isChevronCollapsed(wrapper, 'Group B')).toBe(false)

    // Collapse Group A only
    await getGroupHeader(wrapper, 'Group A').trigger('click')
    await flushPromises()
    expect(isChevronCollapsed(wrapper, 'Group A')).toBe(true)
    expect(isChevronCollapsed(wrapper, 'Group B')).toBe(false)

    // Collapse Group B as well
    await getGroupHeader(wrapper, 'Group B').trigger('click')
    await flushPromises()
    expect(isChevronCollapsed(wrapper, 'Group A')).toBe(true)
    expect(isChevronCollapsed(wrapper, 'Group B')).toBe(true)

    // Expand Group A
    await getGroupHeader(wrapper, 'Group A').trigger('click')
    await flushPromises()
    expect(isChevronCollapsed(wrapper, 'Group A')).toBe(false)
    expect(isChevronCollapsed(wrapper, 'Group B')).toBe(true)
  })
})
