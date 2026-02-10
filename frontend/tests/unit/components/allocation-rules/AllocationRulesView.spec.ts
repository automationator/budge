// UI rendering tests for the AllocationRulesView.
// Data-mutation tests (CRUD, priority reorder, activate/deactivate, preview workflow)
// remain in frontend/tests/e2e/tests/allocation-rules.spec.ts.

import { describe, it, expect } from 'vitest'
import { http, HttpResponse } from 'msw'
import { server } from '@test/mocks/server'
import AllocationRulesView from '@/views/allocation-rules/AllocationRulesView.vue'
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

describe('AllocationRulesView', () => {
  it('displays page title', async () => {
    const { wrapper } = await mountAndSettle(AllocationRulesView)
    expect(wrapper.find('h1').text()).toBe('Allocation Rules')
  })

  it('shows Add Rule button', async () => {
    const { wrapper } = await mountAndSettle(AllocationRulesView)
    const addBtn = wrapper.findAll('.v-btn').find((b) => b.text().includes('Add Rule'))
    expect(addBtn).toBeTruthy()
  })

  it('add rule button opens form dialog', async () => {
    const { wrapper } = await mountAndSettle(AllocationRulesView, { attachTo: document.body })

    const addBtn = wrapper.findAll('.v-btn').find((b) => b.text().includes('Add Rule'))
    await addBtn!.trigger('click')
    await flushPromises()

    expect(document.body.textContent).toContain('New Allocation Rule')
    wrapper.unmount()
  })

  it('renders rules list with correct rule names and formatted amounts', async () => {
    const { wrapper } = await mountAndSettle(AllocationRulesView)

    // Default MSW returns 3 rules: Savings Rule (fixed), Rent Percentage (percentage), Remainder to Savings (inactive)
    // Only active rules are shown by default (showInactive = false)
    const text = wrapper.text()
    expect(text).toContain('Savings Rule')
    expect(text).toContain('$100.00') // fixed amount: 10000 cents
    expect(text).toContain('Rent Percentage')
    expect(text).toContain('10.0%') // percentage: 1000 = 10.0%
    // Inactive rule should not appear by default
    expect(text).not.toContain('Remainder to Savings')
  })

  it('shows inactive chip on inactive rules when show inactive is enabled', async () => {
    const { wrapper } = await mountAndSettle(AllocationRulesView)

    // Toggle "Show inactive" switch
    const switchEl = wrapper.find('.v-switch')
    await switchEl.find('input').setValue(true)
    await flushPromises()

    // Now the inactive rule should appear with "Inactive" chip
    const text = wrapper.text()
    expect(text).toContain('Remainder to Savings')
    expect(text).toContain('Inactive')
  })

  it('shows empty state when no rules exist', async () => {
    server.use(
      http.get(`${API_BASE}/budgets/:budgetId/allocation-rules`, () => {
        return HttpResponse.json([])
      })
    )

    const { wrapper } = await mountAndSettle(AllocationRulesView)

    // With showInactive=false and no rules, condition shows "No rules match your filters."
    // Toggle showInactive on to see the true empty state
    const switchEl = wrapper.find('.v-switch')
    await switchEl.find('input').setValue(true)
    await flushPromises()

    expect(wrapper.text()).toContain('No allocation rules yet.')
    expect(wrapper.text()).toContain('Create Your First Rule')
  })

  it('shows four summary cards with correct values', async () => {
    const { wrapper } = await mountAndSettle(AllocationRulesView)

    const text = wrapper.text()
    // Card labels
    expect(text).toContain('Active Rules')
    expect(text).toContain('Total Rules')
    expect(text).toContain('Envelopes Covered')
    expect(text).toContain('Remainder Rules')

    // Values from default MSW data: 2 active, 3 total, 2 envelopes (envelope-1 and envelope-2), 0 active remainder rules
    const cards = wrapper.findAll('.v-card .text-h6')
    const cardValues = cards.map((c) => c.text())
    expect(cardValues).toContain('2') // Active Rules
    expect(cardValues).toContain('3') // Total Rules
    // Envelopes Covered: envelope-1 (rule-1 + rule-3) and envelope-2 (rule-2) = 2
    expect(cardValues).toContain('2')
    // Remainder Rules: only the inactive one (rule-3), but count is active remainder rules = 0
    expect(cardValues).toContain('0')
  })

  it('create button is disabled without required fields', async () => {
    const { wrapper } = await mountAndSettle(AllocationRulesView, { attachTo: document.body })

    // Click "Add Rule" button
    const addBtn = wrapper.findAll('.v-btn').find((b) => b.text().includes('Add Rule'))
    await addBtn!.trigger('click')
    await flushPromises()

    // Find Create button in the dialog
    const dialogButtons = document.querySelectorAll('.v-dialog .v-btn')
    const createBtn = Array.from(dialogButtons).find(
      (b) => b.textContent?.trim() === 'Create'
    ) as HTMLButtonElement
    expect(createBtn).toBeTruthy()
    expect(createBtn.disabled).toBe(true)
    wrapper.unmount()
  })

  it('delete dialog opens from menu and cancel closes it', async () => {
    const { wrapper } = await mountAndSettle(AllocationRulesView, { attachTo: document.body })

    // Click three-dot menu on first rule
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
    expect(document.body.textContent).toContain('Delete Allocation Rule')
    expect(document.body.textContent).toContain('This action cannot be undone')

    // Click Cancel
    const dialogButtons = document.querySelectorAll('.v-dialog .v-btn')
    const cancelBtn = Array.from(dialogButtons).find(
      (b) => b.textContent?.trim() === 'Cancel'
    ) as HTMLElement
    cancelBtn.click()
    await flushPromises()

    // Dialog should be closed - the delete confirmation text should no longer be in an active dialog
    const activeDialogs = document.querySelectorAll('.v-overlay--active .v-dialog')
    const hasDeleteDialog = Array.from(activeDialogs).some((d) =>
      d.textContent?.includes('Delete Allocation Rule')
    )
    expect(hasDeleteDialog).toBe(false)
    wrapper.unmount()
  })

  it('filter by envelope shows only matching rules', async () => {
    const { wrapper } = await mountAndSettle(AllocationRulesView, { attachTo: document.body })

    // Open the envelope filter v-select by clicking its control area
    const selectEl = wrapper.find('.v-select')
    const fieldInput = selectEl.find('.v-field__input')
    await fieldInput.trigger('mousedown')
    await flushPromises()
    await flushPromises()

    // Select "Rent" (envelope-2) from dropdown
    const overlayItems = document.querySelectorAll('.v-overlay--active .v-list-item')
    const rentOption = Array.from(overlayItems).find((opt) =>
      opt.textContent?.includes('Rent')
    ) as HTMLElement
    expect(rentOption).toBeTruthy()
    rentOption.click()
    await flushPromises()

    // Only rule for envelope-2 should be visible
    const text = wrapper.text()
    expect(text).toContain('Rent Percentage')
    expect(text).not.toContain('Savings Rule')
    wrapper.unmount()
  })

  it('show inactive toggle includes inactive rules', async () => {
    const { wrapper } = await mountAndSettle(AllocationRulesView)

    // Before toggle: inactive rule hidden
    expect(wrapper.text()).not.toContain('Remainder to Savings')

    // Toggle "Show inactive" switch
    const switchEl = wrapper.find('.v-switch')
    await switchEl.find('input').setValue(true)
    await flushPromises()

    // After toggle: inactive rule visible
    expect(wrapper.text()).toContain('Remainder to Savings')
  })

  it('preview section renders with preview table after preview', async () => {
    const { wrapper } = await mountAndSettle(AllocationRulesView, { attachTo: document.body })

    // Open preview expansion panel
    const panelTitle = wrapper.find('.v-expansion-panel-title')
    expect(panelTitle.text()).toContain('Preview Income Distribution')
    await panelTitle.trigger('click')
    await flushPromises()

    // Enter amount in the preview input
    const previewInput = wrapper.find('.v-expansion-panel-text input')
    expect(previewInput.exists()).toBe(true)
    await previewInput.setValue('1000')
    await flushPromises()

    // Click Preview button
    const previewBtn = wrapper
      .findAll('.v-expansion-panel-text .v-btn')
      .find((b) => b.text() === 'Preview')
    expect(previewBtn).toBeTruthy()
    await previewBtn!.trigger('click')
    await flushPromises()
    await flushPromises()

    // Preview table should appear with results from MSW handler
    const text = wrapper.text()
    expect(text).toContain('Rule')
    expect(text).toContain('Envelope')
    expect(text).toContain('Amount')
    expect(text).toContain('Savings Rule')
    expect(text).toContain('Rent Percentage')
    expect(text).toContain('Total')
    wrapper.unmount()
  })
})
