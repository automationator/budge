// Component tests for reconciled filter behavior.
// Tests that the "Hide Reconciled" toggle in TransactionFiltersDrawer
// correctly filters reconciled transactions from the displayed list.

import { describe, it, expect, beforeEach } from 'vitest'
import { nextTick } from 'vue'
import { http, HttpResponse } from 'msw'
import { server } from '@test/mocks/server'
import { factories } from '@test/mocks/factories'
import TransactionsView from '@/views/transactions/TransactionsView.vue'
import { mountView, flushPromises } from '@test/helpers/component-test-utils'

const API_BASE = '/api/v1'

// Test data
const reconciledTxn1 = factories.transaction({
  id: 'txn-reconciled-1',
  payee_id: 'payee-settled-alpha',
  is_reconciled: true,
  is_cleared: true,
  account_id: 'account-1',
})

const reconciledTxn2 = factories.transaction({
  id: 'txn-reconciled-2',
  payee_id: 'payee-settled-beta',
  is_reconciled: true,
  is_cleared: true,
  account_id: 'account-1',
})

const unreconciledTxn = factories.transaction({
  id: 'txn-unreconciled',
  payee_id: 'payee-fresh',
  is_reconciled: false,
  is_cleared: true,
  account_id: 'account-1',
})

const allTransactions = [reconciledTxn1, reconciledTxn2, unreconciledTxn]

const testPayees = [
  factories.payee({ id: 'payee-settled-alpha', name: 'Settled Alpha' }),
  factories.payee({ id: 'payee-settled-beta', name: 'Settled Beta' }),
  factories.payee({ id: 'payee-fresh', name: 'Fresh Pending' }),
]

async function settle() {
  for (let i = 0; i < 5; i++) {
    await flushPromises()
    await new Promise((resolve) => setTimeout(resolve, 20))
    await nextTick()
  }
}

async function mountAndSettle() {
  const result = mountView(TransactionsView, { attachTo: document.body })
  await settle()
  return result
}

// Helper: open filters drawer and toggle hide reconciled
async function toggleHideReconciled(wrapper: ReturnType<typeof mountView>['wrapper']) {
  // Click the Filters button
  const filtersBtn = wrapper.findAll('.v-btn').find((b) => b.text().includes('Filters'))
  expect(filtersBtn).toBeTruthy()
  await filtersBtn!.trigger('click')
  await settle()

  // Find the "Hide Reconciled" switch in the bottom sheet (rendered to document.body)
  const switches = document.body.querySelectorAll('.v-switch')
  let hideReconciledSwitch: Element | null = null
  switches.forEach((s) => {
    if (s.textContent?.includes('Hide Reconciled')) {
      hideReconciledSwitch = s
    }
  })
  expect(hideReconciledSwitch).toBeTruthy()

  // Click the switch input
  const input = hideReconciledSwitch!.querySelector('input')
  expect(input).toBeTruthy()
  input!.click()
  await settle()

  // Click Apply Filters
  const applyBtns = document.body.querySelectorAll('.v-btn')
  let applyBtn: Element | null = null
  applyBtns.forEach((b) => {
    if (b.textContent?.includes('Apply Filters')) {
      applyBtn = b
    }
  })
  expect(applyBtn).toBeTruthy()
  ;(applyBtn as HTMLElement).click()
  await settle()
}

// Helper: create a transactions MSW handler that filters by is_reconciled and account_id
// Returns empty for scheduled (upcoming) requests to avoid interference.
function createTransactionsHandler(txns: typeof allTransactions) {
  return http.get(`${API_BASE}/budgets/:budgetId/transactions`, ({ request }) => {
    const url = new URL(request.url)
    const isReconciled = url.searchParams.get('is_reconciled')
    const accountId = url.searchParams.get('account_id')
    const status = url.searchParams.get('status')

    // Return empty for upcoming/scheduled requests
    if (status) {
      return HttpResponse.json(factories.cursorPage([]))
    }

    let result = [...txns]

    // Filter by account
    if (accountId) {
      result = result.filter((t) => t.account_id === accountId)
    }

    // Filter by reconciled status
    if (isReconciled === 'false') {
      result = result.filter((t) => !t.is_reconciled)
    }

    return HttpResponse.json(factories.cursorPage(result))
  })
}

describe('Reconciled Filter', () => {
  beforeEach(() => {
    server.use(
      http.get(`${API_BASE}/budgets/:budgetId/payees`, () => {
        return HttpResponse.json(testPayees)
      })
    )
  })

  it('hide reconciled filter hides reconciled transactions', async () => {
    server.use(createTransactionsHandler(allTransactions))

    const { wrapper } = await mountAndSettle()

    // Initially all transactions should be visible
    expect(wrapper.text()).toContain('Settled Alpha')
    expect(wrapper.text()).toContain('Settled Beta')
    expect(wrapper.text()).toContain('Fresh Pending')

    // Toggle hide reconciled filter on
    await toggleHideReconciled(wrapper)

    // Reconciled transactions should be hidden
    expect(wrapper.text()).not.toContain('Settled Alpha')
    expect(wrapper.text()).not.toContain('Settled Beta')

    // Unreconciled transaction should still be visible
    expect(wrapper.text()).toContain('Fresh Pending')

    // Toggle filter off
    await toggleHideReconciled(wrapper)

    // All transactions should be visible again
    expect(wrapper.text()).toContain('Settled Alpha')
    expect(wrapper.text()).toContain('Settled Beta')
    expect(wrapper.text()).toContain('Fresh Pending')

    wrapper.unmount()
  })

  it('hide reconciled filter works with account filter', async () => {
    const account1 = factories.account({ id: 'acct-1', name: 'Account One' })
    const account2 = factories.account({ id: 'acct-2', name: 'Account Two' })

    const acct1ReconciledTxn = factories.transaction({
      id: 'txn-acct1-reconciled',
      payee_id: 'payee-acct1',
      account_id: 'acct-1',
      is_reconciled: true,
      is_cleared: true,
    })

    const acct2UnreconciledTxn = factories.transaction({
      id: 'txn-acct2-unreconciled',
      payee_id: 'payee-acct2',
      account_id: 'acct-2',
      is_reconciled: false,
      is_cleared: true,
    })

    server.use(
      http.get(`${API_BASE}/budgets/:budgetId/accounts`, () => {
        return HttpResponse.json([account1, account2])
      }),
      http.get(`${API_BASE}/budgets/:budgetId/payees`, () => {
        return HttpResponse.json([
          factories.payee({ id: 'payee-acct1', name: 'Account1 Payee' }),
          factories.payee({ id: 'payee-acct2', name: 'Account2 Payee' }),
        ])
      }),
      createTransactionsHandler([acct1ReconciledTxn, acct2UnreconciledTxn])
    )

    const { wrapper } = await mountAndSettle()

    // Both transactions visible initially
    expect(wrapper.text()).toContain('Account1 Payee')
    expect(wrapper.text()).toContain('Account2 Payee')

    // Select account 1 filter using the v-select
    const selectEl = wrapper.find('.v-select')
    expect(selectEl.exists()).toBe(true)
    const fieldInput = selectEl.find('.v-field__input')
    await fieldInput.trigger('mousedown')
    await settle()

    // Find and click "Account One" option
    const accountOptions = document.body.querySelectorAll('.v-overlay--active .v-list-item')
    let accountOneOption: Element | null = null
    accountOptions.forEach((o) => {
      if (o.textContent?.includes('Account One')) {
        accountOneOption = o
      }
    })
    expect(accountOneOption).toBeTruthy()
    ;(accountOneOption as HTMLElement).click()
    await settle()

    // Now only account 1 transaction visible
    expect(wrapper.text()).toContain('Account1 Payee')
    expect(wrapper.text()).not.toContain('Account2 Payee')

    // Toggle hide reconciled - should hide the reconciled account 1 transaction
    await toggleHideReconciled(wrapper)

    // Account 1's reconciled transaction should be hidden
    expect(wrapper.text()).not.toContain('Account1 Payee')

    wrapper.unmount()
  })
})
