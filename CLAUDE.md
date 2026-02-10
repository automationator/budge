# Budge

A personal finance envelope budgeting application with budget-based authorization built with FastAPI.

## Requirements

This document must be kept up to date as the project evolves.

## Quick Reference

```bash
make up            # Start all services
make down          # Stop all services
make db-upgrade    # Apply migrations
make test          # Run tests
make lint          # Check code style
make format        # Fix code style
make logs          # View logs
make fresh         # Clean rebuild everything
```

## Tech Stack

- **Python 3.14** with uv for package management
- **FastAPI** for the web framework
- **SQLAlchemy 2.0** with async support (asyncpg)
- **PostgreSQL 18** for the database
- **Alembic** for migrations
- **Pydantic v2** for validation and settings
- **pytest** with pytest-asyncio for testing
- **Docker Compose** for local development

## Project Structure

```
budge/
├── backend/                 # Python FastAPI backend
│   ├── src/                 # Application source code
│   │   ├── main.py          # FastAPI app, routers, middleware
│   │   ├── config.py        # Pydantic settings (env vars)
│   │   ├── database.py      # SQLAlchemy engine, Base class, session
│   │   ├── exceptions.py    # Global HTTP exception classes
│   │   ├── models.py        # Aggregates all models for Alembic
│   │   ├── pagination.py    # Keyset pagination utilities
│   │   ├── accounts/        # Bank/credit card accounts
│   │   ├── admin/           # Admin endpoints
│   │   ├── allocation_rules/ # Automatic allocation rules
│   │   ├── allocations/     # Envelope allocations
│   │   ├── auth/            # Authentication module
│   │   ├── budgets/         # Budgets, members, roles, scopes
│   │   ├── data_transfer/   # Export, import, repair
│   │   ├── envelope_groups/ # Envelope grouping
│   │   ├── envelopes/       # Budget envelopes
│   │   ├── locations/       # Transaction locations
│   │   ├── notifications/   # User notifications
│   │   ├── payees/          # Transaction payees
│   │   ├── public/          # Public endpoints
│   │   ├── recurring_transactions/ # Recurring transactions
│   │   ├── reports/         # Budget reports
│   │   ├── start_fresh/     # Reset budget data
│   │   ├── sync/            # Data sync
│   │   ├── testing/         # E2E test factories (ENV=e2e only)
│   │   ├── transactions/    # Financial transactions
│   │   └── users/           # User management
│   ├── tests/               # Backend pytest tests
│   ├── alembic/             # Database migrations
│   ├── pyproject.toml       # Python dependencies
│   └── alembic.ini          # Alembic config
├── frontend/                # Vue 3 + TypeScript frontend
│   ├── src/                 # Application source code
│   │   ├── api/             # HTTP API clients
│   │   ├── assets/          # Static assets
│   │   ├── components/      # Reusable components
│   │   ├── composables/     # Vue composables
│   │   ├── router/          # Vue Router config
│   │   ├── stores/          # Pinia state management
│   │   ├── types/           # TypeScript types
│   │   ├── utils/           # Utility functions
│   │   └── views/           # Page components
│   ├── tests/               # Frontend tests
│   │   ├── unit/            # Vitest unit tests
│   │   ├── e2e/             # Playwright E2E tests
│   │   └── component/       # Component tests
│   ├── package.json         # Node dependencies
│   └── vitest.config.ts     # Vitest config
├── Makefile                 # Build/dev commands
├── docker-compose.yml       # Docker services
└── Dockerfile               # API Docker image
```

## Module Conventions

Each domain module (auth, users, budgets, etc.) follows this pattern:

| File | Purpose |
|------|---------|
| `models.py` | SQLAlchemy ORM models |
| `schemas.py` | Pydantic request/response models |
| `service.py` | Business logic (no HTTP concerns) |
| `router.py` | FastAPI routes (thin, delegates to service) |
| `exceptions.py` | Domain-specific HTTP exceptions |
| `dependencies.py` | FastAPI dependencies (if needed) |

## Key Patterns

### Base Model

All models inherit from `Base` (in `database.py`) which provides:
- `id`: UUID7 primary key (time-sortable, contains timestamp)
- `updated_at`: Auto-updated on changes
- `created_at`: Property extracted from UUID7 timestamp

### Exception Hierarchy

```python
# backend/src/exceptions.py - inherit from these
NotFoundError    # 404
BadRequestError  # 400
UnauthorizedError # 401
ForbiddenError   # 403
ConflictError    # 409

# Domain exceptions extend these:
class UserNotFoundError(NotFoundError):
    def __init__(self, user_id: UUID | None = None):
        detail = f"User {user_id} not found" if user_id else "User not found"
        super().__init__(detail=detail)
```

### Authentication

JWT-based with access + refresh tokens:
- Access token: 30 min expiry, used in `Authorization: Bearer <token>`
- Refresh token: 7 day expiry, stored in DB, can be revoked
- Use `get_current_active_user` dependency for protected routes

### Budget Authorization

Role-based with scope overrides per budget membership:

```python
# Roles: owner > admin > member > viewer
# Scopes fetched from DB per request (not in JWT)

@router.get("/{budget_id}/members")
async def list_members(
    ctx: Annotated[BudgetContext, Security(BudgetSecurity(), scopes=["members:read"])],
):
    # ctx.budget, ctx.membership, ctx.user, ctx.effective_scopes available
```

**Scopes (48 total across 13 resource groups):**

| Group | Scopes |
|-------|--------|
| budget | `budget:read`, `budget:update`, `budget:delete` |
| members | `members:read`, `members:add`, `members:remove`, `members:manage_roles` |
| accounts | `accounts:create`, `accounts:read`, `accounts:update`, `accounts:delete` |
| payees | `payees:create`, `payees:read`, `payees:update`, `payees:delete` |
| locations | `locations:create`, `locations:read`, `locations:update`, `locations:delete` |
| transactions | `transactions:create`, `transactions:read`, `transactions:update`, `transactions:delete` |
| recurring | `recurring:create`, `recurring:read`, `recurring:update`, `recurring:delete` |
| envelopes | `envelopes:create`, `envelopes:read`, `envelopes:update`, `envelopes:delete` |
| envelope_groups | `envelope_groups:create`, `envelope_groups:read`, `envelope_groups:update`, `envelope_groups:delete` |
| allocations | `allocations:create`, `allocations:read`, `allocations:update`, `allocations:delete` |
| allocation_rules | `allocation_rules:create`, `allocation_rules:read`, `allocation_rules:update`, `allocation_rules:delete` |
| notifications | `notifications:read`, `notifications:update` |
| data | `data:export`, `data:import`, `data:repair` |

**Role defaults:**

| Role | Description |
|------|-------------|
| owner | All 48 scopes |
| admin | All except `budget:delete`, `accounts:delete`, `locations:delete`, `payees:delete`, `recurring:delete`, `transactions:delete`, `members:manage_roles`, `data:*` (38 scopes) |
| member | Read on most resources + create/update on transactions, allocations, envelopes, envelope_groups, recurring, allocation_rules, notifications (24 scopes) |
| viewer | Read-only on all resources (11 scopes) |

Scope overrides stored in `BudgetMembership.scope_additions` / `scope_removals`.

### API Endpoint Structure

All resources in the application (except users and auth) are owned by a budget. This means:

- **Budget-owned resources** are nested under `/api/v1/budgets/{budget_id}/`
- **User resources** use `/api/v1/users/me` (not budget-scoped)

**URL patterns:**

| Resource | Endpoint Pattern |
|----------|------------------|
| Auth | `/api/v1/auth` |
| Users | `/api/v1/users/me` |
| Admin | `/api/v1/admin` |
| Public | `/api/v1/public` |
| Budgets | `/api/v1/budgets`, `/api/v1/budgets/{budget_id}` |
| Budget Members | `/api/v1/budgets/{budget_id}/members` |
| Accounts | `/api/v1/budgets/{budget_id}/accounts` |
| Transactions | `/api/v1/budgets/{budget_id}/transactions` |
| Envelopes | `/api/v1/budgets/{budget_id}/envelopes` |
| Envelope Groups | `/api/v1/budgets/{budget_id}/envelope-groups` |
| Allocations | `/api/v1/budgets/{budget_id}/allocations` |
| Allocation Rules | `/api/v1/budgets/{budget_id}/allocation-rules` |
| Payees | `/api/v1/budgets/{budget_id}/payees` |
| Locations | `/api/v1/budgets/{budget_id}/locations` |
| Recurring Txns | `/api/v1/budgets/{budget_id}/recurring-transactions` |
| Reports | `/api/v1/budgets/{budget_id}/reports` |
| Notifications | `/api/v1/budgets/{budget_id}/notifications` |
| Start Fresh | `/api/v1/budgets/{budget_id}/start-fresh` |
| Data Transfer | `/api/v1/budgets/{budget_id}/export`, `.../import`, `.../repair` |

When adding new domain resources:
1. Model must have a `budget_id` foreign key
2. Router mounted under budgets: `/api/v1/budgets/{budget_id}/<resource>`
3. Use `BudgetSecurity` dependency to verify budget access and scopes

### Keyset Pagination

Large collections use keyset (cursor-based) pagination for O(1) performance regardless of table size. Shared utilities are in `backend/src/pagination.py`.

**Response Format:**

```json
{
    "items": [...],
    "next_cursor": "eyJkYXRlIjogIjIwMjQtMDEtMTUiLCAiaWQiOiAiLi4uIn0=",
    "has_more": true
}
```

**Query Parameters:**

| Param | Default | Description |
|-------|---------|-------------|
| `limit` | 50 | Items per page (1-100) |
| `cursor` | null | Opaque cursor from previous response |

**Adding Pagination to a New Resource:**

1. **Model**: Add composite index for keyset ordering
   ```python
   __table_args__ = (
       Index("ix_<table>_budget_date_id", "budget_id", "date", "id"),
   )
   ```

2. **Service**: Use `tuple_()` for keyset WHERE clause
   ```python
   from sqlalchemy import tuple_

   if cursor_date and cursor_id:
       query = query.where(
           tuple_(Model.date, Model.id) < tuple_(cursor_date, cursor_id)
       )
   query = query.order_by(Model.date.desc(), Model.id.desc()).limit(limit + 1)
   ```

3. **Router**: Use shared `CursorPage[T]` response type
   ```python
   from src.pagination import CursorPage, decode_cursor, encode_cursor

   @router.get("", response_model=CursorPage[ItemResponse])
   async def list_items(..., cursor: str | None = None) -> CursorPage[ItemResponse]:
       decoded = decode_cursor(cursor) if cursor else None
       # ... fetch items ...
       return CursorPage(items=items, next_cursor=next_cursor, has_more=has_more)
   ```

4. **Migration**: Create index via Alembic

## Database

### Running Migrations

```bash
make db-upgrade                        # Apply all migrations
make db-downgrade                      # Rollback one migration
make db-revision MESSAGE="description" # Create new migration
```

### Session Management

The `get_async_session` dependency auto-commits on success, rolls back on exception:

```python
async def create_something(
    session: Annotated[AsyncSession, Depends(get_async_session)],
):
    # Use session.add(), session.flush()
    # Commit happens automatically after request
```

Use `session.flush()` to get IDs before commit.

## Testing

### Backend Tests

Backend tests use a session-scoped transaction that rolls back after all tests:

```bash
make test                                                    # Run all backend tests
make test-file FILE=tests/budgets/test_budget_security.py    # Run specific test file
```

**Backend Test Fixtures:**
- `session` - Function-scoped DB session (rolls back after each test)
- `client` - HTTP client without auth
- `authenticated_client` - HTTP client with valid token for `test_user`
- `test_user` / `test_user2` - Pre-created test users

```python
async def test_something(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,
) -> None:
    response = await authenticated_client.get("/api/v1/users/me")
    assert response.status_code == 200
```

### Frontend Tests

```bash
make web-test      # Run frontend unit tests (Vitest)
make web-test-e2e  # Run frontend E2E tests (Playwright, 5 workers)
```

### E2E Testing Infrastructure

E2E tests use **schema-per-worker isolation** for reliable parallel execution. Each Playwright worker gets its own PostgreSQL schema, preventing data conflicts between workers.

#### Architecture Overview

```
┌──────────────────────────────────────────────────────────────────────────────────────┐
│  Playwright (5 workers)                                                              │
│  ┌───────────┐ ┌───────────┐ ┌───────────┐ ┌───────────┐ ┌───────────┐              │
│  │ Worker 0  │ │ Worker 1  │ │ Worker 2  │ │ Worker 3  │ │ Worker 4  │              │
│  │ e2e_w0    │ │ e2e_w1    │ │ e2e_w2    │ │ e2e_w3    │ │ e2e_w4    │              │
│  └─────┬─────┘ └─────┬─────┘ └─────┬─────┘ └─────┬─────┘ └─────┬─────┘              │
│        │              │              │              │              │                  │
│        └──────────────┴──────────────┼──────────────┴──────────────┘                  │
│                                      │ X-E2E-Schema header                           │
└──────────────────────────────────────┼───────────────────────────────────────────────┘
                                       ▼
┌──────────────────────────────────────────────────────────────────────────────────────┐
│  Backend API (ENV=e2e)                                                               │
│  ┌──────────────────────────────────────────────────────────────────────────────────┐│
│  │  E2ESchemaMiddleware                                                             ││
│  │  - Reads X-E2E-Schema header                                                    ││
│  │  - Sets search_path via ContextVar                                               ││
│  └──────────────────────────────────────────────────────────────────────────────────┘│
│  ┌──────────────────────────────────────────────────────────────────────────────────┐│
│  │  Test Endpoints (/test/*)                                                        ││
│  │  - POST /test/reset - Reset schema, run migrations                               ││
│  │  - POST /test/factory/user - Create test user                                    ││
│  │  - POST /test/factory/account - Create test account                              ││
│  │  - POST /test/factory/envelope - Create test envelope                            ││
│  │  - POST /test/factory/envelope-group - Create test envelope group                ││
│  │  - POST /test/factory/payee - Create test payee                                  ││
│  │  - POST /test/factory/transaction - Create test transaction                      ││
│  │  - POST /test/factory/reconcile - Reconcile account                              ││
│  │  - POST /test/factory/budget - Create new budget                                 ││
│  │  - POST /test/factory/location - Create test location                            ││
│  │  - POST /test/factory/allocation-rule - Create test allocation rule              ││
│  │  - POST /test/factory/set-registration - Enable/disable registration             ││
│  └──────────────────────────────────────────────────────────────────────────────────┘│
└──────────────────────────────────────────────────────────────────────────────────────┘
                                       │
                                       ▼
┌──────────────────────────────────────────────────────────────────────────────────────┐
│  PostgreSQL                                                                          │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐           │
│  │ public  │ │ e2e_w0  │ │ e2e_w1  │ │ e2e_w2  │ │ e2e_w3  │ │ e2e_w4  │           │
│  │ (dev)   │ │(worker0)│ │(worker1)│ │(worker2)│ │(worker3)│ │(worker4)│           │
│  └─────────┘ └─────────┘ └─────────┘ └─────────┘ └─────────┘ └─────────┘           │
└──────────────────────────────────────────────────────────────────────────────────────┘
```

#### Key Components

**Backend (`ENV=e2e` mode):**
- `backend/src/testing/` - Test module with factory endpoints
- `backend/src/database.py` - `e2e_schema_context` ContextVar for per-request schema
- `backend/src/main.py` - `E2ESchemaMiddleware` reads `X-E2E-Schema` header

**Frontend:**
- `frontend/tests/e2e/fixtures/test-api.ts` - `TestApi` class for calling factory endpoints
- `frontend/tests/e2e/fixtures/test-setup.ts` - Playwright fixtures (`testApi`, `testContext`, `authenticatedPage`)

#### E2E Test Fixtures

| Fixture | Description |
|---------|-------------|
| `testApi` | `TestApi` instance for the current worker's schema |
| `testContext` | Contains `user` (with tokens), `schemaName`, `workerId` |
| `authenticatedPage` | Playwright page with auth tokens in localStorage and `X-E2E-Schema` header |
| `authenticatedContext` | Browser context with auth tokens and schema header |

#### Writing E2E Tests

```typescript
import { test, expect } from '../fixtures/test-setup'
import { AccountsPage } from '../pages/accounts.page'

test('creates an account', async ({ authenticatedPage, testApi, testContext }) => {
  // testContext.user has: accessToken, refreshToken, budgetId, userId
  // testApi can create data via factory endpoints
  // authenticatedPage is already logged in with correct schema header

  const accountsPage = new AccountsPage(authenticatedPage)
  await accountsPage.goto()
  await accountsPage.createAccount({
    name: 'Test Checking',
    accountType: 'checking',
  })
  await accountsPage.snackbar.expectMessage('Account created')
})
```

#### Creating Test Data via API

For tests that need pre-existing data (e.g., recurring transactions need payees to exist):

```typescript
test('creates recurring expense', async ({ authenticatedPage, testApi, testContext }) => {
  // Create a payee via API first (recurring form uses v-select, not autocomplete)
  const payeeName = `Test Payee ${Date.now()}`
  await testApi.createPayee(testContext.user.budgetId, payeeName)

  // Now the payee will appear in the dropdown
  const recurringPage = new RecurringPage(authenticatedPage)
  await recurringPage.goto()
  await recurringPage.selectPayee(payeeName)
  // ...
})
```

#### How Schema Isolation Works

1. **Test startup**: Each spec file calls `testApi.reset()` which creates/resets the worker's schema (e.g., `e2e_w0`)
2. **Browser requests**: The `authenticatedPage` fixture adds `X-E2E-Schema: e2e_w0` header to all requests
3. **API middleware**: `E2ESchemaMiddleware` reads the header and sets `e2e_schema_context`
4. **Database session**: `get_async_session()` sets `search_path` based on the context
5. **Complete isolation**: Each worker's data is completely separate

#### Running E2E Tests

```bash
# Run all E2E tests (5 parallel workers)
make web-test-e2e

# Run specific test file
cd frontend && npx playwright test tests/e2e/tests/accounts.spec.ts

# Run with UI mode for debugging
cd frontend && npx playwright test --ui

# Run single worker (useful for debugging)
cd frontend && npx playwright test --workers=1
```

**Playwright projects:** `auth-chromium` (serial auth tests), `chromium` (main), `mobile` (430x715 viewport, `*.mobile.spec.ts` files). Firefox and WebKit projects run in CI only.

#### E2E Test Best Practices

**Never use `waitForTimeout`** - Use proper Playwright waiting mechanisms instead:

| Instead of | Use |
|------------|-----|
| `page.waitForTimeout(500)` | `expect(element).toBeVisible()` |
| Waiting for element to appear | `expect(element).toBeVisible({ timeout: 5000 })` |
| Waiting for element to disappear | `expect(element).toBeHidden({ timeout: 5000 })` |
| Waiting for text to appear | `expect(element).toHaveText('expected text')` |
| Waiting for value to be set | `expect(element).toHaveValue('expected value')` |

**Add helper methods to page objects** for common async operations:

```typescript
// In page object
async waitForEnvelopeAutoFill(expectedEnvelope: string, timeout = 5000): Promise<void> {
  await expect(
    this.envelopeSelect.locator('.v-select__selection-text')
  ).toHaveText(expectedEnvelope, { timeout })
}

async waitForFormHidden() {
  await expect(this.formCard).toBeHidden({ timeout: 5000 })
}

// In test
await formPage.selectPayee(payee.name)
await formPage.waitForEnvelopeAutoFill(envelope.name)  // Polls until envelope appears
```

For cases where you're verifying something does NOT happen (e.g., auto-fill is disabled), no wait is needed - check immediately after the action.

## Code Style

- **Formatter/Linter:** Ruff with 88 char line length
- **Imports:** Always at top of file, never inside functions. The only exception is to avoid circular imports (use `TYPE_CHECKING` blocks when possible). Sorted by ruff (stdlib, third-party, first-party)
- **Type hints:** Required on all function signatures
- **Async:** All DB operations and route handlers are async

Run before committing:
```bash
make format  # Fix style issues
make lint    # Check for issues
```
