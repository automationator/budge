// UI rendering tests for the EnvelopesView.
// Data-mutation tests (CRUD, transfers, auto-assign, reorder)
// remain in frontend/tests/e2e/tests/envelopes.spec.ts.

import { describe, it, expect } from 'vitest'
import { http, HttpResponse } from 'msw'
import { server } from '@test/mocks/server'
import { factories } from '@test/mocks/factories'
import EnvelopesView from '@/views/envelopes/EnvelopesView.vue'
import { mountView, flushPromises } from '@test/helpers/component-test-utils'
import type { EnvelopeBudgetSummaryResponse } from '@/api/envelopes'

const API_BASE = '/api/v1'

// Helper: mount and settle
async function mountAndSettle<T extends Parameters<typeof mountView>[0]>(
  component: T,
  options?: Parameters<typeof mountView>[1]
) {
  const result = mountView(component, options)
  await flushPromises()
  await flushPromises()
  await flushPromises()
  return result
}

describe('EnvelopesView', () => {
  it('displays page title', async () => {
    const { wrapper } = await mountAndSettle(EnvelopesView)
    expect(wrapper.find('h1').text()).toBe('Envelopes')
  })

  it('shows settings menu with options', async () => {
    const { wrapper } = await mountAndSettle(EnvelopesView, { attachTo: document.body })

    // Click gear icon to open menu
    const gearBtn = wrapper.find('.v-btn--icon')
    await gearBtn.trigger('click')
    await flushPromises()

    const body = document.body
    expect(body.textContent).toContain('Add Envelope')
    expect(body.textContent).toContain('Add Envelope Group')
    expect(body.textContent).toContain('Edit Order')
    wrapper.unmount()
  })

  it('shows Ready to Assign card', async () => {
    const { wrapper } = await mountAndSettle(EnvelopesView)
    expect(wrapper.text()).toContain('Ready to Assign')
  })

  it('shows Assign Money button when positive balance', async () => {
    const { wrapper } = await mountAndSettle(EnvelopesView)
    const assignBtn = wrapper.findAll('.v-btn').find((b) => b.text().includes('Assign Money'))
    expect(assignBtn).toBeTruthy()
  })

  it('shows empty state when no envelopes', async () => {
    server.use(
      http.get(`${API_BASE}/budgets/:budgetId/envelopes`, () => {
        return HttpResponse.json([])
      }),
      http.get(`${API_BASE}/budgets/:budgetId/envelopes/budget-summary`, () => {
        return HttpResponse.json({
          start_date: '2024-01-01',
          end_date: '2024-01-31',
          ready_to_assign: 0,
          total_activity: 0,
          total_balance: 0,
          groups: [],
        } satisfies EnvelopeBudgetSummaryResponse)
      })
    )

    const { wrapper } = await mountAndSettle(EnvelopesView)
    expect(wrapper.text()).toContain('No envelopes yet')
    expect(wrapper.text()).toContain('Create Envelope')
  })

  it('shows budget summary groups with envelopes', async () => {
    const { wrapper } = await mountAndSettle(EnvelopesView)
    // Default handler has a group with Groceries and Rent
    expect(wrapper.text()).toContain('Groceries')
    expect(wrapper.text()).toContain('Rent')
  })

  it('shows Activity and Balance column headers', async () => {
    const { wrapper } = await mountAndSettle(EnvelopesView)
    expect(wrapper.text()).toContain('Activity')
    expect(wrapper.text()).toContain('Balance')
  })

  it('can open create envelope dialog', async () => {
    const { wrapper } = await mountAndSettle(EnvelopesView, { attachTo: document.body })

    // Open settings menu
    const gearBtn = wrapper.find('.v-btn--icon')
    await gearBtn.trigger('click')
    await flushPromises()

    // Click "Add Envelope"
    const menuItems = document.querySelectorAll('.v-overlay--active .v-list-item')
    const addEnvelopeItem = Array.from(menuItems).find((item) =>
      item.textContent?.includes('Add Envelope')
    ) as HTMLElement
    expect(addEnvelopeItem).toBeTruthy()
    addEnvelopeItem.click()
    await flushPromises()

    // Dialog should show form fields
    const body = document.body
    expect(body.textContent).toContain('Create Envelope')
    expect(body.innerHTML).toContain('Envelope Name')
    expect(body.innerHTML).toContain('Icon (emoji)')
    expect(body.innerHTML).toContain('Group (optional)')
    expect(body.innerHTML).toContain('Target Balance')
    expect(body.textContent).toContain('Add allocation rule')
    wrapper.unmount()
  })

  it('create envelope button is disabled without name', async () => {
    const { wrapper } = await mountAndSettle(EnvelopesView, { attachTo: document.body })

    // Open settings menu
    const gearBtn = wrapper.find('.v-btn--icon')
    await gearBtn.trigger('click')
    await flushPromises()

    // Click "Add Envelope"
    const menuItems = document.querySelectorAll('.v-overlay--active .v-list-item')
    const addEnvelopeItem = Array.from(menuItems).find((item) =>
      item.textContent?.includes('Add Envelope')
    ) as HTMLElement
    addEnvelopeItem.click()
    await flushPromises()

    // Create button should be disabled (no name entered)
    const dialogButtons = document.querySelectorAll('.v-dialog .v-btn')
    const createBtn = Array.from(dialogButtons).find(
      (b) => b.textContent?.trim() === 'Create'
    ) as HTMLButtonElement
    expect(createBtn).toBeTruthy()
    expect(createBtn.disabled).toBe(true)
    wrapper.unmount()
  })

  it('shows duplicate envelope name error', async () => {
    const { wrapper } = await mountAndSettle(EnvelopesView, { attachTo: document.body })

    // Store already has "Groceries" from MSW handler

    // Open create envelope dialog
    const gearBtn = wrapper.find('.v-btn--icon')
    await gearBtn.trigger('click')
    await flushPromises()

    const menuItems = document.querySelectorAll('.v-overlay--active .v-list-item')
    const addEnvelopeItem = Array.from(menuItems).find((item) =>
      item.textContent?.includes('Add Envelope')
    ) as HTMLElement
    addEnvelopeItem.click()
    await flushPromises()

    // Find the first input in the dialog (Envelope Name) and set its value
    const nameInput = document.querySelector('.v-dialog input') as HTMLInputElement
    expect(nameInput).toBeTruthy()

    // Simulate native input event to trigger Vue's v-model
    const nativeInputEvent = new Event('input', { bubbles: true })
    Object.defineProperty(nameInput, 'value', { writable: true, value: 'Groceries' })
    nameInput.value = 'Groceries'
    nameInput.dispatchEvent(nativeInputEvent)
    await flushPromises()

    expect(document.body.textContent).toContain('An envelope with this name already exists')
    wrapper.unmount()
  })

  it('can open create group dialog', async () => {
    const { wrapper } = await mountAndSettle(EnvelopesView, { attachTo: document.body })

    // Open settings menu
    const gearBtn = wrapper.find('.v-btn--icon')
    await gearBtn.trigger('click')
    await flushPromises()

    // Click "Add Envelope Group"
    const menuItems = document.querySelectorAll('.v-overlay--active .v-list-item')
    const addGroupItem = Array.from(menuItems).find((item) =>
      item.textContent?.includes('Add Envelope Group')
    ) as HTMLElement
    expect(addGroupItem).toBeTruthy()
    addGroupItem.click()
    await flushPromises()

    const body = document.body
    expect(body.textContent).toContain('Create Group')
    expect(body.innerHTML).toContain('Group Name')
    wrapper.unmount()
  })

  it('create group button is disabled without name', async () => {
    const { wrapper } = await mountAndSettle(EnvelopesView, { attachTo: document.body })

    // Open settings menu
    const gearBtn = wrapper.find('.v-btn--icon')
    await gearBtn.trigger('click')
    await flushPromises()

    // Click "Add Envelope Group"
    const menuItems = document.querySelectorAll('.v-overlay--active .v-list-item')
    const addGroupItem = Array.from(menuItems).find((item) =>
      item.textContent?.includes('Add Envelope Group')
    ) as HTMLElement
    addGroupItem.click()
    await flushPromises()

    // Create button should be disabled
    const dialogButtons = document.querySelectorAll('.v-dialog .v-btn')
    const createBtn = Array.from(dialogButtons).find(
      (b) => b.textContent?.trim() === 'Create'
    ) as HTMLButtonElement
    expect(createBtn).toBeTruthy()
    expect(createBtn.disabled).toBe(true)
    wrapper.unmount()
  })

  it('can cancel create group dialog', async () => {
    const { wrapper } = await mountAndSettle(EnvelopesView, { attachTo: document.body })

    // Open settings menu
    const gearBtn = wrapper.find('.v-btn--icon')
    await gearBtn.trigger('click')
    await flushPromises()

    // Click "Add Envelope Group"
    const menuItems = document.querySelectorAll('.v-overlay--active .v-list-item')
    const addGroupItem = Array.from(menuItems).find((item) =>
      item.textContent?.includes('Add Envelope Group')
    ) as HTMLElement
    addGroupItem.click()
    await flushPromises()

    // Cancel
    const dialogButtons = document.querySelectorAll('.v-dialog .v-btn')
    const cancelBtn = Array.from(dialogButtons).find(
      (b) => b.textContent?.trim() === 'Cancel'
    ) as HTMLElement
    expect(cancelBtn).toBeTruthy()
    cancelBtn.click()
    await flushPromises()

    const dialogOverlay = document.querySelector('.v-overlay--active .v-dialog')
    expect(dialogOverlay).toBeNull()
    wrapper.unmount()
  })

  describe('Credit Card Envelopes', () => {
    it('shows Credit Cards group when CC envelopes exist in summary', async () => {
      server.use(
        http.get(`${API_BASE}/budgets/:budgetId/envelopes/budget-summary`, () => {
          return HttpResponse.json({
            start_date: '2024-01-01',
            end_date: '2024-01-31',
            ready_to_assign: 20000,
            total_activity: 0,
            total_balance: 55000,
            groups: [
              {
                group_id: null,
                group_name: null,
                icon: null,
                sort_order: 0,
                envelopes: [
                  {
                    envelope_id: 'envelope-1',
                    envelope_name: 'Groceries',
                    envelope_group_id: null,
                    linked_account_id: null,
                    icon: null,
                    sort_order: 0,
                    is_starred: false,
                    activity: 0,
                    balance: 50000,
                    target_balance: 60000,
                  },
                ],
                total_activity: 0,
                total_balance: 50000,
              },
              {
                group_id: 'cc-group',
                group_name: 'Credit Cards',
                icon: 'mdi-credit-card',
                sort_order: 999,
                envelopes: [
                  {
                    envelope_id: 'cc-envelope-1',
                    envelope_name: 'My Visa',
                    envelope_group_id: 'cc-group',
                    linked_account_id: 'cc-account-1',
                    icon: null,
                    sort_order: 0,
                    is_starred: false,
                    activity: -5000,
                    balance: 5000,
                    target_balance: null,
                  },
                ],
                total_activity: -5000,
                total_balance: 5000,
              },
            ],
          } satisfies EnvelopeBudgetSummaryResponse)
        }),
        http.get(`${API_BASE}/budgets/:budgetId/envelopes`, () => {
          return HttpResponse.json([
            factories.envelope({ is_unallocated: true, name: 'Unallocated', current_balance: 20000 }),
            factories.envelope(),
            factories.envelope({
              id: 'cc-envelope-1',
              name: 'My Visa',
              linked_account_id: 'cc-account-1',
            }),
          ])
        })
      )

      const { wrapper } = await mountAndSettle(EnvelopesView)
      expect(wrapper.text()).toContain('Credit Cards')
      expect(wrapper.text()).toContain('My Visa')
    })

    it('disables inline balance edit for CC envelopes', async () => {
      server.use(
        http.get(`${API_BASE}/budgets/:budgetId/envelopes/budget-summary`, () => {
          return HttpResponse.json({
            start_date: '2024-01-01',
            end_date: '2024-01-31',
            ready_to_assign: 20000,
            total_activity: 0,
            total_balance: 5000,
            groups: [
              {
                group_id: 'cc-group',
                group_name: 'Credit Cards',
                icon: 'mdi-credit-card',
                sort_order: 0,
                envelopes: [
                  {
                    envelope_id: 'cc-envelope-1',
                    envelope_name: 'My Visa',
                    envelope_group_id: 'cc-group',
                    linked_account_id: 'cc-account-1',
                    icon: null,
                    sort_order: 0,
                    is_starred: false,
                    activity: -5000,
                    balance: 5000,
                    target_balance: null,
                  },
                ],
                total_activity: -5000,
                total_balance: 5000,
              },
            ],
          } satisfies EnvelopeBudgetSummaryResponse)
        }),
        http.get(`${API_BASE}/budgets/:budgetId/envelopes`, () => {
          return HttpResponse.json([
            factories.envelope({ is_unallocated: true, name: 'Unallocated', current_balance: 20000 }),
            factories.envelope({
              id: 'cc-envelope-1',
              name: 'My Visa',
              linked_account_id: 'cc-account-1',
            }),
          ])
        })
      )

      const { wrapper } = await mountAndSettle(EnvelopesView)
      const budgetRow = wrapper.findComponent({ name: 'EnvelopeBudgetRow' })
      expect(budgetRow.exists()).toBe(true)

      // CC envelopes should have inline edit disabled
      const inlineEdit = budgetRow.findComponent({ name: 'InlineMoneyEdit' })
      expect(inlineEdit.exists()).toBe(true)
      expect(inlineEdit.props('editable')).toBe(false)
    })

    it('hides Add Transaction button for CC envelopes', async () => {
      server.use(
        http.get(`${API_BASE}/budgets/:budgetId/envelopes/budget-summary`, () => {
          return HttpResponse.json({
            start_date: '2024-01-01',
            end_date: '2024-01-31',
            ready_to_assign: 20000,
            total_activity: 0,
            total_balance: 5000,
            groups: [
              {
                group_id: 'cc-group',
                group_name: 'Credit Cards',
                icon: 'mdi-credit-card',
                sort_order: 0,
                envelopes: [
                  {
                    envelope_id: 'cc-envelope-1',
                    envelope_name: 'My Visa',
                    envelope_group_id: 'cc-group',
                    linked_account_id: 'cc-account-1',
                    icon: null,
                    sort_order: 0,
                    is_starred: false,
                    activity: -5000,
                    balance: 5000,
                    target_balance: null,
                  },
                ],
                total_activity: -5000,
                total_balance: 5000,
              },
            ],
          } satisfies EnvelopeBudgetSummaryResponse)
        }),
        http.get(`${API_BASE}/budgets/:budgetId/envelopes`, () => {
          return HttpResponse.json([
            factories.envelope({ is_unallocated: true, name: 'Unallocated', current_balance: 20000 }),
            factories.envelope({
              id: 'cc-envelope-1',
              name: 'My Visa',
              linked_account_id: 'cc-account-1',
            }),
          ])
        })
      )

      const { wrapper } = await mountAndSettle(EnvelopesView)
      const budgetRow = wrapper.findComponent({ name: 'EnvelopeBudgetRow' })
      expect(budgetRow.exists()).toBe(true)

      // CC envelopes should not have Add Transaction button (mdi-plus)
      const addTxnBtn = budgetRow.findAll('.v-btn').find((b) => b.html().includes('mdi-plus'))
      expect(addTxnBtn).toBeUndefined()
    })
  })
})
