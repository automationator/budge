import apiClient from './client'
import type { Location } from '@/types'

export interface LocationCreate {
  name: string
  icon?: string | null
  description?: string | null
}

export interface LocationUpdate {
  name?: string
  icon?: string | null
  description?: string | null
}

export async function listLocations(budgetId: string): Promise<Location[]> {
  const response = await apiClient.get<Location[]>(`/budgets/${budgetId}/locations`)
  return response.data
}

export async function getLocation(budgetId: string, locationId: string): Promise<Location> {
  const response = await apiClient.get<Location>(`/budgets/${budgetId}/locations/${locationId}`)
  return response.data
}

export async function createLocation(budgetId: string, data: LocationCreate): Promise<Location> {
  const response = await apiClient.post<Location>(`/budgets/${budgetId}/locations`, data)
  return response.data
}

export async function updateLocation(
  budgetId: string,
  locationId: string,
  data: LocationUpdate
): Promise<Location> {
  const response = await apiClient.patch<Location>(
    `/budgets/${budgetId}/locations/${locationId}`,
    data
  )
  return response.data
}

export async function deleteLocation(budgetId: string, locationId: string): Promise<void> {
  await apiClient.delete(`/budgets/${budgetId}/locations/${locationId}`)
}
