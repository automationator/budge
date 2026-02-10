import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { Location } from '@/types'
import { useAuthStore } from './auth'
import {
  listLocations,
  createLocation as apiCreateLocation,
  updateLocation as apiUpdateLocation,
  deleteLocation as apiDeleteLocation,
  type LocationCreate,
  type LocationUpdate,
} from '@/api/locations'

export const useLocationsStore = defineStore('locations', () => {
  // State
  const locations = ref<Location[]>([])
  const loading = ref(false)
  const error = ref<string | null>(null)

  // Getters
  const sortedLocations = computed(() =>
    [...locations.value].sort((a, b) => a.name.localeCompare(b.name))
  )

  // Actions
  async function fetchLocations() {
    const authStore = useAuthStore()
    if (!authStore.currentBudgetId) return

    try {
      loading.value = true
      error.value = null
      locations.value = await listLocations(authStore.currentBudgetId)
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Failed to fetch locations'
      throw e
    } finally {
      loading.value = false
    }
  }

  async function createLocation(data: LocationCreate): Promise<Location> {
    const authStore = useAuthStore()
    if (!authStore.currentBudgetId) throw new Error('No budget selected')

    try {
      loading.value = true
      error.value = null
      const location = await apiCreateLocation(authStore.currentBudgetId, data)
      locations.value.push(location)
      return location
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Failed to create location'
      throw e
    } finally {
      loading.value = false
    }
  }

  async function updateLocation(locationId: string, data: LocationUpdate): Promise<Location> {
    const authStore = useAuthStore()
    if (!authStore.currentBudgetId) throw new Error('No budget selected')

    try {
      loading.value = true
      error.value = null
      const location = await apiUpdateLocation(authStore.currentBudgetId, locationId, data)

      const index = locations.value.findIndex((l) => l.id === locationId)
      if (index >= 0) {
        locations.value[index] = location
      }

      return location
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Failed to update location'
      throw e
    } finally {
      loading.value = false
    }
  }

  async function deleteLocation(locationId: string): Promise<void> {
    const authStore = useAuthStore()
    if (!authStore.currentBudgetId) throw new Error('No budget selected')

    try {
      loading.value = true
      error.value = null
      await apiDeleteLocation(authStore.currentBudgetId, locationId)
      locations.value = locations.value.filter((l) => l.id !== locationId)
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Failed to delete location'
      throw e
    } finally {
      loading.value = false
    }
  }

  function getLocationById(locationId: string): Location | undefined {
    return locations.value.find((l) => l.id === locationId)
  }

  function reset() {
    locations.value = []
    error.value = null
  }

  return {
    // State
    locations,
    loading,
    error,
    // Getters
    sortedLocations,
    // Actions
    fetchLocations,
    createLocation,
    updateLocation,
    deleteLocation,
    getLocationById,
    reset,
  }
})
