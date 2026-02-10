import apiClient from './client'
import type { Transaction, CursorPage, TransactionStatus } from '@/types'

export interface AllocationInput {
  envelope_id: string
  amount: number
  memo?: string | null
}

export interface TransactionCreate {
  account_id: string
  payee_id: string
  location_id?: string | null
  date: string // ISO date string
  amount: number // in cents
  is_cleared?: boolean
  memo?: string | null
  allocations?: AllocationInput[]
  apply_allocation_rules?: boolean // When true, auto-distribute income via allocation rules
}

export interface AdjustmentCreate {
  account_id: string
  date: string // ISO date string
  amount: number // in cents (positive or negative)
  is_cleared?: boolean
  memo?: string | null
  allocations?: AllocationInput[] // Optional allocations (e.g., to unallocated envelope)
}

export interface TransactionUpdate {
  account_id?: string
  payee_id?: string | null
  location_id?: string | null
  date?: string
  amount?: number
  is_cleared?: boolean
  memo?: string | null
  allocations?: AllocationInput[]
}

export interface TransferCreate {
  source_account_id: string
  destination_account_id: string
  amount: number // positive amount in cents
  date: string
  memo?: string | null
  is_cleared?: boolean
  envelope_id?: string | null // Required for budget -> tracking transfers
}

export interface TransferUpdate {
  source_account_id?: string
  destination_account_id?: string
  amount?: number
  date?: string
  memo?: string | null
  source_is_cleared?: boolean
  destination_is_cleared?: boolean
  envelope_id?: string | null // For budget -> tracking transfers
}

export interface TransferResponse {
  source_transaction: Transaction
  destination_transaction: Transaction
}

export interface ListTransactionsParams {
  limit?: number
  cursor?: string | null
  account_id?: string
  envelope_id?: string
  payee_id?: string
  location_id?: string
  status?: TransactionStatus[]
  /** Include scheduled transactions (default: true). Ignored if `status` is set. */
  include_scheduled?: boolean
  /** Include skipped transactions (default: false). Ignored if `status` is set. */
  include_skipped?: boolean
  is_reconciled?: boolean
  include_in_budget?: boolean
  expenses_only?: boolean
  exclude_adjustments?: boolean
}

export async function listTransactions(
  budgetId: string,
  params: ListTransactionsParams = {}
): Promise<CursorPage<Transaction>> {
  const response = await apiClient.get<CursorPage<Transaction>>(
    `/budgets/${budgetId}/transactions`,
    {
      params,
      // FastAPI expects repeated keys for arrays (status=a&status=b), not brackets (status[]=a)
      paramsSerializer: {
        indexes: null, // Removes brackets from array params
      },
    }
  )
  return response.data
}

export async function getTransaction(
  budgetId: string,
  transactionId: string
): Promise<Transaction> {
  const response = await apiClient.get<Transaction>(
    `/budgets/${budgetId}/transactions/${transactionId}`
  )
  return response.data
}

export async function createTransaction(
  budgetId: string,
  data: TransactionCreate
): Promise<Transaction> {
  const response = await apiClient.post<Transaction>(
    `/budgets/${budgetId}/transactions`,
    data
  )
  return response.data
}

export async function createAdjustment(
  budgetId: string,
  data: AdjustmentCreate
): Promise<Transaction> {
  const { allocations, ...rest } = data
  const response = await apiClient.post<Transaction>(
    `/budgets/${budgetId}/transactions`,
    {
      ...rest,
      transaction_type: 'adjustment',
      payee_id: null,
      allocations: allocations || undefined,
    }
  )
  return response.data
}

export async function updateTransaction(
  budgetId: string,
  transactionId: string,
  data: TransactionUpdate
): Promise<Transaction> {
  const response = await apiClient.patch<Transaction>(
    `/budgets/${budgetId}/transactions/${transactionId}`,
    data
  )
  return response.data
}

export async function deleteTransaction(
  budgetId: string,
  transactionId: string
): Promise<void> {
  await apiClient.delete(`/budgets/${budgetId}/transactions/${transactionId}`)
}

export async function skipTransaction(
  budgetId: string,
  transactionId: string
): Promise<Transaction> {
  const response = await apiClient.post<Transaction>(
    `/budgets/${budgetId}/transactions/${transactionId}/skip`
  )
  return response.data
}

export async function resetTransaction(
  budgetId: string,
  transactionId: string
): Promise<Transaction> {
  const response = await apiClient.post<Transaction>(
    `/budgets/${budgetId}/transactions/${transactionId}/reset`
  )
  return response.data
}

// Transfers
export async function createTransfer(
  budgetId: string,
  data: TransferCreate
): Promise<TransferResponse> {
  const response = await apiClient.post<TransferResponse>(
    `/budgets/${budgetId}/transactions/transfers`,
    data
  )
  return response.data
}

export async function getTransfer(
  budgetId: string,
  transactionId: string
): Promise<TransferResponse> {
  const response = await apiClient.get<TransferResponse>(
    `/budgets/${budgetId}/transactions/transfers/${transactionId}`
  )
  return response.data
}

export async function updateTransfer(
  budgetId: string,
  transactionId: string,
  data: TransferUpdate
): Promise<TransferResponse> {
  const response = await apiClient.patch<TransferResponse>(
    `/budgets/${budgetId}/transactions/transfers/${transactionId}`,
    data
  )
  return response.data
}

export async function deleteTransfer(
  budgetId: string,
  transactionId: string
): Promise<void> {
  await apiClient.delete(`/budgets/${budgetId}/transactions/transfers/${transactionId}`)
}

export interface UnallocatedCountResponse {
  count: number
}

export async function getUnallocatedCount(
  budgetId: string
): Promise<UnallocatedCountResponse> {
  const response = await apiClient.get<UnallocatedCountResponse>(
    `/budgets/${budgetId}/transactions/unallocated-count`
  )
  return response.data
}
