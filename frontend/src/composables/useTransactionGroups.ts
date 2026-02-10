import { computed, type Ref, type ComputedRef } from 'vue'
import type { Transaction } from '@/types'

export interface TransactionGroup {
  date: string
  formattedDate: string
  transactions: Transaction[]
}

export interface UseTransactionGroupsOptions {
  transactions: Ref<Transaction[]> | ComputedRef<Transaction[]>
  sortOrder?: 'ascending' | 'descending'
  dateMode?: 'past' | 'future'
}

export function useTransactionGroups(options: UseTransactionGroupsOptions) {
  const { transactions, sortOrder = 'descending', dateMode = 'past' } = options

  function formatDateHeader(dateStr: string): string {
    const date = new Date(dateStr + 'T00:00:00')
    const today = new Date()
    today.setHours(0, 0, 0, 0)

    if (dateMode === 'future') {
      const tomorrow = new Date(today)
      tomorrow.setDate(tomorrow.getDate() + 1)

      // Calculate days from today
      const diffTime = date.getTime() - today.getTime()
      const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24))

      if (date.getTime() === today.getTime()) {
        return 'Today'
      }
      if (date.getTime() === tomorrow.getTime()) {
        return 'Tomorrow'
      }

      // Within 7 days - show weekday name only
      if (diffDays > 0 && diffDays <= 7) {
        return date.toLocaleDateString('en-US', { weekday: 'long' })
      }

      // Full date for further out
      return date.toLocaleDateString('en-US', {
        weekday: 'long',
        month: 'long',
        day: 'numeric',
        year: date.getFullYear() !== today.getFullYear() ? 'numeric' : undefined,
      })
    } else {
      // Past mode (default)
      const yesterday = new Date(today)
      yesterday.setDate(yesterday.getDate() - 1)

      if (date.getTime() === today.getTime()) {
        return 'Today'
      }
      if (date.getTime() === yesterday.getTime()) {
        return 'Yesterday'
      }

      return date.toLocaleDateString('en-US', {
        weekday: 'long',
        month: 'long',
        day: 'numeric',
        year: date.getFullYear() !== today.getFullYear() ? 'numeric' : undefined,
      })
    }
  }

  const groupedTransactions = computed<TransactionGroup[]>(() => {
    const groups: Record<string, Transaction[]> = {}

    for (const txn of transactions.value) {
      const dateKey = txn.date
      if (!groups[dateKey]) {
        groups[dateKey] = []
      }
      groups[dateKey]!.push(txn)
    }

    // Sort based on sortOrder
    const sortFn =
      sortOrder === 'ascending'
        ? ([a]: [string, Transaction[]], [b]: [string, Transaction[]]) => a.localeCompare(b)
        : ([a]: [string, Transaction[]], [b]: [string, Transaction[]]) => b.localeCompare(a)

    return Object.entries(groups)
      .sort(sortFn)
      .map(([date, transactions]) => ({
        date,
        formattedDate: formatDateHeader(date),
        transactions,
      }))
  })

  return { groupedTransactions }
}
