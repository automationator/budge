from datetime import date
from uuid import uuid4

from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.accounts.models import Account, AccountType
from src.allocations.models import Allocation
from src.budgets.models import Budget
from src.envelopes.models import Envelope
from src.transactions.models import Transaction
from src.users.models import User


async def test_balance_check_no_issues(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,
) -> None:
    """Returns needs_repair=false when all balances are correct."""
    result = await session.execute(
        select(Budget).where(Budget.owner_id == test_user.id)
    )
    budget = result.scalars().first()

    response = await authenticated_client.get(
        f"/api/v1/budgets/{budget.id}/balance-check"
    )
    assert response.status_code == 200
    assert response.json()["needs_repair"] is False


async def test_balance_check_account_mismatch(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,
) -> None:
    """Returns needs_repair=true when an account balance is wrong."""
    result = await session.execute(
        select(Budget).where(Budget.owner_id == test_user.id)
    )
    budget = result.scalars().first()

    # Create an account with a deliberately wrong balance
    account = Account(
        budget_id=budget.id,
        name="Bad Balance Checking",
        account_type=AccountType.CHECKING,
        cleared_balance=99999,  # Wrong — no transactions to back this up
    )
    session.add(account)
    await session.flush()

    response = await authenticated_client.get(
        f"/api/v1/budgets/{budget.id}/balance-check"
    )
    assert response.status_code == 200
    assert response.json()["needs_repair"] is True


async def test_balance_check_envelope_mismatch(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,
) -> None:
    """Returns needs_repair=true when an envelope balance is wrong."""
    result = await session.execute(
        select(Budget).where(Budget.owner_id == test_user.id)
    )
    budget = result.scalars().first()

    # Create an envelope with a deliberately wrong balance
    envelope = Envelope(
        budget_id=budget.id,
        name="Bad Balance Envelope",
        current_balance=55555,  # Wrong — no allocations to back this up
    )
    session.add(envelope)
    await session.flush()

    response = await authenticated_client.get(
        f"/api/v1/budgets/{budget.id}/balance-check"
    )
    assert response.status_code == 200
    assert response.json()["needs_repair"] is True


async def test_balance_check_correct_after_matching(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,
) -> None:
    """Returns needs_repair=false when balances match their transactions/allocations."""
    result = await session.execute(
        select(Budget).where(Budget.owner_id == test_user.id)
    )
    budget = result.scalars().first()

    # Create account with correct balance matching its transaction
    account = Account(
        budget_id=budget.id,
        name="Correct Balance Checking",
        account_type=AccountType.CHECKING,
        cleared_balance=5000,
        uncleared_balance=0,
    )
    session.add(account)
    await session.flush()

    txn = Transaction(
        budget_id=budget.id,
        account_id=account.id,
        date=date(2024, 1, 15),
        amount=5000,
        is_cleared=True,
    )
    session.add(txn)
    await session.flush()

    # Create envelope with correct balance matching its allocation
    envelope = Envelope(
        budget_id=budget.id,
        name="Correct Balance Envelope",
        current_balance=5000,
    )
    session.add(envelope)
    await session.flush()

    allocation = Allocation(
        budget_id=budget.id,
        envelope_id=envelope.id,
        transaction_id=txn.id,
        amount=5000,
        date=date(2024, 1, 15),
        group_id=uuid4(),
    )
    session.add(allocation)
    await session.flush()

    response = await authenticated_client.get(
        f"/api/v1/budgets/{budget.id}/balance-check"
    )
    assert response.status_code == 200
    assert response.json()["needs_repair"] is False
