import { type Page, type Locator, expect } from '@playwright/test'
import { BasePage } from './base.page'

/**
 * Page object for the Reports view.
 */
export class ReportsPage extends BasePage {
  // Header
  readonly pageTitle: Locator

  // Date filter
  readonly dateRangeButton: Locator

  // Tabs
  readonly spendingTab: Locator
  readonly cashFlowTab: Locator
  readonly netWorthTab: Locator
  readonly topPayeesTab: Locator
  readonly runwayTab: Locator
  readonly goalsTab: Locator
  readonly upcomingTab: Locator
  readonly recurringTab: Locator
  readonly trendsTab: Locator
  readonly locationsTab: Locator
  readonly envelopeHistoryTab: Locator
  readonly accountHistoryTab: Locator
  readonly allocationRulesTab: Locator

  // Spending tab
  readonly spendingCard: Locator
  readonly spendingPanels: Locator
  readonly spendingEmptyState: Locator

  // Cash Flow tab
  readonly cashFlowCard: Locator
  readonly incomeSummary: Locator
  readonly expensesSummary: Locator
  readonly netSummary: Locator
  readonly cashFlowTable: Locator
  readonly cashFlowEmptyState: Locator

  // Net Worth tab
  readonly netWorthCard: Locator
  readonly assetsSummary: Locator
  readonly liabilitiesSummary: Locator
  readonly netWorthSummary: Locator
  readonly netWorthChangeChip: Locator
  readonly netWorthChart: Locator
  readonly netWorthLineChart: Locator
  readonly netWorthPeriodPanels: Locator
  readonly netWorthEmptyState: Locator

  // Top Payees tab
  readonly topPayeesCard: Locator
  readonly topPayeesList: Locator
  readonly topPayeesEmptyState: Locator

  // Runway tab
  readonly runwayCard: Locator
  readonly overallRunwayChip: Locator
  readonly runwayList: Locator
  readonly runwayEmptyState: Locator
  readonly lookbackSelect: Locator
  readonly runwayTrendChart: Locator
  readonly runwayTrendTitle: Locator
  readonly showOverallButton: Locator

  // Goals tab
  readonly goalsCard: Locator
  readonly goalsList: Locator
  readonly goalsEmptyState: Locator

  // Upcoming tab
  readonly upcomingCard: Locator
  readonly upcomingTable: Locator
  readonly upcomingEmptyState: Locator
  readonly daysAheadSelect: Locator

  // Recurring tab
  readonly recurringCard: Locator
  readonly recurringList: Locator
  readonly recurringEmptyState: Locator
  readonly recurringTotalStat: Locator
  readonly recurringFundedStat: Locator

  // Trends tab
  readonly trendsCard: Locator
  readonly trendsChart: Locator
  readonly trendsTable: Locator
  readonly trendsEmptyState: Locator

  // Locations tab
  readonly locationsCard: Locator
  readonly locationsList: Locator
  readonly locationsEmptyState: Locator
  readonly includeNoLocationCheckbox: Locator

  // Envelope History tab
  readonly envelopeHistoryCard: Locator
  readonly envelopeHistoryChart: Locator
  readonly envelopeHistorySelect: Locator
  readonly envelopeHistoryEmptyState: Locator

  // Account History tab
  readonly accountHistoryCard: Locator
  readonly accountHistoryChart: Locator
  readonly accountHistorySelect: Locator
  readonly accountHistoryEmptyState: Locator

  // Allocation Rules tab
  readonly allocationRulesCard: Locator
  readonly allocationRulesTable: Locator
  readonly allocationRulesEmptyState: Locator
  readonly activeRulesOnlyCheckbox: Locator

  constructor(page: Page) {
    super(page)

    // Header
    this.pageTitle = page.locator('h1').filter({ hasText: 'Reports' })

    // Date filter - matches the DateRangePicker button with calendar icon
    this.dateRangeButton = page.locator('button').filter({ has: page.locator('.mdi-calendar') })

    // Tabs
    this.spendingTab = page.getByRole('tab', { name: 'Spending' })
    this.cashFlowTab = page.getByRole('tab', { name: 'Cash Flow' })
    this.netWorthTab = page.getByRole('tab', { name: 'Net Worth' })
    this.topPayeesTab = page.getByRole('tab', { name: 'Top Payees' })
    this.runwayTab = page.getByRole('tab', { name: 'Runway' })
    this.goalsTab = page.getByRole('tab', { name: 'Goals' })
    this.upcomingTab = page.getByRole('tab', { name: 'Upcoming' })
    this.recurringTab = page.getByRole('tab', { name: 'Recurring' })
    this.trendsTab = page.getByRole('tab', { name: 'Trends' })
    this.locationsTab = page.getByRole('tab', { name: 'Locations' })
    this.envelopeHistoryTab = page.getByRole('tab', { name: 'Envelope History' })
    this.accountHistoryTab = page.getByRole('tab', { name: 'Account History' })
    this.allocationRulesTab = page.getByRole('tab', { name: 'Allocation Rules' })

    // Spending tab elements
    this.spendingCard = page.locator('.v-card').filter({ hasText: 'Spending by Envelope' })
    this.spendingPanels = this.spendingCard.locator('.v-expansion-panels')
    this.spendingEmptyState = this.spendingCard.locator('text=No spending data for this period')

    // Cash Flow tab elements
    this.cashFlowCard = page.locator('.v-card').filter({ hasText: 'Income vs Expenses' })
    this.incomeSummary = this.cashFlowCard.locator('.text-center').filter({ hasText: 'Income' })
    this.expensesSummary = this.cashFlowCard.locator('.text-center').filter({ hasText: 'Expenses' })
    this.netSummary = this.cashFlowCard.locator('.text-center').filter({ hasText: 'Net' })
    this.cashFlowTable = this.cashFlowCard.locator('.v-table')
    this.cashFlowEmptyState = this.cashFlowCard.locator('text=No data for this period')

    // Net Worth tab elements
    this.netWorthCard = page.locator('.v-card').filter({ has: page.locator('.v-card-title', { hasText: 'Net Worth' }) })
    this.assetsSummary = this.netWorthCard.locator('.text-center').filter({ hasText: 'Assets' })
    this.liabilitiesSummary = this.netWorthCard.locator('.text-center').filter({ hasText: 'Liabilities' })
    this.netWorthSummary = this.netWorthCard.locator('.text-center').filter({ hasText: 'Net Worth' })
    this.netWorthChangeChip = this.netWorthCard.locator('.v-chip')
    this.netWorthChart = this.netWorthCard.locator('.net-worth-chart-container')
    this.netWorthLineChart = this.netWorthCard.locator('.net-worth-chart')
    this.netWorthPeriodPanels = this.netWorthCard.locator('.v-expansion-panels')
    this.netWorthEmptyState = this.netWorthCard.locator('text=No account data for this period')

    // Top Payees tab elements
    this.topPayeesCard = page.locator('.v-card').filter({ hasText: 'Top Payees' })
    this.topPayeesList = this.topPayeesCard.locator('.v-list')
    this.topPayeesEmptyState = this.topPayeesCard.locator('text=No payee data for this period')

    // Runway tab elements
    this.runwayCard = page.locator('.v-card').filter({ hasText: 'Days of Runway' })
    this.overallRunwayChip = this.runwayCard.locator('.v-chip').filter({ hasText: 'Overall:' })
    this.runwayList = this.runwayCard.locator('.v-list')
    this.runwayEmptyState = this.runwayCard.locator('text=Not enough spending data')
    this.lookbackSelect = this.runwayCard.locator('.v-select').filter({ hasText: 'Lookback' })
    this.runwayTrendChart = this.runwayCard.locator('.runway-chart')
    this.runwayTrendTitle = this.runwayCard.locator('.text-subtitle-2')
    this.showOverallButton = this.runwayCard.getByRole('button', { name: 'Show Overall' })

    // Goals tab elements
    this.goalsCard = page.locator('.v-card').filter({ hasText: 'Savings Goal Progress' })
    this.goalsList = this.goalsCard.locator('.v-list')
    this.goalsEmptyState = this.goalsCard.locator('text=No envelopes with target balances set')

    // Upcoming tab elements
    this.upcomingCard = page.locator('.v-card').filter({ hasText: 'Upcoming Expenses' })
    this.upcomingTable = this.upcomingCard.locator('.v-table')
    this.upcomingEmptyState = this.upcomingCard.locator('text=No upcoming scheduled expenses')
    this.daysAheadSelect = this.upcomingCard.locator('.v-select').filter({ hasText: 'Days Ahead' })

    // Recurring tab elements
    this.recurringCard = page.locator('.v-card').filter({ hasText: 'Recurring Expense Coverage' })
    this.recurringList = this.recurringCard.locator('.v-list')
    this.recurringEmptyState = this.recurringCard.locator('text=No recurring expenses configured')
    this.recurringTotalStat = this.recurringCard.locator('.text-center').filter({ hasText: 'Total' })
    this.recurringFundedStat = this.recurringCard.locator('.text-center').filter({ hasText: 'Funded' })

    // Trends tab elements
    this.trendsCard = page.locator('.v-card').filter({ hasText: 'Spending Trends' })
    this.trendsChart = this.trendsCard.locator('.spending-trends-chart-container')
    this.trendsTable = this.trendsCard.locator('.v-table')
    this.trendsEmptyState = this.trendsCard.locator('text=No spending data for this period')

    // Locations tab elements
    this.locationsCard = page.locator('.v-card').filter({ hasText: 'Spending by Location' })
    this.locationsList = this.locationsCard.locator('.v-list')
    this.locationsEmptyState = this.locationsCard.locator('text=No location data for this period')
    this.includeNoLocationCheckbox = this.locationsCard.locator('.v-checkbox')

    // Envelope History tab elements
    this.envelopeHistoryCard = page.locator('.v-card').filter({ hasText: 'Envelope Balance History' })
    this.envelopeHistoryChart = this.envelopeHistoryCard.locator('.balance-history-chart-container')
    this.envelopeHistorySelect = this.envelopeHistoryCard.locator('.v-autocomplete').filter({ hasText: 'Select Envelope' })
    this.envelopeHistoryEmptyState = this.envelopeHistoryCard.locator('text=Select an envelope to view')

    // Account History tab elements
    this.accountHistoryCard = page.locator('.v-card').filter({ hasText: 'Account Balance History' })
    this.accountHistoryChart = this.accountHistoryCard.locator('.balance-history-chart-container')
    this.accountHistorySelect = this.accountHistoryCard.locator('.v-select').filter({ hasText: 'Select Account' })
    this.accountHistoryEmptyState = this.accountHistoryCard.locator('text=Select an account to view')

    // Allocation Rules tab elements
    this.allocationRulesCard = page.locator('.v-card').filter({ hasText: 'Allocation Rule Effectiveness' })
    this.allocationRulesTable = this.allocationRulesCard.locator('.v-table')
    this.allocationRulesEmptyState = this.allocationRulesCard.locator('text=No allocation rules configured')
    this.activeRulesOnlyCheckbox = this.allocationRulesCard.locator('.v-checkbox')
  }

  async goto() {
    await this.page.goto('/reports')
    await this.waitForPageLoad()
  }

  /**
   * Set a custom date range for reports.
   */
  async setDateRange(startDate: string, endDate: string) {
    // Open dropdown and select Custom
    await this.dateRangeButton.click()
    await this.page.getByRole('listitem').filter({ hasText: 'Custom...' }).click()

    // Fill in custom dates in dialog
    const dialog = this.page.locator('.v-dialog')
    await dialog.locator('input[type="date"]').first().fill(startDate)
    await dialog.locator('input[type="date"]').nth(1).fill(endDate)
    await dialog.getByRole('button', { name: 'Apply' }).click()
    await this.waitForPageLoad()
  }

  /**
   * Select a date preset from the dropdown.
   */
  async selectDatePreset(
    preset: 'This Month' | 'Last Month' | 'Last 3 Months' | 'Year to Date'
  ) {
    await this.dateRangeButton.click()
    await this.page.getByRole('listitem').filter({ hasText: preset }).click()
    await this.waitForPageLoad()
  }

  /**
   * Navigate to the Spending tab.
   */
  async goToSpendingTab() {
    await this.spendingTab.click()
    await expect(this.spendingCard).toBeVisible()
  }

  /**
   * Navigate to the Cash Flow tab.
   */
  async goToCashFlowTab() {
    await this.cashFlowTab.click()
    await expect(this.cashFlowCard).toBeVisible()
  }

  /**
   * Navigate to the Net Worth tab.
   */
  async goToNetWorthTab() {
    await this.netWorthTab.click()
    await expect(this.netWorthCard).toBeVisible()
  }

  /**
   * Navigate to the Top Payees tab.
   */
  async goToTopPayeesTab() {
    await this.topPayeesTab.click()
    await expect(this.topPayeesCard).toBeVisible()
  }

  /**
   * Navigate to the Runway tab.
   */
  async goToRunwayTab() {
    await this.runwayTab.click()
    await expect(this.runwayCard).toBeVisible()
  }

  /**
   * Navigate to the Goals tab.
   */
  async goToGoalsTab() {
    await this.goalsTab.click()
    await expect(this.goalsCard).toBeVisible()
  }

  /**
   * Navigate to the Upcoming tab.
   */
  async goToUpcomingTab() {
    await this.upcomingTab.click()
    await expect(this.upcomingCard).toBeVisible()
  }

  /**
   * Navigate to the Recurring tab.
   */
  async goToRecurringTab() {
    await this.recurringTab.click()
    await expect(this.recurringCard).toBeVisible()
  }

  /**
   * Navigate to the Trends tab.
   */
  async goToTrendsTab() {
    await this.trendsTab.click()
    await expect(this.trendsCard).toBeVisible()
  }

  /**
   * Navigate to the Locations tab.
   */
  async goToLocationsTab() {
    await this.locationsTab.click()
    await expect(this.locationsCard).toBeVisible()
  }

  /**
   * Navigate to the Envelope History tab.
   */
  async goToEnvelopeHistoryTab() {
    await this.envelopeHistoryTab.click()
    await expect(this.envelopeHistoryCard).toBeVisible()
  }

  /**
   * Navigate to the Account History tab.
   */
  async goToAccountHistoryTab() {
    await this.accountHistoryTab.click()
    await expect(this.accountHistoryCard).toBeVisible()
  }

  /**
   * Navigate to the Allocation Rules tab.
   */
  async goToAllocationRulesTab() {
    await this.allocationRulesTab.click()
    await expect(this.allocationRulesCard).toBeVisible()
  }

  /**
   * Get spending panel by envelope name.
   */
  getSpendingPanel(envelopeName: string): Locator {
    return this.spendingPanels.locator('.v-expansion-panel').filter({ hasText: envelopeName })
  }

  /**
   * Expand a spending item to see average breakdowns.
   */
  async expandSpendingItem(envelopeName: string) {
    const panel = this.getSpendingPanel(envelopeName)
    await panel.locator('.v-expansion-panel-title').click()
    await expect(panel.locator('.v-expansion-panel-text')).toBeVisible()
  }

  /**
   * Get the averages from an expanded spending item.
   * Returns daily, weekly, monthly, yearly averages as strings.
   */
  async getSpendingAverages(envelopeName: string): Promise<{
    daily: string
    weekly: string
    monthly: string
    yearly: string
  }> {
    const panel = this.getSpendingPanel(envelopeName)
    const expandedContent = panel.locator('.v-expansion-panel-text')

    // MoneyDisplay renders as a span with font-weight-medium class in the v-list-item__append slot
    const daily = await expandedContent
      .locator('.v-list-item')
      .filter({ hasText: 'Daily Average' })
      .locator('.v-list-item__append span')
      .textContent()
    const weekly = await expandedContent
      .locator('.v-list-item')
      .filter({ hasText: 'Weekly Average' })
      .locator('.v-list-item__append span')
      .textContent()
    const monthly = await expandedContent
      .locator('.v-list-item')
      .filter({ hasText: 'Monthly Average' })
      .locator('.v-list-item__append span')
      .textContent()
    const yearly = await expandedContent
      .locator('.v-list-item')
      .filter({ hasText: 'Yearly Average' })
      .locator('.v-list-item__append span')
      .textContent()

    return {
      daily: daily || '',
      weekly: weekly || '',
      monthly: monthly || '',
      yearly: yearly || '',
    }
  }

  /**
   * Get payee item by name.
   */
  getPayeeItem(payeeName: string): Locator {
    return this.topPayeesList.locator('.v-list-item').filter({ hasText: payeeName })
  }

  /**
   * Get runway item by envelope name.
   */
  getRunwayItem(envelopeName: string): Locator {
    return this.runwayList.locator('.v-list-item').filter({ hasText: envelopeName })
  }

  /**
   * Get goal item by envelope name.
   */
  getGoalItem(envelopeName: string): Locator {
    return this.goalsList.locator('.v-list-item').filter({ hasText: envelopeName })
  }

  /**
   * Get the income total from Cash Flow tab.
   */
  async getIncomeTotal(): Promise<string> {
    const text = await this.incomeSummary.locator('.text-h6').textContent()
    return text || ''
  }

  /**
   * Get the expenses total from Cash Flow tab.
   */
  async getExpensesTotal(): Promise<string> {
    const text = await this.expensesSummary.locator('.text-h6').textContent()
    return text || ''
  }

  /**
   * Get the net total from Cash Flow tab.
   */
  async getNetTotal(): Promise<string> {
    const text = await this.netSummary.locator('.text-h6').textContent()
    return text || ''
  }

  /**
   * Get the overall runway value.
   */
  async getOverallRunway(): Promise<string> {
    const text = await this.overallRunwayChip.textContent()
    return text?.replace('Overall:', '').trim() || ''
  }

  /**
   * Check if spending tab shows data.
   */
  async hasSpendingData(): Promise<boolean> {
    return !(await this.spendingEmptyState.isVisible())
  }

  /**
   * Check if cash flow tab shows data.
   */
  async hasCashFlowData(): Promise<boolean> {
    return !(await this.cashFlowEmptyState.isVisible().catch(() => true))
  }

  /**
   * Check if top payees tab shows data.
   */
  async hasPayeeData(): Promise<boolean> {
    return !(await this.topPayeesEmptyState.isVisible())
  }

  /**
   * Check if runway tab shows data.
   */
  async hasRunwayData(): Promise<boolean> {
    return !(await this.runwayEmptyState.isVisible())
  }

  /**
   * Check if goals tab shows data.
   */
  async hasGoalsData(): Promise<boolean> {
    return !(await this.goalsEmptyState.isVisible())
  }

  /**
   * Check if net worth tab shows data.
   */
  async hasNetWorthData(): Promise<boolean> {
    return !(await this.netWorthEmptyState.isVisible())
  }

  /**
   * Get the assets total from Net Worth tab.
   */
  async getAssetsTotal(): Promise<string> {
    const text = await this.assetsSummary.locator('.text-h6').textContent()
    return text || ''
  }

  /**
   * Get the liabilities total from Net Worth tab.
   */
  async getLiabilitiesTotal(): Promise<string> {
    const text = await this.liabilitiesSummary.locator('.text-h6').textContent()
    return text || ''
  }

  /**
   * Get the net worth total from Net Worth tab.
   */
  async getNetWorthTotal(): Promise<string> {
    const text = await this.netWorthSummary.locator('.text-h6').textContent()
    return text || ''
  }

  /**
   * Get the net worth change from the chip.
   */
  async getNetWorthChange(): Promise<string> {
    const text = await this.netWorthChangeChip.textContent()
    return text?.trim() || ''
  }

  /**
   * Get the number of periods in the net worth chart (counts data points in line chart).
   */
  async getNetWorthPeriodCount(): Promise<number> {
    return await this.netWorthLineChart.locator('.data-point').count()
  }

  /**
   * Check if the net worth line chart is visible.
   */
  async hasNetWorthLineChart(): Promise<boolean> {
    return await this.netWorthLineChart.isVisible()
  }

  /**
   * Expand a period panel to see account breakdown.
   */
  async expandNetWorthPeriod(monthLabel: string) {
    const panel = this.netWorthPeriodPanels
      .locator('.v-expansion-panel')
      .filter({ hasText: monthLabel })
    await panel.locator('.v-expansion-panel-title').click()
    await expect(panel.locator('.v-expansion-panel-text')).toBeVisible()
  }

  /**
   * Get the count of accounts shown in an expanded period.
   */
  async getExpandedPeriodAccountCount(): Promise<number> {
    return await this.netWorthPeriodPanels
      .locator('.v-expansion-panel-text .v-list-item')
      .count()
  }

  /**
   * Get the count of spending categories.
   */
  async getSpendingCategoryCount(): Promise<number> {
    return await this.spendingPanels.locator('.v-expansion-panel').count()
  }

  /**
   * Get the count of top payees.
   */
  async getPayeeCount(): Promise<number> {
    return await this.topPayeesList.locator('.v-list-item').count()
  }

  /**
   * Get the count of runway items.
   */
  async getRunwayItemCount(): Promise<number> {
    return await this.runwayList.locator('.v-list-item').count()
  }

  /**
   * Get the count of goal items.
   */
  async getGoalItemCount(): Promise<number> {
    return await this.goalsList.locator('.v-list-item').count()
  }

  /**
   * Assert page title is visible.
   */
  async expectPageTitle() {
    await expect(this.pageTitle).toBeVisible()
  }

  /**
   * Assert date filter is visible.
   */
  async expectDateFilterVisible() {
    await expect(this.dateRangeButton).toBeVisible()
  }

  /**
   * Assert all tabs are visible.
   */
  async expectTabsVisible() {
    await expect(this.spendingTab).toBeVisible()
    await expect(this.cashFlowTab).toBeVisible()
    await expect(this.netWorthTab).toBeVisible()
    await expect(this.topPayeesTab).toBeVisible()
    await expect(this.runwayTab).toBeVisible()
    await expect(this.goalsTab).toBeVisible()
    await expect(this.upcomingTab).toBeVisible()
    await expect(this.recurringTab).toBeVisible()
    await expect(this.trendsTab).toBeVisible()
    await expect(this.locationsTab).toBeVisible()
    await expect(this.envelopeHistoryTab).toBeVisible()
    await expect(this.accountHistoryTab).toBeVisible()
    await expect(this.allocationRulesTab).toBeVisible()
  }

  /**
   * Select a lookback period for runway calculation.
   */
  async selectLookbackPeriod(days: number) {
    await this.lookbackSelect.click()
    await this.page.getByRole('option', { name: `${days} days` }).click()
    // Wait for selection to be reflected in the UI
    await expect(this.lookbackSelect.locator('.v-select__selection-text')).toHaveText(`${days} days`)
  }

  /**
   * Get the currently selected lookback period text.
   */
  async getLookbackPeriod(): Promise<string> {
    const text = await this.lookbackSelect.locator('.v-select__selection-text').textContent()
    return text || ''
  }

  /**
   * Check if the runway trend chart is visible.
   */
  async hasTrendChart(): Promise<boolean> {
    return await this.runwayTrendChart.isVisible()
  }

  /**
   * Get the runway trend title (e.g., "Overall Runway Trend" or "Groceries Runway Trend").
   */
  async getTrendTitle(): Promise<string> {
    const text = await this.runwayTrendTitle.textContent()
    return text?.trim() || ''
  }

  /**
   * Get the number of data points (bars) in the trend chart.
   */
  async getTrendDataPointCount(): Promise<number> {
    return await this.runwayTrendChart.locator('.chart-bar').count()
  }

  /**
   * Click on an envelope to show its trend.
   */
  async clickEnvelopeForTrend(envelopeName: string) {
    const item = this.getRunwayItem(envelopeName)
    await item.click()
    // Wait for trend title to update to show envelope name
    await expect(this.runwayTrendTitle).toContainText(envelopeName)
  }

  /**
   * Click the "Show Overall" button to return to overall trend.
   */
  async clickShowOverall() {
    await this.showOverallButton.click()
    // Wait for trend title to update to show "Overall"
    await expect(this.runwayTrendTitle).toContainText('Overall')
  }

  /**
   * Check if "Show Overall" button is visible (only when viewing envelope trend).
   */
  async isShowOverallVisible(): Promise<boolean> {
    return await this.showOverallButton.isVisible()
  }

  /**
   * Check if the "not enough historical data" message is visible.
   */
  async hasInsufficientDataMessage(): Promise<boolean> {
    return await this.runwayCard.locator('text=Not enough historical data').isVisible()
  }
}
