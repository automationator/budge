import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import EnvelopeCard from '@/components/envelopes/EnvelopeCard.vue'
import { createComponentTestContext, populateStores } from '@test/helpers/component-test-utils'
import { factories } from '@test/mocks/factories'
import type { Envelope } from '@/types'

describe('EnvelopeCard', () => {
  function mountComponent(
    envelope: Partial<Envelope> = {},
    options: {
      editMode?: boolean
      isFirst?: boolean
      isLast?: boolean
      reorderLoading?: boolean
      allocationRules?: ReturnType<typeof factories.allocationRule>[]
    } = {}
  ) {
    const context = createComponentTestContext()
    const { allocationRules, ...props } = options

    if (allocationRules) {
      populateStores(context.pinia, { allocationRules })
    }

    return {
      wrapper: mount(EnvelopeCard, {
        props: {
          envelope: factories.envelope(envelope),
          editMode: props.editMode ?? false,
          isFirst: props.isFirst ?? false,
          isLast: props.isLast ?? false,
          reorderLoading: props.reorderLoading ?? false,
        },
        global: context.global,
      }),
      pinia: context.pinia,
    }
  }

  describe('basic rendering', () => {
    it('renders envelope name', () => {
      const { wrapper } = mountComponent({ name: 'My Envelope' })
      expect(wrapper.text()).toContain('My Envelope')
    })

    it('renders default icon when no icon specified', () => {
      const { wrapper } = mountComponent({ icon: null })
      expect(wrapper.html()).toContain('mdi-wallet')
    })

    it('renders custom icon when specified', () => {
      const { wrapper } = mountComponent({ icon: 'mdi-food' })
      expect(wrapper.html()).toContain('mdi-food')
    })
  })

  describe('progress bar', () => {
    it('shows progress bar when target_balance is set', () => {
      const { wrapper } = mountComponent({
        current_balance: 30000,
        target_balance: 60000,
      })
      expect(wrapper.find('.v-progress-linear').exists()).toBe(true)
    })

    it('hides progress bar when target_balance is null', () => {
      const { wrapper } = mountComponent({
        current_balance: 30000,
        target_balance: null,
      })
      expect(wrapper.find('.v-progress-linear').exists()).toBe(false)
    })

    it('hides progress bar when target_balance is 0', () => {
      const { wrapper } = mountComponent({
        current_balance: 30000,
        target_balance: 0,
      })
      expect(wrapper.find('.v-progress-linear').exists()).toBe(false)
    })
  })

  describe('progress percentage calculation', () => {
    it('calculates correct percentage', () => {
      const { wrapper } = mountComponent({
        current_balance: 30000, // $300
        target_balance: 60000, // $600
      })
      // 30000/60000 = 50%
      const progressBar = wrapper.find('.v-progress-linear')
      expect(progressBar.attributes('aria-valuenow')).toBe('50')
    })

    it('caps percentage at 100%', () => {
      const { wrapper } = mountComponent({
        current_balance: 90000, // $900 (over target)
        target_balance: 60000, // $600
      })
      const progressBar = wrapper.find('.v-progress-linear')
      expect(progressBar.attributes('aria-valuenow')).toBe('100')
    })

    it('floors percentage at 0%', () => {
      const { wrapper } = mountComponent({
        current_balance: -10000, // -$100 (negative)
        target_balance: 60000, // $600
      })
      const progressBar = wrapper.find('.v-progress-linear')
      expect(progressBar.attributes('aria-valuenow')).toBe('0')
    })
  })

  describe('progress color', () => {
    it('shows error color when under 25%', () => {
      const { wrapper } = mountComponent({
        current_balance: 10000, // 16.7% of target
        target_balance: 60000,
      })
      // Vuetify adds the color class to an inner element
      expect(wrapper.html()).toContain('bg-error')
    })

    it('shows warning color when between 25% and 50%', () => {
      const { wrapper } = mountComponent({
        current_balance: 20000, // 33% of target
        target_balance: 60000,
      })
      expect(wrapper.html()).toContain('bg-warning')
    })

    it('shows primary color when between 50% and 100%', () => {
      const { wrapper } = mountComponent({
        current_balance: 45000, // 75% of target
        target_balance: 60000,
      })
      expect(wrapper.html()).toContain('bg-primary')
    })

    it('shows success color when at or above 100%', () => {
      const { wrapper } = mountComponent({
        current_balance: 60000, // 100% of target
        target_balance: 60000,
      })
      expect(wrapper.html()).toContain('bg-success')
    })
  })

  describe('balance color', () => {
    it('shows error color for negative balance', () => {
      const { wrapper } = mountComponent({
        current_balance: -5000, // -$50
        target_balance: null,
      })
      expect(wrapper.html()).toContain('text-error')
    })

    it('shows success color when at or above target', () => {
      const { wrapper } = mountComponent({
        current_balance: 60000,
        target_balance: 60000,
      })
      expect(wrapper.html()).toContain('text-success')
    })

    it('does not apply error color for positive balance below target', () => {
      const { wrapper } = mountComponent({
        current_balance: 30000,
        target_balance: 60000,
      })
      // The balance display should not have error color
      // Note: MoneyDisplay adds text-success for positive amounts by default,
      // but the envelope card's balanceColor computed only returns 'success'
      // when at/above target - it returns empty string for positive below target
      expect(wrapper.html()).not.toContain('text-error')
    })

    it('shows no special color for zero balance', () => {
      const { wrapper } = mountComponent({
        current_balance: 0,
        target_balance: null,
      })
      expect(wrapper.html()).not.toContain('text-error')
      expect(wrapper.html()).not.toContain('text-success')
    })
  })

  describe('edit mode', () => {
    it('shows reorder buttons in edit mode', () => {
      const { wrapper } = mountComponent({}, { editMode: true })
      expect(wrapper.find('.mdi-chevron-up').exists()).toBe(true)
      expect(wrapper.find('.mdi-chevron-down').exists()).toBe(true)
    })

    it('hides action buttons in edit mode', () => {
      const { wrapper } = mountComponent({}, { editMode: true })
      expect(wrapper.find('.mdi-swap-horizontal').exists()).toBe(false)
      expect(wrapper.find('.mdi-playlist-plus').exists()).toBe(false)
    })

    it('disables up button when isFirst', () => {
      const { wrapper } = mountComponent({}, { editMode: true, isFirst: true })
      const upButton = wrapper.find('.mdi-chevron-up').element.closest('button')
      expect(upButton?.hasAttribute('disabled')).toBe(true)
    })

    it('disables down button when isLast', () => {
      const { wrapper } = mountComponent({}, { editMode: true, isLast: true })
      const downButton = wrapper.find('.mdi-chevron-down').element.closest('button')
      expect(downButton?.hasAttribute('disabled')).toBe(true)
    })

    it('disables both buttons when reorderLoading', () => {
      const { wrapper } = mountComponent({}, { editMode: true, reorderLoading: true })
      const upButton = wrapper.find('.mdi-chevron-up').element.closest('button')
      const downButton = wrapper.find('.mdi-chevron-down').element.closest('button')
      expect(upButton?.hasAttribute('disabled')).toBe(true)
      expect(downButton?.hasAttribute('disabled')).toBe(true)
    })
  })

  describe('normal mode', () => {
    it('shows transfer button', () => {
      const { wrapper } = mountComponent({}, { editMode: false })
      expect(wrapper.find('.mdi-swap-horizontal').exists()).toBe(true)
    })

    it('shows add transaction button', () => {
      const { wrapper } = mountComponent({}, { editMode: false })
      expect(wrapper.find('.mdi-plus').exists()).toBe(true)
    })

    it('hides reorder buttons', () => {
      const { wrapper } = mountComponent({}, { editMode: false })
      expect(wrapper.find('.mdi-chevron-up').exists()).toBe(false)
      expect(wrapper.find('.mdi-chevron-down').exists()).toBe(false)
    })

    it('shows balance when no target', () => {
      const { wrapper } = mountComponent({
        current_balance: 50000,
        target_balance: null,
      })
      expect(wrapper.text()).toContain('$500.00')
    })
  })

  describe('event emissions', () => {
    it('emits click when list item is clicked', async () => {
      const { wrapper } = mountComponent()
      await wrapper.find('.v-list-item').trigger('click')
      expect(wrapper.emitted('click')).toBeTruthy()
    })

    it('emits transfer when transfer button is clicked', async () => {
      const { wrapper } = mountComponent()
      const transferIcon = wrapper.find('.mdi-swap-horizontal')
      const transferButton = transferIcon.element.closest('button')
      await transferButton?.click()
      expect(wrapper.emitted('transfer')).toBeTruthy()
    })

    it('emits addTransaction when add transaction button is clicked', async () => {
      const { wrapper } = mountComponent()
      const addIcon = wrapper.find('.mdi-plus')
      const addButton = addIcon.element.closest('button')
      await addButton?.click()
      expect(wrapper.emitted('addTransaction')).toBeTruthy()
    })

    it('emits moveUp when up button is clicked', async () => {
      const { wrapper } = mountComponent({}, { editMode: true })
      const upIcon = wrapper.find('.mdi-chevron-up')
      const upButton = upIcon.element.closest('button')
      await upButton?.click()
      expect(wrapper.emitted('moveUp')).toBeTruthy()
    })

    it('emits moveDown when down button is clicked', async () => {
      const { wrapper } = mountComponent({}, { editMode: true })
      const downIcon = wrapper.find('.mdi-chevron-down')
      const downButton = downIcon.element.closest('button')
      await downButton?.click()
      expect(wrapper.emitted('moveDown')).toBeTruthy()
    })
  })

  describe('allocation rule icons', () => {
    it('shows rule icons when envelope has active allocation rules', () => {
      const { wrapper } = mountComponent(
        { id: 'envelope-1' },
        {
          allocationRules: [
            factories.allocationRule({
              envelope_id: 'envelope-1',
              rule_type: 'fixed',
              is_active: true,
            }),
          ],
        }
      )
      // The EnvelopeRuleIcons component should render
      expect(wrapper.findComponent({ name: 'EnvelopeRuleIcons' }).exists()).toBe(true)
    })
  })

  describe('balance display without target', () => {
    it('shows current balance in append slot when no target', () => {
      const { wrapper } = mountComponent({
        current_balance: 75000, // $750
        target_balance: null,
      })
      // The balance should be visible in the append area
      expect(wrapper.text()).toContain('$750.00')
    })

    it('does not show balance in append slot when target is set', () => {
      const { wrapper } = mountComponent({
        current_balance: 30000,
        target_balance: 60000,
      })
      // Balance appears in the subtitle with "of" text, not alone in append
      expect(wrapper.text()).toContain('$300.00')
      expect(wrapper.text()).toContain('of')
      expect(wrapper.text()).toContain('$600.00')
    })
  })
})
