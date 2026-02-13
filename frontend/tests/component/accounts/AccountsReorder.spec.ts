// Component tests for account reorder / edit mode in AccountsView.
// Actual reordering workflows (move up/down, persistence, cross-section isolation)
// remain in frontend/tests/e2e/tests/account-reorder.spec.ts.

import { describe, it, expect, afterEach } from 'vitest'
import { http, HttpResponse } from 'msw'
import { server } from '@test/mocks/server'
import { factories } from '@test/mocks/factories'
import AccountsView from '@/views/accounts/AccountsView.vue'
import { mountView, flushPromises } from '@test/helpers/component-test-utils'
import type { VueWrapper } from '@vue/test-utils'

const API_BASE = '/api/v1'

// Track wrapper for cleanup
let currentWrapper: VueWrapper | null = null

afterEach(() => {
  if (currentWrapper) {
    currentWrapper.unmount()
    currentWrapper = null
  }
})

// MSW overrides: 3 budget accounts + 1 tracking account, all with nonzero sort_order
function useReorderHandlers() {
  server.use(
    http.get(`${API_BASE}/budgets/:budgetId/accounts`, () => {
      return HttpResponse.json([
        factories.budgetAccount({ id: 'acc-1', name: 'Budget Checking', sort_order: 10 }),
        factories.budgetAccount({ id: 'acc-2', name: 'Budget Savings', sort_order: 20 }),
        factories.budgetAccount({ id: 'acc-3', name: 'Budget Cash', sort_order: 30 }),
        factories.offBudgetAccount({ id: 'acc-4', name: 'Tracking Investment', sort_order: 10 }),
      ])
    }),
  )
}

// Helper: mount and settle
async function mountAndSettle() {
  const result = mountView(AccountsView, { attachTo: document.body })
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

// Helper: enter edit mode by clicking the edit-order button
async function enterEditMode(wrapper: VueWrapper) {
  const editBtn = wrapper.find('[data-testid="edit-order-button"]')
  expect(editBtn.exists()).toBe(true)
  await editBtn.trigger('click')
  await flushPromises()
  await flushPromises()
  await flushPromises()
}

// Helper: exit edit mode by clicking the done button
async function exitEditMode(wrapper: VueWrapper) {
  const doneBtn = wrapper.find('[data-testid="edit-order-button"]')
  expect(doneBtn.exists()).toBe(true)
  await doneBtn.trigger('click')
  await flushPromises()
  await flushPromises()
}

describe('AccountsView - Edit Mode / Reordering', () => {
  describe('Edit Mode Toggle', () => {
    it('can enter and exit edit mode', async () => {
      useReorderHandlers()
      const { wrapper } = await mountAndSettle()

      // Initially shows "Edit Order" button, no reorder buttons
      const editBtn = wrapper.find('[data-testid="edit-order-button"]')
      expect(editBtn.text()).toContain('Edit Order')
      expect(el(wrapper).querySelector('[data-testid="move-up-button"]')).toBeNull()

      // Enter edit mode
      await enterEditMode(wrapper)

      // Button text should change to "Done"
      expect(wrapper.find('[data-testid="edit-order-button"]').text()).toContain('Done')
      // Reorder buttons should be visible
      expect(el(wrapper).querySelector('[data-testid="move-up-button"]')).not.toBeNull()

      // Exit edit mode
      await exitEditMode(wrapper)

      // Button should revert to "Edit Order"
      expect(wrapper.find('[data-testid="edit-order-button"]').text()).toContain('Edit Order')
      // Reorder buttons should be hidden
      await flushPromises()
      expect(el(wrapper).querySelector('[data-testid="move-up-button"]')).toBeNull()
    })

    it('hides add button in edit mode', async () => {
      useReorderHandlers()
      const { wrapper } = await mountAndSettle()

      // Add button visible initially
      expect(wrapper.find('[data-testid="add-account-button"]').exists()).toBe(true)

      // Enter edit mode - add button should be hidden
      await enterEditMode(wrapper)
      expect(wrapper.find('[data-testid="add-account-button"]').exists()).toBe(false)

      // Exit edit mode - add button should reappear
      await exitEditMode(wrapper)
      expect(wrapper.find('[data-testid="add-account-button"]').exists()).toBe(true)
    })
  })

  describe('Account Reorder Buttons', () => {
    it('shows reorder buttons on accounts in edit mode', async () => {
      useReorderHandlers()
      const { wrapper } = await mountAndSettle()

      // Verify accounts are rendered
      expect(wrapper.text()).toContain('Budget Checking')

      // Reorder buttons not visible initially
      expect(wrapper.findAll('[data-testid="move-up-button"]').length).toBe(0)
      expect(wrapper.findAll('[data-testid="move-down-button"]').length).toBe(0)

      // Enter edit mode - reorder buttons should appear
      await enterEditMode(wrapper)

      // Should have up/down buttons for each account (3 budget + 1 tracking = 4 each)
      expect(wrapper.findAll('[data-testid="move-up-button"]').length).toBe(4)
      expect(wrapper.findAll('[data-testid="move-down-button"]').length).toBe(4)
    })

    it('up button is disabled for first budget account', async () => {
      useReorderHandlers()
      const { wrapper } = await mountAndSettle()
      await enterEditMode(wrapper)

      // Find the first budget account item
      const budgetItems = wrapper.findAll('[data-testid="budget-account-item"]')
      expect(budgetItems.length).toBe(3)

      // First item: "Budget Checking" - up button should be disabled
      const firstItem = budgetItems[0]!
      expect(firstItem.text()).toContain('Budget Checking')

      const upBtn = firstItem.find('[data-testid="move-up-button"]')
      expect(upBtn.exists()).toBe(true)
      expect((upBtn.element as HTMLButtonElement).disabled).toBe(true)

      // Down button should be enabled
      const downBtn = firstItem.find('[data-testid="move-down-button"]')
      expect(downBtn.exists()).toBe(true)
      expect((downBtn.element as HTMLButtonElement).disabled).toBe(false)
    })
  })

  describe('Navigation Prevention in Edit Mode', () => {
    it('clicking account does not navigate when in edit mode', async () => {
      useReorderHandlers()
      const { wrapper } = await mountAndSettle()
      await enterEditMode(wrapper)

      // In edit mode, account items should NOT have a "to" prop (router-link)
      const budgetItems = wrapper.findAll('[data-testid="budget-account-item"]')
      expect(budgetItems.length).toBeGreaterThan(0)

      // The v-list-item's `:to` binding is `undefined` in edit mode,
      // which means no <a href> or router-link is rendered
      const firstItem = budgetItems[0]!
      const link = firstItem.element.closest('a')
      // In edit mode, there should be no anchor tag wrapping the item
      // (Vuetify renders v-list-item as <div> when no `to` prop)
      expect(link).toBeNull()
    })
  })
})
