// UI rendering tests for the AccountDetailView.
// Data-mutation tests (edit, delete with redirect, reconcile confirm, navigation)
// remain in frontend/tests/e2e/tests/accounts.spec.ts.

import { describe, it, expect } from 'vitest'
import { http, HttpResponse } from 'msw'
import { server } from '@test/mocks/server'
import { factories } from '@test/mocks/factories'
import AccountDetailView from '@/views/accounts/AccountDetailView.vue'
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

// In test env, Vuetify useDisplay() returns mobile=true since matchMedia
// returns matches:false. Buttons show icons instead of text labels.
// Find buttons by their icon HTML content.
function findBtnByIcon(wrapper: ReturnType<typeof mountView>['wrapper'], icon: string) {
  return wrapper.findAll('.v-btn').find((b) => b.html().includes(icon))
}

describe('AccountDetailView', () => {
  function setRouteParams(accountId: string = 'account-1') {
    mockRouteInstance.params = { id: accountId }
  }

  function setupDetailHandlers(accountOverrides: Partial<ReturnType<typeof factories.account>> = {}) {
    server.use(
      http.get(`${API_BASE}/budgets/:budgetId/accounts/:accountId`, () => {
        return HttpResponse.json(factories.account(accountOverrides))
      }),
      http.get(`${API_BASE}/budgets/:budgetId/transactions`, () => {
        return HttpResponse.json(factories.cursorPage([]))
      }),
      http.get(`${API_BASE}/budgets/:budgetId/payees`, () => {
        return HttpResponse.json([])
      })
    )
  }

  it('displays account header with name, type, and balances', async () => {
    setRouteParams()
    setupDetailHandlers({
      name: 'My Checking',
      account_type: 'checking',
      cleared_balance: 100000,
      uncleared_balance: 25000,
    })

    const { wrapper } = await mountAndSettle(AccountDetailView)

    expect(wrapper.text()).toContain('My Checking')
    expect(wrapper.text()).toContain('Checking')
    // Mobile layout shows Working Balance label
    expect(wrapper.text()).toContain('Working Balance')
  })

  it('shows Off-budget label for tracking accounts', async () => {
    setRouteParams()
    setupDetailHandlers({
      include_in_budget: false,
    })

    const { wrapper } = await mountAndSettle(AccountDetailView)

    expect(wrapper.text()).toContain('Off-budget')
  })

  it('shows Never reconciled for new account', async () => {
    setRouteParams()
    setupDetailHandlers({
      last_reconciled_at: null,
    })

    const { wrapper } = await mountAndSettle(AccountDetailView)

    expect(wrapper.find('[data-testid="last-reconciled-text"]').text()).toContain('Never reconciled')
  })

  it('opens reconcile dialog with Step 1 confirmation', async () => {
    setRouteParams()
    setupDetailHandlers({ cleared_balance: 100000 })

    const { wrapper } = await mountAndSettle(AccountDetailView, { attachTo: document.body })

    // Click Reconcile button (identified by scale-balance icon)
    const reconcileBtn = findBtnByIcon(wrapper, 'mdi-scale-balance')
    expect(reconcileBtn).toBeTruthy()
    await reconcileBtn!.trigger('click')
    await flushPromises()

    // Dialog should show Step 1
    const body = document.body
    expect(body.textContent).toContain('Reconcile Account')
    expect(body.textContent).toContain('Is this balance correct')
    expect(body.textContent).toContain('Yes')
    expect(body.textContent).toContain('No')
    // Should show the balance ($1,000.00)
    expect(body.textContent).toContain('$')
    wrapper.unmount()
  })

  it('can navigate back from Step 2 to Step 1', async () => {
    setRouteParams()
    setupDetailHandlers()

    const { wrapper } = await mountAndSettle(AccountDetailView, { attachTo: document.body })

    // Open reconcile dialog
    const reconcileBtn = findBtnByIcon(wrapper, 'mdi-scale-balance')
    await reconcileBtn!.trigger('click')
    await flushPromises()

    // Click No to go to Step 2
    const noBtn = Array.from(document.querySelectorAll('.v-dialog .v-btn')).find(
      (b) => b.textContent?.trim() === 'No'
    ) as HTMLElement
    expect(noBtn).toBeTruthy()
    noBtn.click()
    await flushPromises()

    // Should be on Step 2 - verify Back button and balance input
    expect(document.body.textContent).toContain('Actual Balance')
    const backBtn = Array.from(document.querySelectorAll('.v-dialog .v-btn')).find(
      (b) => b.textContent?.trim() === 'Back'
    ) as HTMLElement
    expect(backBtn).toBeTruthy()

    // Click Back to return to Step 1
    backBtn.click()
    await flushPromises()

    // Should be back on Step 1
    expect(document.body.textContent).toContain('Is this balance correct')
    expect(document.body.textContent).toContain('Yes')
    expect(document.body.textContent).toContain('No')
    wrapper.unmount()
  })

  it('Step 2 input has cleared balance pre-filled', async () => {
    setRouteParams()
    setupDetailHandlers({ cleared_balance: 75000 }) // $750.00

    const { wrapper } = await mountAndSettle(AccountDetailView, { attachTo: document.body })

    // Open reconcile dialog
    const reconcileBtn = findBtnByIcon(wrapper, 'mdi-scale-balance')
    await reconcileBtn!.trigger('click')
    await flushPromises()

    // Click No to go to Step 2
    const noBtn = Array.from(document.querySelectorAll('.v-dialog .v-btn')).find(
      (b) => b.textContent?.trim() === 'No'
    ) as HTMLElement
    noBtn.click()
    await flushPromises()

    // The MoneyInput should have the cleared balance pre-filled
    const balanceInput = document.querySelector('.v-dialog input[type="text"]') as HTMLInputElement
    expect(balanceInput).toBeTruthy()
    expect(balanceInput.value).toBe('750.00')
    wrapper.unmount()
  })

  it('cancel reconcile from Step 1 closes dialog', async () => {
    setRouteParams()
    setupDetailHandlers()

    const { wrapper } = await mountAndSettle(AccountDetailView, { attachTo: document.body })

    // Open reconcile dialog
    const reconcileBtn = findBtnByIcon(wrapper, 'mdi-scale-balance')
    await reconcileBtn!.trigger('click')
    await flushPromises()

    expect(document.body.textContent).toContain('Reconcile Account')

    // Click Cancel
    const cancelBtn = Array.from(document.querySelectorAll('.v-dialog .v-btn')).find(
      (b) => b.textContent?.trim() === 'Cancel'
    ) as HTMLElement
    expect(cancelBtn).toBeTruthy()
    cancelBtn.click()
    await flushPromises()

    const dialogOverlay = document.querySelector('.v-overlay--active .v-dialog')
    expect(dialogOverlay).toBeNull()
    wrapper.unmount()
  })

  it('cancel reconcile from Step 2 closes dialog', async () => {
    setRouteParams()
    setupDetailHandlers()

    const { wrapper } = await mountAndSettle(AccountDetailView, { attachTo: document.body })

    // Open reconcile dialog
    const reconcileBtn = findBtnByIcon(wrapper, 'mdi-scale-balance')
    await reconcileBtn!.trigger('click')
    await flushPromises()

    // Go to Step 2
    const noBtn = Array.from(document.querySelectorAll('.v-dialog .v-btn')).find(
      (b) => b.textContent?.trim() === 'No'
    ) as HTMLElement
    noBtn.click()
    await flushPromises()

    // Cancel from Step 2
    const cancelBtn = Array.from(document.querySelectorAll('.v-dialog .v-btn')).find(
      (b) => b.textContent?.trim() === 'Cancel'
    ) as HTMLElement
    expect(cancelBtn).toBeTruthy()
    cancelBtn.click()
    await flushPromises()

    const dialogOverlay = document.querySelector('.v-overlay--active .v-dialog')
    expect(dialogOverlay).toBeNull()
    wrapper.unmount()
  })

  it('cancel delete does not delete account', async () => {
    setRouteParams()
    setupDetailHandlers({ name: 'Test Account' })

    const { wrapper } = await mountAndSettle(AccountDetailView, { attachTo: document.body })

    // Click Delete button (identified by delete icon)
    const deleteBtn = findBtnByIcon(wrapper, 'mdi-delete')
    expect(deleteBtn).toBeTruthy()
    await deleteBtn!.trigger('click')
    await flushPromises()

    // Dialog should show
    expect(document.body.textContent).toContain('Delete Account?')
    expect(document.body.textContent).toContain('Test Account')

    // Cancel
    const cancelBtn = Array.from(document.querySelectorAll('.v-dialog .v-btn')).find(
      (b) => b.textContent?.trim() === 'Cancel'
    ) as HTMLElement
    expect(cancelBtn).toBeTruthy()
    cancelBtn.click()
    await flushPromises()

    const dialogOverlay = document.querySelector('.v-overlay--active .v-dialog')
    expect(dialogOverlay).toBeNull()
    wrapper.unmount()
  })

  it('Add Transaction button opens dialog', async () => {
    setRouteParams()
    setupDetailHandlers()

    const { wrapper } = await mountAndSettle(AccountDetailView, { attachTo: document.body })

    // Add Transaction button (identified by plus icon, not in card-actions)
    const addBtn = findBtnByIcon(wrapper, 'mdi-plus')
    expect(addBtn).toBeTruthy()

    // Click to open dialog
    await addBtn!.trigger('click')
    await flushPromises()

    // TransactionFormDialog should be visible
    expect(document.body.textContent).toContain('Transaction')
    wrapper.unmount()
  })

  it('shows empty transactions state', async () => {
    setRouteParams()
    setupDetailHandlers()

    const { wrapper } = await mountAndSettle(AccountDetailView)

    // TransactionList shows empty message when no transactions
    expect(wrapper.text()).toContain('No transactions yet')
  })
})
