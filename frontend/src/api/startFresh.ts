import apiClient from './client'

export type DataCategory =
  | 'transactions'
  | 'recurring'
  | 'envelopes'
  | 'accounts'
  | 'payees'
  | 'locations'
  | 'allocations'
  | 'all'

export interface StartFreshPreview {
  transactions_count: number
  allocations_count: number
  recurring_transactions_count: number
  envelopes_count: number
  envelope_groups_count: number
  allocation_rules_count: number
  accounts_count: number
  payees_count: number
  locations_count: number
  envelopes_cleared_count: number
}

export interface StartFreshRequest {
  password: string
  categories: DataCategory[]
}

export interface StartFreshResponse {
  success: boolean
  deleted: StartFreshPreview
  message: string
}

export async function previewDeletion(
  budgetId: string,
  categories: DataCategory[]
): Promise<StartFreshPreview> {
  const params = new URLSearchParams()
  categories.forEach((c) => params.append('categories', c))
  const response = await apiClient.get<StartFreshPreview>(
    `/budgets/${budgetId}/start-fresh/preview?${params}`
  )
  return response.data
}

export async function startFresh(
  budgetId: string,
  request: StartFreshRequest
): Promise<StartFreshResponse> {
  const response = await apiClient.post<StartFreshResponse>(
    `/budgets/${budgetId}/start-fresh`,
    request
  )
  return response.data
}

export async function previewAllUserDataDeletion(
  categories: DataCategory[]
): Promise<StartFreshPreview> {
  const params = new URLSearchParams()
  categories.forEach((c) => params.append('categories', c))
  const response = await apiClient.get<StartFreshPreview>(
    `/users/me/delete-all-data/preview?${params}`
  )
  return response.data
}

export async function deleteAllUserData(
  request: StartFreshRequest
): Promise<StartFreshResponse> {
  const response = await apiClient.post<StartFreshResponse>('/users/me/delete-all-data', request)
  return response.data
}
