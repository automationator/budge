<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { usePayeesStore } from '@/stores/payees'
import { useEnvelopesStore } from '@/stores/envelopes'
import { showSnackbar } from '@/App.vue'
import EnvelopeSelect from '@/components/common/EnvelopeSelect.vue'
import type { Payee } from '@/types'

const router = useRouter()
const payeesStore = usePayeesStore()
const envelopesStore = useEnvelopesStore()

const loading = ref(false)

// Create/Edit dialog
const showEditDialog = ref(false)
const editingPayee = ref<Payee | null>(null)
const formName = ref('')
const formIcon = ref('')
const formDescription = ref('')
const formDefaultEnvelopeId = ref<string | null>(null)
const saving = ref(false)

// Delete dialog
const showDeleteDialog = ref(false)
const payeeToDelete = ref<Payee | null>(null)
const deleting = ref(false)

const isEditing = computed(() => !!editingPayee.value)
const dialogTitle = computed(() => (isEditing.value ? 'Edit Payee' : 'Add Payee'))

function getEnvelopeName(envelopeId: string | null): string | null {
  if (!envelopeId) return null
  const envelope = envelopesStore.envelopes.find((e) => e.id === envelopeId)
  return envelope?.name ?? null
}

onMounted(async () => {
  try {
    loading.value = true
    await Promise.all([payeesStore.fetchPayees(), envelopesStore.fetchEnvelopes()])
  } catch {
    showSnackbar('Failed to load payees', 'error')
  } finally {
    loading.value = false
  }
})

function openCreateDialog() {
  editingPayee.value = null
  formName.value = ''
  formIcon.value = ''
  formDescription.value = ''
  formDefaultEnvelopeId.value = null
  showEditDialog.value = true
}

function openEditDialog(payee: Payee) {
  editingPayee.value = payee
  formName.value = payee.name
  formIcon.value = payee.icon ?? ''
  formDescription.value = payee.description ?? ''
  formDefaultEnvelopeId.value = payee.default_envelope_id
  showEditDialog.value = true
}

async function savePayee() {
  if (!formName.value.trim()) {
    showSnackbar('Name is required', 'error')
    return
  }

  try {
    saving.value = true

    if (isEditing.value && editingPayee.value) {
      await payeesStore.updatePayee(editingPayee.value.id, {
        name: formName.value.trim(),
        icon: formIcon.value.trim() || null,
        description: formDescription.value.trim() || null,
        default_envelope_id: formDefaultEnvelopeId.value,
      })
    } else {
      const newPayee = await payeesStore.createPayee({
        name: formName.value.trim(),
        icon: formIcon.value.trim() || null,
        description: formDescription.value.trim() || null,
      })
      // If a default envelope was selected, update the payee to set it
      // (default_envelope_id is not part of PayeeCreate schema)
      if (formDefaultEnvelopeId.value) {
        await payeesStore.updatePayee(newPayee.id, {
          default_envelope_id: formDefaultEnvelopeId.value,
        })
      }
    }

    showEditDialog.value = false
  } catch (e) {
    const message = e instanceof Error ? e.message : 'Failed to save payee'
    showSnackbar(message, 'error')
  } finally {
    saving.value = false
  }
}

function confirmDelete(payee: Payee) {
  payeeToDelete.value = payee
  showDeleteDialog.value = true
}

async function deletePayee() {
  if (!payeeToDelete.value) return

  try {
    deleting.value = true
    await payeesStore.deletePayee(payeeToDelete.value.id)
    showDeleteDialog.value = false
    payeeToDelete.value = null
  } catch {
    showSnackbar('Failed to delete payee', 'error')
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

    <div class="d-flex align-center mb-4">
      <h1 class="text-h4">
        Manage Payees
      </h1>
      <v-spacer />
      <v-btn
        color="primary"
        prepend-icon="mdi-plus"
        @click="openCreateDialog"
      >
        Add Payee
      </v-btn>
    </div>

    <!-- Loading -->
    <div
      v-if="loading"
      class="text-center py-8"
    >
      <v-progress-circular
        indeterminate
        color="primary"
      />
    </div>

    <!-- Payees List -->
    <v-card v-else>
      <v-list>
        <v-list-item
          v-for="payee in payeesStore.sortedPayees"
          :key="payee.id"
          @click="openEditDialog(payee)"
        >
          <template #prepend>
            <v-avatar
              color="grey-lighten-3"
              variant="tonal"
            >
              <span v-if="payee.icon">{{ payee.icon }}</span>
              <v-icon
                v-else
                icon="mdi-account"
              />
            </v-avatar>
          </template>

          <v-list-item-title>{{ payee.name }}</v-list-item-title>
          <v-list-item-subtitle v-if="getEnvelopeName(payee.default_envelope_id)">
            Default: {{ getEnvelopeName(payee.default_envelope_id) }}
          </v-list-item-subtitle>

          <template #append>
            <v-btn
              icon="mdi-delete"
              variant="text"
              size="small"
              color="error"
              @click.stop="confirmDelete(payee)"
            />
          </template>
        </v-list-item>

        <v-list-item v-if="payeesStore.sortedPayees.length === 0">
          <v-list-item-title class="text-center text-grey py-4">
            No payees yet. Payees are created when you add transactions, or you can add them manually.
          </v-list-item-title>
        </v-list-item>
      </v-list>
    </v-card>

    <!-- Create/Edit Dialog -->
    <v-dialog
      v-model="showEditDialog"
      max-width="500"
    >
      <v-card rounded="xl">
        <v-card-title>{{ dialogTitle }}</v-card-title>
        <v-card-text>
          <v-form @submit.prevent="savePayee">
            <div class="form-fields">
              <v-text-field
                v-model="formName"
                label="Name"
                required
                :rules="[(v) => !!v.trim() || 'Name is required']"
              />

              <v-text-field
                v-model="formIcon"
                label="Icon (emoji)"
                hint="Optional emoji to display"
                persistent-hint
              />

              <v-textarea
                v-model="formDescription"
                label="Description"
                rows="2"
              />

              <EnvelopeSelect
                v-model="formDefaultEnvelopeId"
                label="Default Envelope"
                clearable
                hint="Auto-fill this envelope when selecting this payee"
                persistent-hint
              />
            </div>
          </v-form>
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn
            variant="text"
            @click="showEditDialog = false"
          >
            Cancel
          </v-btn>
          <v-btn
            color="primary"
            class="create-btn"
            :loading="saving"
            :disabled="!formName.trim()"
            @click="savePayee"
          >
            {{ isEditing ? 'Save' : 'Create' }}
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Delete Confirmation Dialog -->
    <v-dialog
      v-model="showDeleteDialog"
      max-width="400"
    >
      <v-card rounded="xl">
        <v-card-title>Delete Payee</v-card-title>
        <v-card-text>
          Are you sure you want to delete <strong>{{ payeeToDelete?.name }}</strong>? Payees that
          are linked to existing transactions cannot be deleted.
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn
            variant="text"
            @click="showDeleteDialog = false"
          >
            Cancel
          </v-btn>
          <v-btn
            color="error"
            :loading="deleting"
            @click="deletePayee"
          >
            Delete
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </div>
</template>
