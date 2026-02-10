# Credit Card Accounts and Linked Envelopes

This document describes the technical implementation of credit card accounts and their automatically-managed linked envelopes.

## Overview

When a credit card account is created, the system automatically creates a corresponding "linked envelope" with the same name. This envelope tracks money set aside to pay off credit card spending. The linked envelope is managed automatically throughout the account's lifecycle.

## Data Model

### Account Model

**File:** `backend/src/accounts/models.py`

```python
class AccountType(str, Enum):
    CHECKING = "checking"
    SAVINGS = "savings"
    CREDIT_CARD = "credit_card"
    CASH = "cash"
    OTHER = "other"
```

The `account_type` field determines whether an account gets a linked envelope.

### Envelope Model

**File:** `backend/src/envelopes/models.py`

The envelope has a nullable `linked_account_id` foreign key:

```python
linked_account_id: Mapped[UUID | None] = mapped_column(
    ForeignKey("accounts.id", ondelete="CASCADE"),
    default=None,
)
```

Key constraints:
- `ondelete="CASCADE"` - Deleting the account automatically deletes the linked envelope
- Unique partial index ensures one envelope per account:

```python
Index(
    "ix_envelopes_linked_account",
    "linked_account_id",
    unique=True,
    postgresql_where=text("linked_account_id IS NOT NULL"),
)
```

## Lifecycle Management

### Account Creation

**File:** `backend/src/accounts/service.py` - `create_account()`

When `account_type == AccountType.CREDIT_CARD`:
1. Account is created and flushed to get its ID
2. `create_cc_envelope()` is called to create the linked envelope

```python
if account_in.account_type == AccountType.CREDIT_CARD:
    from src.envelopes.service import create_cc_envelope
    await create_cc_envelope(session, budget_id, account)
```

### Account Type Change

**File:** `backend/src/accounts/service.py` - `update_account()`

The function captures old state before applying updates, then handles type changes:

| Transition | Action |
|------------|--------|
| Non-CC → Credit Card | Create linked envelope via `create_cc_envelope()` |
| Credit Card → Non-CC | Delete linked envelope via `delete_cc_envelope()` |
| Credit Card → Credit Card (name change) | Sync envelope name via `update_cc_envelope_name()` |

```python
old_type = account.account_type
old_name = account.name

# ... apply updates ...

if old_type != new_type:
    if new_type == AccountType.CREDIT_CARD:
        await create_cc_envelope(session, budget_id, account)
    elif old_type == AccountType.CREDIT_CARD:
        await delete_cc_envelope(session, budget_id, account.id)
elif account.account_type == AccountType.CREDIT_CARD and account.name != old_name:
    await update_cc_envelope_name(session, budget_id, account.id, account.name)
```

### Account Deletion

Handled automatically by the database via `ondelete="CASCADE"` on the foreign key. No application code needed.

## Key Functions

### Envelope Service Functions

**File:** `backend/src/envelopes/service.py`

| Function | Purpose |
|----------|---------|
| `create_cc_envelope(session, budget_id, account)` | Creates linked envelope with same name as account |
| `get_cc_envelope_by_account_id(session, budget_id, account_id)` | Retrieves linked envelope by account ID |
| `delete_cc_envelope(session, budget_id, account_id)` | Deletes linked envelope (bypasses normal CC deletion protection) |
| `update_cc_envelope_name(session, budget_id, account_id, new_name)` | Syncs envelope name with account name |

### Deletion Protection

**File:** `backend/src/envelopes/service.py` - `delete_envelope()`

Users cannot directly delete a credit card envelope:

```python
if envelope.linked_account_id is not None:
    raise CannotDeleteCCEnvelopeError()
```

The error message directs users to delete the account instead:

```python
class CannotDeleteCCEnvelopeError(BadRequestError):
    def __init__(self):
        super().__init__(
            detail="Cannot delete a credit card envelope. Delete the credit card account instead."
        )
```

## Error Handling

### Name Conflicts

Both `create_cc_envelope()` and `update_cc_envelope_name()` handle duplicate name errors:

```python
except IntegrityError as e:
    await session.rollback()
    if "uq_budget_envelope_name" in str(e):
        raise DuplicateEnvelopeNameError(name) from e
    raise
```

This returns HTTP 409 Conflict to the client.

### Scenarios

| Operation | Conflict | Result |
|-----------|----------|--------|
| Change checking → credit card | Envelope "My Card" exists | 409 error, account type unchanged |
| Rename CC account to "Groceries" | Envelope "Groceries" exists | 409 error, name unchanged |

## Balance Handling

When a credit card envelope is deleted (due to account type change), its balance becomes unallocated. This happens automatically because the unallocated balance is calculated dynamically:

**File:** `backend/src/envelopes/service.py` - `calculate_unallocated_balance()`

```python
unallocated = sum(budget_account_balances) - sum(envelope_balances)
```

No explicit balance transfer is needed.

## Tests

**File:** `backend/tests/accounts/test_accounts.py`

| Test | Verifies |
|------|----------|
| `test_create_credit_card_account_creates_linked_envelope` | Envelope auto-created on CC account creation |
| `test_create_non_credit_card_account_does_not_create_envelope` | No envelope for non-CC accounts |
| `test_delete_credit_card_account_deletes_linked_envelope` | Cascade delete works |
| `test_change_account_type_to_credit_card_creates_envelope` | Type change creates envelope |
| `test_change_account_type_from_credit_card_deletes_envelope` | Type change deletes envelope |
| `test_rename_credit_card_account_renames_envelope` | Name sync works |
| `test_change_to_credit_card_fails_if_envelope_name_exists` | Name conflict handled |
| `test_rename_credit_card_fails_if_envelope_name_exists` | Rename conflict handled |

## File Summary

| File | Role |
|------|------|
| `backend/src/accounts/models.py` | Account model with `AccountType` enum |
| `backend/src/accounts/service.py` | Account CRUD with CC envelope lifecycle |
| `backend/src/envelopes/models.py` | Envelope model with `linked_account_id` FK |
| `backend/src/envelopes/service.py` | Envelope CRUD and CC envelope helpers |
| `backend/src/envelopes/exceptions.py` | `CannotDeleteCCEnvelopeError` |
