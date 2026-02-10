import apiClient from './client'
import type { Envelope, EnvelopeGroup } from '@/types'

export interface EnvelopeCreate {
  name: string
  envelope_group_id?: string | null
  icon?: string | null
  description?: string | null
  target_balance?: number | null
  is_active?: boolean
}

export interface EnvelopeUpdate {
  name?: string
  envelope_group_id?: string | null
  icon?: string | null
  description?: string | null
  target_balance?: number | null
  is_active?: boolean
  is_starred?: boolean
  sort_order?: number
}

export interface EnvelopeGroupCreate {
  name: string
  icon?: string | null
}

export interface EnvelopeGroupUpdate {
  name?: string
  icon?: string | null
  sort_order?: number
}

export interface TransferRequest {
  from_envelope_id: string
  to_envelope_id: string
  amount: number
}

export interface EnvelopeSummary {
  ready_to_assign: number
  unfunded_cc_debt: number
}

// Budget summary types (YNAB-style view)
export interface EnvelopeBudgetItem {
  envelope_id: string
  envelope_name: string
  envelope_group_id: string | null
  linked_account_id: string | null
  icon: string | null
  sort_order: number
  is_starred: boolean
  activity: number // Sum of all allocations (transactions + transfers) in date range
  balance: number // current_balance (not date-filtered)
  target_balance: number | null
}

export interface EnvelopeGroupBudgetSummary {
  group_id: string | null
  group_name: string | null
  icon: string | null
  sort_order: number
  envelopes: EnvelopeBudgetItem[]
  total_activity: number
  total_balance: number
}

export interface EnvelopeBudgetSummaryResponse {
  start_date: string
  end_date: string
  ready_to_assign: number
  total_activity: number
  total_balance: number
  groups: EnvelopeGroupBudgetSummary[]
}

export interface EnvelopeActivityItem {
  allocation_id: string
  transaction_id: string | null // null for transfers
  date: string
  activity_type: 'transaction' | 'transfer'

  // Transaction fields (null for transfers)
  account_id: string | null
  account_name: string | null
  payee_id: string | null
  payee_name: string | null
  memo: string | null

  // Transfer fields (null for transactions)
  counterpart_envelope_name?: string | null

  amount: number
}

export interface EnvelopeActivityResponse {
  envelope_id: string
  envelope_name: string
  start_date: string
  end_date: string
  items: EnvelopeActivityItem[]
  total: number
}

// Envelope Groups
export async function listEnvelopeGroups(budgetId: string): Promise<EnvelopeGroup[]> {
  const response = await apiClient.get<EnvelopeGroup[]>(`/budgets/${budgetId}/envelope-groups`)
  return response.data
}

export async function createEnvelopeGroup(
  budgetId: string,
  data: EnvelopeGroupCreate
): Promise<EnvelopeGroup> {
  const response = await apiClient.post<EnvelopeGroup>(`/budgets/${budgetId}/envelope-groups`, data)
  return response.data
}

export async function updateEnvelopeGroup(
  budgetId: string,
  groupId: string,
  data: EnvelopeGroupUpdate
): Promise<EnvelopeGroup> {
  const response = await apiClient.patch<EnvelopeGroup>(
    `/budgets/${budgetId}/envelope-groups/${groupId}`,
    data
  )
  return response.data
}

export async function deleteEnvelopeGroup(budgetId: string, groupId: string): Promise<void> {
  await apiClient.delete(`/budgets/${budgetId}/envelope-groups/${groupId}`)
}

// Envelopes
export async function listEnvelopes(budgetId: string): Promise<Envelope[]> {
  const response = await apiClient.get<Envelope[]>(`/budgets/${budgetId}/envelopes`)
  return response.data
}

export async function getEnvelopeSummary(budgetId: string): Promise<EnvelopeSummary> {
  const response = await apiClient.get<EnvelopeSummary>(`/budgets/${budgetId}/envelopes/summary`)
  return response.data
}

export async function getEnvelope(budgetId: string, envelopeId: string): Promise<Envelope> {
  const response = await apiClient.get<Envelope>(`/budgets/${budgetId}/envelopes/${envelopeId}`)
  return response.data
}

export async function createEnvelope(budgetId: string, data: EnvelopeCreate): Promise<Envelope> {
  const response = await apiClient.post<Envelope>(`/budgets/${budgetId}/envelopes`, data)
  return response.data
}

export async function updateEnvelope(
  budgetId: string,
  envelopeId: string,
  data: EnvelopeUpdate
): Promise<Envelope> {
  const response = await apiClient.patch<Envelope>(
    `/budgets/${budgetId}/envelopes/${envelopeId}`,
    data
  )
  return response.data
}

export async function deleteEnvelope(budgetId: string, envelopeId: string): Promise<void> {
  await apiClient.delete(`/budgets/${budgetId}/envelopes/${envelopeId}`)
}

export interface TransferResponse {
  source_allocation: {
    id: string
    envelope_id: string
    amount: number
  }
  destination_allocation: {
    id: string
    envelope_id: string
    amount: number
  }
}

export async function transferBetweenEnvelopes(
  budgetId: string,
  data: TransferRequest
): Promise<TransferResponse> {
  // Backend expects source_envelope_id and destination_envelope_id
  const response = await apiClient.post<TransferResponse>(
    `/budgets/${budgetId}/allocations/envelope-transfer`,
    {
      source_envelope_id: data.from_envelope_id,
      destination_envelope_id: data.to_envelope_id,
      amount: data.amount,
    }
  )
  return response.data
}

export interface EnvelopeBalanceCorrection {
  envelope_id: string
  envelope_name: string
  old_balance: number
  new_balance: number
}

export async function recalculateEnvelopeBalances(
  budgetId: string
): Promise<EnvelopeBalanceCorrection[]> {
  const response = await apiClient.post<EnvelopeBalanceCorrection[]>(
    `/budgets/${budgetId}/envelopes/recalculate-balances`
  )
  return response.data
}

// Budget Summary (YNAB-style view)
export async function getEnvelopeBudgetSummary(
  budgetId: string,
  startDate: string,
  endDate: string
): Promise<EnvelopeBudgetSummaryResponse> {
  const response = await apiClient.get<EnvelopeBudgetSummaryResponse>(
    `/budgets/${budgetId}/envelopes/budget-summary`,
    { params: { start_date: startDate, end_date: endDate } }
  )
  return response.data
}

// Envelope Activity
export async function getEnvelopeActivity(
  budgetId: string,
  envelopeId: string,
  startDate: string,
  endDate: string
): Promise<EnvelopeActivityResponse> {
  const response = await apiClient.get<EnvelopeActivityResponse>(
    `/budgets/${budgetId}/envelopes/${envelopeId}/activity`,
    { params: { start_date: startDate, end_date: endDate } }
  )
  return response.data
}
