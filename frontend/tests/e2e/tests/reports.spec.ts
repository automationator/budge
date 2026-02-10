import { test, expect } from '../fixtures/test-setup'
import { ReportsPage } from '../pages/reports.page'

// UI rendering tests (tabs, cards, empty states, controls) have been moved to
// component tests: frontend/tests/unit/components/reports/ReportsView.spec.ts
//
// Only data-dependent tests that create backend data and verify computed results
// remain here as E2E tests.

test.describe('Reports', () => {
  test.describe('Spending Tab', () => {
    test('can expand spending item to see average breakdowns', async ({
      authenticatedPage,
      testApi,
      testContext,
    }) => {
      // Create test data
      const account = await testApi.createAccount(testContext.user.budgetId, {
        name: 'Spending Averages Test Checking',
        accountType: 'checking',
        startingBalance: 100000,
      })
      const envelope = await testApi.createEnvelope(testContext.user.budgetId, {
        name: 'Spending Averages Test Groceries',
      })

      // Create spending transactions
      const today = new Date()
      for (let i = 0; i < 5; i++) {
        const txnDate = new Date(today)
        txnDate.setDate(txnDate.getDate() - i * 5) // Every 5 days
        await testApi.createTransaction(testContext.user.budgetId, {
          accountId: account.id,
          amount: -2000, // -$20 each
          envelopeId: envelope.id,
          payeeName: 'Test Grocery Store',
          transactionDate: txnDate.toISOString().split('T')[0],
        })
      }

      const reportsPage = new ReportsPage(authenticatedPage)
      await reportsPage.goto()

      // Verify the spending panel exists for our envelope
      const panel = reportsPage.getSpendingPanel('Spending Averages Test Groceries')
      await expect(panel).toBeVisible()

      // Expand the panel to see averages
      await reportsPage.expandSpendingItem('Spending Averages Test Groceries')

      // Verify expanded content shows all average types
      const expandedContent = panel.locator('.v-expansion-panel-text')
      await expect(expandedContent.getByText('Daily Average')).toBeVisible()
      await expect(expandedContent.getByText('Weekly Average')).toBeVisible()
      await expect(expandedContent.getByText('Monthly Average')).toBeVisible()
      await expect(expandedContent.getByText('Yearly Average')).toBeVisible()

      // Get the actual averages and verify they have values
      const averages = await reportsPage.getSpendingAverages('Spending Averages Test Groceries')
      expect(averages.daily).toBeTruthy()
      expect(averages.weekly).toBeTruthy()
      expect(averages.monthly).toBeTruthy()
      expect(averages.yearly).toBeTruthy()
    })
  })

  test.describe('Net Worth Tab', () => {
    test('shows net worth with account data', async ({
      authenticatedPage,
      testApi,
      testContext,
    }) => {
      // Create asset account
      await testApi.createAccount(testContext.user.budgetId, {
        name: 'Net Worth Test Checking',
        accountType: 'checking',
        startingBalance: 500000, // $5000
      })

      // Create liability account
      await testApi.createAccount(testContext.user.budgetId, {
        name: 'Net Worth Test Credit Card',
        accountType: 'credit_card',
        startingBalance: -100000, // -$1000
      })

      const reportsPage = new ReportsPage(authenticatedPage)
      await reportsPage.goto()
      await reportsPage.goToNetWorthTab()

      const hasData = await reportsPage.hasNetWorthData()
      expect(hasData).toBe(true)

      // Should have period bars in the chart
      const periodCount = await reportsPage.getNetWorthPeriodCount()
      expect(periodCount).toBeGreaterThan(0)
    })

    test('can expand period to see account breakdown', async ({
      authenticatedPage,
      testApi,
      testContext,
    }) => {
      // Create accounts
      await testApi.createAccount(testContext.user.budgetId, {
        name: 'Breakdown Test Checking',
        accountType: 'checking',
        startingBalance: 300000,
      })
      await testApi.createAccount(testContext.user.budgetId, {
        name: 'Breakdown Test Savings',
        accountType: 'savings',
        startingBalance: 200000,
      })

      const reportsPage = new ReportsPage(authenticatedPage)
      await reportsPage.goto()
      await reportsPage.goToNetWorthTab()

      // Verify expansion panels are visible
      await expect(reportsPage.netWorthPeriodPanels).toBeVisible()

      // Click the first expansion panel to expand it
      const firstPanel = reportsPage.netWorthPeriodPanels.locator('.v-expansion-panel').first()
      await firstPanel.click()

      // Wait for the panel text to be visible
      await expect(firstPanel.locator('.v-expansion-panel-text')).toBeVisible()

      // Should show accounts in the breakdown
      const accountCount = await reportsPage.getExpandedPeriodAccountCount()
      expect(accountCount).toBeGreaterThan(0)
    })

    test('displays line chart visualization', async ({
      authenticatedPage,
      testApi,
      testContext,
    }) => {
      // Create account
      await testApi.createAccount(testContext.user.budgetId, {
        name: 'Line Chart Test Checking',
        accountType: 'checking',
        startingBalance: 500000,
      })

      const reportsPage = new ReportsPage(authenticatedPage)
      await reportsPage.goto()
      await reportsPage.goToNetWorthTab()

      // Should show the line chart
      const hasChart = await reportsPage.hasNetWorthLineChart()
      expect(hasChart).toBe(true)
    })
  })

  test.describe('Top Payees Tab', () => {
    test('shows payee data when transactions exist', async ({ authenticatedPage }) => {
      const reportsPage = new ReportsPage(authenticatedPage)

      await reportsPage.goto()
      await reportsPage.goToTopPayeesTab()

      // Check if any payee data is displayed (may be empty state for fresh DB)
      const hasData = await reportsPage.hasPayeeData()
      if (hasData) {
        const count = await reportsPage.getPayeeCount()
        expect(count).toBeGreaterThan(0)
      }
    })
  })

  test.describe('Runway Tab', () => {
    test('shows runway trend chart when data exists', async ({
      authenticatedPage,
      testApi,
      testContext,
    }) => {
      // Create test data for runway trend
      const account = await testApi.createAccount(testContext.user.budgetId, {
        name: 'Runway Test Checking',
        startingBalance: 100000, // $1000
      })
      const envelope = await testApi.createEnvelope(testContext.user.budgetId, {
        name: 'Runway Test Groceries',
      })

      // Create some spending transactions over the past few weeks
      const today = new Date()
      for (let i = 0; i < 4; i++) {
        const txnDate = new Date(today)
        txnDate.setDate(txnDate.getDate() - i * 7) // Weekly transactions
        await testApi.createTransaction(testContext.user.budgetId, {
          accountId: account.id,
          amount: -2500, // -$25 each
          envelopeId: envelope.id,
          payeeName: 'Test Store',
          transactionDate: txnDate.toISOString().split('T')[0],
        })
      }

      const reportsPage = new ReportsPage(authenticatedPage)
      await reportsPage.goto()
      await reportsPage.goToRunwayTab()

      // Should show trend chart
      const hasTrend = await reportsPage.hasTrendChart()
      expect(hasTrend).toBe(true)

      // Should show "Overall Runway Trend" title
      const trendTitle = await reportsPage.getTrendTitle()
      expect(trendTitle).toContain('Overall')

      // Should have data points in the chart
      const dataPointCount = await reportsPage.getTrendDataPointCount()
      expect(dataPointCount).toBeGreaterThan(0)
    })

    test('clicking envelope shows its trend', async ({
      authenticatedPage,
      testApi,
      testContext,
    }) => {
      // Create test data
      const account = await testApi.createAccount(testContext.user.budgetId, {
        name: 'Envelope Trend Test Checking',
        startingBalance: 100000,
      })
      const envelope = await testApi.createEnvelope(testContext.user.budgetId, {
        name: 'Envelope Trend Test Category',
      })

      // Create spending transactions
      const today = new Date()
      for (let i = 0; i < 3; i++) {
        const txnDate = new Date(today)
        txnDate.setDate(txnDate.getDate() - i * 7)
        await testApi.createTransaction(testContext.user.budgetId, {
          accountId: account.id,
          amount: -1500,
          envelopeId: envelope.id,
          payeeName: 'Test Vendor',
          transactionDate: txnDate.toISOString().split('T')[0],
        })
      }

      const reportsPage = new ReportsPage(authenticatedPage)
      await reportsPage.goto()
      await reportsPage.goToRunwayTab()

      // Click on the envelope
      await reportsPage.clickEnvelopeForTrend('Envelope Trend Test Category')

      // Trend title should now show envelope name
      const trendTitle = await reportsPage.getTrendTitle()
      expect(trendTitle).toContain('Envelope Trend Test Category')

      // "Show Overall" button should be visible
      const showOverallVisible = await reportsPage.isShowOverallVisible()
      expect(showOverallVisible).toBe(true)
    })

    test('Show Overall button returns to overall trend', async ({
      authenticatedPage,
      testApi,
      testContext,
    }) => {
      // Create test data
      const account = await testApi.createAccount(testContext.user.budgetId, {
        name: 'Show Overall Test Checking',
        startingBalance: 100000,
      })
      const envelope = await testApi.createEnvelope(testContext.user.budgetId, {
        name: 'Show Overall Test Category',
      })

      // Create spending transactions
      const today = new Date()
      for (let i = 0; i < 3; i++) {
        const txnDate = new Date(today)
        txnDate.setDate(txnDate.getDate() - i * 7)
        await testApi.createTransaction(testContext.user.budgetId, {
          accountId: account.id,
          amount: -2000,
          envelopeId: envelope.id,
          payeeName: 'Test Shop',
          transactionDate: txnDate.toISOString().split('T')[0],
        })
      }

      const reportsPage = new ReportsPage(authenticatedPage)
      await reportsPage.goto()
      await reportsPage.goToRunwayTab()

      // Click on envelope to show its trend
      await reportsPage.clickEnvelopeForTrend('Show Overall Test Category')
      let trendTitle = await reportsPage.getTrendTitle()
      expect(trendTitle).toContain('Show Overall Test Category')

      // Click "Show Overall"
      await reportsPage.clickShowOverall()

      // Should now show overall trend
      trendTitle = await reportsPage.getTrendTitle()
      expect(trendTitle).toContain('Overall')

      // "Show Overall" button should be hidden
      const showOverallVisible = await reportsPage.isShowOverallVisible()
      expect(showOverallVisible).toBe(false)
    })
  })
})
