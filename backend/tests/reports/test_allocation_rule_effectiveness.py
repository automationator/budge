from datetime import date, timedelta
from uuid import uuid7

from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.accounts.models import Account, AccountType
from src.allocation_rules.models import AllocationRule, AllocationRuleType
from src.allocations.models import Allocation
from src.budgets.models import Budget
from src.envelopes.models import Envelope
from src.payees.models import Payee
from src.transactions.models import Transaction, TransactionStatus
from src.users.models import User


async def test_allocation_rule_effectiveness_basic(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,
) -> None:
    """Test basic allocation rule effectiveness report."""
    result = await session.execute(
        select(Budget).where(Budget.owner_id == test_user.id)
    )
    budget = result.scalar_one()

    account = Account(
        budget_id=budget.id,
        name="Checking",
        account_type=AccountType.CHECKING,
        include_in_budget=True,
    )
    payee = Payee(budget_id=budget.id, name="Employer")
    envelope = Envelope(budget_id=budget.id, name="Rent", current_balance=0)
    session.add_all([account, payee, envelope])
    await session.flush()

    # Create a fixed allocation rule
    rule = AllocationRule(
        budget_id=budget.id,
        envelope_id=envelope.id,
        priority=1,
        rule_type=AllocationRuleType.FIXED,
        amount=200000,  # $2000 fixed
        name="Rent Rule",
        is_active=True,
    )
    session.add(rule)
    await session.flush()

    # Create income transactions with allocations via this rule
    today = date.today()
    for i in range(3):
        group_id = uuid7()
        txn = Transaction(
            budget_id=budget.id,
            account_id=account.id,
            payee_id=payee.id,
            date=today - timedelta(days=i * 14),
            amount=500000,  # $5000 paycheck
            status=TransactionStatus.POSTED,
        )
        session.add(txn)
        await session.flush()

        alloc = Allocation(
            budget_id=budget.id,
            envelope_id=envelope.id,
            transaction_id=txn.id,
            allocation_rule_id=rule.id,
            group_id=group_id,
            amount=200000,  # $2000 allocated
            date=txn.date,
        )
        session.add(alloc)
    await session.flush()

    response = await authenticated_client.get(
        f"/api/v1/budgets/{budget.id}/reports/allocation-rule-effectiveness"
    )
    assert response.status_code == 200
    data = response.json()

    assert data["active_rules_only"] is True
    assert len(data["items"]) == 1

    item = data["items"][0]
    assert item["rule_name"] == "Rent Rule"
    assert item["envelope_name"] == "Rent"
    assert item["rule_type"] == "fixed"
    assert item["priority"] == 1
    assert item["configured_amount"] == 200000
    assert item["total_allocated"] == 600000  # 3 x $2000
    assert item["times_triggered"] == 3
    assert item["average_per_trigger"] == 200000


async def test_allocation_rule_effectiveness_with_period_cap(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,
) -> None:
    """Test that period_cap_limited is calculated correctly."""
    result = await session.execute(
        select(Budget).where(Budget.owner_id == test_user.id)
    )
    budget = result.scalar_one()

    account = Account(
        budget_id=budget.id,
        name="Checking",
        account_type=AccountType.CHECKING,
        include_in_budget=True,
    )
    payee = Payee(budget_id=budget.id, name="Employer")
    envelope = Envelope(budget_id=budget.id, name="Groceries", current_balance=0)
    session.add_all([account, payee, envelope])
    await session.flush()

    # Create a PERIOD_CAP rule on the envelope ($250/month)
    from src.allocation_rules.models import AllocationCapPeriodUnit

    cap_rule = AllocationRule(
        budget_id=budget.id,
        envelope_id=envelope.id,
        priority=0,
        rule_type=AllocationRuleType.PERIOD_CAP,
        amount=25000,  # $250 cap
        cap_period_value=1,
        cap_period_unit=AllocationCapPeriodUnit.MONTH,
        name="Groceries Cap",
        is_active=True,
    )
    session.add(cap_rule)

    # Create a percentage rule
    rule = AllocationRule(
        budget_id=budget.id,
        envelope_id=envelope.id,
        priority=2,
        rule_type=AllocationRuleType.PERCENTAGE,
        amount=1000,  # 10% (basis points)
        name="Groceries Rule",
        is_active=True,
    )
    session.add(rule)
    await session.flush()

    today = date.today()

    # Create allocations that exceed the cap amount ($250)
    group1 = uuid7()
    txn1 = Transaction(
        budget_id=budget.id,
        account_id=account.id,
        payee_id=payee.id,
        date=today,
        amount=500000,
        status=TransactionStatus.POSTED,
    )
    session.add(txn1)
    await session.flush()
    session.add(
        Allocation(
            budget_id=budget.id,
            envelope_id=envelope.id,
            transaction_id=txn1.id,
            allocation_rule_id=rule.id,
            group_id=group1,
            amount=25000,  # $250
            date=today,
        )
    )

    group2 = uuid7()
    txn2 = Transaction(
        budget_id=budget.id,
        account_id=account.id,
        payee_id=payee.id,
        date=today - timedelta(days=7),
        amount=400000,
        status=TransactionStatus.POSTED,
    )
    session.add(txn2)
    await session.flush()
    session.add(
        Allocation(
            budget_id=budget.id,
            envelope_id=envelope.id,
            transaction_id=txn2.id,
            allocation_rule_id=rule.id,
            group_id=group2,
            amount=20000,  # $200
            date=txn2.date,
        )
    )
    await session.flush()

    response = await authenticated_client.get(
        f"/api/v1/budgets/{budget.id}/reports/allocation-rule-effectiveness"
    )
    assert response.status_code == 200
    data = response.json()

    # Should have both the cap rule and the percentage rule
    assert len(data["items"]) == 2

    # Find the percentage rule item
    pct_item = next(i for i in data["items"] if i["rule_type"] == "percentage")
    assert pct_item["has_period_cap"] is True
    assert pct_item["period_cap_limited"] is True  # $250 + $200 = $450 >= $250 cap
    assert pct_item["total_allocated"] == 45000  # $250 + $200

    # The cap rule itself should also show has_period_cap
    cap_item = next(i for i in data["items"] if i["rule_type"] == "period_cap")
    assert cap_item["has_period_cap"] is True


async def test_allocation_rule_effectiveness_multiple_rules(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,
) -> None:
    """Test with multiple rules sorted by priority."""
    result = await session.execute(
        select(Budget).where(Budget.owner_id == test_user.id)
    )
    budget = result.scalar_one()

    account = Account(
        budget_id=budget.id,
        name="Checking",
        account_type=AccountType.CHECKING,
        include_in_budget=True,
    )
    payee = Payee(budget_id=budget.id, name="Employer")
    rent_envelope = Envelope(budget_id=budget.id, name="Rent", current_balance=0)
    groceries_envelope = Envelope(
        budget_id=budget.id, name="Groceries", current_balance=0
    )
    savings_envelope = Envelope(budget_id=budget.id, name="Savings", current_balance=0)
    session.add_all(
        [account, payee, rent_envelope, groceries_envelope, savings_envelope]
    )
    await session.flush()

    # Create rules with different priorities
    rent_rule = AllocationRule(
        budget_id=budget.id,
        envelope_id=rent_envelope.id,
        priority=1,
        rule_type=AllocationRuleType.FIXED,
        amount=200000,
        name="Rent",
        is_active=True,
    )
    groceries_rule = AllocationRule(
        budget_id=budget.id,
        envelope_id=groceries_envelope.id,
        priority=2,
        rule_type=AllocationRuleType.FIXED,
        amount=50000,
        name="Groceries",
        is_active=True,
    )
    savings_rule = AllocationRule(
        budget_id=budget.id,
        envelope_id=savings_envelope.id,
        priority=10,
        rule_type=AllocationRuleType.REMAINDER,
        amount=0,
        name="Savings",
        is_active=True,
    )
    session.add_all([rent_rule, groceries_rule, savings_rule])
    await session.flush()

    # Create allocations
    today = date.today()
    group_id = uuid7()
    txn = Transaction(
        budget_id=budget.id,
        account_id=account.id,
        payee_id=payee.id,
        date=today,
        amount=500000,
        status=TransactionStatus.POSTED,
    )
    session.add(txn)
    await session.flush()

    session.add_all(
        [
            Allocation(
                budget_id=budget.id,
                envelope_id=rent_envelope.id,
                transaction_id=txn.id,
                allocation_rule_id=rent_rule.id,
                group_id=group_id,
                execution_order=0,
                amount=200000,
                date=today,
            ),
            Allocation(
                budget_id=budget.id,
                envelope_id=groceries_envelope.id,
                transaction_id=txn.id,
                allocation_rule_id=groceries_rule.id,
                group_id=group_id,
                execution_order=1,
                amount=50000,
                date=today,
            ),
            Allocation(
                budget_id=budget.id,
                envelope_id=savings_envelope.id,
                transaction_id=txn.id,
                allocation_rule_id=savings_rule.id,
                group_id=group_id,
                execution_order=2,
                amount=250000,  # Remainder
                date=today,
            ),
        ]
    )
    await session.flush()

    response = await authenticated_client.get(
        f"/api/v1/budgets/{budget.id}/reports/allocation-rule-effectiveness"
    )
    assert response.status_code == 200
    data = response.json()

    # Should be sorted by priority
    assert len(data["items"]) == 3
    assert data["items"][0]["rule_name"] == "Rent"
    assert data["items"][0]["priority"] == 1
    assert data["items"][1]["rule_name"] == "Groceries"
    assert data["items"][1]["priority"] == 2
    assert data["items"][2]["rule_name"] == "Savings"
    assert data["items"][2]["priority"] == 10


async def test_allocation_rule_effectiveness_inactive_rules(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,
) -> None:
    """Test filtering by active/inactive rules."""
    result = await session.execute(
        select(Budget).where(Budget.owner_id == test_user.id)
    )
    budget = result.scalar_one()

    envelope = Envelope(budget_id=budget.id, name="Test", current_balance=0)
    session.add(envelope)
    await session.flush()

    active_rule = AllocationRule(
        budget_id=budget.id,
        envelope_id=envelope.id,
        priority=1,
        rule_type=AllocationRuleType.FIXED,
        amount=10000,
        name="Active Rule",
        is_active=True,
    )
    inactive_rule = AllocationRule(
        budget_id=budget.id,
        envelope_id=envelope.id,
        priority=2,
        rule_type=AllocationRuleType.FIXED,
        amount=20000,
        name="Inactive Rule",
        is_active=False,
    )
    session.add_all([active_rule, inactive_rule])
    await session.flush()

    # Default: active only
    response = await authenticated_client.get(
        f"/api/v1/budgets/{budget.id}/reports/allocation-rule-effectiveness"
    )
    assert response.status_code == 200
    data = response.json()
    assert data["active_rules_only"] is True
    assert len(data["items"]) == 1
    assert data["items"][0]["rule_name"] == "Active Rule"

    # Include inactive
    response = await authenticated_client.get(
        f"/api/v1/budgets/{budget.id}/reports/allocation-rule-effectiveness",
        params={"active_only": False},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["active_rules_only"] is False
    assert len(data["items"]) == 2


async def test_allocation_rule_effectiveness_date_filter(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,
) -> None:
    """Test date range filtering."""
    result = await session.execute(
        select(Budget).where(Budget.owner_id == test_user.id)
    )
    budget = result.scalar_one()

    account = Account(
        budget_id=budget.id,
        name="Checking",
        account_type=AccountType.CHECKING,
        include_in_budget=True,
    )
    payee = Payee(budget_id=budget.id, name="Employer")
    envelope = Envelope(budget_id=budget.id, name="Test", current_balance=0)
    session.add_all([account, payee, envelope])
    await session.flush()

    rule = AllocationRule(
        budget_id=budget.id,
        envelope_id=envelope.id,
        priority=1,
        rule_type=AllocationRuleType.FIXED,
        amount=10000,
        is_active=True,
    )
    session.add(rule)
    await session.flush()

    # Create allocations in different months
    jan = date(2024, 1, 15)
    feb = date(2024, 2, 15)

    for txn_date in [jan, feb]:
        group_id = uuid7()
        txn = Transaction(
            budget_id=budget.id,
            account_id=account.id,
            payee_id=payee.id,
            date=txn_date,
            amount=100000,
            status=TransactionStatus.POSTED,
        )
        session.add(txn)
        await session.flush()
        session.add(
            Allocation(
                budget_id=budget.id,
                envelope_id=envelope.id,
                transaction_id=txn.id,
                allocation_rule_id=rule.id,
                group_id=group_id,
                amount=10000,
                date=txn_date,
            )
        )
    await session.flush()

    # Filter to January only
    response = await authenticated_client.get(
        f"/api/v1/budgets/{budget.id}/reports/allocation-rule-effectiveness",
        params={"start_date": "2024-01-01", "end_date": "2024-01-31"},
    )
    assert response.status_code == 200
    data = response.json()

    assert data["start_date"] == "2024-01-01"
    assert data["end_date"] == "2024-01-31"
    assert len(data["items"]) == 1
    assert data["items"][0]["times_triggered"] == 1
    assert data["items"][0]["total_allocated"] == 10000


async def test_allocation_rule_effectiveness_excludes_scheduled(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,
) -> None:
    """Test that scheduled transactions are excluded."""
    result = await session.execute(
        select(Budget).where(Budget.owner_id == test_user.id)
    )
    budget = result.scalar_one()

    account = Account(
        budget_id=budget.id,
        name="Checking",
        account_type=AccountType.CHECKING,
        include_in_budget=True,
    )
    payee = Payee(budget_id=budget.id, name="Employer")
    envelope = Envelope(budget_id=budget.id, name="Test", current_balance=0)
    session.add_all([account, payee, envelope])
    await session.flush()

    rule = AllocationRule(
        budget_id=budget.id,
        envelope_id=envelope.id,
        priority=1,
        rule_type=AllocationRuleType.FIXED,
        amount=10000,
        is_active=True,
    )
    session.add(rule)
    await session.flush()

    today = date.today()

    # Posted transaction
    posted_txn = Transaction(
        budget_id=budget.id,
        account_id=account.id,
        payee_id=payee.id,
        date=today,
        amount=100000,
        status=TransactionStatus.POSTED,
    )
    session.add(posted_txn)
    await session.flush()
    session.add(
        Allocation(
            budget_id=budget.id,
            envelope_id=envelope.id,
            transaction_id=posted_txn.id,
            allocation_rule_id=rule.id,
            group_id=uuid7(),
            amount=10000,
            date=today,
        )
    )

    # Scheduled transaction (should be excluded)
    scheduled_txn = Transaction(
        budget_id=budget.id,
        account_id=account.id,
        payee_id=payee.id,
        date=today + timedelta(days=14),
        amount=100000,
        status=TransactionStatus.SCHEDULED,
    )
    session.add(scheduled_txn)
    await session.flush()
    session.add(
        Allocation(
            budget_id=budget.id,
            envelope_id=envelope.id,
            transaction_id=scheduled_txn.id,
            allocation_rule_id=rule.id,
            group_id=uuid7(),
            amount=10000,
            date=scheduled_txn.date,
        )
    )
    await session.flush()

    response = await authenticated_client.get(
        f"/api/v1/budgets/{budget.id}/reports/allocation-rule-effectiveness"
    )
    assert response.status_code == 200
    data = response.json()

    # Only posted transaction should be counted
    assert len(data["items"]) == 1
    assert data["items"][0]["times_triggered"] == 1
    assert data["items"][0]["total_allocated"] == 10000


async def test_allocation_rule_effectiveness_no_rules(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,
) -> None:
    """Test with no allocation rules."""
    result = await session.execute(
        select(Budget).where(Budget.owner_id == test_user.id)
    )
    budget = result.scalar_one()

    response = await authenticated_client.get(
        f"/api/v1/budgets/{budget.id}/reports/allocation-rule-effectiveness"
    )
    assert response.status_code == 200
    data = response.json()

    assert data["items"] == []


async def test_allocation_rule_effectiveness_no_allocations(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,
) -> None:
    """Test rule with no allocations shows zero metrics."""
    result = await session.execute(
        select(Budget).where(Budget.owner_id == test_user.id)
    )
    budget = result.scalar_one()

    envelope = Envelope(budget_id=budget.id, name="Test", current_balance=0)
    session.add(envelope)
    await session.flush()

    rule = AllocationRule(
        budget_id=budget.id,
        envelope_id=envelope.id,
        priority=1,
        rule_type=AllocationRuleType.FIXED,
        amount=10000,
        name="Unused Rule",
        is_active=True,
    )
    session.add(rule)
    await session.flush()

    response = await authenticated_client.get(
        f"/api/v1/budgets/{budget.id}/reports/allocation-rule-effectiveness"
    )
    assert response.status_code == 200
    data = response.json()

    assert len(data["items"]) == 1
    item = data["items"][0]
    assert item["rule_name"] == "Unused Rule"
    assert item["total_allocated"] == 0
    assert item["times_triggered"] == 0
    assert item["period_cap_limited"] is False
    assert item["average_per_trigger"] == 0


async def test_allocation_rule_effectiveness_unauthorized(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,  # noqa: ARG001
    test_user2: User,
) -> None:
    """Test that users cannot access other budgets' reports."""
    result = await session.execute(
        select(Budget).where(Budget.owner_id == test_user2.id)
    )
    other_budget = result.scalar_one()

    response = await authenticated_client.get(
        f"/api/v1/budgets/{other_budget.id}/reports/allocation-rule-effectiveness"
    )
    assert response.status_code == 403
