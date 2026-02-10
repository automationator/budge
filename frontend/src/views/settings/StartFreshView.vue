<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { showSnackbar } from '@/App.vue'
import {
  previewDeletion,
  startFresh,
  previewAllUserDataDeletion,
  deleteAllUserData,
  type DataCategory,
  type StartFreshPreview,
} from '@/api/startFresh'

const router = useRouter()
const authStore = useAuthStore()

// Scope selection (current budget vs all budgets)
const deletionScope = ref<'current_budget' | 'all_budgets'>('current_budget')

// Mode selection
const deleteMode = ref<'all' | 'selective'>('selective')
const selectedCategories = ref<DataCategory[]>([])

// Computed owned budgets count
const ownedBudgetsCount = computed(() =>
  authStore.budgets.filter((t) => t.owner_id === authStore.user?.id).length
)

// Preview state
const preview = ref<StartFreshPreview | null>(null)
const loadingPreview = ref(false)

// Confirmation dialog state
const showConfirmDialog = ref(false)
const password = ref('')
const passwordError = ref('')
const deleting = ref(false)

// Computed categories to send to API
const categoriesToDelete = computed<DataCategory[]>(() => {
  if (deleteMode.value === 'all') {
    return ['all']
  }
  return selectedCategories.value
})

// Check if delete is possible
const canDelete = computed(() => {
  if (deleteMode.value === 'all') return true
  return selectedCategories.value.length > 0
})

// Total items to be deleted
const totalItems = computed(() => {
  if (!preview.value) return 0
  return (
    preview.value.accounts_count +
    preview.value.transactions_count +
    preview.value.allocations_count +
    preview.value.recurring_transactions_count +
    preview.value.envelopes_count +
    preview.value.envelope_groups_count +
    preview.value.allocation_rules_count +
    preview.value.payees_count +
    preview.value.locations_count +
    preview.value.envelopes_cleared_count
  )
})

// Watch for changes to load preview
watch(
  [deleteMode, selectedCategories, deletionScope],
  async () => {
    if (!canDelete.value) {
      preview.value = null
      return
    }

    try {
      loadingPreview.value = true
      if (deletionScope.value === 'all_budgets') {
        preview.value = await previewAllUserDataDeletion(categoriesToDelete.value)
      } else {
        if (!authStore.currentBudgetId) {
          preview.value = null
          return
        }
        preview.value = await previewDeletion(authStore.currentBudgetId, categoriesToDelete.value)
      }
    } catch {
      showSnackbar('Failed to load preview', 'error')
      preview.value = null
    } finally {
      loadingPreview.value = false
    }
  },
  { immediate: true }
)

function openConfirmDialog() {
  password.value = ''
  passwordError.value = ''
  showConfirmDialog.value = true
}

async function confirmDelete() {
  if (!password.value) {
    passwordError.value = 'Password is required'
    return
  }

  try {
    deleting.value = true
    passwordError.value = ''

    if (deletionScope.value === 'all_budgets') {
      await deleteAllUserData({
        password: password.value,
        categories: categoriesToDelete.value,
      })
    } else {
      if (!authStore.currentBudgetId) return
      await startFresh(authStore.currentBudgetId, {
        password: password.value,
        categories: categoriesToDelete.value,
      })
    }

    showConfirmDialog.value = false

    // Reset state and navigate back
    selectedCategories.value = []
    preview.value = null
    router.push('/settings')
  } catch (e) {
    // Check for password error in axios response
    const axiosError = e as { response?: { status?: number; data?: { detail?: string } } }
    if (
      axiosError.response?.status === 401 ||
      axiosError.response?.data?.detail?.toLowerCase().includes('password')
    ) {
      passwordError.value = 'Invalid password'
    } else {
      showSnackbar('Failed to delete data', 'error')
    }
  } finally {
    deleting.value = false
  }
}
</script>

<template>
  <div>
    <v-btn
      variant="text"
      prepend-icon="mdi-arrow-left"
      class="mb-4"
      @click="router.back()"
    >
      Back to Settings
    </v-btn>

    <h1 class="text-h4 mb-4">
      Start Fresh
    </h1>

    <!-- Warning Alert -->
    <v-alert
      type="warning"
      variant="tonal"
      class="mb-4"
    >
      <v-alert-title>Danger Zone</v-alert-title>
      This action will permanently delete data. This cannot be undone.
    </v-alert>

    <!-- Scope Selection Card -->
    <v-card
      v-if="ownedBudgetsCount > 1"
      class="mb-4"
    >
      <v-card-title>Deletion Scope</v-card-title>
      <v-card-text>
        <v-radio-group v-model="deletionScope">
          <v-radio
            value="current_budget"
            :label="`Current budget only (${authStore.currentBudget?.name})`"
          />
          <v-radio
            value="all_budgets"
            label="All budgets I own"
            color="error"
          />
        </v-radio-group>

        <v-alert
          v-if="deletionScope === 'all_budgets'"
          type="error"
          variant="tonal"
          density="compact"
        >
          This will delete data from all {{ ownedBudgetsCount }} budget(s) you own.
          Budgets will be emptied but not deleted.
        </v-alert>
      </v-card-text>
    </v-card>

    <!-- Data Type Selection Card -->
    <v-card class="mb-4">
      <v-card-title>Select What to Delete</v-card-title>
      <v-card-text>
        <v-radio-group v-model="deleteMode">
          <v-radio
            label="Delete ALL data"
            value="all"
            color="error"
          />
          <v-radio
            label="Select specific data types"
            value="selective"
          />
        </v-radio-group>

        <!-- Checkboxes for selective deletion -->
        <div
          v-if="deleteMode === 'selective'"
          class="ml-8"
        >
          <v-checkbox
            v-model="selectedCategories"
            value="accounts"
            label="Accounts (will also delete all transactions)"
            color="error"
            density="compact"
            hide-details
          />
          <v-checkbox
            v-model="selectedCategories"
            value="transactions"
            label="Transactions (includes allocations)"
            color="error"
            density="compact"
            hide-details
          />
          <v-checkbox
            v-model="selectedCategories"
            value="recurring"
            label="Recurring Transactions"
            color="error"
            density="compact"
            hide-details
          />
          <v-checkbox
            v-model="selectedCategories"
            value="envelopes"
            label="Envelopes (includes groups and allocation rules)"
            color="error"
            density="compact"
            hide-details
          />
          <v-checkbox
            v-model="selectedCategories"
            value="allocations"
            label="Clear envelope allocations (resets all envelope balances to zero)"
            color="warning"
            density="compact"
            hide-details
          />
          <v-checkbox
            v-model="selectedCategories"
            value="payees"
            label="Payees (only those not linked to transactions)"
            color="error"
            density="compact"
            hide-details
          />
          <v-checkbox
            v-model="selectedCategories"
            value="locations"
            label="Locations"
            color="error"
            density="compact"
            hide-details
          />
        </div>
      </v-card-text>
    </v-card>

    <!-- Preview Card -->
    <v-card
      v-if="preview && totalItems > 0"
      class="mb-4"
    >
      <v-card-title class="text-error">
        Data to be Deleted
      </v-card-title>
      <v-card-text>
        <v-list density="compact">
          <v-list-item v-if="preview.accounts_count > 0">
            <template #prepend>
              <v-icon icon="mdi-bank" />
            </template>
            <v-list-item-title>{{ preview.accounts_count }} account(s)</v-list-item-title>
          </v-list-item>

          <v-list-item v-if="preview.transactions_count > 0">
            <template #prepend>
              <v-icon icon="mdi-swap-horizontal" />
            </template>
            <v-list-item-title>{{ preview.transactions_count }} transaction(s)</v-list-item-title>
          </v-list-item>

          <v-list-item v-if="preview.allocations_count > 0">
            <template #prepend>
              <v-icon icon="mdi-chart-pie" />
            </template>
            <v-list-item-title>{{ preview.allocations_count }} allocation(s)</v-list-item-title>
          </v-list-item>

          <v-list-item v-if="preview.recurring_transactions_count > 0">
            <template #prepend>
              <v-icon icon="mdi-repeat" />
            </template>
            <v-list-item-title>
              {{ preview.recurring_transactions_count }} recurring transaction(s)
            </v-list-item-title>
          </v-list-item>

          <v-list-item v-if="preview.envelopes_count > 0">
            <template #prepend>
              <v-icon icon="mdi-email" />
            </template>
            <v-list-item-title>{{ preview.envelopes_count }} envelope(s)</v-list-item-title>
          </v-list-item>

          <v-list-item v-if="preview.envelope_groups_count > 0">
            <template #prepend>
              <v-icon icon="mdi-folder" />
            </template>
            <v-list-item-title>
              {{ preview.envelope_groups_count }} envelope group(s)
            </v-list-item-title>
          </v-list-item>

          <v-list-item v-if="preview.allocation_rules_count > 0">
            <template #prepend>
              <v-icon icon="mdi-auto-fix" />
            </template>
            <v-list-item-title>
              {{ preview.allocation_rules_count }} allocation rule(s)
            </v-list-item-title>
          </v-list-item>

          <v-list-item v-if="preview.payees_count > 0">
            <template #prepend>
              <v-icon icon="mdi-account-cash" />
            </template>
            <v-list-item-title>{{ preview.payees_count }} payee(s)</v-list-item-title>
          </v-list-item>

          <v-list-item v-if="preview.locations_count > 0">
            <template #prepend>
              <v-icon icon="mdi-map-marker" />
            </template>
            <v-list-item-title>{{ preview.locations_count }} location(s)</v-list-item-title>
          </v-list-item>

          <v-list-item v-if="preview.envelopes_cleared_count > 0">
            <template #prepend>
              <v-icon icon="mdi-refresh" />
            </template>
            <v-list-item-title>
              {{ preview.envelopes_cleared_count }} envelope balance(s) reset to zero
            </v-list-item-title>
          </v-list-item>
        </v-list>
      </v-card-text>
    </v-card>

    <!-- Empty Preview -->
    <v-card
      v-else-if="canDelete && !loadingPreview"
      class="mb-4"
    >
      <v-card-text class="text-center text-grey py-8">
        No data to delete in selected data types.
      </v-card-text>
    </v-card>

    <!-- Loading Preview -->
    <v-card
      v-else-if="loadingPreview"
      class="mb-4"
    >
      <v-card-text class="text-center py-8">
        <v-progress-circular
          indeterminate
          color="primary"
        />
      </v-card-text>
    </v-card>

    <!-- Delete Button -->
    <v-btn
      color="error"
      size="large"
      :disabled="!canDelete || totalItems === 0"
      :loading="loadingPreview"
      @click="openConfirmDialog"
    >
      <v-icon start>
        mdi-delete-forever
      </v-icon>
      Delete Selected Data
    </v-btn>

    <!-- Confirmation Dialog -->
    <v-dialog
      v-model="showConfirmDialog"
      max-width="500"
    >
      <v-card>
        <v-card-title class="text-error">
          Confirm Deletion
        </v-card-title>
        <v-card-text>
          <v-alert
            type="error"
            variant="tonal"
            class="mb-4"
          >
            You are about to permanently delete {{ totalItems }} item(s). This cannot be undone.
          </v-alert>

          <p class="mb-4">
            Enter your password to confirm:
          </p>

          <v-text-field
            v-model="password"
            label="Password"
            type="password"
            :error-messages="passwordError"
            @keyup.enter="confirmDelete"
          />
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn
            variant="text"
            @click="showConfirmDialog = false"
          >
            Cancel
          </v-btn>
          <v-btn
            color="error"
            :loading="deleting"
            :disabled="!password"
            @click="confirmDelete"
          >
            Delete Forever
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </div>
</template>
