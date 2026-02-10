import { http, HttpResponse } from 'msw'
import type { Account, Envelope, EnvelopeGroup, Transaction, Payee, User, AllocationRule, RecurringTransaction } from '@/types'
import type { EnvelopeBudgetSummaryResponse } from '@/api/envelopes'
import type {
  SpendingByCategoryResponse,
  IncomeVsExpensesResponse,
  PayeeAnalysisResponse,
  DaysOfRunwayResponse,
  SavingsGoalProgressResponse,
  RunwayTrendResponse,
  NetWorthResponse,
  UpcomingExpensesResponse,
  RecurringExpenseCoverageResponse,
  SpendingTrendsResponse,
  LocationSpendingResponse,
  EnvelopeBalanceHistoryResponse,
  AccountBalanceHistoryResponse,
  AllocationRuleEffectivenessResponse,
} from '@/api/reports'
import { factories } from './factories'

// Re-export factories for backward compatibility
export { factories }

const API_BASE = '/api/v1'

export const handlers = [
  // Auth endpoints
  http.post(`${API_BASE}/auth/login`, async ({ request }) => {
    const body = (await request.json()) as { username: string; password: string }
    if (body.username === 'testuser' && body.password === 'password') {
      return HttpResponse.json(factories.loginResponse())
    }
    return HttpResponse.json({ detail: 'Invalid credentials' }, { status: 401 })
  }),

  http.post(`${API_BASE}/users`, async ({ request }) => {
    const body = (await request.json()) as { username: string; password: string }
    return HttpResponse.json(factories.user({ username: body.username }), { status: 201 })
  }),

  http.post(`${API_BASE}/auth/logout`, () => {
    return HttpResponse.json(null, { status: 204 })
  }),

  http.post(`${API_BASE}/auth/refresh`, async ({ request }) => {
    const body = (await request.json()) as { refresh_token: string }
    if (body.refresh_token) {
      return HttpResponse.json({
        access_token: 'new-access-token',
        refresh_token: 'new-refresh-token',
      })
    }
    return HttpResponse.json({ detail: 'Invalid refresh token' }, { status: 401 })
  }),

  // User endpoints
  http.get(`${API_BASE}/users/me`, () => {
    return HttpResponse.json(factories.user())
  }),

  http.patch(`${API_BASE}/users/me`, async ({ request }) => {
    const body = (await request.json()) as Partial<User>
    return HttpResponse.json(factories.user(body))
  }),

  http.get(`${API_BASE}/budgets`, () => {
    return HttpResponse.json(factories.cursorPage([factories.budget()]))
  }),

  // Budget endpoints
  http.get(`${API_BASE}/budgets/:budgetId`, ({ params }) => {
    return HttpResponse.json(factories.budget({ id: params.budgetId as string }))
  }),

  // Accounts
  http.get(`${API_BASE}/budgets/:budgetId/accounts`, () => {
    return HttpResponse.json([
      factories.account(),
      factories.account({
        id: 'account-2',
        name: 'Savings',
        account_type: 'savings',
        cleared_balance: 500000,
        uncleared_balance: 0,
      }),
    ])
  }),

  http.post(`${API_BASE}/budgets/:budgetId/accounts`, async ({ request, params }) => {
    const body = (await request.json()) as Partial<Account>
    return HttpResponse.json(
      factories.account({
        ...body,
        id: 'new-account-id',
        budget_id: params.budgetId as string,
      }),
      { status: 201 }
    )
  }),

  http.get(`${API_BASE}/budgets/:budgetId/accounts/:accountId`, ({ params }) => {
    return HttpResponse.json(
      factories.account({
        id: params.accountId as string,
        budget_id: params.budgetId as string,
      })
    )
  }),

  http.patch(`${API_BASE}/budgets/:budgetId/accounts/:accountId`, async ({ request, params }) => {
    const body = (await request.json()) as Partial<Account>
    return HttpResponse.json(
      factories.account({
        ...body,
        id: params.accountId as string,
        budget_id: params.budgetId as string,
      })
    )
  }),

  http.delete(`${API_BASE}/budgets/:budgetId/accounts/:accountId`, () => {
    return HttpResponse.json(null, { status: 204 })
  }),

  http.post(`${API_BASE}/budgets/:budgetId/accounts/:accountId/reconcile`, () => {
    return HttpResponse.json(null, { status: 204 })
  }),

  // Transaction unallocated count (must be before generic transactions handler)
  http.get(`${API_BASE}/budgets/:budgetId/transactions/unallocated-count`, () => {
    return HttpResponse.json({ count: 0 })
  }),

  // Transactions
  http.get(`${API_BASE}/budgets/:budgetId/transactions`, () => {
    return HttpResponse.json(
      factories.cursorPage([
        factories.transaction(),
        factories.transaction({
          id: 'transaction-2',
          amount: 150000,
          date: '2024-01-10',
        }),
      ])
    )
  }),

  http.post(`${API_BASE}/budgets/:budgetId/transactions`, async ({ request, params }) => {
    const body = (await request.json()) as Partial<Transaction>
    return HttpResponse.json(
      factories.transaction({
        ...body,
        id: 'new-transaction-id',
        budget_id: params.budgetId as string,
      }),
      { status: 201 }
    )
  }),

  http.get(`${API_BASE}/budgets/:budgetId/transactions/:transactionId`, ({ params }) => {
    return HttpResponse.json(
      factories.transaction({
        id: params.transactionId as string,
        budget_id: params.budgetId as string,
      })
    )
  }),

  http.patch(`${API_BASE}/budgets/:budgetId/transactions/:transactionId`, async ({ request, params }) => {
    const body = (await request.json()) as Partial<Transaction>
    return HttpResponse.json(
      factories.transaction({
        ...body,
        id: params.transactionId as string,
        budget_id: params.budgetId as string,
      })
    )
  }),

  http.delete(`${API_BASE}/budgets/:budgetId/transactions/:transactionId`, () => {
    return HttpResponse.json(null, { status: 204 })
  }),

  // Envelope summary (quick summary - must be before generic /envelopes handler)
  http.get(`${API_BASE}/budgets/:budgetId/envelopes/summary`, () => {
    return HttpResponse.json({
      ready_to_assign: 20000,
      unfunded_cc_debt: 0,
    })
  }),

  // Envelope budget summary (must be before generic /envelopes handler)
  http.get(`${API_BASE}/budgets/:budgetId/envelopes/budget-summary`, () => {
    return HttpResponse.json({
      start_date: '2024-01-01',
      end_date: '2024-01-31',
      ready_to_assign: 20000,
      total_activity: 0,
      total_balance: 170000,
      groups: [
        {
          group_id: null,
          group_name: null,
          icon: null,
          sort_order: 0,
          envelopes: [
            {
              envelope_id: 'envelope-1',
              envelope_name: 'Groceries',
              envelope_group_id: null,
              linked_account_id: null,
              icon: null,
              sort_order: 0,
              is_starred: false,
              activity: 0,
              balance: 50000,
              target_balance: 60000,
            },
            {
              envelope_id: 'envelope-2',
              envelope_name: 'Rent',
              envelope_group_id: null,
              linked_account_id: null,
              icon: null,
              sort_order: 1,
              is_starred: false,
              activity: 0,
              balance: 120000,
              target_balance: 150000,
            },
          ],
          total_activity: 0,
          total_balance: 170000,
        },
      ],
    } satisfies EnvelopeBudgetSummaryResponse)
  }),

  // Envelopes
  http.get(`${API_BASE}/budgets/:budgetId/envelopes`, () => {
    return HttpResponse.json([
      factories.envelope({ is_unallocated: true, name: 'Unallocated', current_balance: 20000 }),
      factories.envelope(),
      factories.envelope({
        id: 'envelope-2',
        name: 'Rent',
        current_balance: 120000,
        target_balance: 150000,
      }),
    ])
  }),

  http.post(`${API_BASE}/budgets/:budgetId/envelopes`, async ({ request, params }) => {
    const body = (await request.json()) as Partial<Envelope>
    return HttpResponse.json(
      factories.envelope({
        ...body,
        id: 'new-envelope-id',
        budget_id: params.budgetId as string,
      }),
      { status: 201 }
    )
  }),

  http.get(`${API_BASE}/budgets/:budgetId/envelopes/:envelopeId`, ({ params }) => {
    return HttpResponse.json(
      factories.envelope({
        id: params.envelopeId as string,
        budget_id: params.budgetId as string,
      })
    )
  }),

  http.patch(`${API_BASE}/budgets/:budgetId/envelopes/:envelopeId`, async ({ request, params }) => {
    const body = (await request.json()) as Partial<Envelope>
    return HttpResponse.json(
      factories.envelope({
        ...body,
        id: params.envelopeId as string,
        budget_id: params.budgetId as string,
      })
    )
  }),

  http.delete(`${API_BASE}/budgets/:budgetId/envelopes/:envelopeId`, () => {
    return HttpResponse.json(null, { status: 204 })
  }),

  // Allocations
  http.get(`${API_BASE}/budgets/:budgetId/allocations`, () => {
    return HttpResponse.json([])
  }),

  // Budget members
  http.get(`${API_BASE}/budgets/:budgetId/members`, () => {
    return HttpResponse.json([
      {
        id: 'user-1',
        username: 'testuser',
        email: null,
        first_name: null,
        last_name: null,
        role: 'owner',
        effective_scopes: [],
      },
    ])
  }),

  // Budget update
  http.patch(`${API_BASE}/budgets/:budgetId`, async ({ request, params }) => {
    const body = (await request.json()) as Partial<{ name: string }>
    return HttpResponse.json(factories.budget({ id: params.budgetId as string, ...body }))
  }),

  // Budget delete
  http.delete(`${API_BASE}/budgets/:budgetId`, () => {
    return HttpResponse.json(null, { status: 204 })
  }),

  // Envelope groups
  http.get(`${API_BASE}/budgets/:budgetId/envelope-groups`, () => {
    return HttpResponse.json([])
  }),

  http.post(`${API_BASE}/budgets/:budgetId/envelope-groups`, async ({ request, params }) => {
    const body = (await request.json()) as Partial<EnvelopeGroup>
    return HttpResponse.json(
      {
        id: 'new-group-id',
        budget_id: params.budgetId as string,
        name: body.name || 'New Group',
        icon: body.icon || null,
        sort_order: 0,
      },
      { status: 201 }
    )
  }),

  http.patch(`${API_BASE}/budgets/:budgetId/envelope-groups/:groupId`, async ({ request, params }) => {
    const body = (await request.json()) as Partial<EnvelopeGroup>
    return HttpResponse.json({
      id: params.groupId as string,
      budget_id: params.budgetId as string,
      name: body.name || 'Group',
      icon: body.icon || null,
      sort_order: body.sort_order ?? 0,
    })
  }),

  // Payees
  http.get(`${API_BASE}/budgets/:budgetId/payees`, () => {
    return HttpResponse.json([factories.payee()])
  }),

  http.post(`${API_BASE}/budgets/:budgetId/payees`, async ({ request, params }) => {
    const body = (await request.json()) as Partial<Payee>
    return HttpResponse.json(
      factories.payee({
        ...body,
        id: 'new-payee-id',
        budget_id: params.budgetId as string,
      }),
      { status: 201 }
    )
  }),

  // Locations
  http.get(`${API_BASE}/budgets/:budgetId/locations`, () => {
    return HttpResponse.json([])
  }),

  // Notification preferences
  http.get(`${API_BASE}/budgets/:budgetId/notifications/preferences`, () => {
    return HttpResponse.json([
      {
        id: 'pref-1',
        budget_id: 'budget-1',
        user_id: 'user-1',
        notification_type: 'low_balance',
        is_enabled: true,
        low_balance_threshold: 5000,
        upcoming_expense_days: null,
      },
      {
        id: 'pref-2',
        budget_id: 'budget-1',
        user_id: 'user-1',
        notification_type: 'upcoming_expense',
        is_enabled: true,
        low_balance_threshold: null,
        upcoming_expense_days: 3,
      },
      {
        id: 'pref-3',
        budget_id: 'budget-1',
        user_id: 'user-1',
        notification_type: 'recurring_not_funded',
        is_enabled: true,
        low_balance_threshold: null,
        upcoming_expense_days: null,
      },
      {
        id: 'pref-4',
        budget_id: 'budget-1',
        user_id: 'user-1',
        notification_type: 'goal_reached',
        is_enabled: true,
        low_balance_threshold: null,
        upcoming_expense_days: null,
      },
    ])
  }),

  // Allocations
  http.post(`${API_BASE}/budgets/:budgetId/allocations/transfer`, async () => {
    return HttpResponse.json({ success: true })
  }),

  // Allocation Rules
  http.get(`${API_BASE}/budgets/:budgetId/allocation-rules`, () => {
    return HttpResponse.json([
      factories.allocationRule(),
      factories.allocationRule({
        id: 'rule-2',
        envelope_id: 'envelope-2',
        priority: 1,
        rule_type: 'percentage',
        amount: 1000, // 10%
        name: 'Rent Percentage',
      }),
      factories.allocationRule({
        id: 'rule-3',
        envelope_id: 'envelope-1',
        priority: 2,
        rule_type: 'remainder',
        amount: 1,
        name: 'Remainder to Savings',
        is_active: false,
      }),
    ])
  }),

  http.get(`${API_BASE}/budgets/:budgetId/allocation-rules/:ruleId`, ({ params }) => {
    return HttpResponse.json(
      factories.allocationRule({
        id: params.ruleId as string,
        budget_id: params.budgetId as string,
      })
    )
  }),

  http.post(`${API_BASE}/budgets/:budgetId/allocation-rules`, async ({ request, params }) => {
    const body = (await request.json()) as Partial<AllocationRule>
    return HttpResponse.json(
      factories.allocationRule({
        ...body,
        id: 'new-rule-id',
        budget_id: params.budgetId as string,
      }),
      { status: 201 }
    )
  }),

  http.patch(`${API_BASE}/budgets/:budgetId/allocation-rules/:ruleId`, async ({ request, params }) => {
    const body = (await request.json()) as Partial<AllocationRule>
    return HttpResponse.json(
      factories.allocationRule({
        ...body,
        id: params.ruleId as string,
        budget_id: params.budgetId as string,
      })
    )
  }),

  http.delete(`${API_BASE}/budgets/:budgetId/allocation-rules/:ruleId`, () => {
    return HttpResponse.json(null, { status: 204 })
  }),

  http.post(`${API_BASE}/budgets/:budgetId/allocation-rules/preview`, async ({ request }) => {
    const body = (await request.json()) as { amount: number }
    return HttpResponse.json(
      factories.rulePreviewResponse({
        income_amount: body.amount,
        allocations: [
          {
            envelope_id: 'envelope-1',
            amount: Math.round(body.amount * 0.1),
            rule_id: 'rule-1',
            rule_name: 'Savings Rule',
          },
          {
            envelope_id: 'envelope-2',
            amount: Math.round(body.amount * 0.1),
            rule_id: 'rule-2',
            rule_name: 'Rent Percentage',
          },
        ],
        unallocated: Math.round(body.amount * 0.8),
      })
    )
  }),

  // Recurring Transactions
  http.get(`${API_BASE}/budgets/:budgetId/recurring-transactions`, () => {
    return HttpResponse.json([
      factories.recurringTransaction(),
      factories.recurringIncome({
        id: 'recurring-2',
        payee_id: 'payee-2',
      }),
      factories.inactiveRecurring({
        id: 'recurring-3',
        payee_id: 'payee-1',
        amount: -3000,
      }),
    ])
  }),

  http.post(`${API_BASE}/budgets/:budgetId/recurring-transactions`, async ({ request, params }) => {
    const body = (await request.json()) as Partial<RecurringTransaction>
    return HttpResponse.json(
      factories.recurringTransaction({
        ...body,
        id: 'new-recurring-id',
        budget_id: params.budgetId as string,
      }),
      { status: 201 }
    )
  }),

  http.patch(`${API_BASE}/budgets/:budgetId/recurring-transactions/:recurringId`, async ({ request, params }) => {
    const body = (await request.json()) as Partial<RecurringTransaction>
    return HttpResponse.json(
      factories.recurringTransaction({
        ...body,
        id: params.recurringId as string,
        budget_id: params.budgetId as string,
      })
    )
  }),

  http.delete(`${API_BASE}/budgets/:budgetId/recurring-transactions/:recurringId`, () => {
    return HttpResponse.json(null, { status: 204 })
  }),

  // Report endpoints
  http.get(`${API_BASE}/budgets/:budgetId/reports/spending-by-category`, () => {
    return HttpResponse.json({
      start_date: null,
      end_date: null,
      days_in_period: 90,
      items: [],
    } satisfies SpendingByCategoryResponse)
  }),

  http.get(`${API_BASE}/budgets/:budgetId/reports/income-vs-expenses`, () => {
    return HttpResponse.json({
      start_date: null,
      end_date: null,
      total_income: 0,
      total_expenses: 0,
      total_net: 0,
      periods: [],
    } satisfies IncomeVsExpensesResponse)
  }),

  http.get(`${API_BASE}/budgets/:budgetId/reports/payee-analysis`, () => {
    return HttpResponse.json({
      start_date: null,
      end_date: null,
      items: [],
    } satisfies PayeeAnalysisResponse)
  }),

  http.get(`${API_BASE}/budgets/:budgetId/reports/days-of-runway`, () => {
    return HttpResponse.json({
      start_date: '2024-01-01',
      end_date: '2024-03-31',
      calculation_period_days: 30,
      total_balance: 0,
      total_average_daily_spending: 0,
      total_days_of_runway: null,
      items: [],
    } satisfies DaysOfRunwayResponse)
  }),

  http.get(`${API_BASE}/budgets/:budgetId/reports/savings-goal-progress`, () => {
    return HttpResponse.json({
      as_of_date: '2024-01-01',
      items: [],
    } satisfies SavingsGoalProgressResponse)
  }),

  http.get(`${API_BASE}/budgets/:budgetId/reports/runway-trend`, () => {
    return HttpResponse.json({
      start_date: '2024-01-01',
      end_date: '2024-03-31',
      lookback_days: 30,
      envelope_id: null,
      envelope_name: null,
      data_points: [],
    } satisfies RunwayTrendResponse)
  }),

  http.get(`${API_BASE}/budgets/:budgetId/reports/net-worth`, () => {
    return HttpResponse.json({
      start_date: '2024-01-01',
      end_date: '2024-03-31',
      current_net_worth: 0,
      current_total_assets: 0,
      current_total_liabilities: 0,
      net_worth_change: 0,
      periods: [],
    } satisfies NetWorthResponse)
  }),

  http.get(`${API_BASE}/budgets/:budgetId/reports/upcoming-expenses`, () => {
    return HttpResponse.json({
      as_of_date: '2024-01-01',
      items: [],
    } satisfies UpcomingExpensesResponse)
  }),

  http.get(`${API_BASE}/budgets/:budgetId/reports/recurring-expense-coverage`, () => {
    return HttpResponse.json({
      as_of_date: '2024-01-01',
      total_recurring: 0,
      fully_funded_count: 0,
      partially_funded_count: 0,
      not_linked_count: 0,
      total_shortfall: 0,
      items: [],
    } satisfies RecurringExpenseCoverageResponse)
  }),

  http.get(`${API_BASE}/budgets/:budgetId/reports/spending-trends`, () => {
    return HttpResponse.json({
      start_date: '2024-01-01',
      end_date: '2024-03-31',
      period_count: 0,
      envelopes: [],
    } satisfies SpendingTrendsResponse)
  }),

  http.get(`${API_BASE}/budgets/:budgetId/reports/location-spending`, () => {
    return HttpResponse.json({
      start_date: null,
      end_date: null,
      include_no_location: true,
      items: [],
    } satisfies LocationSpendingResponse)
  }),

  http.get(`${API_BASE}/budgets/:budgetId/reports/envelope-balance-history`, () => {
    return HttpResponse.json({
      envelope_id: 'envelope-1',
      envelope_name: 'Groceries',
      start_date: '2024-01-01',
      end_date: '2024-03-31',
      current_balance: 0,
      target_balance: null,
      items: [],
    } satisfies EnvelopeBalanceHistoryResponse)
  }),

  http.get(`${API_BASE}/budgets/:budgetId/reports/account-balance-history`, () => {
    return HttpResponse.json({
      account_id: 'account-1',
      account_name: 'Checking',
      start_date: '2024-01-01',
      end_date: '2024-03-31',
      current_balance: 0,
      items: [],
    } satisfies AccountBalanceHistoryResponse)
  }),

  http.get(`${API_BASE}/budgets/:budgetId/reports/allocation-rule-effectiveness`, () => {
    return HttpResponse.json({
      start_date: null,
      end_date: null,
      active_rules_only: true,
      items: [],
    } satisfies AllocationRuleEffectivenessResponse)
  }),

  // Admin settings
  http.get(`${API_BASE}/admin/settings`, () => {
    return HttpResponse.json({ registration_enabled: true })
  }),

  http.patch(`${API_BASE}/admin/settings`, async ({ request }) => {
    const body = (await request.json()) as Partial<{ registration_enabled: boolean }>
    return HttpResponse.json({ registration_enabled: body.registration_enabled ?? true })
  }),

  // Export budget data
  http.get(`${API_BASE}/budgets/:budgetId/export`, () => {
    return HttpResponse.json({
      data: {
        version: '1.0',
        exported_at: '2024-01-15T00:00:00Z',
        budget: { name: 'Personal' },
        accounts: [],
        envelope_groups: [],
        envelopes: [],
        payees: [],
        locations: [],
        allocation_rules: [],
        recurring_transactions: [],
        transactions: [],
        allocations: [],
      },
    })
  }),

  // Import budget data
  http.post(`${API_BASE}/budgets/:budgetId/import`, () => {
    return HttpResponse.json({
      success: true,
      accounts_imported: 0,
      envelope_groups_imported: 0,
      envelopes_imported: 0,
      payees_imported: 0,
      locations_imported: 0,
      allocation_rules_imported: 0,
      recurring_transactions_imported: 0,
      transactions_imported: 0,
      allocations_imported: 0,
      errors: [],
    })
  }),

  // Recalculate account balances
  http.post(`${API_BASE}/budgets/:budgetId/accounts/recalculate-balances`, () => {
    return HttpResponse.json([])
  }),

  // Recalculate envelope balances
  http.post(`${API_BASE}/budgets/:budgetId/envelopes/recalculate-balances`, () => {
    return HttpResponse.json([])
  }),

  // Public endpoints
  http.get(`${API_BASE}/public/registration-status`, () => {
    return HttpResponse.json({ registration_enabled: true })
  }),
]
