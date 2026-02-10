import apiClient from './client'
import type { Allocation } from '@/types'

export interface AllocationUpdate {
  envelope_id?: string
  amount?: number
  memo?: string | null
}

export async function listAllocationsForEnvelope(
  budgetId: string,
  envelopeId: string
): Promise<Allocation[]> {
  const response = await apiClient.get<Allocation[]>(`/budgets/${budgetId}/allocations`, {
    params: { envelope_id: envelopeId },
  })
  return response.data
}

export async function listAllocationsForTransaction(
  budgetId: string,
  transactionId: string
): Promise<Allocation[]> {
  const response = await apiClient.get<Allocation[]>(`/budgets/${budgetId}/allocations`, {
    params: { transaction_id: transactionId },
  })
  return response.data
}

export async function updateAllocation(
  budgetId: string,
  allocationId: string,
  data: AllocationUpdate
): Promise<Allocation> {
  const response = await apiClient.patch<Allocation>(
    `/budgets/${budgetId}/allocations/${allocationId}`,
    data
  )
  return response.data
}
