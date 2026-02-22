<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useLocationsStore } from '@/stores/locations'
import { showSnackbar } from '@/App.vue'
import type { Location } from '@/types'

const router = useRouter()
const locationsStore = useLocationsStore()

const loading = ref(false)

// Create/Edit dialog
const showEditDialog = ref(false)
const editingLocation = ref<Location | null>(null)
const formName = ref('')
const formIcon = ref('')
const formDescription = ref('')
const saving = ref(false)

// Delete dialog
const showDeleteDialog = ref(false)
const locationToDelete = ref<Location | null>(null)
const deleting = ref(false)

const isEditing = computed(() => !!editingLocation.value)
const dialogTitle = computed(() => (isEditing.value ? 'Edit Location' : 'Add Location'))

onMounted(async () => {
  try {
    loading.value = true
    await locationsStore.fetchLocations()
  } catch {
    showSnackbar('Failed to load locations', 'error')
  } finally {
    loading.value = false
  }
})

function openCreateDialog() {
  editingLocation.value = null
  formName.value = ''
  formIcon.value = ''
  formDescription.value = ''
  showEditDialog.value = true
}

function openEditDialog(location: Location) {
  editingLocation.value = location
  formName.value = location.name
  formIcon.value = location.icon ?? ''
  formDescription.value = location.description ?? ''
  showEditDialog.value = true
}

async function saveLocation() {
  if (!formName.value.trim()) {
    showSnackbar('Name is required', 'error')
    return
  }

  try {
    saving.value = true

    if (isEditing.value && editingLocation.value) {
      await locationsStore.updateLocation(editingLocation.value.id, {
        name: formName.value.trim(),
        icon: formIcon.value.trim() || null,
        description: formDescription.value.trim() || null,
      })
    } else {
      await locationsStore.createLocation({
        name: formName.value.trim(),
        icon: formIcon.value.trim() || null,
        description: formDescription.value.trim() || null,
      })
    }

    showEditDialog.value = false
  } catch (e) {
    const message = e instanceof Error ? e.message : 'Failed to save location'
    showSnackbar(message, 'error')
  } finally {
    saving.value = false
  }
}

function confirmDelete(location: Location) {
  locationToDelete.value = location
  showDeleteDialog.value = true
}

async function deleteLocation() {
  if (!locationToDelete.value) return

  try {
    deleting.value = true
    await locationsStore.deleteLocation(locationToDelete.value.id)
    showDeleteDialog.value = false
    locationToDelete.value = null
  } catch {
    showSnackbar('Failed to delete location', 'error')
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
        Manage Locations
      </h1>
      <v-spacer />
      <v-btn
        color="primary"
        prepend-icon="mdi-plus"
        @click="openCreateDialog"
      >
        Add Location
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

    <!-- Locations List -->
    <v-card v-else>
      <v-list>
        <v-list-item
          v-for="location in locationsStore.sortedLocations"
          :key="location.id"
          @click="openEditDialog(location)"
        >
          <template #prepend>
            <v-avatar
              color="grey-lighten-3"
              variant="tonal"
            >
              <span v-if="location.icon">{{ location.icon }}</span>
              <v-icon
                v-else
                icon="mdi-map-marker"
              />
            </v-avatar>
          </template>

          <v-list-item-title>{{ location.name }}</v-list-item-title>
          <v-list-item-subtitle v-if="location.description">
            {{ location.description }}
          </v-list-item-subtitle>

          <template #append>
            <v-btn
              icon="mdi-delete"
              variant="text"
              size="small"
              color="error"
              @click.stop="confirmDelete(location)"
            />
          </template>
        </v-list-item>

        <v-list-item v-if="locationsStore.sortedLocations.length === 0">
          <v-list-item-title class="text-center text-grey py-4">
            No locations yet. Locations are created when you add transactions, or you can add them manually.
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
          <v-form @submit.prevent="saveLocation">
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
            @click="saveLocation"
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
        <v-card-title>Delete Location</v-card-title>
        <v-card-text>
          Are you sure you want to delete <strong>{{ locationToDelete?.name }}</strong>? Transactions
          linked to this location will have their location cleared.
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
            @click="deleteLocation"
          >
            Delete
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </div>
</template>
