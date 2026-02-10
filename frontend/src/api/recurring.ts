import apiClient from './client'
import type { RecurringTransaction, FrequencyUnit } from '@/types'

export interface RecurringTransactionCreate {
  account_id: string
  destination_account_id?: string | null
  payee_id?: string | null
  location_id?: string | null
  envelope_id?: string | null
  frequency_value: number
  frequency_unit: FrequencyUnit
  start_date: string
  end_date?: string | null
  amount: number
  memo?: string | null
}

export interface RecurringTransactionUpdate {
  account_id?: string
  destination_account_id?: string | null
  payee_id?: string | null
  location_id?: string | null
  envelope_id?: string | null
  frequency_value?: number
  frequency_unit?: FrequencyUnit
  start_date?: string
  end_date?: string | null
  amount?: number
  memo?: string | null
  is_active?: boolean
}

export async function listRecurringTransactions(
  budgetId: string,
  includeInactive = false
): Promise<RecurringTransaction[]> {
  const response = await apiClient.get<RecurringTransaction[]>(
    `/budgets/${budgetId}/recurring-transactions`,
    { params: { include_inactive: includeInactive } }
  )
  return response.data
}

export async function getRecurringTransaction(
  budgetId: string,
  recurringId: string
): Promise<RecurringTransaction> {
  const response = await apiClient.get<RecurringTransaction>(
    `/budgets/${budgetId}/recurring-transactions/${recurringId}`
  )
  return response.data
}

export async function createRecurringTransaction(
  budgetId: string,
  data: RecurringTransactionCreate
): Promise<RecurringTransaction> {
  const response = await apiClient.post<RecurringTransaction>(
    `/budgets/${budgetId}/recurring-transactions`,
    data
  )
  return response.data
}

export async function updateRecurringTransaction(
  budgetId: string,
  recurringId: string,
  data: RecurringTransactionUpdate,
  propagateToFuture = true
): Promise<RecurringTransaction> {
  const response = await apiClient.patch<RecurringTransaction>(
    `/budgets/${budgetId}/recurring-transactions/${recurringId}`,
    data,
    { params: { propagate_to_future: propagateToFuture } }
  )
  return response.data
}

export async function deleteRecurringTransaction(
  budgetId: string,
  recurringId: string,
  deleteScheduled = true
): Promise<void> {
  await apiClient.delete(`/budgets/${budgetId}/recurring-transactions/${recurringId}`, {
    params: { delete_scheduled: deleteScheduled },
  })
}
