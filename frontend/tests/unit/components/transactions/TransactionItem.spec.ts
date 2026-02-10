import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import TransactionItem from '@/components/transactions/TransactionItem.vue'
import { createComponentTestContext, populateStores } from '@test/helpers/component-test-utils'
import { factories } from '@test/mocks/factories'
import type { Transaction, Account, Payee, Envelope, TransactionType } from '@/types'

describe('TransactionItem', () => {
  function mountComponent(
    transaction: Partial<Transaction>,
    storeData: {
      accounts?: Account[]
      payees?: Payee[]
      envelopes?: Envelope[]
    } = {}
  ) {
    const testContext = createComponentTestContext()
    populateStores(testContext.pinia, {
      accounts: storeData.accounts ?? [factories.account()],
      payees: storeData.payees ?? [factories.payee()],
      envelopes: storeData.envelopes ?? [factories.envelope()],
    })

    return {
      wrapper: mount(TransactionItem, {
        props: { transaction: factories.transaction(transaction) },
        global: testContext.global,
      }),
      pinia: testContext.pinia,
    }
  }

  describe('display name', () => {
    it('shows payee name for standard transactions', () => {
      const { wrapper } = mountComponent(
        { transaction_type: 'standard', payee_id: 'payee-1' },
        { payees: [factories.payee({ id: 'payee-1', name: 'Coffee Shop' })] }
      )
      expect(wrapper.text()).toContain('Coffee Shop')
    })

    it('shows "Transfer to [Account]" for outgoing transfers with linked account', () => {
      const { wrapper } = mountComponent(
        {
          transaction_type: 'transfer',
          payee_id: null,
          amount: -5000,
          linked_account_id: 'account-2',
        },
        {
          accounts: [
            factories.account({ id: 'account-1', name: 'Checking' }),
            factories.account({ id: 'account-2', name: 'Savings' }),
          ],
        }
      )
      expect(wrapper.text()).toContain('Transfer to Savings')
    })

    it('shows "Transfer from [Account]" for incoming transfers with linked account', () => {
      const { wrapper } = mountComponent(
        {
          transaction_type: 'transfer',
          payee_id: null,
          amount: 5000,
          linked_account_id: 'account-2',
        },
        {
          accounts: [
            factories.account({ id: 'account-1', name: 'Checking' }),
            factories.account({ id: 'account-2', name: 'Savings' }),
          ],
        }
      )
      expect(wrapper.text()).toContain('Transfer from Savings')
    })

    it('shows "Transfer" when linked_account_id is null', () => {
      const { wrapper } = mountComponent({
        transaction_type: 'transfer',
        payee_id: null,
        linked_account_id: null,
      })
      expect(wrapper.text()).toContain('Transfer')
    })

    it('shows memo for adjustment transactions with memo', () => {
      const { wrapper } = mountComponent({
        transaction_type: 'adjustment' as TransactionType,
        memo: 'Starting balance',
        payee_id: null,
      })
      expect(wrapper.text()).toContain('Starting balance')
    })

    it('shows "Balance Adjustment" for adjustment transactions without memo', () => {
      const { wrapper } = mountComponent({
        transaction_type: 'adjustment' as TransactionType,
        memo: null,
        payee_id: null,
      })
      expect(wrapper.text()).toContain('Balance Adjustment')
    })

    it('shows "Unknown Payee" when payee not found', () => {
      const { wrapper } = mountComponent(
        { transaction_type: 'standard', payee_id: 'nonexistent' },
        { payees: [] }
      )
      expect(wrapper.text()).toContain('Unknown Payee')
    })
  })

  describe('layout', () => {
    it('does not render left avatar/icon', () => {
      const { wrapper } = mountComponent({ transaction_type: 'standard' })
      // No VAvatar should exist as the left icon
      const avatar = wrapper.findComponent({ name: 'VAvatar' })
      expect(avatar.exists()).toBe(false)
    })

    it('renders date as first element in subtitle', () => {
      const { wrapper } = mountComponent(
        { date: '2024-01-15', account_id: 'account-1' },
        { accounts: [factories.account({ id: 'account-1', name: 'Checking' })] }
      )
      const subtitle = wrapper.find('.v-list-item-subtitle')
      const textContent = subtitle.text()
      // Date should come before account name
      const dateIndex = textContent.indexOf('Jan')
      const accountIndex = textContent.indexOf('Checking')
      expect(dateIndex).toBeLessThan(accountIndex)
    })
  })

  describe('account display', () => {
    it('shows account name', () => {
      const { wrapper } = mountComponent(
        { account_id: 'account-1' },
        { accounts: [factories.account({ id: 'account-1', name: 'Checking' })] }
      )
      expect(wrapper.text()).toContain('Checking')
    })

    it('shows "Unknown Account" when account not found', () => {
      const { wrapper } = mountComponent(
        { account_id: 'nonexistent' },
        { accounts: [] }
      )
      expect(wrapper.text()).toContain('Unknown Account')
    })
  })

  describe('envelope display', () => {
    it('shows envelope name for single allocation', () => {
      const allocation = factories.allocation({ envelope_id: 'envelope-1' })
      const { wrapper } = mountComponent(
        { allocations: [allocation] },
        { envelopes: [factories.envelope({ id: 'envelope-1', name: 'Groceries' })] }
      )
      expect(wrapper.text()).toContain('Groceries')
    })

    it('shows "Split" for multiple allocations', () => {
      const allocations = [
        factories.allocation({ id: 'a1', envelope_id: 'envelope-1' }),
        factories.allocation({ id: 'a2', envelope_id: 'envelope-2' }),
      ]
      const { wrapper } = mountComponent(
        { allocations },
        {
          envelopes: [
            factories.envelope({ id: 'envelope-1', name: 'Groceries' }),
            factories.envelope({ id: 'envelope-2', name: 'Dining' }),
          ],
        }
      )
      expect(wrapper.text()).toContain('Split')
    })

    it('hides envelope name when transaction is unallocated', () => {
      const allocation = factories.allocation({ envelope_id: 'unallocated-env' })
      const { wrapper } = mountComponent(
        { allocations: [allocation] },
        {
          envelopes: [
            factories.envelope({
              id: 'unallocated-env',
              name: 'Unallocated',
              is_unallocated: true,
            }),
          ],
        }
      )
      // Unallocated envelope name should not be shown
      expect(wrapper.text()).not.toContain('Unallocated')
    })

    it('hides envelope display when no allocations', () => {
      const { wrapper } = mountComponent({ allocations: [] })
      expect(wrapper.text()).not.toContain('Groceries')
      expect(wrapper.text()).not.toContain('Split')
    })
  })

  describe('status chip', () => {
    it('shows "Scheduled" chip for scheduled transactions', () => {
      const { wrapper } = mountComponent({ status: 'scheduled' })
      expect(wrapper.text()).toContain('Scheduled')
    })

    it('does not show chip for pending transactions', () => {
      const { wrapper } = mountComponent({ status: 'pending' })
      expect(wrapper.text()).not.toContain('Pending')
      expect(wrapper.text()).not.toContain('Scheduled')
    })

    it('does not show "Uncleared" chip (shown via icon instead)', () => {
      const { wrapper } = mountComponent({ status: 'completed', is_cleared: false })
      // Uncleared is now shown via icon, not chip
      expect(wrapper.text()).not.toContain('Uncleared')
    })

    it('shows no chip for cleared completed transactions', () => {
      const { wrapper } = mountComponent({ status: 'completed', is_cleared: true })
      expect(wrapper.text()).not.toContain('Uncleared')
      expect(wrapper.text()).not.toContain('Scheduled')
      expect(wrapper.text()).not.toContain('Pending')
    })
  })

  describe('cleared status indicator', () => {
    it('shows filled checkmark icon for cleared transactions', () => {
      const { wrapper } = mountComponent({ is_cleared: true, is_reconciled: false })
      expect(wrapper.html()).toContain('mdi-check-circle')
      expect(wrapper.html()).not.toContain('mdi-check-circle-outline')
    })

    it('shows outline checkmark icon for uncleared transactions', () => {
      const { wrapper } = mountComponent({ is_cleared: false, is_reconciled: false })
      expect(wrapper.html()).toContain('mdi-check-circle-outline')
    })

    it('shows green color for cleared transactions', () => {
      const { wrapper } = mountComponent({ is_cleared: true, is_reconciled: false })
      const icons = wrapper.findAllComponents({ name: 'VIcon' })
      // Find the cleared indicator icon (the one with check-circle)
      const clearedIcon = icons.find((icon) => {
        const html = icon.html()
        return html.includes('mdi-check-circle') && !html.includes('mdi-check-decagram')
      })
      expect(clearedIcon?.props('color')).toBe('success')
    })

    it('shows grey color for uncleared transactions', () => {
      const { wrapper } = mountComponent({ is_cleared: false, is_reconciled: false })
      const icons = wrapper.findAllComponents({ name: 'VIcon' })
      const unclearedIcon = icons.find((icon) => icon.html().includes('mdi-check-circle-outline'))
      expect(unclearedIcon?.props('color')).toBe('grey-lighten-1')
    })
  })

  describe('reconciliation indicator', () => {
    it('shows check-decagram icon for reconciled transactions', () => {
      const { wrapper } = mountComponent({ is_reconciled: true })
      expect(wrapper.html()).toContain('mdi-check-decagram')
    })

    it('hides reconciled icon and shows cleared icon for non-reconciled transactions', () => {
      const { wrapper } = mountComponent({ is_reconciled: false, is_cleared: true })
      expect(wrapper.html()).not.toContain('mdi-check-decagram')
      expect(wrapper.html()).toContain('mdi-check-circle')
    })
  })

  describe('amount display', () => {
    it('displays transaction amount', () => {
      const { wrapper } = mountComponent({ amount: -5000 })
      expect(wrapper.text()).toContain('-$50.00')
    })

    it('displays positive amount', () => {
      const { wrapper } = mountComponent({ amount: 10000 })
      expect(wrapper.text()).toContain('$100.00')
    })
  })

  describe('event emissions', () => {
    it('emits click when list item is clicked', async () => {
      const { wrapper } = mountComponent({})
      await wrapper.find('.v-list-item').trigger('click')
      expect(wrapper.emitted('click')).toBeTruthy()
    })
  })

  describe('date formatting', () => {
    it('formats date with month and day', () => {
      // Use today's date to avoid timezone issues
      const today = new Date()
      const dateStr = today.toISOString().split('T')[0]
      const { wrapper } = mountComponent({ date: dateStr })
      // Just verify it shows the month abbreviation format
      expect(wrapper.text()).toMatch(/Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec/)
    })
  })

  describe('pending transaction styling', () => {
    it('does not apply opacity to pending transactions', () => {
      const { wrapper } = mountComponent({ status: 'pending' })
      expect(wrapper.find('.v-list-item').classes()).not.toContain('opacity-60')
    })

    it('does not apply opacity to completed transactions', () => {
      const { wrapper } = mountComponent({ status: 'completed' })
      expect(wrapper.find('.v-list-item').classes()).not.toContain('opacity-60')
    })
  })
})
