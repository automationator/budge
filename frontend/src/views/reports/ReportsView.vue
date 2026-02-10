<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useAuthStore } from '@/stores/auth'
import { useEnvelopesStore } from '@/stores/envelopes'
import type { DateRangePreset } from '@/stores/envelopes'
import { showSnackbar } from '@/App.vue'
import MoneyDisplay from '@/components/common/MoneyDisplay.vue'
import DateRangePicker from '@/components/common/DateRangePicker.vue'
import NetWorthChart from '@/components/reports/NetWorthChart.vue'
import BalanceHistoryChart from '@/components/reports/BalanceHistoryChart.vue'
import SpendingTrendsChart from '@/components/reports/SpendingTrendsChart.vue'
import FundingStatusChip from '@/components/reports/FundingStatusChip.vue'
import EnvelopeSelect from '@/components/common/EnvelopeSelect.vue'
import AccountSelect from '@/components/common/AccountSelect.vue'
import { useAccountsStore } from '@/stores/accounts'
import {
  getSpendingByCategory,
  getIncomeVsExpenses,
  getPayeeAnalysis,
  getDaysOfRunway,
  getSavingsGoalProgress,
  getRunwayTrend,
  getNetWorth,
  getUpcomingExpenses,
  getRecurringExpenseCoverage,
  getSpendingTrends,
  getLocationSpending,
  getEnvelopeBalanceHistory,
  getAccountBalanceHistory,
  getAllocationRuleEffectiveness,
  type SpendingByCategoryItem,
  type IncomeVsExpensesPeriod,
  type PayeeAnalysisItem,
  type DaysOfRunwayItem,
  type SavingsGoalItem,
  type RunwayTrendResponse,
  type NetWorthResponse,
  type NetWorthAccountItem,
  type UpcomingExpenseItem,
  type RecurringExpenseCoverageResponse,
  type SpendingTrendsResponse,
  type LocationSpendingItem,
  type EnvelopeBalanceHistoryResponse,
  type AccountBalanceHistoryResponse,
  type AllocationRuleEffectivenessItem,
} from '@/api/reports'

const authStore = useAuthStore()
const envelopesStore = useEnvelopesStore()
const accountsStore = useAccountsStore()

const loading = ref(false)
const activeTab = ref('spending')

// Date filters
const startDate = ref('')
const endDate = ref('')

// Report data
const spendingByCategory = ref<SpendingByCategoryItem[]>([])
const incomeVsExpenses = ref<IncomeVsExpensesPeriod[]>([])
const incomeTotals = ref({ income: 0, expenses: 0, net: 0 })
const topPayees = ref<PayeeAnalysisItem[]>([])
const runwayData = ref<DaysOfRunwayItem[]>([])
const overallRunway = ref<number | null>(null)
const savingsGoals = ref<SavingsGoalItem[]>([])
const netWorthData = ref<NetWorthResponse | null>(null)

// New report data
const upcomingExpenses = ref<UpcomingExpenseItem[]>([])
const recurringCoverage = ref<RecurringExpenseCoverageResponse | null>(null)
const spendingTrends = ref<SpendingTrendsResponse | null>(null)
const locationSpending = ref<LocationSpendingItem[]>([])
const envelopeBalanceHistory = ref<EnvelopeBalanceHistoryResponse | null>(null)
const accountBalanceHistory = ref<AccountBalanceHistoryResponse | null>(null)
const allocationRules = ref<AllocationRuleEffectivenessItem[]>([])

// Selectors for balance history
const selectedEnvelopeForHistory = ref<string | null>(null)
const selectedAccountForHistory = ref<string | null>(null)

// Controls for new reports
const daysAhead = ref(90)
const daysAheadOptions = [
  { title: '30 days', value: 30 },
  { title: '60 days', value: 60 },
  { title: '90 days', value: 90 },
  { title: '180 days', value: 180 },
  { title: '1 year', value: 365 },
]
const includeNoLocation = ref(true)
const activeRulesOnly = ref(true)

// Loading states for new reports
const loadingUpcoming = ref(false)
const loadingRecurring = ref(false)
const loadingTrends = ref(false)
const loadingLocations = ref(false)
const loadingEnvelopeHistory = ref(false)
const loadingAccountHistory = ref(false)
const loadingAllocationRules = ref(false)

// Runway trend data
const lookbackDays = ref(30)
const lookbackOptions = [
  { title: '7 days', value: 7 },
  { title: '30 days', value: 30 },
  { title: '60 days', value: 60 },
  { title: '90 days', value: 90 },
]
const selectedEnvelopeId = ref<string | null>(null)
const selectedEnvelopeName = ref<string | null>(null)
const runwayTrend = ref<RunwayTrendResponse | null>(null)
const loadingTrend = ref(false)

const loadingNetWorth = ref(false)

// Date range preset
const datePreset = ref<DateRangePreset>('last_3_months')

function formatDateStr(date: Date): string {
  return date.toISOString().split('T')[0] ?? ''
}

function handleDatePreset(preset: DateRangePreset) {
  datePreset.value = preset
  const today = new Date()
  switch (preset) {
    case 'this_month':
      startDate.value = formatDateStr(new Date(today.getFullYear(), today.getMonth(), 1))
      endDate.value = formatDateStr(today)
      break
    case 'last_month': {
      const lastMonth = new Date(today.getFullYear(), today.getMonth() - 1, 1)
      startDate.value = formatDateStr(lastMonth)
      endDate.value = formatDateStr(new Date(today.getFullYear(), today.getMonth(), 0))
      break
    }
    case 'last_3_months':
      startDate.value = formatDateStr(new Date(today.getFullYear(), today.getMonth() - 3, 1))
      endDate.value = formatDateStr(today)
      break
    case 'year_to_date':
      startDate.value = formatDateStr(new Date(today.getFullYear(), 0, 1))
      endDate.value = formatDateStr(today)
      break
  }
}

function handleCustomDateRange(start: string, end: string) {
  datePreset.value = 'custom'
  startDate.value = start
  endDate.value = end
}

// Set default date range (last 3 months)
const today = new Date()
const threeMonthsAgo = new Date(today.getFullYear(), today.getMonth() - 3, 1)
startDate.value = threeMonthsAgo.toISOString().split('T')[0] ?? ''
endDate.value = today.toISOString().split('T')[0] ?? ''

onMounted(async () => {
  await loadReports()
})

// Watch for lookback days changes to reload runway data
watch(lookbackDays, async () => {
  await loadRunwayData()
  await loadRunwayTrend()
})

async function loadReports() {
  if (!authStore.currentBudgetId) return

  try {
    loading.value = true

    const [spending, income, payees, runway, goals] = await Promise.all([
      getSpendingByCategory(authStore.currentBudgetId, startDate.value, endDate.value),
      getIncomeVsExpenses(authStore.currentBudgetId, startDate.value, endDate.value),
      getPayeeAnalysis(authStore.currentBudgetId, startDate.value, endDate.value),
      getDaysOfRunway(authStore.currentBudgetId, lookbackDays.value),
      getSavingsGoalProgress(authStore.currentBudgetId),
    ])

    spendingByCategory.value = spending.items.sort((a, b) => a.total_spent - b.total_spent)
    incomeVsExpenses.value = income.periods
    incomeTotals.value = {
      income: income.total_income,
      expenses: income.total_expenses,
      net: income.total_net,
    }
    topPayees.value = payees.items.slice(0, 10)
    runwayData.value = runway.items.filter((i) => i.days_of_runway !== null)
    overallRunway.value = runway.total_days_of_runway
    savingsGoals.value = goals.items

    // Load initial runway trend (overall), net worth, and additional reports
    await Promise.all([
      loadRunwayTrend(),
      loadNetWorth(),
      loadSelectorsData(),
      loadUpcomingExpenses(),
      loadRecurringCoverage(),
      loadSpendingTrends(),
      loadLocationSpending(),
      loadAllocationRules(),
    ])
  } catch {
    showSnackbar('Failed to load reports', 'error')
  } finally {
    loading.value = false
  }
}

async function loadNetWorth() {
  if (!authStore.currentBudgetId) return

  try {
    loadingNetWorth.value = true
    netWorthData.value = await getNetWorth(
      authStore.currentBudgetId,
      startDate.value || null,
      endDate.value
    )
  } catch {
    showSnackbar('Failed to load net worth data', 'error')
  } finally {
    loadingNetWorth.value = false
  }
}

async function loadRunwayData() {
  if (!authStore.currentBudgetId) return

  try {
    const runway = await getDaysOfRunway(authStore.currentBudgetId, lookbackDays.value)
    runwayData.value = runway.items.filter((i) => i.days_of_runway !== null)
    overallRunway.value = runway.total_days_of_runway
  } catch {
    showSnackbar('Failed to load runway data', 'error')
  }
}

async function loadRunwayTrend() {
  if (!authStore.currentBudgetId) return

  try {
    loadingTrend.value = true
    runwayTrend.value = await getRunwayTrend(
      authStore.currentBudgetId,
      startDate.value,
      endDate.value,
      lookbackDays.value,
      selectedEnvelopeId.value || undefined
    )
  } catch {
    showSnackbar('Failed to load runway trend', 'error')
  } finally {
    loadingTrend.value = false
  }
}

async function selectEnvelope(envelopeId: string | null, envelopeName: string | null) {
  selectedEnvelopeId.value = envelopeId
  selectedEnvelopeName.value = envelopeName
  await loadRunwayTrend()
}

// Load envelopes and accounts for selectors
async function loadSelectorsData() {
  if (!authStore.currentBudgetId) return
  try {
    // Fetch envelopes and accounts via stores (for select components)
    await Promise.all([
      envelopesStore.fetchEnvelopes(),
      accountsStore.fetchAccounts(),
    ])
  } catch {
    // Silently fail - selectors will just be empty
  }
}

// New report load functions
async function loadUpcomingExpenses() {
  if (!authStore.currentBudgetId) return
  try {
    loadingUpcoming.value = true
    const data = await getUpcomingExpenses(authStore.currentBudgetId, daysAhead.value)
    upcomingExpenses.value = data.items
  } catch {
    showSnackbar('Failed to load upcoming expenses', 'error')
  } finally {
    loadingUpcoming.value = false
  }
}

async function loadRecurringCoverage() {
  if (!authStore.currentBudgetId) return
  try {
    loadingRecurring.value = true
    recurringCoverage.value = await getRecurringExpenseCoverage(authStore.currentBudgetId)
  } catch {
    showSnackbar('Failed to load recurring expense coverage', 'error')
  } finally {
    loadingRecurring.value = false
  }
}

async function loadSpendingTrends() {
  if (!authStore.currentBudgetId || !startDate.value || !endDate.value) return
  try {
    loadingTrends.value = true
    spendingTrends.value = await getSpendingTrends(
      authStore.currentBudgetId,
      startDate.value,
      endDate.value
    )
  } catch {
    showSnackbar('Failed to load spending trends', 'error')
  } finally {
    loadingTrends.value = false
  }
}

async function loadLocationSpending() {
  if (!authStore.currentBudgetId) return
  try {
    loadingLocations.value = true
    const data = await getLocationSpending(
      authStore.currentBudgetId,
      startDate.value,
      endDate.value,
      includeNoLocation.value
    )
    locationSpending.value = data.items
  } catch {
    showSnackbar('Failed to load location spending', 'error')
  } finally {
    loadingLocations.value = false
  }
}

async function loadEnvelopeBalanceHistory() {
  if (!authStore.currentBudgetId || !selectedEnvelopeForHistory.value) return
  try {
    loadingEnvelopeHistory.value = true
    envelopeBalanceHistory.value = await getEnvelopeBalanceHistory(
      authStore.currentBudgetId,
      selectedEnvelopeForHistory.value,
      startDate.value,
      endDate.value
    )
  } catch {
    showSnackbar('Failed to load envelope balance history', 'error')
  } finally {
    loadingEnvelopeHistory.value = false
  }
}

async function loadAccountBalanceHistory() {
  if (!authStore.currentBudgetId || !selectedAccountForHistory.value) return
  try {
    loadingAccountHistory.value = true
    accountBalanceHistory.value = await getAccountBalanceHistory(
      authStore.currentBudgetId,
      selectedAccountForHistory.value,
      startDate.value,
      endDate.value
    )
  } catch {
    showSnackbar('Failed to load account balance history', 'error')
  } finally {
    loadingAccountHistory.value = false
  }
}

async function loadAllocationRules() {
  if (!authStore.currentBudgetId) return
  try {
    loadingAllocationRules.value = true
    const data = await getAllocationRuleEffectiveness(
      authStore.currentBudgetId,
      startDate.value,
      endDate.value,
      activeRulesOnly.value
    )
    allocationRules.value = data.items
  } catch {
    showSnackbar('Failed to load allocation rule effectiveness', 'error')
  } finally {
    loadingAllocationRules.value = false
  }
}

// Watchers for new reports
watch(daysAhead, () => loadUpcomingExpenses())
watch(includeNoLocation, () => loadLocationSpending())
watch(activeRulesOnly, () => loadAllocationRules())
watch(selectedEnvelopeForHistory, () => {
  if (selectedEnvelopeForHistory.value) loadEnvelopeBalanceHistory()
})
watch(selectedAccountForHistory, () => {
  if (selectedAccountForHistory.value) loadAccountBalanceHistory()
})
watch([startDate, endDate], () => {
  loadReports()
})

// Max location spending for progress bars
const maxLocationSpending = computed(() => {
  if (locationSpending.value.length === 0) return 1
  return Math.max(...locationSpending.value.map((i) => Math.abs(i.total_spent)))
})

function getLocationPercent(amount: number): number {
  return (Math.abs(amount) / maxLocationSpending.value) * 100
}

// Format rule type for display
function formatRuleType(type: string): string {
  const types: Record<string, string> = {
    fixed: 'Fixed',
    percentage: 'Percentage',
    fill_to_target: 'Fill to Target',
    remainder: 'Remainder',
    period_cap: 'Period Cap',
  }
  return types[type] || type
}

const maxTrendRunway = computed(() => {
  if (!runwayTrend.value || runwayTrend.value.data_points.length === 0) return 90
  const validPoints = runwayTrend.value.data_points
    .filter((p) => p.days_of_runway !== null)
    .map((p) => Math.abs(p.days_of_runway as number))
  if (validPoints.length === 0) return 90
  return Math.max(...validPoints, 30) // Minimum scale of 30 days
})

// Check if we have any trend data (at least 1 non-null point)
const hasValidTrendData = computed(() => {
  if (!runwayTrend.value) return false
  const validPoints = runwayTrend.value.data_points.filter((p) => p.days_of_runway !== null)
  return validPoints.length >= 1
})

// Check if we have enough data for a meaningful trend (2+ points)
const hasMeaningfulTrend = computed(() => {
  if (!runwayTrend.value) return false
  const validPoints = runwayTrend.value.data_points.filter((p) => p.days_of_runway !== null)
  return validPoints.length >= 2
})

// Calculate bar height for trend chart, handling negative values
function getTrendBarHeight(daysOfRunway: number | null): string {
  if (daysOfRunway === null) return '3px' // Fixed small height for no data
  const absValue = Math.abs(daysOfRunway)
  const percent = Math.min(100, Math.max(10, (absValue / maxTrendRunway.value) * 100))
  return `${percent}%`
}

// Get CSS color for runway value
function getRunwayCssColor(days: number | null): string {
  if (days === null) return '#e0e0e0' // grey
  if (days >= 90) return '#4caf50' // green (success)
  if (days >= 30) return '#ff9800' // orange (warning)
  return '#f44336' // red (error)
}

// Get bar style for trend chart
function getTrendBarStyle(daysOfRunway: number | null): Record<string, string> {
  if (daysOfRunway === null) {
    return {
      backgroundColor: '#e0e0e0',
      opacity: '0.5',
    }
  }
  return {
    backgroundColor: getRunwayCssColor(daysOfRunway),
    opacity: '1',
  }
}

const maxSpending = computed(() => {
  if (spendingByCategory.value.length === 0) return 1
  return Math.max(...spendingByCategory.value.map((i) => Math.abs(i.total_spent)))
})

const maxPayeeSpending = computed(() => {
  if (topPayees.value.length === 0) return 1
  return Math.max(...topPayees.value.map((i) => Math.abs(i.total_spent)))
})

function getSpendingPercent(amount: number): number {
  return (Math.abs(amount) / maxSpending.value) * 100
}

function getPayeePercent(amount: number): number {
  return (Math.abs(amount) / maxPayeeSpending.value) * 100
}

function formatRunway(days: number | null): string {
  if (days === null) return 'N/A'
  if (days >= 365) return `${Math.floor(days / 365)}y ${Math.floor((days % 365) / 30)}m`
  if (days >= 30) return `${Math.floor(days / 30)} months`
  return `${Math.round(days)} days`
}

function getRunwayColor(days: number | null): string {
  if (days === null) return 'grey'
  if (days >= 90) return 'success'
  if (days >= 30) return 'warning'
  return 'error'
}

// Net Worth helpers
function formatMonth(dateStr: string): string {
  // Parse date string directly to avoid timezone issues
  // dateStr is in YYYY-MM-DD format
  const parts = dateStr.split('-').map(Number)
  const year = parts[0] ?? 0
  const month = parts[1] ?? 1
  const monthNames = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
  return `${monthNames[month - 1]} ${year}`
}

function getAssets(accounts: NetWorthAccountItem[]): NetWorthAccountItem[] {
  return accounts.filter((a) => !a.is_liability)
}

function getLiabilities(accounts: NetWorthAccountItem[]): NetWorthAccountItem[] {
  return accounts.filter((a) => a.is_liability)
}
</script>

<template>
  <div>
    <h1 class="text-h4 mb-4">
      Reports
    </h1>

    <!-- Date Range Filter -->
    <div class="d-flex justify-end mb-4">
      <DateRangePicker
        :start-date="startDate"
        :end-date="endDate"
        :preset="datePreset"
        @update:preset="handleDatePreset"
        @update:custom-range="handleCustomDateRange"
      />
    </div>

    <!-- Report Tabs -->
    <v-tabs
      v-model="activeTab"
      class="mb-4"
    >
      <v-tab value="spending">
        Spending
      </v-tab>
      <v-tab value="income">
        Cash Flow
      </v-tab>
      <v-tab value="networth">
        Net Worth
      </v-tab>
      <v-tab value="payees">
        Top Payees
      </v-tab>
      <v-tab value="runway">
        Runway
      </v-tab>
      <v-tab value="goals">
        Goals
      </v-tab>
      <v-tab value="upcoming">
        Upcoming
      </v-tab>
      <v-tab value="recurring">
        Recurring
      </v-tab>
      <v-tab value="trends">
        Trends
      </v-tab>
      <v-tab value="locations">
        Locations
      </v-tab>
      <v-tab value="envelope-history">
        Envelope History
      </v-tab>
      <v-tab value="account-history">
        Account History
      </v-tab>
      <v-tab value="allocation-rules">
        Allocation Rules
      </v-tab>
    </v-tabs>

    <!-- Loading State -->
    <div
      v-if="loading"
      class="text-center py-8"
    >
      <v-progress-circular
        indeterminate
        color="primary"
      />
    </div>

    <template v-else>
      <!-- Spending by Envelope -->
      <v-card v-if="activeTab === 'spending'">
        <v-card-title>Spending by Envelope</v-card-title>
        <v-card-text v-if="spendingByCategory.length === 0">
          <p class="text-center text-grey py-4">
            No spending data for this period.
          </p>
        </v-card-text>
        <v-card-text v-else>
          <v-expansion-panels variant="accordion">
            <v-expansion-panel
              v-for="item in spendingByCategory"
              :key="item.envelope_id"
            >
              <v-expansion-panel-title>
                <div class="w-100">
                  <div class="d-flex justify-space-between align-center mb-1">
                    <span class="font-weight-medium">{{ item.envelope_name }}</span>
                    <MoneyDisplay :amount="item.total_spent" />
                  </div>
                  <v-progress-linear
                    :model-value="getSpendingPercent(item.total_spent)"
                    color="error"
                    height="8"
                    rounded
                  />
                  <div class="text-caption text-medium-emphasis mt-1">
                    {{ item.transaction_count }} transactions
                  </div>
                </div>
              </v-expansion-panel-title>
              <v-expansion-panel-text>
                <v-list
                  density="compact"
                  class="bg-transparent"
                >
                  <v-list-item>
                    <template #prepend>
                      <v-icon
                        size="small"
                        class="mr-2"
                      >
                        mdi-calendar-today
                      </v-icon>
                    </template>
                    <v-list-item-title>Daily Average</v-list-item-title>
                    <template #append>
                      <MoneyDisplay :amount="-item.average_daily" />
                    </template>
                  </v-list-item>
                  <v-list-item>
                    <template #prepend>
                      <v-icon
                        size="small"
                        class="mr-2"
                      >
                        mdi-calendar-week
                      </v-icon>
                    </template>
                    <v-list-item-title>Weekly Average</v-list-item-title>
                    <template #append>
                      <MoneyDisplay :amount="-item.average_weekly" />
                    </template>
                  </v-list-item>
                  <v-list-item>
                    <template #prepend>
                      <v-icon
                        size="small"
                        class="mr-2"
                      >
                        mdi-calendar-month
                      </v-icon>
                    </template>
                    <v-list-item-title>Monthly Average</v-list-item-title>
                    <template #append>
                      <MoneyDisplay :amount="-item.average_monthly" />
                    </template>
                  </v-list-item>
                  <v-list-item>
                    <template #prepend>
                      <v-icon
                        size="small"
                        class="mr-2"
                      >
                        mdi-calendar
                      </v-icon>
                    </template>
                    <v-list-item-title>Yearly Average</v-list-item-title>
                    <template #append>
                      <MoneyDisplay :amount="-item.average_yearly" />
                    </template>
                  </v-list-item>
                </v-list>
              </v-expansion-panel-text>
            </v-expansion-panel>
          </v-expansion-panels>
        </v-card-text>
      </v-card>

      <!-- Income vs Expenses -->
      <v-card v-if="activeTab === 'income'">
        <v-card-title>Income vs Expenses</v-card-title>
        <v-card-text class="cash-flow-card-text">
          <!-- Summary -->
          <v-row class="mb-4">
            <v-col cols="4">
              <div class="text-center">
                <div class="text-subtitle-2 text-medium-emphasis">
                  Income
                </div>
                <MoneyDisplay
                  :amount="incomeTotals.income"
                  class="text-h6 text-success"
                />
              </div>
            </v-col>
            <v-col cols="4">
              <div class="text-center">
                <div class="text-subtitle-2 text-medium-emphasis">
                  Expenses
                </div>
                <MoneyDisplay
                  :amount="-incomeTotals.expenses"
                  class="text-h6 text-error"
                />
              </div>
            </v-col>
            <v-col cols="4">
              <div class="text-center">
                <div class="text-subtitle-2 text-medium-emphasis">
                  Net
                </div>
                <MoneyDisplay
                  :amount="incomeTotals.net"
                  class="text-h6"
                  :class="incomeTotals.net >= 0 ? 'text-success' : 'text-error'"
                />
              </div>
            </v-col>
          </v-row>

          <v-divider class="my-4" />

          <!-- Monthly breakdown -->
          <div
            v-if="incomeVsExpenses.length === 0"
            class="text-center text-grey py-4"
          >
            No data for this period.
          </div>
          <div
            v-else
            class="table-scroll-container"
          >
            <v-table
              density="compact"
              class="cash-flow-table"
            >
              <thead>
                <tr>
                  <th>Month</th>
                  <th class="text-right">
                    Income
                  </th>
                  <th class="text-right">
                    Expenses
                  </th>
                  <th class="text-right">
                    Net
                  </th>
                </tr>
              </thead>
              <tbody>
                <tr
                  v-for="period in incomeVsExpenses"
                  :key="period.period_start"
                >
                  <td>{{ formatMonth(period.period_start) }}</td>
                  <td class="text-right text-success">
                    <MoneyDisplay :amount="period.income" />
                  </td>
                  <td class="text-right text-error">
                    <MoneyDisplay :amount="-period.expenses" />
                  </td>
                  <td
                    class="text-right font-weight-medium"
                    :class="period.net >= 0 ? 'text-success' : 'text-error'"
                  >
                    <MoneyDisplay :amount="period.net" />
                  </td>
                </tr>
              </tbody>
            </v-table>
          </div>
        </v-card-text>
      </v-card>

      <!-- Net Worth -->
      <v-card v-if="activeTab === 'networth'">
        <v-card-title>Net Worth</v-card-title>
        <v-card-text>
          <!-- Loading state -->
          <v-progress-linear
            v-if="loadingNetWorth"
            indeterminate
            class="mb-4"
          />

          <!-- Current Summary -->
          <v-row class="mb-4">
            <v-col cols="4">
              <div class="text-center">
                <div class="text-subtitle-2 text-medium-emphasis">
                  Assets
                </div>
                <MoneyDisplay
                  :amount="netWorthData?.current_total_assets || 0"
                  class="text-h6 text-success"
                />
              </div>
            </v-col>
            <v-col cols="4">
              <div class="text-center">
                <div class="text-subtitle-2 text-medium-emphasis">
                  Liabilities
                </div>
                <MoneyDisplay
                  :amount="-(netWorthData?.current_total_liabilities || 0)"
                  class="text-h6 text-error"
                />
              </div>
            </v-col>
            <v-col cols="4">
              <div class="text-center">
                <div class="text-subtitle-2 text-medium-emphasis">
                  Net Worth
                </div>
                <MoneyDisplay
                  :amount="netWorthData?.current_net_worth || 0"
                  class="text-h6"
                  :class="(netWorthData?.current_net_worth || 0) >= 0 ? 'text-success' : 'text-error'"
                />
              </div>
            </v-col>
          </v-row>

          <!-- Change indicator -->
          <div
            v-if="netWorthData && netWorthData.periods.length >= 2"
            class="text-center mb-4"
          >
            <v-chip
              :color="netWorthData.net_worth_change >= 0 ? 'success' : 'error'"
              size="small"
            >
              <v-icon
                :icon="netWorthData.net_worth_change >= 0 ? 'mdi-trending-up' : 'mdi-trending-down'"
                start
              />
              <MoneyDisplay :amount="netWorthData.net_worth_change" />
              <span class="ml-1">over period</span>
            </v-chip>
          </div>

          <v-divider class="my-4" />

          <!-- Line Chart Visualization -->
          <NetWorthChart
            v-if="netWorthData && netWorthData.periods.length > 0"
            :periods="netWorthData.periods"
            :height="220"
            class="mb-4"
          />
          <div
            v-else-if="!loadingNetWorth"
            class="text-center text-grey py-4"
          >
            No account data for this period.
          </div>

          <v-divider
            v-if="netWorthData && netWorthData.periods.length > 0"
            class="my-4"
          />

          <!-- Expandable Account Breakdown -->
          <v-expansion-panels
            v-if="netWorthData && netWorthData.periods.length > 0"
            variant="accordion"
          >
            <v-expansion-panel
              v-for="period in netWorthData.periods"
              :key="period.period_start"
            >
              <v-expansion-panel-title>
                <div class="d-flex justify-space-between w-100 pr-4">
                  <span>{{ formatMonth(period.period_start) }}</span>
                  <MoneyDisplay :amount="period.net_worth" />
                </div>
              </v-expansion-panel-title>
              <v-expansion-panel-text>
                <!-- Assets Section -->
                <div
                  v-if="getAssets(period.accounts).length > 0"
                  class="mb-4"
                >
                  <div class="text-subtitle-2 text-success mb-2">
                    Assets
                  </div>
                  <v-list density="compact">
                    <v-list-item
                      v-for="acc in getAssets(period.accounts)"
                      :key="acc.account_id"
                    >
                      <v-list-item-title class="d-flex justify-space-between">
                        <span>{{ acc.account_name }}</span>
                        <MoneyDisplay :amount="acc.balance" />
                      </v-list-item-title>
                    </v-list-item>
                  </v-list>
                  <div class="d-flex justify-space-between px-4 py-2 bg-grey-lighten-4 rounded">
                    <span class="font-weight-bold">Total Assets</span>
                    <MoneyDisplay
                      :amount="period.total_assets"
                      class="font-weight-bold"
                    />
                  </div>
                </div>

                <!-- Liabilities Section -->
                <div v-if="getLiabilities(period.accounts).length > 0">
                  <div class="text-subtitle-2 text-error mb-2">
                    Liabilities
                  </div>
                  <v-list density="compact">
                    <v-list-item
                      v-for="acc in getLiabilities(period.accounts)"
                      :key="acc.account_id"
                    >
                      <v-list-item-title class="d-flex justify-space-between">
                        <span>{{ acc.account_name }}</span>
                        <MoneyDisplay :amount="acc.balance" />
                      </v-list-item-title>
                    </v-list-item>
                  </v-list>
                  <div class="d-flex justify-space-between px-4 py-2 bg-grey-lighten-4 rounded">
                    <span class="font-weight-bold">Total Liabilities</span>
                    <MoneyDisplay
                      :amount="-period.total_liabilities"
                      class="font-weight-bold"
                    />
                  </div>
                </div>
              </v-expansion-panel-text>
            </v-expansion-panel>
          </v-expansion-panels>
        </v-card-text>
      </v-card>

      <!-- Top Payees -->
      <v-card v-if="activeTab === 'payees'">
        <v-card-title>Top Payees</v-card-title>
        <v-card-text v-if="topPayees.length === 0">
          <p class="text-center text-grey py-4">
            No payee data for this period.
          </p>
        </v-card-text>
        <v-list v-else>
          <v-list-item
            v-for="(item, index) in topPayees"
            :key="item.payee_id"
          >
            <template #prepend>
              <v-avatar
                color="primary"
                variant="tonal"
                size="32"
              >
                {{ index + 1 }}
              </v-avatar>
            </template>
            <v-list-item-title class="d-flex justify-space-between mb-1">
              <span>{{ item.payee_name }}</span>
              <MoneyDisplay :amount="item.total_spent" />
            </v-list-item-title>
            <v-progress-linear
              :model-value="getPayeePercent(item.total_spent)"
              color="primary"
              height="6"
              rounded
            />
            <v-list-item-subtitle class="text-caption mt-1">
              {{ item.transaction_count }} transactions · Avg:
              <MoneyDisplay :amount="item.average_amount" />
            </v-list-item-subtitle>
          </v-list-item>
        </v-list>
      </v-card>

      <!-- Days of Runway -->
      <v-card v-if="activeTab === 'runway'">
        <v-card-title class="d-flex align-center flex-wrap ga-2">
          Days of Runway
          <v-spacer />
          <v-select
            v-model="lookbackDays"
            :items="lookbackOptions"
            item-title="title"
            item-value="value"
            density="compact"
            variant="outlined"
            hide-details
            style="max-width: 140px"
            label="Lookback"
          />
          <v-chip
            v-if="overallRunway !== null"
            :color="getRunwayColor(overallRunway)"
          >
            Overall: {{ formatRunway(overallRunway) }}
          </v-chip>
        </v-card-title>

        <!-- Runway Trend Chart -->
        <v-card-text v-if="runwayTrend && runwayTrend.data_points.length > 0">
          <div class="d-flex align-center mb-2">
            <span class="text-subtitle-2">
              {{ selectedEnvelopeName ? selectedEnvelopeName : 'Overall' }} Runway Trend
            </span>
            <v-spacer />
            <v-btn
              v-if="selectedEnvelopeId"
              size="small"
              variant="text"
              @click="selectEnvelope(null, null)"
            >
              Show Overall
            </v-btn>
          </div>
          <v-progress-linear
            v-if="loadingTrend"
            indeterminate
            class="mb-2"
          />
          <div
            v-else-if="hasValidTrendData"
            class="runway-chart"
          >
            <div
              class="chart-container"
              style="height: 120px; display: flex; align-items: flex-end; gap: 2px;"
            >
              <v-tooltip
                v-for="(point, index) in runwayTrend.data_points"
                :key="index"
                location="top"
              >
                <template #activator="{ props }">
                  <div
                    v-bind="props"
                    class="chart-bar"
                    :style="{
                      flex: 1,
                      height: getTrendBarHeight(point.days_of_runway),
                      ...getTrendBarStyle(point.days_of_runway),
                      borderRadius: '2px 2px 0 0',
                      cursor: 'pointer',
                    }"
                  />
                </template>
                <div class="text-center">
                  <div class="font-weight-bold">
                    {{ point.date }}
                  </div>
                  <div v-if="point.days_of_runway !== null">
                    <div>{{ point.days_of_runway }} days</div>
                    <div class="text-caption">
                      ({{ formatRunway(point.days_of_runway) }})
                    </div>
                  </div>
                  <div
                    v-else
                    class="text-grey"
                  >
                    No spending data
                  </div>
                </div>
              </v-tooltip>
            </div>
            <div class="d-flex justify-space-between text-caption text-grey mt-1">
              <span>{{ runwayTrend.data_points[0]?.date }}</span>
              <span>{{ runwayTrend.data_points[runwayTrend.data_points.length - 1]?.date }}</span>
            </div>
            <p
              v-if="!hasMeaningfulTrend"
              class="text-caption text-grey text-center mt-2"
            >
              Limited data - need transactions spread over multiple weeks for full trend
            </p>
          </div>
          <div
            v-else
            class="text-center text-grey py-2"
          >
            <p class="text-body-2 mb-1">
              Not enough historical data to show trend.
            </p>
            <p class="text-caption">
              Need spending data over multiple weeks to calculate runway trend.
            </p>
          </div>
        </v-card-text>

        <v-divider v-if="runwayTrend && runwayTrend.data_points.length > 0 && hasValidTrendData" />

        <v-card-text v-if="runwayData.length === 0">
          <p class="text-center text-grey py-4">
            Not enough spending data to calculate runway.
          </p>
        </v-card-text>
        <v-list v-else>
          <v-list-item
            v-for="item in runwayData"
            :key="item.envelope_id"
            :class="{ 'bg-grey-lighten-4': selectedEnvelopeId === item.envelope_id }"
            style="cursor: pointer"
            @click="selectEnvelope(item.envelope_id, item.envelope_name)"
          >
            <v-list-item-title class="d-flex justify-space-between">
              <span>{{ item.envelope_name }}</span>
              <v-chip
                size="small"
                :color="getRunwayColor(item.days_of_runway)"
              >
                {{ formatRunway(item.days_of_runway) }}
              </v-chip>
            </v-list-item-title>
            <v-list-item-subtitle>
              Balance: <MoneyDisplay :amount="item.current_balance" />
              · Daily rate: <MoneyDisplay :amount="-Math.round(item.average_daily_spending)" />
            </v-list-item-subtitle>
          </v-list-item>
        </v-list>
      </v-card>

      <!-- Savings Goals -->
      <v-card v-if="activeTab === 'goals'">
        <v-card-title>Savings Goal Progress</v-card-title>
        <v-card-text v-if="savingsGoals.length === 0">
          <p class="text-center text-grey py-4">
            No envelopes with target balances set.
          </p>
          <p class="text-center text-body-2">
            Set target balances on your envelopes to track savings goals.
          </p>
        </v-card-text>
        <v-list v-else>
          <v-list-item
            v-for="item in savingsGoals"
            :key="item.envelope_id"
          >
            <v-list-item-title class="d-flex justify-space-between mb-1">
              <span>{{ item.envelope_name }}</span>
              <span>{{ item.progress_percent.toFixed(0) }}%</span>
            </v-list-item-title>
            <v-progress-linear
              :model-value="item.progress_percent"
              :color="item.progress_percent >= 100 ? 'success' : 'primary'"
              height="8"
              rounded
            />
            <v-list-item-subtitle class="d-flex justify-space-between mt-1 text-caption">
              <span>
                <MoneyDisplay :amount="item.current_balance" />
                of
                <MoneyDisplay :amount="item.target_balance" />
              </span>
              <span v-if="item.months_to_goal !== null && item.months_to_goal > 0">
                ~{{ item.months_to_goal }} months to goal
              </span>
              <span
                v-else-if="item.progress_percent >= 100"
                class="text-success"
              >
                Goal reached!
              </span>
            </v-list-item-subtitle>
          </v-list-item>
        </v-list>
      </v-card>

      <!-- Upcoming Expenses -->
      <v-card v-if="activeTab === 'upcoming'">
        <v-card-title class="d-flex align-center flex-wrap ga-2">
          Upcoming Expenses
          <v-spacer />
          <v-select
            v-model="daysAhead"
            :items="daysAheadOptions"
            item-title="title"
            item-value="value"
            density="compact"
            variant="outlined"
            hide-details
            style="max-width: 140px"
            label="Days Ahead"
          />
        </v-card-title>
        <v-progress-linear
          v-if="loadingUpcoming"
          indeterminate
        />
        <v-card-text v-if="!loadingUpcoming && upcomingExpenses.length === 0">
          <p class="text-center text-grey py-4">
            No upcoming scheduled expenses.
          </p>
        </v-card-text>
        <v-table
          v-else-if="!loadingUpcoming"
          density="compact"
        >
          <thead>
            <tr>
              <th>Date</th>
              <th>Days</th>
              <th>Payee</th>
              <th class="text-right">
                Amount
              </th>
              <th>Envelope</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="item in upcomingExpenses"
              :key="item.transaction_id"
            >
              <td>{{ item.date }}</td>
              <td>{{ item.days_away }}</td>
              <td>{{ item.payee_name || '-' }}</td>
              <td class="text-right">
                <MoneyDisplay :amount="item.amount" />
              </td>
              <td>{{ item.envelope_name || '-' }}</td>
              <td>
                <FundingStatusChip :status="item.funding_status" />
              </td>
            </tr>
          </tbody>
        </v-table>
      </v-card>

      <!-- Recurring Expense Coverage -->
      <v-card v-if="activeTab === 'recurring'">
        <v-card-title>Recurring Expense Coverage</v-card-title>
        <v-progress-linear
          v-if="loadingRecurring"
          indeterminate
        />
        <v-card-text v-if="!loadingRecurring && !recurringCoverage">
          <p class="text-center text-grey py-4">
            No recurring expenses configured.
          </p>
        </v-card-text>
        <template v-else-if="!loadingRecurring && recurringCoverage">
          <!-- Summary Cards -->
          <v-card-text>
            <v-row>
              <v-col
                cols="6"
                md="3"
              >
                <div class="text-center">
                  <div class="text-subtitle-2 text-medium-emphasis">
                    Total
                  </div>
                  <div class="text-h6">
                    {{ recurringCoverage.total_recurring }}
                  </div>
                </div>
              </v-col>
              <v-col
                cols="6"
                md="3"
              >
                <div class="text-center">
                  <div class="text-subtitle-2 text-medium-emphasis">
                    Funded
                  </div>
                  <div class="text-h6 text-success">
                    {{ recurringCoverage.fully_funded_count }}
                  </div>
                </div>
              </v-col>
              <v-col
                cols="6"
                md="3"
              >
                <div class="text-center">
                  <div class="text-subtitle-2 text-medium-emphasis">
                    Partial
                  </div>
                  <div class="text-h6 text-warning">
                    {{ recurringCoverage.partially_funded_count }}
                  </div>
                </div>
              </v-col>
              <v-col
                cols="6"
                md="3"
              >
                <div class="text-center">
                  <div class="text-subtitle-2 text-medium-emphasis">
                    Shortfall
                  </div>
                  <div class="text-h6 text-error">
                    <MoneyDisplay :amount="-recurringCoverage.total_shortfall" />
                  </div>
                </div>
              </v-col>
            </v-row>
          </v-card-text>
          <v-divider />
          <!-- Recurring List -->
          <v-list
            v-if="recurringCoverage.items.length > 0"
            density="compact"
          >
            <v-list-item
              v-for="item in recurringCoverage.items"
              :key="item.recurring_transaction_id"
            >
              <v-list-item-title class="d-flex justify-space-between align-center">
                <span>{{ item.payee_name || 'Unnamed' }}</span>
                <div class="d-flex align-center ga-2">
                  <MoneyDisplay :amount="item.amount" />
                  <FundingStatusChip :status="item.funding_status" />
                </div>
              </v-list-item-title>
              <v-list-item-subtitle>
                {{ item.frequency }} · Next: {{ item.next_occurrence }}
                <span v-if="item.envelope_name">
                  · {{ item.envelope_name }}
                </span>
                <span
                  v-if="item.shortfall > 0"
                  class="text-error"
                >
                  · Need: <MoneyDisplay :amount="-item.shortfall" />
                </span>
              </v-list-item-subtitle>
            </v-list-item>
          </v-list>
        </template>
      </v-card>

      <!-- Spending Trends -->
      <v-card v-if="activeTab === 'trends'">
        <v-card-title>Spending Trends</v-card-title>
        <v-progress-linear
          v-if="loadingTrends"
          indeterminate
        />
        <v-card-text v-if="!loadingTrends && (!spendingTrends || spendingTrends.envelopes.length === 0)">
          <p class="text-center text-grey py-4">
            No spending data for this period.
          </p>
          <p class="text-center text-body-2">
            Set a date range and click "Update Reports" to see spending trends.
          </p>
        </v-card-text>
        <v-card-text v-else-if="!loadingTrends && spendingTrends">
          <SpendingTrendsChart
            :envelopes="spendingTrends.envelopes"
            :height="280"
          />
          <v-divider class="my-4" />
          <!-- Data Table -->
          <div class="table-scroll-container">
            <v-table
              density="compact"
              class="trends-table"
            >
              <thead>
                <tr>
                  <th>Envelope</th>
                  <th class="text-right">
                    Total
                  </th>
                  <th class="text-right">
                    Monthly Average
                  </th>
                </tr>
              </thead>
              <tbody>
                <tr
                  v-for="env in spendingTrends.envelopes"
                  :key="env.envelope_id"
                >
                  <td>{{ env.envelope_name }}</td>
                  <td class="text-right">
                    <MoneyDisplay :amount="-env.total_spent" />
                  </td>
                  <td class="text-right">
                    <MoneyDisplay :amount="-env.average_per_period" />
                  </td>
                </tr>
              </tbody>
            </v-table>
          </div>
        </v-card-text>
      </v-card>

      <!-- Location Spending -->
      <v-card v-if="activeTab === 'locations'">
        <v-card-title class="d-flex align-center flex-wrap ga-2">
          Spending by Location
          <v-spacer />
          <v-checkbox
            v-model="includeNoLocation"
            label="Include (No location)"
            density="compact"
            hide-details
          />
        </v-card-title>
        <v-progress-linear
          v-if="loadingLocations"
          indeterminate
        />
        <v-card-text v-if="!loadingLocations && locationSpending.length === 0">
          <p class="text-center text-grey py-4">
            No location data for this period.
          </p>
        </v-card-text>
        <v-list v-else-if="!loadingLocations">
          <v-list-item
            v-for="(item, index) in locationSpending"
            :key="item.location_id || 'no-location'"
          >
            <template #prepend>
              <v-avatar
                color="primary"
                variant="tonal"
                size="32"
              >
                {{ index + 1 }}
              </v-avatar>
            </template>
            <v-list-item-title class="d-flex justify-space-between mb-1">
              <span>{{ item.location_name }}</span>
              <MoneyDisplay :amount="-item.total_spent" />
            </v-list-item-title>
            <v-progress-linear
              :model-value="getLocationPercent(item.total_spent)"
              color="primary"
              height="6"
              rounded
            />
            <v-list-item-subtitle class="text-caption mt-1">
              {{ item.transaction_count }} transactions · Avg:
              <MoneyDisplay :amount="-item.average_amount" />
            </v-list-item-subtitle>
          </v-list-item>
        </v-list>
      </v-card>

      <!-- Envelope Balance History -->
      <v-card v-if="activeTab === 'envelope-history'">
        <v-card-title>Envelope Balance History</v-card-title>
        <v-card-text>
          <EnvelopeSelect
            v-model="selectedEnvelopeForHistory"
            label="Select Envelope"
            :include-unallocated="false"
            grouped
            clearable
            density="compact"
            class="mb-4"
          />
          <v-progress-linear
            v-if="loadingEnvelopeHistory"
            indeterminate
            class="mb-4"
          />
          <div v-if="!selectedEnvelopeForHistory">
            <p class="text-center text-grey py-4">
              Select an envelope to view its balance history.
            </p>
          </div>
          <div v-else-if="!loadingEnvelopeHistory && envelopeBalanceHistory && envelopeBalanceHistory.items.length > 0">
            <BalanceHistoryChart
              :items="envelopeBalanceHistory.items"
              :target-balance="envelopeBalanceHistory.target_balance"
              :height="220"
            />
            <div class="d-flex justify-space-between mt-4 text-body-2">
              <div>
                <span class="text-medium-emphasis">Current Balance:</span>
                <MoneyDisplay
                  :amount="envelopeBalanceHistory.current_balance"
                  class="ml-2"
                />
              </div>
              <div v-if="envelopeBalanceHistory.target_balance">
                <span class="text-medium-emphasis">Target:</span>
                <MoneyDisplay
                  :amount="envelopeBalanceHistory.target_balance"
                  class="ml-2"
                />
              </div>
            </div>
          </div>
          <div v-else-if="!loadingEnvelopeHistory && selectedEnvelopeForHistory">
            <p class="text-center text-grey py-4">
              No balance history for this envelope.
            </p>
          </div>
        </v-card-text>
      </v-card>

      <!-- Account Balance History -->
      <v-card v-if="activeTab === 'account-history'">
        <v-card-title>Account Balance History</v-card-title>
        <v-card-text>
          <AccountSelect
            v-model="selectedAccountForHistory"
            label="Select Account"
            grouped
            clearable
            density="compact"
            class="mb-4"
          />
          <v-progress-linear
            v-if="loadingAccountHistory"
            indeterminate
            class="mb-4"
          />
          <div v-if="!selectedAccountForHistory">
            <p class="text-center text-grey py-4">
              Select an account to view its balance history.
            </p>
          </div>
          <div v-else-if="!loadingAccountHistory && accountBalanceHistory && accountBalanceHistory.items.length > 0">
            <BalanceHistoryChart
              :items="accountBalanceHistory.items"
              :height="220"
            />
            <div class="d-flex justify-center mt-4 text-body-2">
              <span class="text-medium-emphasis">Current Balance:</span>
              <MoneyDisplay
                :amount="accountBalanceHistory.current_balance"
                class="ml-2"
              />
            </div>
          </div>
          <div v-else-if="!loadingAccountHistory && selectedAccountForHistory">
            <p class="text-center text-grey py-4">
              No balance history for this account.
            </p>
          </div>
        </v-card-text>
      </v-card>

      <!-- Allocation Rule Effectiveness -->
      <v-card v-if="activeTab === 'allocation-rules'">
        <v-card-title class="d-flex align-center flex-wrap ga-2">
          Allocation Rule Effectiveness
          <v-spacer />
          <v-checkbox
            v-model="activeRulesOnly"
            label="Active rules only"
            density="compact"
            hide-details
          />
        </v-card-title>
        <v-progress-linear
          v-if="loadingAllocationRules"
          indeterminate
        />
        <v-card-text v-if="!loadingAllocationRules && allocationRules.length === 0">
          <p class="text-center text-grey py-4">
            No allocation rules configured.
          </p>
        </v-card-text>
        <div
          v-else-if="!loadingAllocationRules"
          class="table-scroll-container"
        >
          <v-table
            density="compact"
            class="allocation-rules-table"
          >
            <thead>
              <tr>
                <th>Rule</th>
                <th>Envelope</th>
                <th>Type</th>
                <th class="text-center">
                  Priority
                </th>
                <th class="text-right">
                  Allocated
                </th>
                <th class="text-center">
                  Triggered
                </th>
                <th class="text-center">
                  Period Cap
                </th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="item in allocationRules"
                :key="item.rule_id"
              >
                <td>{{ item.rule_name || '-' }}</td>
                <td>{{ item.envelope_name }}</td>
                <td>{{ formatRuleType(item.rule_type) }}</td>
                <td class="text-center">
                  {{ item.priority }}
                </td>
                <td class="text-right">
                  <MoneyDisplay :amount="item.total_allocated" />
                </td>
                <td class="text-center">
                  {{ item.times_triggered }}
                </td>
                <td class="text-center">
                  <v-icon
                    v-if="item.has_period_cap"
                    :color="item.period_cap_limited ? 'warning' : 'success'"
                    size="small"
                  >
                    {{ item.period_cap_limited ? 'mdi-speedometer' : 'mdi-check-circle-outline' }}
                  </v-icon>
                  <span v-else>-</span>
                </td>
              </tr>
            </tbody>
          </v-table>
        </div>
      </v-card>
    </template>
  </div>
</template>

<style scoped>
.table-scroll-container {
  overflow-x: auto;
  margin-left: -16px;
  margin-right: -16px;
  padding-left: 16px;
  padding-right: 16px;
}

.cash-flow-table {
  min-width: 550px;
}

.cash-flow-table :deep(td),
.cash-flow-table :deep(th) {
  white-space: nowrap;
}

.trends-table {
  min-width: 400px;
}

.trends-table :deep(td),
.trends-table :deep(th) {
  white-space: nowrap;
}

.allocation-rules-table {
  min-width: 700px;
}

.allocation-rules-table :deep(td),
.allocation-rules-table :deep(th) {
  white-space: nowrap;
}
</style>
