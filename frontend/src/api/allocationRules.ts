import apiClient from './client'
import type { AllocationRule, AllocationRuleType } from '@/types'

export interface AllocationRuleCreate {
  envelope_id: string
  priority: number
  rule_type: AllocationRuleType
  amount?: number
  is_active?: boolean
  name?: string | null
  respect_target?: boolean
  cap_period_value?: number
  cap_period_unit?: string | null
}

export interface AllocationRuleUpdate {
  envelope_id?: string
  priority?: number
  rule_type?: AllocationRuleType
  amount?: number
  is_active?: boolean
  name?: string | null
  respect_target?: boolean
  cap_period_value?: number
  cap_period_unit?: string | null
}

export interface RulePreviewInput {
  amount: number
}

export interface RulePreviewAllocation {
  envelope_id: string
  amount: number
  rule_id: string
  rule_name: string | null
}

export interface RulePreviewResponse {
  income_amount: number
  allocations: RulePreviewAllocation[]
  unallocated: number
}

export interface ApplyRulesAllocation {
  envelope_id: string
  envelope_name: string
  amount: number
  rule_id: string | null
  rule_name: string | null
}

export interface ApplyRulesResponse {
  initial_unallocated: number
  allocations: ApplyRulesAllocation[]
  final_unallocated: number
}

export async function listAllocationRules(
  budgetId: string,
  activeOnly = false
): Promise<AllocationRule[]> {
  const response = await apiClient.get<AllocationRule[]>(
    `/budgets/${budgetId}/allocation-rules`,
    { params: { active_only: activeOnly } }
  )
  return response.data
}

export async function getAllocationRule(
  budgetId: string,
  ruleId: string
): Promise<AllocationRule> {
  const response = await apiClient.get<AllocationRule>(
    `/budgets/${budgetId}/allocation-rules/${ruleId}`
  )
  return response.data
}

export async function createAllocationRule(
  budgetId: string,
  data: AllocationRuleCreate
): Promise<AllocationRule> {
  const response = await apiClient.post<AllocationRule>(
    `/budgets/${budgetId}/allocation-rules`,
    data
  )
  return response.data
}

export async function updateAllocationRule(
  budgetId: string,
  ruleId: string,
  data: AllocationRuleUpdate
): Promise<AllocationRule> {
  const response = await apiClient.patch<AllocationRule>(
    `/budgets/${budgetId}/allocation-rules/${ruleId}`,
    data
  )
  return response.data
}

export async function deleteAllocationRule(
  budgetId: string,
  ruleId: string
): Promise<void> {
  await apiClient.delete(`/budgets/${budgetId}/allocation-rules/${ruleId}`)
}

export async function previewAllocationRules(
  budgetId: string,
  data: RulePreviewInput
): Promise<RulePreviewResponse> {
  const response = await apiClient.post<RulePreviewResponse>(
    `/budgets/${budgetId}/allocation-rules/preview`,
    data
  )
  return response.data
}

export async function applyAllocationRules(
  budgetId: string
): Promise<ApplyRulesResponse> {
  const response = await apiClient.post<ApplyRulesResponse>(
    `/budgets/${budgetId}/allocation-rules/apply`
  )
  return response.data
}
