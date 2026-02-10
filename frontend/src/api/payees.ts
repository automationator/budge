import apiClient from './client'
import type { Payee, DefaultEnvelope } from '@/types'

export interface PayeeCreate {
  name: string
  icon?: string | null
  description?: string | null
}

export interface PayeeUpdate {
  name?: string
  icon?: string | null
  description?: string | null
  default_envelope_id?: string | null
}

export async function listPayees(budgetId: string): Promise<Payee[]> {
  const response = await apiClient.get<Payee[]>(`/budgets/${budgetId}/payees`)
  return response.data
}

export async function getPayee(budgetId: string, payeeId: string): Promise<Payee> {
  const response = await apiClient.get<Payee>(`/budgets/${budgetId}/payees/${payeeId}`)
  return response.data
}

export async function createPayee(budgetId: string, data: PayeeCreate): Promise<Payee> {
  const response = await apiClient.post<Payee>(`/budgets/${budgetId}/payees`, data)
  return response.data
}

export async function updatePayee(
  budgetId: string,
  payeeId: string,
  data: PayeeUpdate
): Promise<Payee> {
  const response = await apiClient.patch<Payee>(`/budgets/${budgetId}/payees/${payeeId}`, data)
  return response.data
}

export async function deletePayee(budgetId: string, payeeId: string): Promise<void> {
  await apiClient.delete(`/budgets/${budgetId}/payees/${payeeId}`)
}

export async function getDefaultEnvelope(
  budgetId: string,
  payeeId: string
): Promise<DefaultEnvelope> {
  const response = await apiClient.get<DefaultEnvelope>(
    `/budgets/${budgetId}/payees/${payeeId}/default-envelope`
  )
  return response.data
}
