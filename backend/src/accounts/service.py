from uuid import UUID

from sqlalchemy import case, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.accounts.exceptions import AccountNotFoundError, DuplicateAccountNameError
from src.accounts.models import Account, AccountType
from src.accounts.schemas import AccountCreate, AccountUpdate
from src.allocations.service import reverse_allocations_for_transaction
from src.transactions.models import Transaction, TransactionStatus


async def list_accounts(session: AsyncSession, budget_id: UUID) -> list[Account]:
    """List all accounts for a budget, ordered by sort_order then name."""
    result = await session.execute(
        select(Account)
        .where(Account.budget_id == budget_id)
        .order_by(Account.sort_order, Account.name)
    )
    return list(result.scalars().all())


async def get_account_by_id(
    session: AsyncSession, budget_id: UUID, account_id: UUID
) -> Account:
    """Get an account by ID, ensuring it belongs to the specified budget."""
    result = await session.execute(
        select(Account).where(Account.id == account_id, Account.budget_id == budget_id)
    )
    account = result.scalar_one_or_none()
    if not account:
        raise AccountNotFoundError(account_id)
    return account


async def create_account(
    session: AsyncSession, budget_id: UUID, account_in: AccountCreate
) -> Account:
    """Create a new account for a budget.

    For credit card accounts, automatically creates a linked envelope
    with the same name to track money set aside for CC payments.
    """
    account = Account(
        budget_id=budget_id,
        name=account_in.name,
        account_type=account_in.account_type,
        icon=account_in.icon,
        description=account_in.description,
        sort_order=account_in.sort_order,
        include_in_budget=account_in.include_in_budget,
        is_active=account_in.is_active,
    )
    session.add(account)
    try:
        await session.flush()
    except IntegrityError as e:
        await session.rollback()
        if "uq_budget_account_name" in str(e):
            raise DuplicateAccountNameError(account_in.name) from e
        raise

    # Auto-create linked envelope for credit card accounts
    if account_in.account_type == AccountType.CREDIT_CARD:
        from src.envelopes.service import create_cc_envelope

        await create_cc_envelope(session, budget_id, account)

    return account


async def update_account(
    session: AsyncSession, budget_id: UUID, account_id: UUID, account_in: AccountUpdate
) -> Account:
    """Update an existing account.

    Handles special cases:
    - Type change to credit_card: Creates linked envelope
    - Type change from credit_card: Deletes linked envelope
    - Name change on credit_card: Updates linked envelope name
    """
    account = await get_account_by_id(session, budget_id, account_id)

    # Capture state before updates
    old_type = account.account_type
    old_name = account.name

    update_data = account_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(account, field, value)

    try:
        await session.flush()
    except IntegrityError as e:
        await session.rollback()
        if "uq_budget_account_name" in str(e):
            raise DuplicateAccountNameError(account_in.name or account.name) from e
        raise

    # Handle account type changes
    new_type = account.account_type
    if old_type != new_type:
        if new_type == AccountType.CREDIT_CARD:
            # Changed TO credit card - create linked envelope
            from src.envelopes.service import create_cc_envelope

            await create_cc_envelope(session, budget_id, account)
        elif old_type == AccountType.CREDIT_CARD:
            # Changed FROM credit card - delete linked envelope
            from src.envelopes.service import delete_cc_envelope

            await delete_cc_envelope(session, budget_id, account.id)
    elif account.account_type == AccountType.CREDIT_CARD and account.name != old_name:
        # Credit card renamed - sync envelope name
        from src.envelopes.service import update_cc_envelope_name

        await update_cc_envelope_name(session, budget_id, account.id, account.name)

    return account


async def delete_account(
    session: AsyncSession, budget_id: UUID, account_id: UUID
) -> None:
    """Delete an account.

    Before deletion, reverses all envelope balances from transactions in this account.
    The database cascade will handle deleting the transactions and allocations.
    """
    account = await get_account_by_id(session, budget_id, account_id)

    # Get all transactions for this account to reverse their envelope allocations
    result = await session.execute(
        select(Transaction).where(
            Transaction.budget_id == budget_id,
            Transaction.account_id == account_id,
        )
    )
    transactions = result.scalars().all()

    # Reverse envelope balances for each transaction
    for transaction in transactions:
        await reverse_allocations_for_transaction(session, budget_id, transaction.id)

    await session.delete(account)
    await session.flush()


async def recalculate_account_balances(
    session: AsyncSession,
    budget_id: UUID,
) -> list[dict]:
    """Recalculate and fix account balances from POSTED transactions.

    Returns list of accounts that were corrected with before/after values.
    """
    # Get all accounts for budget
    accounts = await list_accounts(session, budget_id)
    corrections = []

    for account in accounts:
        # Calculate correct balances from POSTED transactions
        result = await session.execute(
            select(
                func.coalesce(
                    func.sum(
                        case(
                            (Transaction.is_cleared == True, Transaction.amount),  # noqa: E712
                            else_=0,
                        )
                    ),
                    0,
                ).label("cleared"),
                func.coalesce(
                    func.sum(
                        case(
                            (Transaction.is_cleared == False, Transaction.amount),  # noqa: E712
                            else_=0,
                        )
                    ),
                    0,
                ).label("uncleared"),
            ).where(
                Transaction.budget_id == budget_id,
                Transaction.account_id == account.id,
                Transaction.status == TransactionStatus.POSTED,
            )
        )
        row = result.one()
        correct_cleared = row.cleared
        correct_uncleared = row.uncleared

        # Check if correction needed
        if (
            account.cleared_balance != correct_cleared
            or account.uncleared_balance != correct_uncleared
        ):
            corrections.append(
                {
                    "account_id": account.id,
                    "account_name": account.name,
                    "old_cleared": account.cleared_balance,
                    "old_uncleared": account.uncleared_balance,
                    "new_cleared": correct_cleared,
                    "new_uncleared": correct_uncleared,
                }
            )

            # Apply correction
            account.cleared_balance = correct_cleared
            account.uncleared_balance = correct_uncleared

    await session.flush()
    return corrections
