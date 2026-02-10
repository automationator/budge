"""Tests for allocation cap functionality via PERIOD_CAP rules."""

from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.allocation_rules.models import (
    AllocationCapPeriodUnit,
    AllocationRule,
    AllocationRuleType,
)
from src.allocation_rules.service import apply_rules_to_income
from src.budgets.models import Budget
from src.envelopes.models import Envelope
from src.envelopes.service import (
    calculate_period_boundaries,
)
from src.transactions.models import Transaction
from src.users.models import User


class TestPeriodBoundaries:
    """Tests for calculate_period_boundaries helper function."""

    def test_weekly_period_monday(self) -> None:
        """A Monday should start a new week period."""
        # Monday, January 6, 2025
        ref_date = date(2025, 1, 6)
        start, end = calculate_period_boundaries(
            ref_date, 1, AllocationCapPeriodUnit.WEEK
        )
        assert start == date(2025, 1, 6)  # Monday
        assert end == date(2025, 1, 13)  # Next Monday

    def test_weekly_period_wednesday(self) -> None:
        """A Wednesday should be in the same week as Monday."""
        # Wednesday, January 8, 2025
        ref_date = date(2025, 1, 8)
        start, end = calculate_period_boundaries(
            ref_date, 1, AllocationCapPeriodUnit.WEEK
        )
        assert start == date(2025, 1, 6)  # Previous Monday
        assert end == date(2025, 1, 13)  # Next Monday

    def test_monthly_period_first(self) -> None:
        """First of month should start the monthly period."""
        ref_date = date(2025, 1, 1)
        start, end = calculate_period_boundaries(
            ref_date, 1, AllocationCapPeriodUnit.MONTH
        )
        assert start == date(2025, 1, 1)
        assert end == date(2025, 2, 1)

    def test_monthly_period_mid_month(self) -> None:
        """Mid-month date should be in same period as first."""
        ref_date = date(2025, 1, 15)
        start, end = calculate_period_boundaries(
            ref_date, 1, AllocationCapPeriodUnit.MONTH
        )
        assert start == date(2025, 1, 1)
        assert end == date(2025, 2, 1)

    def test_monthly_period_december(self) -> None:
        """December should roll over to next year."""
        ref_date = date(2025, 12, 15)
        start, end = calculate_period_boundaries(
            ref_date, 1, AllocationCapPeriodUnit.MONTH
        )
        assert start == date(2025, 12, 1)
        assert end == date(2026, 1, 1)

    def test_quarterly_period_q1(self) -> None:
        """Q1 should be Jan-Mar."""
        ref_date = date(2025, 2, 15)
        start, end = calculate_period_boundaries(
            ref_date, 3, AllocationCapPeriodUnit.MONTH
        )
        assert start == date(2025, 1, 1)
        assert end == date(2025, 4, 1)

    def test_quarterly_period_q4(self) -> None:
        """Q4 should be Oct-Dec."""
        ref_date = date(2025, 11, 1)
        start, end = calculate_period_boundaries(
            ref_date, 3, AllocationCapPeriodUnit.MONTH
        )
        assert start == date(2025, 10, 1)
        assert end == date(2026, 1, 1)

    def test_yearly_period(self) -> None:
        """Yearly period should be full calendar year."""
        ref_date = date(2025, 6, 15)
        start, end = calculate_period_boundaries(
            ref_date, 1, AllocationCapPeriodUnit.YEAR
        )
        assert start == date(2025, 1, 1)
        assert end == date(2026, 1, 1)


class TestAllocationCapEnforcement:
    """Tests for PERIOD_CAP rule enforcement in apply_rules_to_income."""

    async def test_period_cap_limits_single_allocation(
        self,
        session: AsyncSession,
        test_user: User,
    ) -> None:
        """Allocation should be limited by PERIOD_CAP rule."""
        # Get budget
        result = await session.execute(
            select(Budget).where(Budget.owner_id == test_user.id)
        )
        budget = result.scalar_one()

        # Create envelope
        envelope = Envelope(
            budget_id=budget.id,
            name="Capped Envelope",
        )
        session.add(envelope)
        await session.flush()

        # Create PERIOD_CAP rule for $100/month
        cap_rule = AllocationRule(
            budget_id=budget.id,
            envelope_id=envelope.id,
            priority=0,
            rule_type=AllocationRuleType.PERIOD_CAP,
            amount=10000,  # $100
            cap_period_value=1,
            cap_period_unit=AllocationCapPeriodUnit.MONTH,
            is_active=True,
        )
        session.add(cap_rule)

        # Create fixed rule for $500
        rule = AllocationRule(
            budget_id=budget.id,
            envelope_id=envelope.id,
            priority=1,
            rule_type=AllocationRuleType.FIXED,
            amount=50000,  # $500
            is_active=True,
        )
        session.add(rule)
        await session.flush()

        # Apply rules with $1000 income
        allocations, remaining = await apply_rules_to_income(
            session,
            budget.id,
            100000,
            date.today(),  # $1000
        )

        # Should only allocate $100 due to period cap
        assert len(allocations) == 1
        assert allocations[0].amount == 10000  # $100 (capped)
        assert remaining == 90000  # $900 remaining

    async def test_period_cap_respects_prior_allocations(
        self,
        session: AsyncSession,
        test_user: User,
    ) -> None:
        """PERIOD_CAP should consider allocations already made this period."""
        # Get budget
        result = await session.execute(
            select(Budget).where(Budget.owner_id == test_user.id)
        )
        budget = result.scalar_one()

        # Get an account for transactions
        from src.accounts.models import Account

        result = await session.execute(
            select(Account).where(Account.budget_id == budget.id)
        )
        account = result.scalars().first()
        if not account:
            account = Account(
                budget_id=budget.id,
                name="Test Account",
                account_type="checking",
                include_in_budget=True,
            )
            session.add(account)
            await session.flush()

        # Create envelope
        envelope = Envelope(
            budget_id=budget.id,
            name="Monthly Cap Test",
        )
        session.add(envelope)
        await session.flush()

        # Create PERIOD_CAP rule for $200/month
        cap_rule = AllocationRule(
            budget_id=budget.id,
            envelope_id=envelope.id,
            priority=0,
            rule_type=AllocationRuleType.PERIOD_CAP,
            amount=20000,  # $200
            cap_period_value=1,
            cap_period_unit=AllocationCapPeriodUnit.MONTH,
            is_active=True,
        )
        session.add(cap_rule)

        # Create a prior income transaction this month with allocation
        prior_transaction = Transaction(
            budget_id=budget.id,
            account_id=account.id,
            date=date.today(),
            amount=50000,  # $500 income
        )
        session.add(prior_transaction)
        await session.flush()

        # Create prior allocation of $150 to the envelope
        from uuid import uuid4

        from src.allocations.models import Allocation

        prior_allocation = Allocation(
            budget_id=budget.id,
            envelope_id=envelope.id,
            transaction_id=prior_transaction.id,
            group_id=uuid4(),
            execution_order=0,
            amount=15000,  # $150
            date=prior_transaction.date,
        )
        session.add(prior_allocation)

        # Create fixed rule for $100
        rule = AllocationRule(
            budget_id=budget.id,
            envelope_id=envelope.id,
            priority=1,
            rule_type=AllocationRuleType.FIXED,
            amount=10000,  # $100
            is_active=True,
        )
        session.add(rule)
        await session.flush()

        # Apply rules with $500 income
        allocations, remaining = await apply_rules_to_income(
            session,
            budget.id,
            50000,
            date.today(),  # $500
        )

        # Should only allocate $50 (cap is $200, already have $150)
        assert len(allocations) == 1
        assert allocations[0].amount == 5000  # $50 (200 - 150)
        assert remaining == 45000  # $450 remaining

    async def test_no_allocation_when_period_cap_already_reached(
        self,
        session: AsyncSession,
        test_user: User,
    ) -> None:
        """No allocation when period cap is already exhausted."""
        # Get budget
        result = await session.execute(
            select(Budget).where(Budget.owner_id == test_user.id)
        )
        budget = result.scalar_one()

        # Get an account for transactions
        from src.accounts.models import Account

        result = await session.execute(
            select(Account).where(Account.budget_id == budget.id)
        )
        account = result.scalars().first()
        if not account:
            account = Account(
                budget_id=budget.id,
                name="Test Account 2",
                account_type="checking",
                include_in_budget=True,
            )
            session.add(account)
            await session.flush()

        # Create envelope
        envelope = Envelope(
            budget_id=budget.id,
            name="Exhausted Cap Test",
        )
        session.add(envelope)
        await session.flush()

        # Create PERIOD_CAP rule for $100/month
        cap_rule = AllocationRule(
            budget_id=budget.id,
            envelope_id=envelope.id,
            priority=0,
            rule_type=AllocationRuleType.PERIOD_CAP,
            amount=10000,  # $100
            cap_period_value=1,
            cap_period_unit=AllocationCapPeriodUnit.MONTH,
            is_active=True,
        )
        session.add(cap_rule)

        # Create prior allocation that exhausts the cap
        prior_transaction = Transaction(
            budget_id=budget.id,
            account_id=account.id,
            date=date.today(),
            amount=50000,
        )
        session.add(prior_transaction)
        await session.flush()

        from uuid import uuid4

        from src.allocations.models import Allocation

        prior_allocation = Allocation(
            budget_id=budget.id,
            envelope_id=envelope.id,
            transaction_id=prior_transaction.id,
            group_id=uuid4(),
            execution_order=0,
            amount=10000,  # $100 - exactly at cap
            date=prior_transaction.date,
        )
        session.add(prior_allocation)

        # Create fixed rule for $100
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

        # Apply rules with $500 income
        allocations, remaining = await apply_rules_to_income(
            session, budget.id, 50000, date.today()
        )

        # Should not allocate anything - cap is exhausted
        assert len(allocations) == 0
        assert remaining == 50000  # All income remains
