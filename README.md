# Budge

A rolling envelope budgeting application for continuous cash flow management.

## What is Budge?

Budge is a personal finance application built on **rolling envelope budgeting**—a continuous cash flow model with no monthly cycles. You allocate money to envelopes on your own schedule, whether manually with each paycheck or automatically via rules. There's no "fresh start" each month, no reconciling at month-end, and no arbitrary calendar boundaries. Your envelope balances are what matter.

See the [Philosophy](#philosophy) section for more on the thinking behind this approach.

## Core Concepts

### Envelopes

Purpose-driven containers that hold money for specific uses (groceries, rent, vacation, emergency fund). Each envelope answers one question: "How much do I have available for this purpose?"

### Accounts

Where your money actually sits—checking, savings, money market, credit cards, cash, investments, loans, and more. Budge tracks balances across all accounts to give you a complete financial picture. Accounts can be excluded from budget calculations, and reconciliation verifies your records match your bank.

### Transactions

You record every financial event—income that adds to your accounts, expenses that draw from your envelopes, and transfers that move money between accounts.

### Ready to Assign

Unallocated cash sitting in your accounts. This is money you've received but haven't yet assigned to an envelope. The goal is to assign every dollar to an envelope.

## Key Features

### Manual Control (Default)

Budge doesn't force automation. By default, you have complete control:

- Allocate income to envelopes however you want, whenever you want
- Move money between envelopes at any time
- No required workflows or forced automation
- Full control over every dollar

### Envelope Management

- **Balance tracking** — See how much is in each envelope
- **Target balances** — Set goals ("stop accumulating at $X")
- **Envelope groups** — Organize envelopes into categories
- **Favorites** — Star important envelopes for quick access
- **Icons** — Visual identification for envelopes

### Allocation Rules (Optional Automation)

If you want to automate income distribution, allocation rules handle it for you. These are completely optional—use them only if you find them helpful.

**Rule types:**
| Type | Behavior |
|------|----------|
| Fill to Target | Allocate until envelope reaches its target balance |
| Fixed Amount | Allocate exact amount (e.g., $1,500 to rent) |
| Percentage | Allocate percentage of income (e.g., 10% to savings) |
| Remainder | Split whatever's left among weighted envelopes |
| Period Cap | Limit how much can be allocated to an envelope per time period (e.g., max of $250/month to vacation) |

**How rules work:**
- Rules execute in priority order
- Overflow from one rule cascades to the next
- Preview allocations before applying
- Override with manual allocations anytime

**Default income allocation:** Each budget has a default income allocation setting that controls what happens when income arrives:

| Setting | Behavior |
|---------|----------|
| Rules | Run allocation rules automatically |
| Envelope | Allocate to a specific default envelope |
| Unallocated | Leave in Ready to Assign for manual allocation |

### Period Cap Rules (Rate Limiting)

Period Cap is a special rule type that limits how fast an envelope fills. Unlike other rule types, Period Cap rules don't allocate money—they limit how much other rules can allocate to the same envelope within a time period.

**Configuration:** Create a Period Cap rule with a maximum amount and period (week, month, or year).

| Example | Configuration |
|---------|---------------|
| $300/month for savings | Period Cap: $300, period: 1 month |
| $50/week for dining out | Period Cap: $50, period: 1 week |

**Calendar-aligned periods:**

| Period | Alignment |
|--------|-----------|
| Week | Monday–Sunday (ISO week) |
| Month | 1st through end of month |
| Year | January 1 – December 31 |

**Period Caps vs. Targets:**

These two concepts work together but serve different purposes:

| Concept | Purpose |
|---------|---------|
| Target balance | Maximum envelope balance ("stop when I have $3,600") |
| Period Cap rule | Maximum funding rate ("add at most $300/month") |

For an emergency fund, you might set a target balance of $3,600 and a Period Cap of $300/month to spread contributions evenly over the year.

**How overflow works when caps are hit:**

When an allocation rule runs and an envelope's Period Cap is reached, the excess flows to subsequent rules in priority order. This ensures your income is fully distributed according to your priorities.

**Example: $1,000 paycheck with three allocation rules**

| Priority | Rule | Period Cap Status |
|----------|------|-------------------|
| 1 | Vacation: 25% ($250) | $150/month cap, already at $100 this month |
| 2 | Savings: 20% ($200) | No cap |
| 3 | Dining: remainder | $100/month cap |

What happens:
1. Rule 1 calculates $250 for vacation, but cap allows only $50 more → $50 allocated, $200 overflows
2. Rule 2 receives its $200 for savings (no cap) → $200 allocated
3. Rule 3 (remainder) gets remaining $550, but cap allows only $100 → $100 allocated, $450 to Ready to Assign

**Result:** Vacation +$50, Savings +$200, Dining +$100, Ready to Assign +$650

### Credit Card Handling

Credit cards present a unique challenge for envelope budgeting: when you swipe a credit card, no money leaves your bank account yet, but you've committed to pay it later. Budge handles this with **linked credit card envelopes**.

**The problem:**

Without special handling, credit card spending can create a mismatch:

1. You budget $200 for dining out
2. You spend $150 on your credit card at restaurants
3. Your dining envelope shows $50 remaining—but that $150 hasn't left your bank yet
4. When the credit card bill comes, you need $150 you may have already allocated elsewhere

**How credit card envelopes work:**

When you create a credit card account, Budge automatically creates a linked credit card envelope. This envelope tracks how much money you have set aside to pay the card.

When you spend on a credit card:
1. The transaction reduces your spending envelope (dining, groceries, etc.)
2. Money automatically moves from that envelope to the credit card envelope
3. The CC envelope balance increases by the purchase amount

When you pay your credit card:
1. The payment reduces your bank account balance
2. The CC envelope balance decreases by the payment amount
3. No envelope move needed—you're using money already set aside

**Tracking payment coverage:**

A credit card envelope with a positive balance means you have that much set aside to pay the card. If the envelope balance is less than the card balance, the difference is unfunded debt. The budget summary displays total **Unfunded CC Debt** across all cards so you can see at a glance whether you need to allocate more.

| CC Envelope Balance | Card Balance | Result |
|---------------------|--------------|--------|
| $500 | $500 owed | Fully covered—pay anytime |
| $300 | $500 owed | $200 unfunded debt |
| $500 | $200 owed | $300 overfunded |

**Credit vs. debit spending:**

From an envelope perspective, credit and debit spending work identically:

| Action | Debit Card | Credit Card |
|--------|-----------|-------------|
| Buy $50 groceries | Groceries envelope: -$50 | Groceries envelope: -$50, CC envelope: +$50 |
| Net envelope impact | -$50 from groceries | -$50 from groceries (moved to CC) |

The extra step for credit cards (the envelope move) happens automatically.

**Credit cards and Ready to Assign:**

Credit card spending has a net-zero effect on Ready to Assign. The formula is:

```
Ready to Assign = Non-CC Budget Account Balances − Assigned Envelope Balances
```

Assigned envelope balances means all envelopes except Ready to Assign itself. Credit card accounts are excluded because CC debt is a liability—borrowed money that hasn't affected your actual cash yet. When you pay the card, that's when cash leaves your bank account.

**Example:**
1. Checking: $100, Groceries envelope: $100, Ready to Assign: $0
2. Spend $10 on CC from Groceries
3. After: Groceries: $90, CC envelope: $10, Ready to Assign: still $0

The total in envelopes ($90 + $10 = $100) still matches your actual cash ($100 in checking).

**Unfunded credit card debt:**

If you add a credit card with existing debt from before you started using Budge, the system shows a warning for unfunded CC debt—debt not covered by any envelope balance.

**Example:**
- Checking: $100, Groceries envelope: $100, Ready to Assign: $0
- Add CC with existing -$50 balance
- CC envelope: $0 (no funds set aside yet)
- Ready to Assign: still $0 (CC debt doesn't affect it)
- Warning shown: "$50 unfunded CC debt"

The warning reminds you that this debt needs a payoff plan. You can allocate money to the CC envelope to cover it, or pay it down over time as income arrives.

### Recurring Transactions

Set up templates for regular income and expenses:

- **Frequency options:** Daily, weekly, monthly, yearly (with multipliers like "every 2 weeks")
- **Types:** Expenses, income, or transfers between accounts
- **Auto-allocation:** Assign to a default envelope
- **Skip functionality:** Skip individual occurrences without deleting the template

### Transfers

Move money between:
- **Accounts** — Transfer from checking to savings
- **Envelopes** — Reallocate from dining out to groceries

Transfers create linked transaction pairs for accurate tracking.

### Payees and Locations

Track who and where your money goes:

- **Payees** — Merchants, employers, or anyone you transact with
- **Locations** — Physical places (useful for tracking spending by city, state, etc. if you travel a lot)
- **Default envelopes** — Auto-assign transactions from specific payees to envelopes

### Account Reconciliation

Reconciliation verifies that your records match your bank's records:

- Mark cleared transactions as reconciled
- If your cleared balance doesn't match the bank, an adjustment transaction is created automatically
- Tracks the last reconciliation date per account

### Budget Sharing

Create multiple budgets for different purposes (personal, household, side business). Each budget supports collaborative access:

| Role | Access Level |
|------|-------------|
| Owner | Full control including budget deletion and data management |
| Admin | Manage accounts, transactions, and members (no deletion or data management) |
| Member | Create and update transactions, envelopes, and allocations |
| Viewer | Read-only access to all budget data |

Per-member permissions can be customized by adding or removing individual scopes from the role defaults.

### Notifications

Budge generates notifications to keep you informed:

| Type | Description |
|------|-------------|
| Low Balance | Envelope balance drops below a threshold |
| Upcoming Expense | A scheduled expense is coming soon |
| Recurring Not Funded | A recurring expense can't be fully covered by its envelope |
| Goal Reached | An envelope reaches its target balance |

Notification preferences are configurable per budget membership.

## Handling Different Expense Types

### Regular Recurring Expenses

For predictable recurring expenses (rent, insurance, subscriptions), create a recurring transaction linked to an envelope. The system will:
- Show you upcoming expenses from that envelope
- Calculate if you're on track based on envelope balance vs. upcoming amount
- Automatically allocate from the envelope when the transaction posts

### Irregular Large Expenses

For irregular but predictable expenses (annual insurance, property taxes):
1. Set a target balance on the envelope ($1,200 for annual car insurance)
2. Create an allocation rule to route money there (e.g., fixed $100/paycheck or 5% of income)
3. Optionally add a Period Cap rule to spread contributions evenly (e.g., $100/month)
4. Link the recurring transaction to this envelope

The envelope fills up over time. The recurring transaction link provides visibility: "Car insurance due in 90 days, envelope has $800, you're on track."

### Variable Spending Categories

For categories like groceries or entertainment:
1. Determine your per-spending-event budget ($150 per grocery trip)
2. Set that as your envelope target
3. Allocation rules refill it as income arrives

The target prevents over-accumulation. If your groceries envelope is full, money flows to the next allocation rule.

## Reports & Analytics

**Spending Analysis:**
- Spending by envelope with averages
- Top payees
- Location-based spending
- Spending trends over time

**Cash Flow:**
- Income vs. expenses by period
- Running totals

**Financial Position:**
- Net worth tracking (assets minus liabilities)
- Per-account breakdown
- Account balance history
- Envelope balance history
- Historical trends

**Runway:**
- Days of coverage per envelope
- Total runway across all spending
- Runway trends over time

**Goals:**
- Progress toward envelope targets
- Contribution rates
- Estimated time to goal

**Upcoming & Recurring:**
- Upcoming expenses with funding status
- Recurring expense coverage

**Allocation Analysis:**
- Rule effectiveness
- Times triggered and amounts allocated per rule
- Period Cap limit tracking

## Data Management

### Export & Import

Full JSON backup and restore of all budget data. Imports are atomic—if any part fails, no data is changed. Password confirmation is required before import. You can optionally clear existing data before importing.

### Start Fresh

Selectively delete categories of data without losing everything:

| Category | What's Deleted |
|----------|---------------|
| Transactions | All transactions and their allocations |
| Recurring | Recurring transaction templates |
| Envelopes | Envelopes, envelope groups, and allocation rules |
| Accounts | All accounts (cascades to their transactions) |
| Allocations | Allocations only; resets envelope balances |
| Payees | Payees not linked to transactions |
| Locations | All locations |
| All | Everything above |

A preview shows what will be affected before you confirm.

## Setup

### Prerequisites

- [Docker](https://www.docker.com/) and Docker Compose

### Development

```bash
git clone https://github.com/automationator/budge.git && cd budge
make fresh
```

- **Frontend:** http://localhost:5173
- **API:** http://localhost:8000
- **API docs:** http://localhost:8000/docs

Code changes auto-reload via volume mounts and hot reload on both the backend and frontend. If things get into a bad state, `make fresh` does a clean rebuild (removes volumes, rebuilds images, starts services, and runs migrations).

### Production

```bash
cp .env.prod.example .env.prod
# Edit .env.prod — at minimum set JWT_SECRET_KEY and POSTGRES_PASSWORD
make prod-up
```

The app will be available at `http://localhost:80` (or the `HTTP_PORT` configured in `.env.prod`). See `.env.prod.example` for all configurable options including CORS, worker count, and log level. For secure HTTPS access, I suggest using something along the lines of Tailscale or a Cloudflare tunnel.

Use `make prod-backup` to create database backups. Similarly, `make prod-restore` can restore a backup.

### Useful Commands

| Command | Description |
|---------|-------------|
| `make up` | Start all services |
| `make down` | Stop all services |
| `make logs` | View logs |
| `make fresh` | Clean rebuild everything |
| `make db-upgrade` | Apply database migrations |
| `make db-revision MESSAGE="..."` | Create a new migration |
| `make test` | Run backend tests |
| `make web-test` | Run frontend unit tests |
| `make web-test-e2e` | Run frontend E2E tests |
| `make lint` | Check code style |
| `make format` | Fix code style |

Run `make help` for the full list.

## Usage Guide

### Basic Workflow

1. **Set up accounts** — Add your checking, savings, credit cards, and other accounts
2. **Create envelopes** — Define categories for your money (rent, groceries, savings, etc.)
3. **Record transactions** — Log income and expenses as they happen
4. **Allocate income** — Distribute new money to envelopes (manually or via rules)

### Tips for Different Situations

**Irregular income (freelancers, gig workers, seasonal):**
- Income arrives when it arrives—allocate it when you have it
- Focus on envelope levels, not monthly amounts
- Prioritize essential envelopes (rent, utilities, food)
- Use Period Cap rules to prevent over-funding discretionary categories during high-income periods
- Build runway in essential envelopes for lean months

**Regular income (salaried employees):**
- Set up allocation rules to automate distribution
- Use targets to prevent over-accumulation
- Focus on building buffer in essential envelopes

**Paycheck to paycheck:**
- Prioritize essentials—lower-priority envelopes may stay underfunded
- Use Period Cap rules to enforce reality-based limits ("I can only afford $100/week for groceries")
- Excess flows to other necessities instead of over-funding one category
- The system shows reality without judgment

**Buffered:**
- Use targets to stop accumulating in full envelopes
- Let overflow route to savings and lower-priority goals
- Use Period Cap rules to spread large annual contributions evenly

### Paycheck to Paycheck vs. Buffered

Beyond income regularity, the experience differs based on how much financial cushion you have.

**Paycheck to paycheck:** Money comes in and goes out quickly. Envelopes rarely stay full for long.

**Buffered:** You have enough saved that you're spending money earned 30+ days ago. Envelopes stay comfortably full.

| Aspect | Paycheck to Paycheck | Buffered |
|--------|---------------------|----------|
| Envelope funding | Prioritization (not everything gets funded) | Distribution (everything gets funded) |
| Envelope targets | Rarely hit—money flows out first | Actively prevent over-accumulation |
| Period Cap rules | Enforce reality-based limits on necessities | Prevent lifestyle creep, enforce savings discipline |
| Overflow mechanism | Less relevant | Routes excess to lower priorities |
| System feel | Triage mode | Steady state |

Budge doesn't track buffer status as a separate metric. Your envelope balances are the indicator—if envelopes stay full between paychecks, you're buffered. Reports surface trends (envelope balances over time, days of runway) for those who want deeper insight.

## Philosophy

The central idea behind Budge is that you're **maintaining appropriate envelope levels for your spending patterns**, not allocating a monthly budget. The question isn't "how much should I budget for groceries this month?" but "do I have enough available for my next grocery trip?"

> "I need $150 available each time I go to the grocery store."

This framing works regardless of income pattern, pay schedule, or financial situation.

### Design Decisions

**Why no monthly cycles?**
Cash flow is continuous—income and expenses happen on their own schedules. A rolling model lets you budget when it makes sense for you, whether that's with each paycheck, once a week, or whenever you have time. It also works naturally with irregular income, where fitting variable paychecks into a monthly framework adds unnecessary friction.

**Why rolling envelopes?**
Envelope balances reflect real purchasing power at any moment. There's no need to think about rollovers, month-end reconciliation, or whether you're "on track" for a particular month. The envelope balance is the answer.

**Why zero-based principles without monthly scaffolding?**
Intentional allocation—assigning every dollar to an envelope—is a sound principle. Budge applies it the same way: income arrives, you assign it to envelopes (manually or via rules), and you spend from those envelopes. The only difference is that this happens continuously rather than in monthly batches.

### Principles

1. **Your choice of manual or automatic** — Both are equally valid approaches
2. **Envelope levels over monthly allocations** — "Do I have enough for my next expense?" is the right question
3. **Continuous cash flow** — Money arrives and leaves on its own schedule; Budge works the same way
4. **Budget on your own schedule** — No required rituals or calendar-driven workflows
5. **Flexibility** — Adjust envelopes, rules, and caps anytime

## License

Copyright (c) 2025-2026 Matthew Wilson. Licensed under [AGPL-3.0](LICENSE).
