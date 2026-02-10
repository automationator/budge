import { useAccountsStore } from '@/stores/accounts'
import { useEnvelopesStore } from '@/stores/envelopes'
import { showSnackbar } from '@/composables/useSnackbar'
import { formatMoney } from '@/utils/money'
import type { Transaction } from '@/types'

export async function showEnvelopeBalanceToast(transaction: Transaction): Promise<void> {
  const accountsStore = useAccountsStore()
  const envelopesStore = useEnvelopesStore()

  // Only show for budget account transactions with allocations
  const account = accountsStore.getAccountById(transaction.account_id)
  if (!account?.include_in_budget) return
  if (!transaction.allocations?.length) return

  // Ensure budget summary is fresh (may already be refreshed by caller)
  await envelopesStore.fetchBudgetSummary()
  if (!envelopesStore.budgetSummary) return

  // Build flat lookup of envelope balances
  const balanceMap = new Map<string, { name: string; balance: number }>()
  for (const group of envelopesStore.budgetSummary.groups) {
    for (const env of group.envelopes) {
      balanceMap.set(env.envelope_id, {
        name: env.envelope_name,
        balance: env.balance,
      })
    }
  }

  // Collect updated balances for this transaction's allocations
  const parts: string[] = []
  for (const alloc of transaction.allocations) {
    const info = balanceMap.get(alloc.envelope_id)
    if (info) {
      parts.push(`${info.name}: ${formatMoney(info.balance)}`)
    }
  }

  if (parts.length > 0) {
    showSnackbar(parts.join(' · '), 'success')
  }
}
