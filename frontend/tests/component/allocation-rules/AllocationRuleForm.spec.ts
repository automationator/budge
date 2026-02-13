import { describe, it, expect } from 'vitest'
import { mount, VueWrapper } from '@vue/test-utils'
import { nextTick, ComponentPublicInstance } from 'vue'
import AllocationRuleForm from '@/components/allocation-rules/AllocationRuleForm.vue'
import { createComponentTestContext, populateStores } from '@test/helpers/component-test-utils'
import { factories } from '@test/mocks/factories'
import type { AllocationRule, AllocationRuleType } from '@/types'

interface AllocationRuleFormData {
  envelope_id: string
  rule_type: AllocationRuleType
  amount: number
  priority: number
  is_active: boolean
  name: string | null
  respect_target: boolean
  cap_period_value?: number
  cap_period_unit?: string | null
}

interface RuleTypeOption {
  title: string
  value: AllocationRuleType
}

interface AllocationRuleFormVM extends ComponentPublicInstance {
  getFormData: () => AllocationRuleFormData | null
  isValid: () => boolean
  reset: () => void
}

interface AllocationRuleFormProps {
  rule?: AllocationRule | null
  envelopeId?: string | null
  loading?: boolean
  showEnvelopeSelect?: boolean
  defaultPriority?: number
  allowedRuleTypes?: AllocationRuleType[]
  showActions?: boolean
  defaultName?: string | null
}

describe('AllocationRuleForm', () => {
  function mountComponent(props: AllocationRuleFormProps = {}, storeData?: { envelopes?: ReturnType<typeof factories.envelope>[] }): { wrapper: VueWrapper<AllocationRuleFormVM>; pinia: ReturnType<typeof createComponentTestContext>['pinia'] } {
    const testContext = createComponentTestContext()

    // Populate stores with test data if provided
    if (storeData) {
      populateStores(testContext.pinia, storeData)
    }

    return {
      wrapper: mount(AllocationRuleForm, {
        props,
        global: testContext.global,
      }),
      pinia: testContext.pinia,
    }
  }

  describe('create mode', () => {
    it('defaults to fixed rule type', () => {
      const { wrapper } = mountComponent()
      const selects = wrapper.findAllComponents({ name: 'VSelect' })
      const ruleTypeSelect = selects.find((s) => s.text().includes('Rule Type'))
      expect(ruleTypeSelect?.props('modelValue')).toBe('fixed')
    })

    it('shows "Create" button text', () => {
      const { wrapper } = mountComponent()
      expect(wrapper.text()).toContain('Create')
    })

    it('defaults is_active to true', () => {
      const { wrapper } = mountComponent()
      const switches = wrapper.findAllComponents({ name: 'VSwitch' })
      const activeSwitch = switches.find((s) => s.text().includes('Active'))
      expect(activeSwitch?.props('modelValue')).toBe(true)
    })

    it('shows envelope select when showEnvelopeSelect is true', () => {
      const { wrapper } = mountComponent(
        { showEnvelopeSelect: true },
        { envelopes: [factories.envelope({ id: 'env-1', name: 'Groceries' })] }
      )
      expect(wrapper.text()).toContain('Envelope')
    })

    it('hides envelope select when envelopeId is provided', () => {
      const { wrapper } = mountComponent({ envelopeId: 'env-1' })
      const selects = wrapper.findAllComponents({ name: 'VSelect' })
      const envelopeSelect = selects.find((s) => s.text().includes('Envelope'))
      expect(envelopeSelect).toBeUndefined()
    })
  })

  describe('edit mode', () => {
    const existingRule = factories.allocationRule({
      name: 'My Rule',
      rule_type: 'percentage',
      amount: 1000, // 10%
      is_active: true,
      priority: 5,
    })

    it('shows "Save" button text', () => {
      const { wrapper } = mountComponent({ rule: existingRule })
      expect(wrapper.text()).toContain('Save')
    })

    it('populates name from rule', async () => {
      const { wrapper } = mountComponent({ rule: existingRule })
      await nextTick()
      const nameInput = wrapper.find('input[type="text"]')
      expect((nameInput.element as HTMLInputElement).value).toBe('My Rule')
    })

    it('populates rule type from rule', async () => {
      const { wrapper } = mountComponent({ rule: existingRule })
      await nextTick()
      const selects = wrapper.findAllComponents({ name: 'VSelect' })
      const ruleTypeSelect = selects.find((s) => s.text().includes('Rule Type'))
      expect(ruleTypeSelect?.props('modelValue')).toBe('percentage')
    })
  })

  describe('rule type switching', () => {
    it('shows different amount labels for different rule types', async () => {
      const { wrapper } = mountComponent()

      // Fixed type shows "Amount ($)"
      expect(wrapper.text()).toContain('Amount ($)')

      // Change to percentage
      const selects = wrapper.findAllComponents({ name: 'VSelect' })
      const ruleTypeSelect = selects.find((s) => s.text().includes('Rule Type'))
      await ruleTypeSelect?.setValue('percentage')
      await nextTick()
      expect(wrapper.text()).toContain('Percentage (%)')

      // Change to remainder
      await ruleTypeSelect?.setValue('remainder')
      await nextTick()
      expect(wrapper.text()).toContain('Weight')
    })

    it('shows period cap fields only for period_cap rules', async () => {
      const { wrapper } = mountComponent({ allowedRuleTypes: ['fixed', 'period_cap'] })

      // Fixed type - no period fields
      expect(wrapper.text()).not.toContain('Every')

      // Change to period_cap
      const selects = wrapper.findAllComponents({ name: 'VSelect' })
      const ruleTypeSelect = selects.find((s) => s.text().includes('Rule Type'))
      await ruleTypeSelect?.setValue('period_cap')
      await nextTick()
      expect(wrapper.text()).toContain('Every')
      expect(wrapper.text()).toContain('Period')
    })

    it('hides respect target toggle for fill_to_target', async () => {
      const { wrapper } = mountComponent({ allowedRuleTypes: ['fixed', 'fill_to_target'] })

      // Fixed type - shows toggle
      expect(wrapper.text()).toContain('Stop at target balance')

      // Change to fill_to_target
      const selects = wrapper.findAllComponents({ name: 'VSelect' })
      const ruleTypeSelect = selects.find((s) => s.text().includes('Rule Type'))
      await ruleTypeSelect?.setValue('fill_to_target')
      await nextTick()

      const switches = wrapper.findAllComponents({ name: 'VSwitch' })
      const respectTargetSwitch = switches.find((s) => s.text().includes('Stop at target'))
      expect(respectTargetSwitch).toBeUndefined()
    })
  })

  describe('amount conversion', () => {
    it('converts fixed amount to cents', async () => {
      const { wrapper } = mountComponent({ envelopeId: 'env-1' })

      // Set amount
      const amountInputs = wrapper.findAll('input[type="number"]')
      const amountInput = amountInputs[0]
      await amountInput.setValue('50.25')
      await nextTick()

      // Get form data
      const vm = wrapper.vm
      const formData = vm.getFormData()
      expect(formData.amount).toBe(5025) // $50.25 = 5025 cents
    })

    it('converts percentage to basis points', async () => {
      const { wrapper } = mountComponent({ envelopeId: 'env-1' })

      // Change to percentage
      const selects = wrapper.findAllComponents({ name: 'VSelect' })
      const ruleTypeSelect = selects.find((s) => s.text().includes('Rule Type'))
      await ruleTypeSelect?.setValue('percentage')
      await nextTick()

      // Set amount
      const amountInputs = wrapper.findAll('input[type="number"]')
      const amountInput = amountInputs[0]
      await amountInput.setValue('10.5')
      await nextTick()

      // Get form data
      const vm = wrapper.vm
      const formData = vm.getFormData()
      expect(formData.amount).toBe(1050) // 10.5% = 1050 basis points
    })

    it('keeps remainder weight as-is', async () => {
      const { wrapper } = mountComponent({ envelopeId: 'env-1' })

      // Change to remainder
      const selects = wrapper.findAllComponents({ name: 'VSelect' })
      const ruleTypeSelect = selects.find((s) => s.text().includes('Rule Type'))
      await ruleTypeSelect?.setValue('remainder')
      await nextTick()

      // Set amount
      const amountInputs = wrapper.findAll('input[type="number"]')
      const amountInput = amountInputs[0]
      await amountInput.setValue('5')
      await nextTick()

      // Get form data
      const vm = wrapper.vm
      const formData = vm.getFormData()
      expect(formData.amount).toBe(5) // Weight stays as integer
    })

    it('converts period cap amount to cents', async () => {
      // Use an existing period_cap rule to bypass the conditional rendering issue
      // with VSelect setValue in tests
      const periodCapRule = factories.allocationRule({
        rule_type: 'period_cap',
        amount: 10000,
        cap_period_value: 1,
        cap_period_unit: 'month',
      })
      const { wrapper } = mountComponent({
        envelopeId: 'env-1',
        rule: periodCapRule,
        allowedRuleTypes: ['fixed', 'period_cap'],
      })
      await nextTick()

      // Get form data - rule is pre-populated with period_cap values
      const vm = wrapper.vm
      const formData = vm.getFormData()
      expect(formData).not.toBeNull()
      expect(formData!.amount).toBe(10000) // $100 = 10000 cents
      expect(formData!.cap_period_value).toBe(1)
      expect(formData!.cap_period_unit).toBe('month')
    })
  })

  describe('validation', () => {
    it('is invalid without amount for fixed rule', () => {
      const { wrapper } = mountComponent({ envelopeId: 'env-1' })
      const vm = wrapper.vm
      expect(vm.isValid()).toBe(false)
    })

    it('is valid with amount for fixed rule', async () => {
      const { wrapper } = mountComponent({ envelopeId: 'env-1' })

      const amountInputs = wrapper.findAll('input[type="number"]')
      await amountInputs[0].setValue('50')
      await nextTick()

      const vm = wrapper.vm
      expect(vm.isValid()).toBe(true)
    })

    it('is valid without amount for fill_to_target rule', async () => {
      const { wrapper } = mountComponent({
        envelopeId: 'env-1',
        allowedRuleTypes: ['fill_to_target'],
      })
      await nextTick()

      const vm = wrapper.vm
      expect(vm.isValid()).toBe(true)
    })

    it('requires envelope when showEnvelopeSelect is true', () => {
      const { wrapper } = mountComponent(
        { showEnvelopeSelect: true },
        { envelopes: [factories.envelope({ id: 'env-1', name: 'Groceries' })] }
      )
      const vm = wrapper.vm
      expect(vm.isValid()).toBe(false)
    })
  })

  describe('submit', () => {
    it('emits submit with form data', async () => {
      const { wrapper } = mountComponent({ envelopeId: 'env-1' })

      // Fill form
      const nameInput = wrapper.find('input[type="text"]')
      await nameInput.setValue('Test Rule')

      const amountInputs = wrapper.findAll('input[type="number"]')
      await amountInputs[0].setValue('100')
      await nextTick()

      // Submit via form (not button click)
      const form = wrapper.findComponent({ name: 'VForm' })
      await form.trigger('submit.prevent')
      await nextTick()

      expect(wrapper.emitted('submit')).toBeTruthy()
      const emittedData = wrapper.emitted('submit')![0][0] as AllocationRuleFormData
      expect(emittedData.name).toBe('Test Rule')
      expect(emittedData.amount).toBe(10000) // $100 = 10000 cents
      expect(emittedData.envelope_id).toBe('env-1')
      expect(emittedData.rule_type).toBe('fixed')
    })

  })

  describe('cancel', () => {
    it('emits cancel when cancel button clicked', async () => {
      const { wrapper } = mountComponent()
      const cancelBtn = wrapper.findAllComponents({ name: 'VBtn' }).find((b) => b.text().includes('Cancel'))
      await cancelBtn?.trigger('click')

      expect(wrapper.emitted('cancel')).toBeTruthy()
    })
  })

  describe('exposed methods', () => {
    it('exposes getFormData method', async () => {
      const { wrapper } = mountComponent({ envelopeId: 'env-1' })

      const amountInputs = wrapper.findAll('input[type="number"]')
      await amountInputs[0].setValue('50')
      await nextTick()

      const vm = wrapper.vm
      const formData = vm.getFormData()
      expect(formData).not.toBeNull()
      expect(formData.amount).toBe(5000)
    })

    it('exposes isValid method', () => {
      const { wrapper } = mountComponent({ envelopeId: 'env-1' })
      const vm = wrapper.vm
      expect(typeof vm.isValid).toBe('function')
    })

    it('exposes reset method', async () => {
      const { wrapper } = mountComponent({ envelopeId: 'env-1' })

      const nameInput = wrapper.find('input[type="text"]')
      await nameInput.setValue('Test Name')
      await nextTick()

      const vm = wrapper.vm
      vm.reset()
      await nextTick()

      expect((nameInput.element as HTMLInputElement).value).toBe('')
    })
  })

  describe('allowed rule types', () => {
    it('only shows allowed rule types', async () => {
      const { wrapper } = mountComponent({
        allowedRuleTypes: ['fixed', 'percentage'] as AllocationRuleType[],
      })

      const selects = wrapper.findAllComponents({ name: 'VSelect' })
      const ruleTypeSelect = selects.find((s) => s.text().includes('Rule Type'))
      const items = ruleTypeSelect?.props('items') as RuleTypeOption[]
      const types = items.map((i) => i.value)

      expect(types).toContain('fixed')
      expect(types).toContain('percentage')
      expect(types).not.toContain('fill_to_target')
      expect(types).not.toContain('remainder')
    })
  })

  describe('hasPeriodCap', () => {
    it('hides period_cap from rule type dropdown when hasPeriodCap is true', () => {
      const { wrapper } = mountComponent({ hasPeriodCap: true })

      const selects = wrapper.findAllComponents({ name: 'VSelect' })
      const ruleTypeSelect = selects.find((s) => s.text().includes('Rule Type'))
      const items = ruleTypeSelect?.props('items') as RuleTypeOption[]
      const types = items.map((i) => i.value)

      expect(types).not.toContain('period_cap')
      expect(types).toContain('fixed')
      expect(types).toContain('percentage')
    })

    it('shows period_cap in rule type dropdown when hasPeriodCap is false', () => {
      const { wrapper } = mountComponent({ hasPeriodCap: false })

      const selects = wrapper.findAllComponents({ name: 'VSelect' })
      const ruleTypeSelect = selects.find((s) => s.text().includes('Rule Type'))
      const items = ruleTypeSelect?.props('items') as RuleTypeOption[]
      const types = items.map((i) => i.value)

      expect(types).toContain('period_cap')
    })

    it('shows period_cap by default (hasPeriodCap not provided)', () => {
      const { wrapper } = mountComponent()

      const selects = wrapper.findAllComponents({ name: 'VSelect' })
      const ruleTypeSelect = selects.find((s) => s.text().includes('Rule Type'))
      const items = ruleTypeSelect?.props('items') as RuleTypeOption[]
      const types = items.map((i) => i.value)

      expect(types).toContain('period_cap')
    })
  })

  describe('props', () => {
    it('uses defaultPriority for new rules', () => {
      const { wrapper } = mountComponent({ defaultPriority: 10 })
      const priorityInput = wrapper.findAll('input[type="number"]').find((i) =>
        i.element.closest('.v-text-field')?.textContent?.includes('Priority')
      )
      expect((priorityInput?.element as HTMLInputElement).value).toBe('10')
    })

    it('hides actions when showActions is false', () => {
      const { wrapper } = mountComponent({ showActions: false })
      expect(wrapper.text()).not.toContain('Create')
      expect(wrapper.text()).not.toContain('Cancel')
    })
  })
})
