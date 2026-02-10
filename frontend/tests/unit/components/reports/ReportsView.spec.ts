// UI rendering tests for ReportsView.
// Data-dependent tests (computed averages, charts with real data) remain in
// frontend/tests/e2e/tests/reports.spec.ts.

import { describe, it, expect } from 'vitest'
import type { VueWrapper } from '@vue/test-utils'
import ReportsView from '@/views/reports/ReportsView.vue'
import { mountView, flushPromises } from '@test/helpers/component-test-utils'

// Helper: mount ReportsView and wait for initial API calls to resolve
async function mountReports() {
  const result = mountView(ReportsView)
  // Allow onMounted + all parallel API fetches to settle
  await flushPromises()
  await flushPromises()
  await flushPromises()
  return result
}

// Helper: click a tab by its text label and wait for render
async function clickTab(wrapper: VueWrapper, label: string) {
  const tabs = wrapper.findAll('.v-tab')
  const tab = tabs.find((t) => t.text().includes(label))
  expect(tab, `Tab "${label}" should exist`).toBeTruthy()
  await tab!.trigger('click')
  await flushPromises()
}

describe('ReportsView', () => {
  describe('Navigation', () => {
    it('renders page title', async () => {
      const { wrapper } = await mountReports()
      expect(wrapper.find('h1').text()).toBe('Reports')
    })

    it('renders all 13 tabs', async () => {
      const { wrapper } = await mountReports()
      const expectedTabs = [
        'Spending', 'Cash Flow', 'Net Worth', 'Top Payees', 'Runway',
        'Goals', 'Upcoming', 'Recurring', 'Trends', 'Locations',
        'Envelope History', 'Account History', 'Allocation Rules',
      ]
      const tabs = wrapper.findAll('.v-tab')
      expect(tabs).toHaveLength(13)
      for (const label of expectedTabs) {
        expect(tabs.some((t) => t.text().includes(label))).toBe(true)
      }
    })

    it('shows date filter controls', async () => {
      const { wrapper } = await mountReports()
      // DateRangePicker renders inside the view
      expect(wrapper.findComponent({ name: 'DateRangePicker' }).exists()).toBe(true)
    })
  })

  describe('Spending Tab', () => {
    it('displays spending card by default', async () => {
      const { wrapper } = await mountReports()
      const card = wrapper.findAll('.v-card').find((c) => c.text().includes('Spending by Envelope'))
      expect(card).toBeTruthy()
    })

    it('can switch away and back to spending tab', async () => {
      const { wrapper } = await mountReports()
      await clickTab(wrapper, 'Cash Flow')
      expect(wrapper.text()).toContain('Income vs Expenses')
      await clickTab(wrapper, 'Spending')
      expect(wrapper.text()).toContain('Spending by Envelope')
    })
  })

  describe('Cash Flow Tab', () => {
    it('displays cash flow card with summary sections', async () => {
      const { wrapper } = await mountReports()
      await clickTab(wrapper, 'Cash Flow')
      expect(wrapper.text()).toContain('Income vs Expenses')
      expect(wrapper.text()).toContain('Income')
      expect(wrapper.text()).toContain('Expenses')
      expect(wrapper.text()).toContain('Net')
    })

    it('shows income, expenses, and net totals', async () => {
      const { wrapper } = await mountReports()
      await clickTab(wrapper, 'Cash Flow')
      // With empty data, should show $0.00 values
      const moneyDisplays = wrapper.findAllComponents({ name: 'MoneyDisplay' })
      expect(moneyDisplays.length).toBeGreaterThan(0)
    })
  })

  describe('Net Worth Tab', () => {
    it('displays net worth card', async () => {
      const { wrapper } = await mountReports()
      await clickTab(wrapper, 'Net Worth')
      expect(wrapper.text()).toContain('Net Worth')
    })

    it('shows assets, liabilities, and net worth summaries', async () => {
      const { wrapper } = await mountReports()
      await clickTab(wrapper, 'Net Worth')
      expect(wrapper.text()).toContain('Assets')
      expect(wrapper.text()).toContain('Liabilities')
      expect(wrapper.text()).toContain('Net Worth')
    })

    it('shows net worth totals', async () => {
      const { wrapper } = await mountReports()
      await clickTab(wrapper, 'Net Worth')
      // MoneyDisplay components should be present for the three summaries
      const moneyDisplays = wrapper.findAllComponents({ name: 'MoneyDisplay' })
      expect(moneyDisplays.length).toBeGreaterThanOrEqual(3)
    })
  })

  describe('Top Payees Tab', () => {
    it('displays top payees card', async () => {
      const { wrapper } = await mountReports()
      await clickTab(wrapper, 'Top Payees')
      expect(wrapper.text()).toContain('Top Payees')
    })
  })

  describe('Runway Tab', () => {
    it('displays runway card', async () => {
      const { wrapper } = await mountReports()
      await clickTab(wrapper, 'Runway')
      expect(wrapper.text()).toContain('Days of Runway')
    })

    it('shows lookback period selector', async () => {
      const { wrapper } = await mountReports()
      await clickTab(wrapper, 'Runway')
      // The v-select with label "Lookback" should be present
      const selects = wrapper.findAll('.v-select')
      const lookbackSelect = selects.find((s) => s.text().includes('Lookback') || s.html().includes('Lookback'))
      expect(lookbackSelect).toBeTruthy()
    })

    it('shows empty state when no data', async () => {
      const { wrapper } = await mountReports()
      await clickTab(wrapper, 'Runway')
      expect(wrapper.text()).toContain('Not enough spending data to calculate runway')
    })
  })

  describe('Goals Tab', () => {
    it('displays goals card', async () => {
      const { wrapper } = await mountReports()
      await clickTab(wrapper, 'Goals')
      expect(wrapper.text()).toContain('Savings Goal Progress')
    })

    it('shows empty state when no goals', async () => {
      const { wrapper } = await mountReports()
      await clickTab(wrapper, 'Goals')
      expect(wrapper.text()).toContain('No envelopes with target balances set')
    })
  })

  describe('Upcoming Tab', () => {
    it('displays upcoming card', async () => {
      const { wrapper } = await mountReports()
      await clickTab(wrapper, 'Upcoming')
      expect(wrapper.text()).toContain('Upcoming Expenses')
    })

    it('shows days ahead selector', async () => {
      const { wrapper } = await mountReports()
      await clickTab(wrapper, 'Upcoming')
      const selects = wrapper.findAll('.v-select')
      const daysSelect = selects.find((s) => s.text().includes('Days Ahead') || s.html().includes('Days Ahead'))
      expect(daysSelect).toBeTruthy()
    })

    it('shows empty state with no scheduled expenses', async () => {
      const { wrapper } = await mountReports()
      await clickTab(wrapper, 'Upcoming')
      expect(wrapper.text()).toContain('No upcoming scheduled expenses')
    })
  })

  describe('Recurring Tab', () => {
    it('displays recurring card', async () => {
      const { wrapper } = await mountReports()
      await clickTab(wrapper, 'Recurring')
      expect(wrapper.text()).toContain('Recurring Expense Coverage')
    })

    it('shows summary stats when data exists', async () => {
      const { wrapper } = await mountReports()
      await clickTab(wrapper, 'Recurring')
      // With zero data from MSW, recurring coverage is returned (total_recurring: 0)
      // The template renders summary cards when recurringCoverage is not null
      expect(wrapper.text()).toContain('Total')
      expect(wrapper.text()).toContain('Funded')
    })
  })

  describe('Trends Tab', () => {
    it('displays trends card', async () => {
      const { wrapper } = await mountReports()
      await clickTab(wrapper, 'Trends')
      expect(wrapper.text()).toContain('Spending Trends')
    })

    it('shows empty state when no data', async () => {
      const { wrapper } = await mountReports()
      await clickTab(wrapper, 'Trends')
      expect(wrapper.text()).toContain('No spending data for this period')
    })
  })

  describe('Locations Tab', () => {
    it('displays locations card', async () => {
      const { wrapper } = await mountReports()
      await clickTab(wrapper, 'Locations')
      expect(wrapper.text()).toContain('Spending by Location')
    })

    it('shows include-no-location checkbox', async () => {
      const { wrapper } = await mountReports()
      await clickTab(wrapper, 'Locations')
      expect(wrapper.text()).toContain('Include (No location)')
    })

    it('shows empty state when no data', async () => {
      const { wrapper } = await mountReports()
      await clickTab(wrapper, 'Locations')
      expect(wrapper.text()).toContain('No location data for this period')
    })
  })

  describe('Envelope History Tab', () => {
    it('displays envelope history card', async () => {
      const { wrapper } = await mountReports()
      await clickTab(wrapper, 'Envelope History')
      expect(wrapper.text()).toContain('Envelope Balance History')
    })

    it('shows envelope selector', async () => {
      const { wrapper } = await mountReports()
      await clickTab(wrapper, 'Envelope History')
      expect(wrapper.findComponent({ name: 'EnvelopeSelect' }).exists()).toBe(true)
    })

    it('shows empty state when no envelope selected', async () => {
      const { wrapper } = await mountReports()
      await clickTab(wrapper, 'Envelope History')
      expect(wrapper.text()).toContain('Select an envelope to view its balance history')
    })
  })

  describe('Account History Tab', () => {
    it('displays account history card', async () => {
      const { wrapper } = await mountReports()
      await clickTab(wrapper, 'Account History')
      expect(wrapper.text()).toContain('Account Balance History')
    })

    it('shows account selector', async () => {
      const { wrapper } = await mountReports()
      await clickTab(wrapper, 'Account History')
      expect(wrapper.findComponent({ name: 'AccountSelect' }).exists()).toBe(true)
    })

    it('shows empty state when no account selected', async () => {
      const { wrapper } = await mountReports()
      await clickTab(wrapper, 'Account History')
      expect(wrapper.text()).toContain('Select an account to view its balance history')
    })
  })

  describe('Allocation Rules Tab', () => {
    it('displays allocation rules card', async () => {
      const { wrapper } = await mountReports()
      await clickTab(wrapper, 'Allocation Rules')
      expect(wrapper.text()).toContain('Allocation Rule Effectiveness')
    })

    it('shows active-rules-only checkbox', async () => {
      const { wrapper } = await mountReports()
      await clickTab(wrapper, 'Allocation Rules')
      expect(wrapper.text()).toContain('Active rules only')
    })

    it('shows empty state when no rules', async () => {
      const { wrapper } = await mountReports()
      await clickTab(wrapper, 'Allocation Rules')
      expect(wrapper.text()).toContain('No allocation rules configured')
    })
  })

  describe('Tab Navigation', () => {
    it('can navigate through all tabs and see each card', async () => {
      const { wrapper } = await mountReports()

      const tabsAndContent: [string, string][] = [
        ['Spending', 'Spending by Envelope'],
        ['Cash Flow', 'Income vs Expenses'],
        ['Net Worth', 'Net Worth'],
        ['Top Payees', 'Top Payees'],
        ['Runway', 'Days of Runway'],
        ['Goals', 'Savings Goal Progress'],
        ['Upcoming', 'Upcoming Expenses'],
        ['Recurring', 'Recurring Expense Coverage'],
        ['Trends', 'Spending Trends'],
        ['Locations', 'Spending by Location'],
        ['Envelope History', 'Envelope Balance History'],
        ['Account History', 'Account Balance History'],
        ['Allocation Rules', 'Allocation Rule Effectiveness'],
      ]

      for (const [tabLabel, expectedContent] of tabsAndContent) {
        await clickTab(wrapper, tabLabel)
        expect(wrapper.text()).toContain(expectedContent)
      }
    })
  })
})
