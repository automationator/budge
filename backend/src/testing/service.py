import re
from datetime import date
from uuid import UUID

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from src.accounts.models import Account
from src.allocation_rules.models import AllocationRule
from src.allocations.models import Allocation
from src.auth.service import create_access_token, create_refresh_token
from src.budgets.models import Budget, BudgetMembership, BudgetRole
from src.envelope_groups.models import EnvelopeGroup
from src.envelopes.models import Envelope
from src.envelopes.service import ensure_unallocated_envelope
from src.locations.models import Location
from src.payees.models import Payee
from src.transactions.models import Transaction, TransactionStatus, TransactionType
from src.users.models import User
from src.users.service import hash_password


def validate_worker_id(worker_id: str) -> str:
    """Validate and return schema name for worker."""
    if not re.match(r"^w\d+$", worker_id):
        raise ValueError(f"Invalid worker_id format: {worker_id}")
    return f"e2e_{worker_id}"


async def reset_schema(session: AsyncSession, worker_id: str) -> str:
    """Reset the schema for a worker.

    Drops and recreates the schema, then creates all tables.
    Returns the schema name.
    """
    schema_name = validate_worker_id(worker_id)

    # Drop and recreate schema
    await session.execute(text(f"DROP SCHEMA IF EXISTS {schema_name} CASCADE"))
    await session.execute(text(f"CREATE SCHEMA {schema_name}"))
    await session.commit()

    # Create all tables in this schema
    await create_tables_for_schema(session, schema_name)

    return schema_name


async def create_tables_for_schema(session: AsyncSession, schema_name: str) -> None:
    """Create all tables in the specified schema using SQLAlchemy metadata."""
    from src.admin.models import SystemSettingsBase
    from src.models import Base  # Triggers all model imports

    conn = await session.connection()
    await conn.execute(text(f"SET search_path TO {schema_name}"))

    # Create all domain tables
    await conn.run_sync(Base.metadata.create_all)

    # Create system_settings (uses separate DeclarativeBase)
    await conn.run_sync(SystemSettingsBase.metadata.create_all)

    # Seed default system_settings row
    await conn.execute(
        text("INSERT INTO system_settings (id, registration_enabled) VALUES (1, true)")
    )
    await session.commit()


async def set_search_path(session: AsyncSession, schema_name: str) -> None:
    """Set the search_path for the current session."""
    await session.execute(text(f"SET search_path TO {schema_name}, public"))


async def create_test_user(
    session: AsyncSession,
    schema_name: str,
    username: str,
    password: str,
    is_admin: bool | None = None,
) -> dict:
    """Create a user with budget and return auth tokens.

    This is a low-level factory that directly creates records in the specified schema.
    When is_admin is None (default), the first user in the schema will be made an admin.
    When is_admin is explicitly set, that value is used.
    """
    await set_search_path(session, schema_name)

    # Determine admin status
    if is_admin is None:
        # Auto-detect: first user is admin
        result = await session.execute(select(func.count(User.id)))
        count = result.scalar()
        is_admin = count == 0

    # Create user
    user = User(
        username=username,
        hashed_password=hash_password(password),
        is_admin=is_admin,
    )
    session.add(user)
    await session.flush()

    # Create budget
    budget = Budget(name=f"{username}'s Budget", owner_id=user.id)
    session.add(budget)
    await session.flush()

    # Create budget membership
    membership = BudgetMembership(
        user_id=user.id, budget_id=budget.id, role=BudgetRole.OWNER
    )
    session.add(membership)
    await session.flush()

    # Create tokens
    access_token = create_access_token(user.id)
    refresh_token = await create_refresh_token(session, user.id)

    await session.commit()

    return {
        "user_id": user.id,
        "budget_id": budget.id,
        "access_token": access_token,
        "refresh_token": refresh_token,
    }


async def create_test_budget(
    session: AsyncSession,
    schema_name: str,
    user_id: UUID,
    name: str,
) -> Budget:
    """Create a new budget for an existing user.

    The user becomes the owner of the budget.
    """
    await set_search_path(session, schema_name)

    # Create budget
    budget = Budget(name=name, owner_id=user_id)
    session.add(budget)
    await session.flush()

    # Create budget membership
    membership = BudgetMembership(
        user_id=user_id, budget_id=budget.id, role=BudgetRole.OWNER
    )
    session.add(membership)
    await session.flush()
    await session.commit()

    return budget


async def create_test_account(
    session: AsyncSession,
    schema_name: str,
    budget_id: UUID,
    name: str,
    account_type: str = "checking",
    include_in_budget: bool = True,
    starting_balance: int = 0,
) -> Account:
    """Create an account with optional starting balance."""
    await set_search_path(session, schema_name)

    account = Account(
        budget_id=budget_id,
        name=name,
        account_type=account_type,
        include_in_budget=include_in_budget,
    )
    session.add(account)
    await session.flush()

    # If starting balance, create an adjustment transaction
    if starting_balance != 0:
        transaction = Transaction(
            budget_id=budget_id,
            account_id=account.id,
            date=date.today(),
            amount=starting_balance,
            is_cleared=True,
            memo="Starting balance",
            transaction_type=TransactionType.ADJUSTMENT,
            status=TransactionStatus.POSTED,
        )
        session.add(transaction)
        # Adjustments are always cleared
        account.cleared_balance = starting_balance
        await session.flush()

    await session.commit()
    return account


async def create_test_envelope(
    session: AsyncSession,
    schema_name: str,
    budget_id: UUID,
    name: str,
    group_name: str | None = None,
    target_balance: int | None = None,
    is_starred: bool = False,
) -> Envelope:
    """Create an envelope, or return existing one with same name."""
    await set_search_path(session, schema_name)

    # Ensure the unallocated envelope exists
    await ensure_unallocated_envelope(session, budget_id)

    envelope_group_id = None

    # Create or get envelope group if specified
    if group_name:
        # Check if group already exists
        result = await session.execute(
            select(EnvelopeGroup).where(
                EnvelopeGroup.budget_id == budget_id,
                EnvelopeGroup.name == group_name,
            )
        )
        group = result.scalar_one_or_none()

        if not group:
            # Get max sort_order for groups in this budget
            max_order_result = await session.execute(
                select(func.coalesce(func.max(EnvelopeGroup.sort_order), 0)).where(
                    EnvelopeGroup.budget_id == budget_id
                )
            )
            max_order = max_order_result.scalar_one()

            group = EnvelopeGroup(
                budget_id=budget_id,
                name=group_name,
                sort_order=max_order + 10,
            )
            session.add(group)
            await session.flush()

        envelope_group_id = group.id

    # Check if envelope already exists
    result = await session.execute(
        select(Envelope).where(
            Envelope.budget_id == budget_id,
            Envelope.name == name,
        )
    )
    envelope = result.scalar_one_or_none()

    if not envelope:
        # Get max sort_order for envelopes in this group
        max_order_result = await session.execute(
            select(func.coalesce(func.max(Envelope.sort_order), 0)).where(
                Envelope.budget_id == budget_id,
                Envelope.envelope_group_id == envelope_group_id,
            )
        )
        max_order = max_order_result.scalar_one()

        # Create envelope
        envelope = Envelope(
            budget_id=budget_id,
            name=name,
            envelope_group_id=envelope_group_id,
            target_balance=target_balance,
            current_balance=0,
            sort_order=max_order + 10,
            is_starred=is_starred,
        )
        session.add(envelope)
        await session.flush()
        await session.commit()

    return envelope


async def create_test_envelope_group(
    session: AsyncSession,
    schema_name: str,
    budget_id: UUID,
    name: str,
) -> EnvelopeGroup:
    """Create an envelope group, or return existing one with same name."""
    await set_search_path(session, schema_name)

    # Check if group already exists
    result = await session.execute(
        select(EnvelopeGroup).where(
            EnvelopeGroup.budget_id == budget_id,
            EnvelopeGroup.name == name,
        )
    )
    group = result.scalar_one_or_none()

    if not group:
        # Get max sort_order for groups in this budget
        max_order_result = await session.execute(
            select(func.coalesce(func.max(EnvelopeGroup.sort_order), 0)).where(
                EnvelopeGroup.budget_id == budget_id
            )
        )
        max_order = max_order_result.scalar_one()

        group = EnvelopeGroup(
            budget_id=budget_id,
            name=name,
            sort_order=max_order + 10,
        )
        session.add(group)
        await session.flush()
        await session.commit()

    return group


async def create_test_payee(
    session: AsyncSession,
    schema_name: str,
    budget_id: UUID,
    name: str,
) -> Payee:
    """Create a payee."""
    await set_search_path(session, schema_name)

    payee = Payee(
        budget_id=budget_id,
        name=name,
    )
    session.add(payee)
    await session.flush()
    await session.commit()

    return payee


async def create_test_transaction(
    session: AsyncSession,
    schema_name: str,
    budget_id: UUID,
    account_id: UUID,
    amount: int,
    payee_name: str | None = None,
    envelope_id: UUID | None = None,
    transaction_date: date | None = None,
    memo: str | None = None,
    is_cleared: bool = False,
) -> Transaction:
    """Create a transaction with optional payee and allocation."""
    await set_search_path(session, schema_name)

    payee_id = None
    payee = None
    if payee_name:
        # Check if payee already exists
        result = await session.execute(
            select(Payee).where(Payee.budget_id == budget_id, Payee.name == payee_name)
        )
        payee = result.scalar_one_or_none()
        if not payee:
            payee = Payee(budget_id=budget_id, name=payee_name)
            session.add(payee)
            await session.flush()
        payee_id = payee.id

    # Create transaction
    transaction = Transaction(
        budget_id=budget_id,
        account_id=account_id,
        payee_id=payee_id,
        date=transaction_date or date.today(),
        amount=amount,
        is_cleared=is_cleared,
        memo=memo,
        transaction_type=TransactionType.STANDARD,
        status=TransactionStatus.POSTED,
    )
    session.add(transaction)
    await session.flush()

    # Update account balance based on cleared status
    result = await session.execute(select(Account).where(Account.id == account_id))
    account = result.scalar_one()
    if is_cleared:
        account.cleared_balance += amount
    else:
        account.uncleared_balance += amount

    # Create allocation if envelope specified, otherwise use unallocated
    if account.include_in_budget:
        # Use transaction.id as group_id (one allocation per transaction)
        group_id = transaction.id

        if envelope_id:
            allocation = Allocation(
                budget_id=budget_id,
                transaction_id=transaction.id,
                envelope_id=envelope_id,
                group_id=group_id,
                amount=amount,
                date=transaction.date,
            )
            session.add(allocation)

            # Update envelope balance
            result = await session.execute(
                select(Envelope).where(Envelope.id == envelope_id)
            )
            envelope = result.scalar_one()
            envelope.current_balance += amount

            # Auto-set default envelope on payee if not already set
            if payee and payee.default_envelope_id is None:
                payee.default_envelope_id = envelope_id
        else:
            # Default to unallocated envelope
            unallocated = await ensure_unallocated_envelope(session, budget_id)
            allocation = Allocation(
                budget_id=budget_id,
                transaction_id=transaction.id,
                envelope_id=unallocated.id,
                group_id=group_id,
                amount=amount,
                date=transaction.date,
            )
            session.add(allocation)

    await session.flush()
    await session.commit()

    return transaction


async def reconcile_test_account(
    session: AsyncSession,
    schema_name: str,
    budget_id: UUID,
    account_id: UUID,
    actual_balance: int,
) -> dict:
    """Reconcile an account - marks cleared transactions as reconciled.

    Returns dict with transactions_reconciled count and optional adjustment_transaction_id.
    """
    from sqlalchemy import update

    await set_search_path(session, schema_name)

    # Mark all cleared transactions as reconciled
    result = await session.execute(
        update(Transaction)
        .where(
            Transaction.budget_id == budget_id,
            Transaction.account_id == account_id,
            Transaction.is_cleared == True,  # noqa: E712
            Transaction.is_reconciled == False,  # noqa: E712
        )
        .values(is_reconciled=True)
    )
    reconciled_count = result.rowcount

    # Get account to check balance
    account_result = await session.execute(
        select(Account).where(Account.id == account_id)
    )
    account = account_result.scalar_one()

    working_balance = account.cleared_balance + account.uncleared_balance
    difference = actual_balance - working_balance

    adjustment_transaction_id = None
    if difference != 0:
        # Get unallocated envelope
        unallocated = await ensure_unallocated_envelope(session, budget_id)

        # Create adjustment transaction
        adjustment = Transaction(
            budget_id=budget_id,
            account_id=account_id,
            date=date.today(),
            amount=difference,
            is_cleared=True,
            is_reconciled=True,
            memo="Balance adjustment",
            transaction_type=TransactionType.ADJUSTMENT,
            status=TransactionStatus.POSTED,
        )
        session.add(adjustment)
        await session.flush()

        # Update account balance
        account.cleared_balance += difference

        # Create allocation
        allocation = Allocation(
            budget_id=budget_id,
            transaction_id=adjustment.id,
            envelope_id=unallocated.id,
            group_id=adjustment.id,
            amount=difference,
            date=adjustment.date,
        )
        session.add(allocation)

        adjustment_transaction_id = adjustment.id
        reconciled_count += 1

    await session.flush()
    await session.commit()

    return {
        "transactions_reconciled": reconciled_count,
        "adjustment_transaction_id": adjustment_transaction_id,
    }


async def create_test_location(
    session: AsyncSession,
    schema_name: str,
    budget_id: UUID,
    name: str,
) -> Location:
    """Create a location."""
    await set_search_path(session, schema_name)

    location = Location(
        budget_id=budget_id,
        name=name,
    )
    session.add(location)
    await session.flush()
    await session.commit()

    return location


async def create_test_allocation_rule(
    session: AsyncSession,
    schema_name: str,
    budget_id: UUID,
    envelope_id: UUID,
    rule_type: str = "fixed",
    amount: int = 0,
    priority: int = 1,
    is_active: bool = True,
    name: str | None = None,
    cap_period_value: int = 1,
    cap_period_unit: str | None = None,
) -> AllocationRule:
    """Create an allocation rule."""
    from src.allocation_rules.models import (
        AllocationCapPeriodUnit,
        AllocationRule,
        AllocationRuleType,
    )

    await set_search_path(session, schema_name)

    # Map string to enum
    rule_type_enum = AllocationRuleType(rule_type)
    cap_unit_enum = (
        AllocationCapPeriodUnit(cap_period_unit) if cap_period_unit else None
    )

    rule = AllocationRule(
        budget_id=budget_id,
        envelope_id=envelope_id,
        rule_type=rule_type_enum,
        amount=amount,
        priority=priority,
        is_active=is_active,
        name=name,
        cap_period_value=cap_period_value,
        cap_period_unit=cap_unit_enum,
    )
    session.add(rule)
    await session.flush()
    await session.commit()

    return rule


async def set_registration_enabled(
    session: AsyncSession,
    schema_name: str,
    enabled: bool,
) -> bool:
    """Set whether registration is enabled for the given schema."""
    from src.admin.models import SystemSettings

    await set_search_path(session, schema_name)

    # Get or create settings row
    result = await session.execute(select(SystemSettings).where(SystemSettings.id == 1))
    settings = result.scalar_one_or_none()

    if settings is None:
        # Create default settings
        settings = SystemSettings(id=1, registration_enabled=enabled)
        session.add(settings)
    else:
        settings.registration_enabled = enabled

    await session.flush()
    await session.commit()

    return settings.registration_enabled
