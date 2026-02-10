// UI rendering tests for the EnvelopeDetailView.
// Data-mutation tests (edit, delete, transfer, star/unstar, allocation rule CRUD)
// remain in frontend/tests/e2e/tests/envelopes.spec.ts.

import { describe, it, expect } from 'vitest'
import { http, HttpResponse } from 'msw'
import { server } from '@test/mocks/server'
import { factories } from '@test/mocks/factories'
import EnvelopeDetailView from '@/views/envelopes/EnvelopeDetailView.vue'
import { mountView, flushPromises } from '@test/helpers/component-test-utils'
import { mockRouteInstance } from '@test/setup'

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

describe('EnvelopeDetailView', () => {
  // Set up route params before each test
  function setRouteParams(envelopeId: string = 'envelope-1') {
    mockRouteInstance.params = { id: envelopeId }
  }

  it('displays envelope name and balance', async () => {
    setRouteParams()
    const { wrapper } = await mountAndSettle(EnvelopeDetailView)

    expect(wrapper.find('h1').text()).toBe('Groceries')
    expect(wrapper.text()).toContain('Current Balance')
  })

  it('shows back button', async () => {
    setRouteParams()
    const { wrapper } = await mountAndSettle(EnvelopeDetailView)

    expect(wrapper.text()).toContain('Back to Envelopes')
  })

  it('shows progress bar when target is set', async () => {
    setRouteParams()
    const { wrapper } = await mountAndSettle(EnvelopeDetailView)

    // Default envelope has target_balance: 60000
    const progressBar = wrapper.find('.v-progress-linear')
    expect(progressBar.exists()).toBe(true)
    expect(wrapper.text()).toContain('% of goal')
    expect(wrapper.text()).toContain('Target:')
  })

  it('shows no progress bar without target', async () => {
    setRouteParams()
    // Override all envelope endpoints to return no target balance
    server.use(
      http.get(`${API_BASE}/budgets/:budgetId/envelopes/summary`, () => {
        return HttpResponse.json({ ready_to_assign: 20000, unfunded_cc_debt: 0 })
      }),
      http.get(`${API_BASE}/budgets/:budgetId/envelopes/budget-summary`, () => {
        return HttpResponse.json({
          start_date: '2024-01-01', end_date: '2024-01-31',
          ready_to_assign: 0, total_activity: 0, total_balance: 0, groups: [],
        })
      }),
      http.get(`${API_BASE}/budgets/:budgetId/envelopes/:envelopeId`, () => {
        return HttpResponse.json(factories.envelope({ target_balance: null }))
      }),
      http.get(`${API_BASE}/budgets/:budgetId/envelopes`, () => {
        return HttpResponse.json([
          factories.envelope({ target_balance: null }),
        ])
      })
    )

    const { wrapper } = await mountAndSettle(EnvelopeDetailView)
    // Extra settle for async store updates
    await flushPromises()
    await flushPromises()

    expect(wrapper.text()).not.toContain('% of goal')
  })

  it('shows allocation rules section with Add Rule button', async () => {
    setRouteParams()
    const { wrapper } = await mountAndSettle(EnvelopeDetailView)

    expect(wrapper.text()).toContain('Allocation Rules')
    const addRuleBtn = wrapper.findAll('.v-btn').find((b) => b.text().includes('Add Rule'))
    expect(addRuleBtn).toBeTruthy()
  })

  it('shows empty rules state', async () => {
    setRouteParams()
    server.use(
      http.get(`${API_BASE}/budgets/:budgetId/allocation-rules`, () => {
        return HttpResponse.json([])
      })
    )

    const { wrapper } = await mountAndSettle(EnvelopeDetailView)

    expect(wrapper.text()).toContain('No allocation rules for this envelope')
    expect(wrapper.text()).toContain('Rules automatically distribute income')
  })

  it('shows rules when they exist', async () => {
    setRouteParams()
    // Default handler returns rules for envelope-1

    const { wrapper } = await mountAndSettle(EnvelopeDetailView)

    expect(wrapper.text()).toContain('Savings Rule')
    expect(wrapper.text()).toContain('Fixed Amount')
  })

  it('shows empty activity state', async () => {
    setRouteParams()
    const { wrapper } = await mountAndSettle(EnvelopeDetailView)

    expect(wrapper.text()).toContain('Recent Activity')
    expect(wrapper.text()).toContain('No allocation history yet')
    expect(wrapper.text()).toContain('0 allocations')
  })

  it('shows delete button', async () => {
    setRouteParams()
    const { wrapper } = await mountAndSettle(EnvelopeDetailView)

    const deleteBtn = wrapper.findAll('.v-btn').find((b) => b.text().includes('Delete Envelope'))
    expect(deleteBtn).toBeTruthy()
  })

  it('can open and cancel delete dialog', async () => {
    setRouteParams()
    const { wrapper } = await mountAndSettle(EnvelopeDetailView, { attachTo: document.body })

    // Click delete button
    const deleteBtn = wrapper.findAll('.v-btn').find((b) => b.text().includes('Delete Envelope'))
    await deleteBtn!.trigger('click')
    await flushPromises()

    // Dialog should show confirmation
    expect(document.body.textContent).toContain('Are you sure you want to delete')
    expect(document.body.textContent).toContain('Groceries')

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

  it('shows transfer button and can open transfer dialog', async () => {
    setRouteParams()
    const { wrapper } = await mountAndSettle(EnvelopeDetailView, { attachTo: document.body })

    // Find Transfer button
    const transferBtn = wrapper.findAll('.v-btn').find((b) => b.text().includes('Transfer'))
    expect(transferBtn).toBeTruthy()
    await transferBtn!.trigger('click')
    await flushPromises()

    // Dialog should show direction toggle
    const body = document.body
    expect(body.textContent).toContain('Transfer Money')
    expect(body.textContent).toContain('To Groceries')
    expect(body.textContent).toContain('From Groceries')
    wrapper.unmount()
  })

  it('shows edit button that opens edit dialog', async () => {
    setRouteParams()
    const { wrapper } = await mountAndSettle(EnvelopeDetailView, { attachTo: document.body })

    // Find a button with pencil icon by checking its HTML
    const editBtn = wrapper.findAll('.v-btn').find((b) => b.html().includes('mdi-pencil'))
    expect(editBtn).toBeTruthy()

    // Click to open edit dialog
    await editBtn!.trigger('click')
    await flushPromises()

    expect(document.body.textContent).toContain('Edit Envelope')
    expect(document.body.innerHTML).toContain('Name')
    wrapper.unmount()
  })
})
