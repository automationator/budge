import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import MoneyDisplay from '@/components/common/MoneyDisplay.vue'

describe('MoneyDisplay', () => {
  function mountComponent(props: {
    amount: number
    colored?: boolean
    size?: 'small' | 'medium' | 'large'
  }) {
    return mount(MoneyDisplay, { props })
  }

  describe('rendering', () => {
    it('renders formatted amount', () => {
      const wrapper = mountComponent({ amount: 12345 })
      expect(wrapper.text()).toBe('$123.45')
    })

    it('renders negative amount', () => {
      const wrapper = mountComponent({ amount: -12345 })
      expect(wrapper.text()).toBe('-$123.45')
    })

    it('renders zero', () => {
      const wrapper = mountComponent({ amount: 0 })
      expect(wrapper.text()).toBe('$0.00')
    })

    it('renders large amounts with commas', () => {
      const wrapper = mountComponent({ amount: 123456789 })
      expect(wrapper.text()).toBe('$1,234,567.89')
    })
  })

  describe('color classes', () => {
    it('applies success color for positive amounts', () => {
      const wrapper = mountComponent({ amount: 100 })
      expect(wrapper.classes()).toContain('text-success')
    })

    it('applies error color for negative amounts', () => {
      const wrapper = mountComponent({ amount: -100 })
      expect(wrapper.classes()).toContain('text-error')
    })

    it('applies no color for zero', () => {
      const wrapper = mountComponent({ amount: 0 })
      expect(wrapper.classes()).not.toContain('text-success')
      expect(wrapper.classes()).not.toContain('text-error')
    })

    it('respects colored=false prop', () => {
      const wrapper = mountComponent({ amount: 100, colored: false })
      expect(wrapper.classes()).not.toContain('text-success')
      expect(wrapper.classes()).not.toContain('text-error')
    })

    it('respects colored=false for negative amounts', () => {
      const wrapper = mountComponent({ amount: -100, colored: false })
      expect(wrapper.classes()).not.toContain('text-error')
    })
  })

  describe('size classes', () => {
    it('applies small size class', () => {
      const wrapper = mountComponent({ amount: 100, size: 'small' })
      expect(wrapper.classes()).toContain('text-body-2')
    })

    it('applies medium size class by default', () => {
      const wrapper = mountComponent({ amount: 100 })
      expect(wrapper.classes()).toContain('text-body-1')
    })

    it('applies large size class', () => {
      const wrapper = mountComponent({ amount: 100, size: 'large' })
      expect(wrapper.classes()).toContain('text-h5')
    })
  })

  describe('base styles', () => {
    it('has font-weight-medium class', () => {
      const wrapper = mountComponent({ amount: 100 })
      expect(wrapper.classes()).toContain('font-weight-medium')
    })

    it('renders as a span element', () => {
      const wrapper = mountComponent({ amount: 100 })
      expect(wrapper.element.tagName).toBe('SPAN')
    })
  })
})
