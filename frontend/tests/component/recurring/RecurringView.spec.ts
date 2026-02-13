// UI rendering tests for RecurringView.
// Data-mutation tests (CRUD, pause/resume, delete with scheduled)
// remain in frontend/tests/e2e/tests/recurring.spec.ts.

import { describe, it, expect } from 'vitest'
import { http, HttpResponse } from 'msw'
import { server } from '@test/mocks/server'
import RecurringView from '@/views/recurring/RecurringView.vue'
import { mountView, flushPromises } from '@test/helpers/component-test-utils'

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

describe('RecurringView', () => {
  it('displays page title', async () => {
    const { wrapper } = await mountAndSettle(RecurringView)
    expect(wrapper.find('h1').text()).toBe('Recurring Transactions')
  })

  it('shows Add Recurring button', async () => {
    const { wrapper } = await mountAndSettle(RecurringView)
    const addBtn = wrapper.findAll('.v-btn').find((b) => b.text().includes('Add Recurring'))
    expect(addBtn).toBeTruthy()
  })

  it('add recurring button opens form dialog', async () => {
    const { wrapper } = await mountAndSettle(RecurringView, { attachTo: document.body })

    const addBtn = wrapper.findAll('.v-btn').find((b) => b.text().includes('Add Recurring'))
    await addBtn!.trigger('click')
    await flushPromises()

    expect(document.body.textContent).toContain('New Recurring Transaction')
    wrapper.unmount()
  })

  it('shows summary cards with correct labels', async () => {
    const { wrapper } = await mountAndSettle(RecurringView)

    const text = wrapper.text()
    expect(text).toContain('Monthly Expenses')
    expect(text).toContain('Monthly Income')
    expect(text).toContain('Net Monthly')
    expect(text).toContain('Active Rules')

    // Default MSW data: 2 active recurring (expense + income), 1 inactive
    const cards = wrapper.findAll('.v-card .text-h6')
    const cardValues = cards.map((c) => c.text())
    expect(cardValues).toContain('2') // Active Rules count
  })

  it('create button is disabled without required fields', async () => {
    const { wrapper } = await mountAndSettle(RecurringView, { attachTo: document.body })

    const addBtn = wrapper.findAll('.v-btn').find((b) => b.text().includes('Add Recurring'))
    await addBtn!.trigger('click')
    await flushPromises()

    const dialogButtons = document.querySelectorAll('.v-dialog .v-btn')
    const createBtn = Array.from(dialogButtons).find(
      (b) => b.textContent?.trim() === 'Create'
    ) as HTMLButtonElement
    expect(createBtn).toBeTruthy()
    expect(createBtn.disabled).toBe(true)
    wrapper.unmount()
  })

  it('renders recurring list with payee names, amounts, and frequency', async () => {
    const { wrapper } = await mountAndSettle(RecurringView)

    const text = wrapper.text()
    // Default MSW: active expense (payee-1 = "Grocery Store", -$50), active income (payee-2, +$2000)
    expect(text).toContain('Grocery Store')
    expect(text).toContain('$50.00')
    expect(text).toContain('$2,000.00')
    expect(text).toContain('Monthly')
  })

  it('shows empty state when no recurring transactions', async () => {
    server.use(
      http.get(`${API_BASE}/budgets/:budgetId/recurring-transactions`, () => {
        return HttpResponse.json([])
      })
    )

    const { wrapper } = await mountAndSettle(RecurringView)

    expect(wrapper.text()).toContain('No recurring transactions yet.')
    expect(wrapper.text()).toContain('Add Recurring Transaction')
  })

  it('shows Paused chip on inactive recurring when show inactive is enabled', async () => {
    const { wrapper } = await mountAndSettle(RecurringView)

    // Toggle "Show inactive" switch
    const switchEl = wrapper.find('.v-switch')
    await switchEl.find('input').setValue(true)
    await flushPromises()
    await flushPromises()

    // Now the inactive recurring should appear with "Paused" chip
    expect(wrapper.text()).toContain('Paused')
  })

  it('form dialog title changes between create and edit mode', async () => {
    const { wrapper } = await mountAndSettle(RecurringView, { attachTo: document.body })

    // Open create dialog
    const addBtn = wrapper.findAll('.v-btn').find((b) => b.text().includes('Add Recurring'))
    await addBtn!.trigger('click')
    await flushPromises()

    expect(document.body.textContent).toContain('New Recurring Transaction')

    // Close dialog
    const cancelBtns = document.querySelectorAll('.v-dialog .v-btn')
    const cancelBtn = Array.from(cancelBtns).find(
      (b) => b.textContent?.trim() === 'Cancel'
    ) as HTMLElement
    cancelBtn.click()
    await flushPromises()

    // Open edit dialog via three-dot menu on first item
    const menuBtns = wrapper.findAll('.v-list-item .v-btn')
    const dotsBtn = menuBtns.find((b) => b.find('.mdi-dots-vertical').exists())
    expect(dotsBtn).toBeTruthy()
    await dotsBtn!.trigger('click')
    await flushPromises()

    const menuItems = document.querySelectorAll('.v-overlay--active .v-list-item')
    const editItem = Array.from(menuItems).find((item) =>
      item.textContent?.includes('Edit')
    ) as HTMLElement
    expect(editItem).toBeTruthy()
    editItem.click()
    await flushPromises()

    expect(document.body.textContent).toContain('Edit Recurring Transaction')
    wrapper.unmount()
  })

  it('delete dialog opens and cancel closes it', async () => {
    const { wrapper } = await mountAndSettle(RecurringView, { attachTo: document.body })

    // Click three-dot menu on first item
    const menuBtns = wrapper.findAll('.v-list-item .v-btn')
    const dotsBtn = menuBtns.find((b) => b.find('.mdi-dots-vertical').exists())
    expect(dotsBtn).toBeTruthy()
    await dotsBtn!.trigger('click')
    await flushPromises()

    // Click "Delete" in the menu
    const menuItems = document.querySelectorAll('.v-overlay--active .v-list-item')
    const deleteItem = Array.from(menuItems).find((item) =>
      item.textContent?.includes('Delete')
    ) as HTMLElement
    expect(deleteItem).toBeTruthy()
    deleteItem.click()
    await flushPromises()

    // Delete confirmation dialog should be visible
    expect(document.body.textContent).toContain('Delete Recurring Transaction')
    expect(document.body.textContent).toContain('Are you sure you want to delete')

    // Click Cancel
    const dialogButtons = document.querySelectorAll('.v-dialog .v-btn')
    const cancelBtn = Array.from(dialogButtons).find(
      (b) => b.textContent?.trim() === 'Cancel'
    ) as HTMLElement
    cancelBtn.click()
    await flushPromises()

    // Dialog should be closed
    const activeDialogs = document.querySelectorAll('.v-overlay--active .v-dialog')
    const hasDeleteDialog = Array.from(activeDialogs).some((d) =>
      d.textContent?.includes('Delete Recurring Transaction')
    )
    expect(hasDeleteDialog).toBe(false)
    wrapper.unmount()
  })

  it('show inactive toggle includes inactive items in list', async () => {
    const { wrapper } = await mountAndSettle(RecurringView)

    // Before toggle: only active items (2)
    const itemsBefore = wrapper.findAll('.v-list-item')
    expect(itemsBefore.length).toBe(2)

    // Toggle "Show inactive" switch
    const switchEl = wrapper.find('.v-switch')
    await switchEl.find('input').setValue(true)
    await flushPromises()
    await flushPromises()

    // After toggle: all items including inactive (3)
    const itemsAfter = wrapper.findAll('.v-list-item')
    expect(itemsAfter.length).toBe(3)
  })

  it('transfer mode hides payee field and shows destination account', async () => {
    const { wrapper } = await mountAndSettle(RecurringView, { attachTo: document.body })

    // Open create dialog
    const addBtn = wrapper.findAll('.v-btn').find((b) => b.text().includes('Add Recurring'))
    await addBtn!.trigger('click')
    await flushPromises()

    // In transaction mode (default), Payee field should be present
    const dialogText = () => {
      const dialogs = document.querySelectorAll('.v-dialog')
      return Array.from(dialogs).map((d) => d.textContent).join('')
    }
    expect(dialogText()).toContain('Payee')
    expect(dialogText()).not.toContain('To Account')

    // Click Transfer button in the dialog's btn-toggle (teleported to body)
    const dialogBtnToggle = document.querySelector('.v-dialog .v-btn-toggle')
    expect(dialogBtnToggle).toBeTruthy()
    const toggleBtns = dialogBtnToggle!.querySelectorAll('.v-btn')
    const transferBtn = Array.from(toggleBtns).find((b) => b.textContent?.trim() === 'Transfer') as HTMLElement
    expect(transferBtn).toBeTruthy()
    transferBtn.click()
    await flushPromises()
    await flushPromises()

    // In transfer mode, "To Account" should appear
    expect(dialogText()).toContain('To Account')
    wrapper.unmount()
  })

  it('frequency unit options display correctly', async () => {
    const { wrapper } = await mountAndSettle(RecurringView, { attachTo: document.body })

    // Open create dialog
    const addBtn = wrapper.findAll('.v-btn').find((b) => b.text().includes('Add Recurring'))
    await addBtn!.trigger('click')
    await flushPromises()

    // Find the Period v-select inside the dialog and open it
    const selects = document.querySelectorAll('.v-dialog .v-select')
    const periodSelect = Array.from(selects).find((s) =>
      s.textContent?.includes('Period')
    ) as HTMLElement
    expect(periodSelect).toBeTruthy()

    const fieldInput = periodSelect.querySelector('.v-field__input') as HTMLElement
    fieldInput.dispatchEvent(new MouseEvent('mousedown', { bubbles: true }))
    await flushPromises()
    await flushPromises()
    await flushPromises()

    // Check that all frequency options are available in any overlay list
    const allOverlayItems = document.querySelectorAll('.v-overlay .v-list-item')
    const optionTexts = Array.from(allOverlayItems).map((item) => item.textContent?.trim())
    expect(optionTexts).toContain('Day(s)')
    expect(optionTexts).toContain('Week(s)')
    expect(optionTexts).toContain('Month(s)')
    expect(optionTexts).toContain('Year(s)')
    wrapper.unmount()
  })
})
