// UI rendering tests for TransactionsView.
// Data-mutation tests (CRUD, filtering, pagination)
// remain in frontend/tests/e2e/tests/transactions.spec.ts.

import { describe, it, expect, beforeEach } from 'vitest'
import TransactionsView from '@/views/transactions/TransactionsView.vue'
import { mountView, flushPromises } from '@test/helpers/component-test-utils'
import { showTransactionDialog } from '@/composables/useGlobalTransactionDialog'

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

describe('TransactionsView', () => {
  beforeEach(() => {
    showTransactionDialog.value = false
  })

  it('displays page title and Add Transaction button', async () => {
    const { wrapper } = await mountAndSettle(TransactionsView)
    expect(wrapper.find('h1').text()).toBe('Transactions')

    const addBtn = wrapper.findAll('.v-btn').find((b) => b.text().includes('Add Transaction'))
    expect(addBtn).toBeTruthy()
  })

  it('add transaction button opens global dialog', async () => {
    const { wrapper } = await mountAndSettle(TransactionsView)
    expect(showTransactionDialog.value).toBe(false)

    const addBtn = wrapper.findAll('.v-btn').find((b) => b.text().includes('Add Transaction'))
    expect(addBtn).toBeTruthy()
    await addBtn!.trigger('click')
    await flushPromises()

    expect(showTransactionDialog.value).toBe(true)
  })
})
