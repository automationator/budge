import apiClient from './client'
import type { Account } from '@/types'

export interface AccountCreate {
  name: string
  account_type: Account['account_type']
  icon?: string | null
  description?: string | null
  sort_order?: number
  include_in_budget?: boolean
  is_active?: boolean
}

export interface AccountUpdate {
  name?: string
  account_type?: Account['account_type']
  icon?: string | null
  description?: string | null
  sort_order?: number
  include_in_budget?: boolean
  is_active?: boolean
}

export interface ReconcileRequest {
  actual_balance: number
}

export async function listAccounts(budgetId: string): Promise<Account[]> {
  const response = await apiClient.get<Account[]>(`/budgets/${budgetId}/accounts`)
  return response.data
}

export async function getAccount(budgetId: string, accountId: string): Promise<Account> {
  const response = await apiClient.get<Account>(`/budgets/${budgetId}/accounts/${accountId}`)
  return response.data
}

export async function createAccount(budgetId: string, data: AccountCreate): Promise<Account> {
  const response = await apiClient.post<Account>(`/budgets/${budgetId}/accounts`, data)
  return response.data
}

export async function updateAccount(
  budgetId: string,
  accountId: string,
  data: AccountUpdate
): Promise<Account> {
  const response = await apiClient.patch<Account>(`/budgets/${budgetId}/accounts/${accountId}`, data)
  return response.data
}

export async function deleteAccount(budgetId: string, accountId: string): Promise<void> {
  await apiClient.delete(`/budgets/${budgetId}/accounts/${accountId}`)
}

export async function reconcileAccount(
  budgetId: string,
  accountId: string,
  actualBalance: number
): Promise<void> {
  await apiClient.post(`/budgets/${budgetId}/accounts/${accountId}/reconcile`, {
    actual_balance: actualBalance,
  })
}

export interface BalanceCorrection {
  account_id: string
  account_name: string
  old_cleared: number
  old_uncleared: number
  new_cleared: number
  new_uncleared: number
}

export async function recalculateBalances(budgetId: string): Promise<BalanceCorrection[]> {
  const response = await apiClient.post<BalanceCorrection[]>(
    `/budgets/${budgetId}/accounts/recalculate-balances`
  )
  return response.data
}
