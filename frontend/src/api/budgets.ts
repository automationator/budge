import apiClient from './client'
import type { Budget, CursorPage, BudgetRole, DefaultIncomeAllocation } from '@/types'

export interface BudgetMember {
  id: string
  username: string
  email?: string
  first_name?: string
  last_name?: string
  role: BudgetRole
  effective_scopes: string[]
}

export interface AddMemberRequest {
  username: string
  role?: BudgetRole
}

export async function getMyBudgets(): Promise<CursorPage<Budget>> {
  const response = await apiClient.get<CursorPage<Budget>>('/budgets')
  return response.data
}

export async function getBudget(budgetId: string): Promise<Budget> {
  const response = await apiClient.get<Budget>(`/budgets/${budgetId}`)
  return response.data
}

export async function createBudget(name: string): Promise<Budget> {
  const response = await apiClient.post<Budget>('/budgets', { name })
  return response.data
}

export interface BudgetUpdateRequest {
  name?: string
  default_income_allocation?: DefaultIncomeAllocation
}

export async function updateBudget(budgetId: string, data: BudgetUpdateRequest): Promise<Budget> {
  const response = await apiClient.patch<Budget>(`/budgets/${budgetId}`, data)
  return response.data
}

export async function deleteBudget(budgetId: string, password: string): Promise<void> {
  await apiClient.delete(`/budgets/${budgetId}`, { data: { password } })
}

export async function getBudgetMembers(budgetId: string): Promise<BudgetMember[]> {
  const response = await apiClient.get<BudgetMember[]>(`/budgets/${budgetId}/members`)
  return response.data
}

export async function addBudgetMember(
  budgetId: string,
  data: AddMemberRequest
): Promise<BudgetMember> {
  const response = await apiClient.post<BudgetMember>(`/budgets/${budgetId}/members`, data)
  return response.data
}

export async function removeBudgetMember(
  budgetId: string,
  data: { username: string }
): Promise<void> {
  await apiClient.delete(`/budgets/${budgetId}/members`, { data })
}

export async function updateMemberRole(
  budgetId: string,
  userId: string,
  role: BudgetRole
): Promise<BudgetMember> {
  const response = await apiClient.patch<BudgetMember>(
    `/budgets/${budgetId}/members/${userId}/role`,
    { role }
  )
  return response.data
}

// Balance integrity check
export interface BalanceCheckResponse {
  needs_repair: boolean
}

export async function checkBalanceIntegrity(budgetId: string): Promise<BalanceCheckResponse> {
  const response = await apiClient.get<BalanceCheckResponse>(`/budgets/${budgetId}/balance-check`)
  return response.data
}

// Data export/import types
export interface ExportData {
  version: string
  exported_at: string
  budget: { name: string }
  accounts: unknown[]
  envelope_groups: unknown[]
  envelopes: unknown[]
  payees: unknown[]
  locations: unknown[]
  allocation_rules: unknown[]
  recurring_transactions: unknown[]
  transactions: unknown[]
  allocations: unknown[]
}

export interface ExportResponse {
  data: ExportData
}

export interface ImportResult {
  success: boolean
  accounts_imported: number
  envelope_groups_imported: number
  envelopes_imported: number
  payees_imported: number
  locations_imported: number
  allocation_rules_imported: number
  recurring_transactions_imported: number
  transactions_imported: number
  allocations_imported: number
  errors: string[]
}

export async function exportBudgetData(budgetId: string): Promise<ExportResponse> {
  const response = await apiClient.get<ExportResponse>(`/budgets/${budgetId}/export`)
  return response.data
}

export async function importBudgetData(
  budgetId: string,
  data: ExportData,
  clearExisting: boolean,
  password: string
): Promise<ImportResult> {
  const response = await apiClient.post<ImportResult>(`/budgets/${budgetId}/import`, {
    data,
    clear_existing: clearExisting,
    password,
  })
  return response.data
}
