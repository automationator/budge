// UI rendering tests for TransactionFormDialog.
// CRUD workflows, data persistence, and multi-step operations
// remain in frontend/tests/e2e/tests/transactions.spec.ts.

import { describe, it, expect, afterEach } from 'vitest'
import { http, HttpResponse } from 'msw'
import { server } from '@test/mocks/server'
import { factories } from '@test/mocks/factories'
import TransactionFormDialog from '@/components/transactions/TransactionFormDialog.vue'
import { mountView, flushPromises } from '@test/helpers/component-test-utils'
import type { VueWrapper } from '@vue/test-utils'
import { useAuthStore } from '@/stores/auth'

const API_BASE = '/api/v1'

// Helper: mount the dialog open with attachTo: document.body and settle
async function mountDialog(options?: {
  props?: Record<string, unknown>
  accountsOverride?: ReturnType<typeof factories.account>[]
}) {
  if (options?.accountsOverride) {
    server.use(
      http.get(`${API_BASE}/budgets/:budgetId/accounts`, () => {
        return HttpResponse.json(options.accountsOverride)
      })
    )
  }

  const result = mountView(TransactionFormDialog, {
    props: {
      modelValue: true,
      ...options?.props,
    },
    attachTo: document.body,
  })

  // Set budgets on auth store so resetForm() can read default_income_allocation
  const authStore = useAuthStore(result.pinia)
  authStore.budgets = [factories.budget()]

  await flushPromises()
  await flushPromises()
  await flushPromises()

  return result
}

// Helper: select an account by emitting update:modelValue on the AccountSelect component
async function selectAccount(wrapper: VueWrapper, accountId: string, label?: string) {
  const accountSelects = wrapper.findAllComponents({ name: 'AccountSelect' })
  const target = label
    ? accountSelects.find((c) => c.props('label') === label)
    : accountSelects[0]

  if (!target) throw new Error(`AccountSelect with label "${label}" not found`)
  target.vm.$emit('update:modelValue', accountId)
  await flushPromises()
  await flushPromises()
}

// Helper: select a payee by emitting update:modelValue on the PayeeSelect component
async function selectPayee(wrapper: VueWrapper, payeeId: string) {
  const payeeSelect = wrapper.findComponent({ name: 'PayeeSelect' })
  if (!payeeSelect.exists()) throw new Error('PayeeSelect not found')
  payeeSelect.vm.$emit('update:modelValue', payeeId)
  await flushPromises()
  await flushPromises()
}

// Helper: select an envelope by emitting update:modelValue on the first EnvelopeSelect component
async function selectEnvelope(wrapper: VueWrapper, envelopeId: string) {
  const envelopeSelect = wrapper.findComponent({ name: 'EnvelopeSelect' })
  if (!envelopeSelect.exists()) throw new Error('EnvelopeSelect not found')
  envelopeSelect.vm.$emit('update:modelValue', envelopeId)
  await flushPromises()
  await flushPromises()
}

// Helper: click the amount sign toggle to switch to income
async function switchToIncome() {
  const toggle = document.querySelector('[data-testid="amount-sign-toggle"]') as HTMLElement
  if (toggle && (toggle.textContent?.includes('−') || toggle.textContent?.includes('-'))) {
    toggle.click()
    await flushPromises()
    await flushPromises()
  }
}

// Helper: find a button in the dialog by text
function findButton(text: string): HTMLButtonElement | null {
  const buttons = document.querySelectorAll('.v-dialog .v-btn')
  return (
    (Array.from(buttons).find((b) => b.textContent?.trim() === text) as HTMLButtonElement) ?? null
  )
}

let currentWrapper: VueWrapper | null = null

afterEach(() => {
  if (currentWrapper) {
    currentWrapper.unmount()
    currentWrapper = null
  }
})

describe('TransactionFormDialog', () => {
  describe('Validation', () => {
    it('create button is disabled without required fields', async () => {
      const { wrapper } = await mountDialog()
      currentWrapper = wrapper

      const createBtn = findButton('Create')
      expect(createBtn).toBeTruthy()
      expect(createBtn!.disabled).toBe(true)
    })

    it('requires account selection', async () => {
      const { wrapper } = await mountDialog()
      currentWrapper = wrapper

      // Fill payee input
      const payeeInput = document.querySelector('.v-autocomplete input') as HTMLInputElement
      expect(payeeInput).toBeTruthy()
      payeeInput.value = 'Some Payee'
      payeeInput.dispatchEvent(new Event('input', { bubbles: true }))
      await flushPromises()

      // Fill amount
      const amountInput = document.querySelector('input[inputmode="numeric"]') as HTMLInputElement
      expect(amountInput).toBeTruthy()
      amountInput.value = '25.00'
      amountInput.dispatchEvent(new Event('input', { bubbles: true }))
      await flushPromises()

      // Create should still be disabled (no account selected)
      const createBtn = findButton('Create')
      expect(createBtn).toBeTruthy()
      expect(createBtn!.disabled).toBe(true)
    })
  })

  describe('Dialog Actions', () => {
    it('cancel button closes dialog', async () => {
      const { wrapper } = await mountDialog()
      currentWrapper = wrapper

      const cancelBtn = findButton('Cancel')
      expect(cancelBtn).toBeTruthy()
      cancelBtn!.click()
      await flushPromises()

      const emitted = wrapper.emitted('update:modelValue')
      expect(emitted).toBeTruthy()
      expect(emitted![emitted!.length - 1]).toEqual([false])
    })
  })

  describe('Transaction Types', () => {
    it('can switch between transaction and transfer tabs', async () => {
      const { wrapper } = await mountDialog()
      currentWrapper = wrapper

      const body = document.body
      // Initially on Transaction tab - Payee visible
      expect(body.textContent).toContain('Payee')

      // Switch to Transfer
      const tabs = wrapper.findAllComponents({ name: 'VTab' })
      expect(tabs).toHaveLength(2)
      await tabs[1]!.trigger('click')
      await flushPromises()
      await flushPromises()

      expect(body.innerHTML).toContain('From Account')
      expect(body.innerHTML).toContain('To Account')

      // Switch back to Transaction
      await tabs[0]!.trigger('click')
      await flushPromises()
      await flushPromises()

      expect(body.textContent).toContain('Payee')
    })
  })

  describe('Transfer Envelope Visibility', () => {
    it('shows envelope selector for budget to tracking transfers', async () => {
      const budgetAccount = factories.budgetAccount({
        id: 'budget-acct',
        name: 'Budget Checking',
      })
      const trackingAccount = factories.offBudgetAccount({
        id: 'tracking-acct',
        name: 'Tracking Investment',
      })

      const { wrapper } = await mountDialog({
        accountsOverride: [budgetAccount, trackingAccount],
      })
      currentWrapper = wrapper

      // Switch to Transfer tab
      const tabs = wrapper.findAllComponents({ name: 'VTab' })
      await tabs[1]!.trigger('click')
      await flushPromises()
      await flushPromises()

      // Select budget account as source (From Account)
      await selectAccount(wrapper, 'budget-acct', 'From Account')

      // Envelope should not be visible yet (no destination)
      expect(document.body.innerHTML).not.toContain('Which envelope is this money coming from?')

      // Select tracking account as destination (To Account)
      await selectAccount(wrapper, 'tracking-acct', 'To Account')

      // Envelope selector should now be visible
      expect(document.body.innerHTML).toContain('Which envelope is this money coming from?')
    })

    it('hides envelope selector for budget to budget transfers', async () => {
      const budgetAccount1 = factories.budgetAccount({
        id: 'budget-1-acct',
        name: 'Budget Checking',
      })
      const budgetAccount2 = factories.budgetAccount({
        id: 'budget-2-acct',
        name: 'Budget Savings',
        account_type: 'savings',
      })

      const { wrapper } = await mountDialog({
        accountsOverride: [budgetAccount1, budgetAccount2],
      })
      currentWrapper = wrapper

      // Switch to Transfer tab
      const tabs = wrapper.findAllComponents({ name: 'VTab' })
      await tabs[1]!.trigger('click')
      await flushPromises()
      await flushPromises()

      // Select both budget accounts
      await selectAccount(wrapper, 'budget-1-acct', 'From Account')
      await selectAccount(wrapper, 'budget-2-acct', 'To Account')

      // Envelope should NOT be visible for budget -> budget
      expect(document.body.innerHTML).not.toContain('Which envelope is this money coming from?')
    })
  })

  describe('Envelope Selection', () => {
    it('envelope selector appears for budget accounts', async () => {
      const budgetAccount = factories.budgetAccount({
        id: 'budget-acct',
        name: 'Budget Checking',
      })

      const { wrapper } = await mountDialog({
        accountsOverride: [budgetAccount],
      })
      currentWrapper = wrapper

      // Select the budget account
      await selectAccount(wrapper, 'budget-acct')

      // Envelope section should be visible
      expect(document.body.textContent).toContain('Split across envelopes')
    })

    it('envelope selector does not appear for non-budget accounts', async () => {
      const offBudgetAccount = factories.offBudgetAccount({
        id: 'tracking-acct',
        name: 'Tracking Account',
      })

      const { wrapper } = await mountDialog({
        accountsOverride: [offBudgetAccount],
      })
      currentWrapper = wrapper

      // Select the non-budget account
      await selectAccount(wrapper, 'tracking-acct')

      // Envelope section should NOT be visible
      expect(document.body.textContent).not.toContain('Split across envelopes')
    })
  })

  describe('Income Allocation Mode', () => {
    it('shows income allocation mode selector for new income transactions', async () => {
      const budgetAccount = factories.budgetAccount({
        id: 'budget-acct',
        name: 'Budget Checking',
      })

      const { wrapper } = await mountDialog({
        accountsOverride: [budgetAccount],
      })
      currentWrapper = wrapper

      // Select budget account
      await selectAccount(wrapper, 'budget-acct')

      // Switch to income
      await switchToIncome()

      // Income allocation mode radio group should be visible
      const radioGroup = document.querySelector('.v-dialog .v-radio-group')
      expect(radioGroup).toBeTruthy()
      expect(radioGroup!.textContent).toContain('Envelope')
      expect(radioGroup!.textContent).toContain('None')
    })

    it('hides income allocation mode selector for expenses', async () => {
      const budgetAccount = factories.budgetAccount({
        id: 'budget-acct',
        name: 'Budget Checking',
      })

      const { wrapper } = await mountDialog({
        accountsOverride: [budgetAccount],
      })
      currentWrapper = wrapper

      // Select budget account (default is expense)
      await selectAccount(wrapper, 'budget-acct')

      // Radio group should NOT be visible for expenses
      const radioGroup = document.querySelector('.v-dialog .v-radio-group')
      expect(radioGroup).toBeNull()
    })
  })

  describe('Envelope Auto-fill', () => {
    it('auto-fills envelope when selecting a payee with a default envelope', async () => {
      const budgetAccount = factories.budgetAccount({
        id: 'budget-acct',
        name: 'Budget Checking',
      })

      // Payee with default_envelope_id set
      const payeeWithDefault = factories.payee({
        id: 'payee-with-default',
        name: 'Grocery Store',
        default_envelope_id: 'envelope-1',
      })

      server.use(
        http.get(`${API_BASE}/budgets/:budgetId/payees`, () => {
          return HttpResponse.json([payeeWithDefault])
        })
      )

      const { wrapper } = await mountDialog({
        accountsOverride: [budgetAccount],
      })
      currentWrapper = wrapper

      // Select budget account to make envelope selector visible
      await selectAccount(wrapper, 'budget-acct')

      // Select the payee with a default envelope
      await selectPayee(wrapper, 'payee-with-default')

      // Verify the envelope was auto-filled
      const envelopeSelect = wrapper.findComponent({ name: 'EnvelopeSelect' })
      expect(envelopeSelect.exists()).toBe(true)
      expect(envelopeSelect.props('modelValue')).toBe('envelope-1')
    })

    it('does not auto-fill for a payee without a default envelope', async () => {
      const budgetAccount = factories.budgetAccount({
        id: 'budget-acct',
        name: 'Budget Checking',
      })

      // Payee without default_envelope_id
      const payeeNoDefault = factories.payee({
        id: 'payee-no-default',
        name: 'New Store',
        default_envelope_id: null,
      })

      server.use(
        http.get(`${API_BASE}/budgets/:budgetId/payees`, () => {
          return HttpResponse.json([payeeNoDefault])
        })
      )

      const { wrapper } = await mountDialog({
        accountsOverride: [budgetAccount],
      })
      currentWrapper = wrapper

      // Select budget account
      await selectAccount(wrapper, 'budget-acct')

      // Select the payee without a default envelope
      await selectPayee(wrapper, 'payee-no-default')

      // Verify the envelope was NOT auto-filled
      const envelopeSelect = wrapper.findComponent({ name: 'EnvelopeSelect' })
      expect(envelopeSelect.exists()).toBe(true)
      expect(envelopeSelect.props('modelValue')).toBeNull()
    })

    it('does not override existing envelope selection', async () => {
      const budgetAccount = factories.budgetAccount({
        id: 'budget-acct',
        name: 'Budget Checking',
      })

      // Payee with default_envelope_id pointing to envelope-1
      const payeeWithDefault = factories.payee({
        id: 'payee-with-default',
        name: 'Grocery Store',
        default_envelope_id: 'envelope-1',
      })

      server.use(
        http.get(`${API_BASE}/budgets/:budgetId/payees`, () => {
          return HttpResponse.json([payeeWithDefault])
        })
      )

      const { wrapper } = await mountDialog({
        accountsOverride: [budgetAccount],
      })
      currentWrapper = wrapper

      // Select budget account
      await selectAccount(wrapper, 'budget-acct')

      // Select an envelope FIRST (envelope-2, different from the payee's default)
      await selectEnvelope(wrapper, 'envelope-2')

      // Now select the payee with a default envelope
      await selectPayee(wrapper, 'payee-with-default')

      // Verify the envelope was NOT overridden (still envelope-2)
      const envelopeSelect = wrapper.findComponent({ name: 'EnvelopeSelect' })
      expect(envelopeSelect.exists()).toBe(true)
      expect(envelopeSelect.props('modelValue')).toBe('envelope-2')
    })
  })

  describe('Credit Card Accounts', () => {
    it('shows envelope section for credit card accounts', async () => {
      const ccAccount = factories.creditCardAccount({
        id: 'cc-acct',
        name: 'Test Credit Card',
      })

      const { wrapper } = await mountDialog({
        accountsOverride: [ccAccount],
      })
      currentWrapper = wrapper

      // Select the CC account
      await selectAccount(wrapper, 'cc-acct')

      // Envelope section should be visible (CC accounts are budget accounts)
      expect(document.body.textContent).toContain('Split across envelopes')
    })

    it('does not include CC envelopes in the envelope dropdown', async () => {
      const ccAccount = factories.creditCardAccount({
        id: 'cc-acct',
        name: 'Test CC',
      })

      // Override envelopes to include a CC envelope (linked_account_id set)
      server.use(
        http.get(`${API_BASE}/budgets/:budgetId/envelopes`, () => {
          return HttpResponse.json([
            factories.envelope({ is_unallocated: true, name: 'Unallocated', current_balance: 20000 }),
            factories.envelope({ id: 'regular-envelope', name: 'Groceries' }),
            factories.envelope({
              id: 'cc-envelope',
              name: 'Test CC',
              linked_account_id: 'cc-acct',
            }),
          ])
        })
      )

      const { wrapper } = await mountDialog({
        accountsOverride: [ccAccount],
      })
      currentWrapper = wrapper

      // Select the CC account
      await selectAccount(wrapper, 'cc-acct')

      // EnvelopeSelect should not have includeCreditCards enabled,
      // so CC envelopes are filtered out of the dropdown
      const envelopeSelect = wrapper.findComponent({ name: 'EnvelopeSelect' })
      expect(envelopeSelect.exists()).toBe(true)
      expect(envelopeSelect.props('includeCreditCards')).toBeFalsy()
    })
  })
})
