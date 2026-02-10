<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useTransactionsStore } from '@/stores/transactions'
import { useAccountsStore } from '@/stores/accounts'
import { usePayeesStore } from '@/stores/payees'
import { useEnvelopesStore } from '@/stores/envelopes'
import { useLocationsStore } from '@/stores/locations'
import { useAuthStore } from '@/stores/auth'
import { showSnackbar } from '@/App.vue'
import TransactionList from '@/components/transactions/TransactionList.vue'
import TransactionFiltersDrawer, {
  type TransactionFilters,
} from '@/components/transactions/TransactionFiltersDrawer.vue'
import UpcomingTransactionsSection from '@/components/transactions/UpcomingTransactionsSection.vue'
import {
  openNewTransaction as globalOpenNewTransaction,
  openEditTransaction as globalOpenEditTransaction,
  setOnChangeCallback,
} from '@/composables/useGlobalTransactionDialog'
import { listTransactions } from '@/api/transactions'
import type { Transaction } from '@/types'

const route = useRoute()
const router = useRouter()
const transactionsStore = useTransactionsStore()
const accountsStore = useAccountsStore()
const payeesStore = usePayeesStore()
const envelopesStore = useEnvelopesStore()
const locationsStore = useLocationsStore()
const authStore = useAuthStore()

// Upcoming transactions state
const upcomingTransactions = ref<Transaction[]>([])
const upcomingLoading = ref(false)

// Initialize filter state from URL query params
function parseIncludeInBudget(value: unknown): boolean | null {
  if (value === 'true') return true
  if (value === 'false') return false
  return null
}

const selectedAccountId = ref<string | null>((route.query.account_id as string) || null)

// Filter drawer state
const showFiltersDrawer = ref(false)
const filters = ref<TransactionFilters>({
  payeeId: null,
  locationId: null,
  envelopeId: null,
  hideReconciled: false,
  includeInBudget: parseIncludeInBudget(route.query.include_in_budget),
  needsReview: route.query.filter === 'unallocated',
})

// Count active filters for badge
const activeFilterCount = computed(() => {
  let count = 0
  if (filters.value.payeeId) count++
  if (filters.value.locationId) count++
  if (filters.value.envelopeId && !filters.value.needsReview) count++ // Don't double-count when needsReview
  if (filters.value.hideReconciled) count++
  if (filters.value.includeInBudget !== null && !filters.value.needsReview) count++ // Don't double-count when needsReview
  if (filters.value.needsReview) count++
  return count
})

async function fetchUpcomingTransactions() {
  if (!authStore.currentBudgetId) return

  try {
    upcomingLoading.value = true
    const response = await listTransactions(authStore.currentBudgetId, {
      status: ['scheduled'],
      limit: 50,
    })
    upcomingTransactions.value = response.items
  } catch {
    // Silently fail - upcoming section is optional
  } finally {
    upcomingLoading.value = false
  }
}

onMounted(async () => {
  try {
    await Promise.all([
      transactionsStore.fetchTransactions(true, getFilterParams()),
      transactionsStore.fetchUnallocatedCount(),
      accountsStore.fetchAccounts(),
      payeesStore.fetchPayees(),
      locationsStore.fetchLocations(),
      envelopesStore.fetchEnvelopes(),
      fetchUpcomingTransactions(),
    ])
  } catch {
    showSnackbar('Failed to load transactions', 'error')
  }
})

type SelectOption = { title: string; value: string | null } | { type: 'subheader'; title: string }

const accountOptions = computed((): SelectOption[] => {
  const options: SelectOption[] = [{ title: 'All Accounts', value: null }]

  const sortAccounts = (accounts: typeof accountsStore.activeAccounts) =>
    [...accounts].sort((a, b) => {
      if (a.sort_order !== b.sort_order) return a.sort_order - b.sort_order
      return a.name.localeCompare(b.name)
    })

  const budgetAccounts = sortAccounts(
    accountsStore.activeAccounts.filter((a) => a.include_in_budget)
  )
  const trackingAccounts = sortAccounts(
    accountsStore.activeAccounts.filter((a) => !a.include_in_budget)
  )

  if (budgetAccounts.length > 0) {
    options.push({ type: 'subheader', title: 'Budget' })
    for (const account of budgetAccounts) {
      options.push({ title: account.name, value: account.id })
    }
  }

  if (trackingAccounts.length > 0) {
    options.push({ type: 'subheader', title: 'Tracking' })
    for (const account of trackingAccounts) {
      options.push({ title: account.name, value: account.id })
    }
  }

  return options
})

function getFilterParams() {
  const needsReview = filters.value.needsReview
  return {
    account_id: selectedAccountId.value || undefined,
    payee_id: filters.value.payeeId || undefined,
    location_id: filters.value.locationId || undefined,
    envelope_id: filters.value.envelopeId || undefined,
    is_reconciled: filters.value.hideReconciled ? false : undefined,
    // For needsReview filter, force include_in_budget=true to match count logic
    include_in_budget: needsReview ? true : (filters.value.includeInBudget ?? undefined),
    expenses_only: needsReview || undefined,
    exclude_adjustments: needsReview || undefined,
    // Exclude scheduled transactions from main list - they appear in Upcoming section
    include_scheduled: false,
  }
}

// Watch route query for changes (deep link support)
watch(
  () => route.query,
  (query) => {
    const newAccountId = (query.account_id as string) || null
    const newIncludeInBudget = parseIncludeInBudget(query.include_in_budget)
    const newNeedsReview = query.filter === 'unallocated'

    // Handle needsReview filter - set envelope_id to unallocated envelope
    let newEnvelopeId = filters.value.envelopeId
    if (newNeedsReview) {
      const unallocatedEnvelope = envelopesStore.unallocatedEnvelope
      newEnvelopeId = unallocatedEnvelope?.id || null
    }

    // Only refetch if values actually changed
    if (
      newAccountId !== selectedAccountId.value ||
      newIncludeInBudget !== filters.value.includeInBudget ||
      newEnvelopeId !== filters.value.envelopeId ||
      newNeedsReview !== filters.value.needsReview
    ) {
      selectedAccountId.value = newAccountId
      filters.value.includeInBudget = newIncludeInBudget
      filters.value.envelopeId = newEnvelopeId
      filters.value.needsReview = newNeedsReview
      handleFilter()
    }
  },
  { immediate: true }
)

async function handleFilter() {
  try {
    await transactionsStore.fetchTransactions(true, getFilterParams())
  } catch {
    showSnackbar('Failed to filter transactions', 'error')
  }
}

async function handleFiltersUpdate(newFilters: TransactionFilters) {
  const needsReviewChanged = newFilters.needsReview !== filters.value.needsReview
  filters.value = newFilters

  // Sync URL with needsReview state
  if (needsReviewChanged) {
    const query = { ...route.query }
    if (newFilters.needsReview) {
      query.filter = 'unallocated'
      // Also set envelopeId to unallocated envelope
      const unallocatedEnvelope = envelopesStore.unallocatedEnvelope
      filters.value.envelopeId = unallocatedEnvelope?.id || null
    } else {
      delete query.filter
      // Clear the envelope filter when turning off needsReview
      filters.value.envelopeId = null
    }
    router.replace({ query })
  }

  await handleFilter()
}

async function loadMore() {
  if (!transactionsStore.hasMore || transactionsStore.loading) return

  try {
    await transactionsStore.fetchTransactions(false, getFilterParams())
  } catch {
    showSnackbar('Failed to load more transactions', 'error')
  }
}

function openNewTransaction() {
  globalOpenNewTransaction(selectedAccountId.value)
}

function openEditTransaction(transactionId: string) {
  globalOpenEditTransaction(transactionId)
}

// Refresh local data when transaction changes via global dialog
async function handleTransactionChange() {
  await Promise.all([
    transactionsStore.fetchTransactions(true, getFilterParams()),
    transactionsStore.fetchUnallocatedCount(),
    fetchUpcomingTransactions(),
  ])
}

// Register/unregister callback for global dialog changes
onMounted(() => {
  setOnChangeCallback(handleTransactionChange)
})

onUnmounted(() => {
  setOnChangeCallback(null)
})
</script>

<template>
  <div>
    <div class="d-flex align-center flex-wrap ga-2 mb-4">
      <h1 class="text-h4">
        Transactions
      </h1>
      <v-spacer />
      <v-btn
        color="primary"
        prepend-icon="mdi-plus"
        @click="openNewTransaction"
      >
        Add Transaction
      </v-btn>
    </div>

    <!-- Filters -->
    <v-card class="mb-4">
      <v-card-text>
        <div class="d-flex align-center ga-3">
          <v-select
            v-model="selectedAccountId"
            :items="accountOptions"
            label="Account"
            density="compact"
            hide-details
            class="flex-grow-1"
            style="max-width: 300px"
            @update:model-value="handleFilter"
          />
          <v-badge
            :content="activeFilterCount"
            :model-value="activeFilterCount > 0"
            color="primary"
          >
            <v-btn
              variant="outlined"
              prepend-icon="mdi-filter-variant"
              @click="showFiltersDrawer = true"
            >
              Filters
            </v-btn>
          </v-badge>
        </div>
      </v-card-text>
    </v-card>

    <!-- Filter Drawer -->
    <TransactionFiltersDrawer
      v-model="showFiltersDrawer"
      :filters="filters"
      @update:filters="handleFiltersUpdate"
    />

    <!-- Upcoming Transactions Section -->
    <UpcomingTransactionsSection
      :transactions="upcomingTransactions"
      :loading="upcomingLoading"
      storage-key="budge:transactions:upcoming-collapsed"
      @transaction-click="openEditTransaction"
    />

    <!-- Transaction List -->
    <TransactionList
      :transactions="transactionsStore.transactions"
      :loading="transactionsStore.loading"
      :has-more="transactionsStore.hasMore"
      @transaction-click="openEditTransaction"
      @load-more="loadMore"
    >
      <template #empty-action>
        <v-btn
          color="primary"
          class="mt-4"
          @click="openNewTransaction"
        >
          Add Transaction
        </v-btn>
      </template>
    </TransactionList>
  </div>
</template>
