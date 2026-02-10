from datetime import date
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.allocation_rules.exceptions import (
    AllocationRuleNotFoundError,
    DuplicatePeriodCapError,
    NoActiveRulesError,
    NoUnallocatedMoneyError,
)
from src.allocation_rules.models import AllocationRule, AllocationRuleType
from src.allocation_rules.schemas import (
    AllocationRuleCreate,
    AllocationRuleUpdate,
    ApplyRulesAllocation,
    RulePreviewAllocation,
)
from src.allocations.schemas import AllocationInput
from src.allocations.service import create_envelope_transfer
from src.envelopes.exceptions import EnvelopeNotFoundError
from src.envelopes.models import Envelope
from src.envelopes.service import (
    get_period_to_date_allocation,
    get_unallocated_envelope,
)


async def get_envelope_by_id(
    session: AsyncSession, budget_id: UUID, envelope_id: UUID
) -> Envelope:
    """Get an envelope by ID, ensuring it belongs to the specified budget."""
    result = await session.execute(
        select(Envelope).where(
            Envelope.id == envelope_id, Envelope.budget_id == budget_id
        )
    )
    envelope = result.scalar_one_or_none()
    if not envelope:
        raise EnvelopeNotFoundError(envelope_id)
    return envelope


async def _check_period_cap_uniqueness(
    session: AsyncSession,
    budget_id: UUID,
    envelope_id: UUID,
    exclude_rule_id: UUID | None = None,
) -> None:
    """Raise DuplicatePeriodCapError if a period_cap rule already exists on this envelope."""
    query = select(AllocationRule).where(
        AllocationRule.budget_id == budget_id,
        AllocationRule.envelope_id == envelope_id,
        AllocationRule.rule_type == AllocationRuleType.PERIOD_CAP,
    )
    if exclude_rule_id is not None:
        query = query.where(AllocationRule.id != exclude_rule_id)
    result = await session.execute(query)
    if result.scalar_one_or_none() is not None:
        raise DuplicatePeriodCapError()


async def list_rules(
    session: AsyncSession, budget_id: UUID, active_only: bool = False
) -> list[AllocationRule]:
    """List all allocation rules for a budget, ordered by priority."""
    query = select(AllocationRule).where(AllocationRule.budget_id == budget_id)
    if active_only:
        query = query.where(AllocationRule.is_active.is_(True))
    query = query.order_by(AllocationRule.priority, AllocationRule.id)
    result = await session.execute(query)
    return list(result.scalars().all())


async def get_rule_by_id(
    session: AsyncSession, budget_id: UUID, rule_id: UUID
) -> AllocationRule:
    """Get an allocation rule by ID, ensuring it belongs to the specified budget."""
    result = await session.execute(
        select(AllocationRule).where(
            AllocationRule.id == rule_id, AllocationRule.budget_id == budget_id
        )
    )
    rule = result.scalar_one_or_none()
    if not rule:
        raise AllocationRuleNotFoundError(rule_id)
    return rule


async def create_rule(
    session: AsyncSession, budget_id: UUID, rule_in: AllocationRuleCreate
) -> AllocationRule:
    """Create a new allocation rule."""
    # Verify envelope exists and belongs to budget
    await get_envelope_by_id(session, budget_id, rule_in.envelope_id)

    # Enforce one period_cap rule per envelope
    if rule_in.rule_type == AllocationRuleType.PERIOD_CAP:
        await _check_period_cap_uniqueness(session, budget_id, rule_in.envelope_id)

    rule = AllocationRule(
        budget_id=budget_id,
        envelope_id=rule_in.envelope_id,
        priority=rule_in.priority,
        rule_type=rule_in.rule_type,
        amount=rule_in.amount,
        is_active=rule_in.is_active,
        name=rule_in.name,
        respect_target=rule_in.respect_target,
        cap_period_value=rule_in.cap_period_value,
        cap_period_unit=rule_in.cap_period_unit,
    )
    session.add(rule)
    await session.flush()
    return rule


async def update_rule(
    session: AsyncSession,
    budget_id: UUID,
    rule_id: UUID,
    rule_in: AllocationRuleUpdate,
) -> AllocationRule:
    """Update an allocation rule."""
    rule = await get_rule_by_id(session, budget_id, rule_id)

    update_data = rule_in.model_dump(exclude_unset=True)

    # Verify envelope if being changed
    if "envelope_id" in update_data:
        await get_envelope_by_id(session, budget_id, update_data["envelope_id"])

    # Enforce one period_cap rule per envelope
    new_rule_type = update_data.get("rule_type", rule.rule_type)
    new_envelope_id = update_data.get("envelope_id", rule.envelope_id)
    if new_rule_type == AllocationRuleType.PERIOD_CAP and (
        "rule_type" in update_data or "envelope_id" in update_data
    ):
        await _check_period_cap_uniqueness(
            session, budget_id, new_envelope_id, exclude_rule_id=rule_id
        )

    for field, value in update_data.items():
        setattr(rule, field, value)

    await session.flush()
    return rule


async def delete_rule(session: AsyncSession, budget_id: UUID, rule_id: UUID) -> None:
    """Delete an allocation rule."""
    rule = await get_rule_by_id(session, budget_id, rule_id)
    await session.delete(rule)
    await session.flush()


def calculate_rule_amount(
    rule: AllocationRule,
    envelope: Envelope,
    remaining: int,
) -> int:
    """Calculate how much to allocate for a single rule.

    Args:
        rule: The allocation rule to apply
        envelope: The target envelope (for fill_to_target)
        remaining: Remaining income to distribute

    Returns:
        Amount to allocate in cents (always >= 0)
    """
    if remaining <= 0:
        return 0

    if rule.rule_type == AllocationRuleType.FILL_TO_TARGET:
        # Fill envelope until it reaches target_balance
        if envelope.target_balance is None:
            return 0

        needed = envelope.target_balance - envelope.current_balance
        if needed <= 0:
            return 0

        return min(needed, remaining)

    elif rule.rule_type == AllocationRuleType.FIXED:
        # Allocate fixed amount
        amount = min(rule.amount, remaining)
        # Respect target balance if enabled
        if rule.respect_target and envelope.target_balance is not None:
            headroom = max(0, envelope.target_balance - envelope.current_balance)
            amount = min(amount, headroom)
        return amount

    elif rule.rule_type == AllocationRuleType.PERCENTAGE:
        # Allocate percentage of remaining
        amount = (remaining * rule.amount) // 10000
        # Respect target balance if enabled
        if rule.respect_target and envelope.target_balance is not None:
            headroom = max(0, envelope.target_balance - envelope.current_balance)
            amount = min(amount, headroom)
        return amount

    # REMAINDER and PERIOD_CAP types are handled separately
    return 0


async def apply_rules_to_income(
    session: AsyncSession,
    budget_id: UUID,
    income_amount: int,
    transaction_date: date | None = None,
) -> tuple[list[AllocationInput], int]:
    """Apply allocation rules to distribute income.

    Args:
        session: Database session
        budget_id: Budget ID
        income_amount: Amount of income to distribute (cents)
        transaction_date: Date of the income transaction (for allocation cap tracking)

    Returns:
        Tuple of (list of allocations to create, unallocated amount)
    """
    if income_amount <= 0:
        return [], income_amount

    rules = await list_rules(session, budget_id, active_only=True)
    if not rules:
        return [], income_amount

    # Separate PERIOD_CAP rules from allocating rules
    period_cap_rules: dict[UUID, AllocationRule] = {}  # envelope_id -> cap rule
    allocating_rules: list[AllocationRule] = []
    for rule in rules:
        if rule.rule_type == AllocationRuleType.PERIOD_CAP:
            period_cap_rules[rule.envelope_id] = rule
        else:
            allocating_rules.append(rule)

    remaining = income_amount
    allocations: list[AllocationInput] = []
    remainder_rules: list[tuple[AllocationRule, Envelope]] = []

    # Prefetch all envelopes we need
    envelope_ids = {r.envelope_id for r in allocating_rules} | set(
        period_cap_rules.keys()
    )
    result = await session.execute(
        select(Envelope).where(
            Envelope.id.in_(envelope_ids),
            Envelope.budget_id == budget_id,
            Envelope.is_active.is_(True),
        )
    )
    envelopes = {e.id: e for e in result.scalars().all()}

    # Calculate period-to-date allocations for envelopes with PERIOD_CAP rules
    period_allocations: dict[UUID, int] = {}
    running_period_totals: dict[UUID, int] = {}

    for envelope_id, cap_rule in period_cap_rules.items():
        if envelope_id in envelopes:
            ptd = await get_period_to_date_allocation(
                session,
                budget_id,
                envelope_id,
                cap_rule.cap_period_value,
                cap_rule.cap_period_unit,
                transaction_date,
            )
            period_allocations[envelope_id] = ptd
            running_period_totals[envelope_id] = 0

    # Process allocating rules in priority order (already sorted)
    for rule in allocating_rules:
        envelope = envelopes.get(rule.envelope_id)
        if not envelope:
            continue  # Skip rules for inactive/deleted envelopes

        if rule.rule_type == AllocationRuleType.REMAINDER:
            remainder_rules.append((rule, envelope))
            continue

        if remaining <= 0:
            break

        amount = calculate_rule_amount(rule, envelope, remaining)

        # Apply PERIOD_CAP constraint if envelope has one
        if envelope.id in period_allocations and amount > 0:
            cap = period_cap_rules[envelope.id].amount
            ptd = period_allocations[envelope.id]
            running = running_period_totals[envelope.id]
            period_headroom = max(0, cap - ptd - running)
            amount = min(amount, period_headroom)
            running_period_totals[envelope.id] += amount

        if amount > 0:
            allocations.append(
                AllocationInput(
                    envelope_id=rule.envelope_id,
                    amount=amount,
                    memo=rule.name,
                    allocation_rule_id=rule.id,
                )
            )
            remaining -= amount

    # Handle remainder rules (weighted split with optional target respect)
    if remaining > 0 and remainder_rules:
        total_weight = sum(r.amount for r, _ in remainder_rules)
        if total_weight > 0:
            # Calculate headroom for rules with respect_target and/or PERIOD_CAP
            headrooms: list[int | None] = []
            for rule, envelope in remainder_rules:
                headroom = None

                # Target balance headroom
                if rule.respect_target and envelope.target_balance is not None:
                    headroom = max(
                        0, envelope.target_balance - envelope.current_balance
                    )

                # PERIOD_CAP headroom
                if envelope.id in period_allocations:
                    cap = period_cap_rules[envelope.id].amount
                    ptd = period_allocations[envelope.id]
                    running = running_period_totals.get(envelope.id, 0)
                    cap_headroom = max(0, cap - ptd - running)
                    if headroom is None:
                        headroom = cap_headroom
                    else:
                        headroom = min(headroom, cap_headroom)

                headrooms.append(headroom)

            # Allocate with redistribution when rules hit their target/cap
            pool = remaining
            allocated_shares = [0] * len(remainder_rules)
            active_indices = list(range(len(remainder_rules)))

            while pool > 0 and active_indices:
                active_weight = sum(
                    remainder_rules[i][0].amount for i in active_indices
                )
                if active_weight <= 0:
                    break

                # Calculate all shares for this round at once
                round_shares = []
                for i in active_indices:
                    rule, _envelope = remainder_rules[i]
                    share = (pool * rule.amount) // active_weight
                    round_shares.append((i, share))

                # Handle rounding: give any remainder to last active rule
                total_round = sum(s for _, s in round_shares)
                if round_shares and total_round < pool:
                    last_idx, last_share = round_shares[-1]
                    round_shares[-1] = (last_idx, last_share + (pool - total_round))

                # Apply shares and check target/cap limits
                any_hit_limit = False
                new_active = []
                total_allocated_this_round = 0

                for i, share in round_shares:
                    if headrooms[i] is not None:
                        available = headrooms[i] - allocated_shares[i]
                        if share >= available:
                            share = available
                            any_hit_limit = True
                        else:
                            new_active.append(i)
                    else:
                        new_active.append(i)

                    allocated_shares[i] += share
                    total_allocated_this_round += share

                pool -= total_allocated_this_round

                if not any_hit_limit:
                    # No rules hit target/cap, we're done
                    break

                active_indices = new_active

            # Create allocations and update running period totals
            for i, (rule, envelope) in enumerate(remainder_rules):
                share = allocated_shares[i]
                if share > 0:
                    allocations.append(
                        AllocationInput(
                            envelope_id=rule.envelope_id,
                            amount=share,
                            memo=rule.name,
                            allocation_rule_id=rule.id,
                        )
                    )
                    # Update running total for PERIOD_CAP tracking
                    if envelope.id in running_period_totals:
                        running_period_totals[envelope.id] += share

            remaining = pool

    return allocations, remaining


async def preview_rules(
    session: AsyncSession,
    budget_id: UUID,
    income_amount: int,
    transaction_date: date | None = None,
) -> tuple[list[RulePreviewAllocation], int]:
    """Preview what allocations rules would create for a given income amount.

    Similar to apply_rules_to_income but returns preview data with rule info.
    """
    if income_amount <= 0:
        return [], income_amount

    rules = await list_rules(session, budget_id, active_only=True)
    if not rules:
        return [], income_amount

    # Separate PERIOD_CAP rules from allocating rules
    period_cap_rules: dict[UUID, AllocationRule] = {}  # envelope_id -> cap rule
    allocating_rules: list[AllocationRule] = []
    for rule in rules:
        if rule.rule_type == AllocationRuleType.PERIOD_CAP:
            period_cap_rules[rule.envelope_id] = rule
        else:
            allocating_rules.append(rule)

    remaining = income_amount
    preview: list[RulePreviewAllocation] = []
    remainder_rules: list[tuple[AllocationRule, Envelope]] = []

    # Prefetch all envelopes we need
    envelope_ids = {r.envelope_id for r in allocating_rules} | set(
        period_cap_rules.keys()
    )
    result = await session.execute(
        select(Envelope).where(
            Envelope.id.in_(envelope_ids),
            Envelope.budget_id == budget_id,
            Envelope.is_active.is_(True),
        )
    )
    envelopes = {e.id: e for e in result.scalars().all()}

    # Calculate period-to-date allocations for envelopes with PERIOD_CAP rules
    period_allocations: dict[UUID, int] = {}
    running_period_totals: dict[UUID, int] = {}

    for envelope_id, cap_rule in period_cap_rules.items():
        if envelope_id in envelopes:
            ptd = await get_period_to_date_allocation(
                session,
                budget_id,
                envelope_id,
                cap_rule.cap_period_value,
                cap_rule.cap_period_unit,
                transaction_date,
            )
            period_allocations[envelope_id] = ptd
            running_period_totals[envelope_id] = 0

    for rule in allocating_rules:
        envelope = envelopes.get(rule.envelope_id)
        if not envelope:
            continue

        if rule.rule_type == AllocationRuleType.REMAINDER:
            remainder_rules.append((rule, envelope))
            continue

        if remaining <= 0:
            break

        amount = calculate_rule_amount(rule, envelope, remaining)

        # Apply PERIOD_CAP constraint if envelope has one
        if envelope.id in period_allocations and amount > 0:
            cap = period_cap_rules[envelope.id].amount
            ptd = period_allocations[envelope.id]
            running = running_period_totals[envelope.id]
            period_headroom = max(0, cap - ptd - running)
            amount = min(amount, period_headroom)
            running_period_totals[envelope.id] += amount

        if amount > 0:
            preview.append(
                RulePreviewAllocation(
                    envelope_id=rule.envelope_id,
                    amount=amount,
                    rule_id=rule.id,
                    rule_name=rule.name,
                )
            )
            remaining -= amount

    # Handle remainder rules (weighted split with optional target respect)
    if remaining > 0 and remainder_rules:
        total_weight = sum(r.amount for r, _ in remainder_rules)
        if total_weight > 0:
            # Calculate headroom for rules with respect_target and/or PERIOD_CAP
            headrooms: list[int | None] = []
            for rule, envelope in remainder_rules:
                headroom = None

                # Target balance headroom
                if rule.respect_target and envelope.target_balance is not None:
                    headroom = max(
                        0, envelope.target_balance - envelope.current_balance
                    )

                # PERIOD_CAP headroom
                if envelope.id in period_allocations:
                    cap = period_cap_rules[envelope.id].amount
                    ptd = period_allocations[envelope.id]
                    running = running_period_totals.get(envelope.id, 0)
                    cap_headroom = max(0, cap - ptd - running)
                    if headroom is None:
                        headroom = cap_headroom
                    else:
                        headroom = min(headroom, cap_headroom)

                headrooms.append(headroom)

            # Allocate with redistribution when rules hit their target/cap
            pool = remaining
            allocated_shares = [0] * len(remainder_rules)
            active_indices = list(range(len(remainder_rules)))

            while pool > 0 and active_indices:
                active_weight = sum(
                    remainder_rules[i][0].amount for i in active_indices
                )
                if active_weight <= 0:
                    break

                # Calculate all shares for this round at once
                round_shares = []
                for i in active_indices:
                    rule, _envelope = remainder_rules[i]
                    share = (pool * rule.amount) // active_weight
                    round_shares.append((i, share))

                # Handle rounding: give any remainder to last active rule
                total_round = sum(s for _, s in round_shares)
                if round_shares and total_round < pool:
                    last_idx, last_share = round_shares[-1]
                    round_shares[-1] = (last_idx, last_share + (pool - total_round))

                # Apply shares and check target/cap limits
                any_hit_limit = False
                new_active = []
                total_allocated_this_round = 0

                for i, share in round_shares:
                    if headrooms[i] is not None:
                        available = headrooms[i] - allocated_shares[i]
                        if share >= available:
                            share = available
                            any_hit_limit = True
                        else:
                            new_active.append(i)
                    else:
                        new_active.append(i)

                    allocated_shares[i] += share
                    total_allocated_this_round += share

                pool -= total_allocated_this_round

                if not any_hit_limit:
                    # No rules hit target/cap, we're done
                    break

                active_indices = new_active

            # Create preview allocations
            for i, (rule, envelope) in enumerate(remainder_rules):
                share = allocated_shares[i]
                if share > 0:
                    preview.append(
                        RulePreviewAllocation(
                            envelope_id=rule.envelope_id,
                            amount=share,
                            rule_id=rule.id,
                            rule_name=rule.name,
                        )
                    )
                    # Update running total for PERIOD_CAP tracking
                    if envelope.id in running_period_totals:
                        running_period_totals[envelope.id] += share

            remaining = pool

    return preview, remaining


async def apply_rules_to_unallocated(
    session: AsyncSession,
    budget_id: UUID,
) -> tuple[int, list[ApplyRulesAllocation], int]:
    """Apply allocation rules to the unallocated envelope balance.

    Gets the current unallocated balance, applies allocation rules to it,
    and creates envelope transfers to distribute the money.

    Returns:
        Tuple of (initial_unallocated, allocations, final_unallocated)

    Raises:
        NoUnallocatedMoneyError: If unallocated balance is <= 0
        NoActiveRulesError: If no active allocation rules exist
    """
    # Get unallocated envelope
    unallocated = await get_unallocated_envelope(session, budget_id)
    if not unallocated or unallocated.current_balance <= 0:
        raise NoUnallocatedMoneyError()

    initial_balance = unallocated.current_balance

    # Calculate allocations using existing logic
    # Use today's date for allocation cap tracking
    allocation_inputs, remaining = await apply_rules_to_income(
        session, budget_id, initial_balance, date.today()
    )

    if not allocation_inputs:
        raise NoActiveRulesError()

    # Prefetch envelopes for names
    envelope_ids = {a.envelope_id for a in allocation_inputs}
    result = await session.execute(
        select(Envelope).where(
            Envelope.id.in_(envelope_ids),
            Envelope.budget_id == budget_id,
        )
    )
    envelopes = {e.id: e for e in result.scalars().all()}

    # Create envelope transfers and build response
    allocations: list[ApplyRulesAllocation] = []
    for alloc_input in allocation_inputs:
        envelope = envelopes.get(alloc_input.envelope_id)
        if not envelope:
            continue

        # Create transfer from unallocated to target envelope
        await create_envelope_transfer(
            session=session,
            budget_id=budget_id,
            source_envelope_id=unallocated.id,
            destination_envelope_id=alloc_input.envelope_id,
            amount=alloc_input.amount,
            memo=alloc_input.memo,
        )

        allocations.append(
            ApplyRulesAllocation(
                envelope_id=alloc_input.envelope_id,
                envelope_name=envelope.name,
                amount=alloc_input.amount,
                rule_id=alloc_input.allocation_rule_id,
                rule_name=alloc_input.memo,
            )
        )

    return initial_balance, allocations, remaining
