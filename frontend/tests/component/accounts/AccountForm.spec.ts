import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import { nextTick } from 'vue'
import AccountForm from '@/components/accounts/AccountForm.vue'
import { createComponentTestContext } from '@test/helpers/component-test-utils'
import { factories } from '@test/mocks/factories'
import type { Account, AccountType } from '@/types'

interface AccountFormData {
  name: string
  account_type: AccountType
  include_in_budget: boolean
  starting_balance?: number | null
}

interface AccountTypeOption {
  value: AccountType
  title: string
  icon: string
}

describe('AccountForm', () => {
  function mountComponent(props: { account?: Account | null; loading?: boolean } = {}) {
    const testContext = createComponentTestContext()

    return {
      wrapper: mount(AccountForm, {
        props,
        global: testContext.global,
      }),
      pinia: testContext.pinia,
    }
  }

  describe('create mode', () => {
    it('shows starting balance field', () => {
      const { wrapper } = mountComponent()
      expect(wrapper.find('input[type="number"]').exists()).toBe(true)
      expect(wrapper.text()).toContain('Starting Balance')
    })

    it('hides active toggle', () => {
      const { wrapper } = mountComponent()
      // Active switch should not be present in create mode
      const switches = wrapper.findAllComponents({ name: 'VSwitch' })
      const hasActiveSwitch = switches.some((s) => s.text().includes('Active'))
      expect(hasActiveSwitch).toBe(false)
    })

    it('shows "Create" button text', () => {
      const { wrapper } = mountComponent()
      expect(wrapper.text()).toContain('Create')
    })

    it('defaults to checking account type', () => {
      const { wrapper } = mountComponent()
      const select = wrapper.findComponent({ name: 'VSelect' })
      expect(select.props('modelValue')).toBe('checking')
    })

    it('defaults include in budget to true', () => {
      const { wrapper } = mountComponent()
      const switches = wrapper.findAllComponents({ name: 'VSwitch' })
      const budgetSwitch = switches.find((s) => s.text().includes('Include in budget'))
      expect(budgetSwitch?.props('modelValue')).toBe(true)
    })
  })

  describe('edit mode', () => {
    const existingAccount = factories.account({
      name: 'My Checking',
      account_type: 'checking',
      description: 'Main account',
      include_in_budget: true,
      is_active: true,
    })

    it('hides starting balance field', () => {
      const { wrapper } = mountComponent({ account: existingAccount })
      expect(wrapper.find('input[type="number"]').exists()).toBe(false)
    })

    it('shows active toggle', () => {
      const { wrapper } = mountComponent({ account: existingAccount })
      expect(wrapper.text()).toContain('Active')
    })

    it('shows "Save" button text', () => {
      const { wrapper } = mountComponent({ account: existingAccount })
      expect(wrapper.text()).toContain('Save')
    })

    it('populates name from account', async () => {
      const { wrapper } = mountComponent({ account: existingAccount })
      await nextTick()
      const input = wrapper.find('input[type="text"]')
      expect((input.element as HTMLInputElement).value).toBe('My Checking')
    })

    it('populates account type from account', async () => {
      const account = factories.account({ account_type: 'savings' })
      const { wrapper } = mountComponent({ account })
      await nextTick()
      const select = wrapper.findComponent({ name: 'VSelect' })
      expect(select.props('modelValue')).toBe('savings')
    })

    it('populates description from account', async () => {
      const { wrapper } = mountComponent({ account: existingAccount })
      await nextTick()
      const textarea = wrapper.find('textarea')
      expect((textarea.element as HTMLTextAreaElement).value).toBe('Main account')
    })
  })

  describe('form validation', () => {
    it('disables submit when name is empty', async () => {
      const { wrapper } = mountComponent()
      await nextTick()
      const submitBtn = wrapper.findAll('.v-btn').find((b) => b.text().includes('Create'))
      expect(submitBtn?.attributes('disabled')).toBeDefined()
    })

    it('enables submit when name is provided', async () => {
      const { wrapper } = mountComponent()
      const input = wrapper.find('input[type="text"]')
      await input.setValue('New Account')
      await nextTick()
      await nextTick() // Wait for validation to complete
      const submitBtn = wrapper.findAll('.v-btn').find((b) => b.text().includes('Create'))
      expect(submitBtn?.attributes('disabled')).toBeUndefined()
    })
  })

  describe('submit', () => {
    it('emits submit with form data', async () => {
      const { wrapper } = mountComponent()
      const input = wrapper.find('input[type="text"]')
      await input.setValue('New Account')
      await nextTick()
      await nextTick()

      // Click submit button
      const submitBtn = wrapper.findAll('.v-btn').find((b) => b.text().includes('Create'))
      await submitBtn?.trigger('click')

      expect(wrapper.emitted('submit')).toBeTruthy()
      const emittedData = wrapper.emitted('submit')![0][0] as AccountFormData
      expect(emittedData.name).toBe('New Account')
      expect(emittedData.account_type).toBe('checking')
      expect(emittedData.include_in_budget).toBe(true)
    })

    it('converts starting balance to cents', async () => {
      const { wrapper } = mountComponent()
      const nameInput = wrapper.find('input[type="text"]')
      await nameInput.setValue('New Account')

      const balanceInput = wrapper.find('input[type="number"]')
      await balanceInput.setValue('123.45')
      await nextTick()
      await nextTick()

      const submitBtn = wrapper.findAll('.v-btn').find((b) => b.text().includes('Create'))
      await submitBtn?.trigger('click')

      const emittedData = wrapper.emitted('submit')![0][0] as AccountFormData
      expect(emittedData.starting_balance).toBe(12345) // $123.45 = 12345 cents
    })

    it('trims whitespace from name', async () => {
      const { wrapper } = mountComponent()
      const input = wrapper.find('input[type="text"]')
      await input.setValue('  Trimmed Name  ')
      await nextTick()
      await nextTick()

      const submitBtn = wrapper.findAll('.v-btn').find((b) => b.text().includes('Create'))
      await submitBtn?.trigger('click')

      const emittedData = wrapper.emitted('submit')![0][0] as AccountFormData
      expect(emittedData.name).toBe('Trimmed Name')
    })

    it('includes selected account type', async () => {
      const { wrapper } = mountComponent()
      const nameInput = wrapper.find('input[type="text"]')
      await nameInput.setValue('Test Account')

      // Change account type
      const select = wrapper.findComponent({ name: 'VSelect' })
      await select.setValue('savings')
      await nextTick()
      await nextTick()

      const submitBtn = wrapper.findAll('.v-btn').find((b) => b.text().includes('Create'))
      await submitBtn?.trigger('click')

      const emittedData = wrapper.emitted('submit')![0][0] as AccountFormData
      expect(emittedData.account_type).toBe('savings')
    })
  })

  describe('cancel', () => {
    it('emits cancel when cancel button clicked', async () => {
      const { wrapper } = mountComponent()
      const cancelBtn = wrapper.findAll('.v-btn').find((b) => b.text().includes('Cancel'))
      await cancelBtn?.trigger('click')

      expect(wrapper.emitted('cancel')).toBeTruthy()
    })
  })

  describe('loading state', () => {
    it('shows loading state on submit button', async () => {
      const { wrapper } = mountComponent({ loading: true })
      const buttons = wrapper.findAllComponents({ name: 'VBtn' })
      const submitBtn = buttons.find((b) => b.text().includes('Create'))
      expect(submitBtn?.props('loading')).toBe(true)
    })
  })

  describe('account type options', () => {
    it('includes all account types', () => {
      const { wrapper } = mountComponent()
      const select = wrapper.findComponent({ name: 'VSelect' })
      const items = select.props('items') as AccountTypeOption[]
      const types = items.map((i) => i.value)
      expect(types).toContain('checking')
      expect(types).toContain('savings')
      expect(types).toContain('credit_card')
      expect(types).toContain('cash')
      expect(types).toContain('investment')
      expect(types).toContain('loan')
      expect(types).toContain('other')
    })
  })

  describe('include in budget toggle', () => {
    it('can be toggled off', async () => {
      const { wrapper } = mountComponent()
      const nameInput = wrapper.find('input[type="text"]')
      await nameInput.setValue('Test Account')

      const switches = wrapper.findAllComponents({ name: 'VSwitch' })
      const budgetSwitch = switches.find((s) => s.text().includes('Include in budget'))
      await budgetSwitch?.setValue(false)
      await nextTick()
      await nextTick()

      const submitBtn = wrapper.findAll('.v-btn').find((b) => b.text().includes('Create'))
      await submitBtn?.trigger('click')

      const emittedData = wrapper.emitted('submit')![0][0] as AccountFormData
      expect(emittedData.include_in_budget).toBe(false)
    })
  })
})
