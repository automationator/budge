from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_async_session
from src.testing.dependencies import require_e2e_environment
from src.testing.schemas import (
    AccountFactoryRequest,
    AccountFactoryResponse,
    AllocationRuleFactoryRequest,
    AllocationRuleFactoryResponse,
    BudgetFactoryRequest,
    BudgetFactoryResponse,
    EnvelopeFactoryRequest,
    EnvelopeFactoryResponse,
    EnvelopeGroupFactoryRequest,
    EnvelopeGroupFactoryResponse,
    LocationFactoryRequest,
    LocationFactoryResponse,
    PayeeFactoryRequest,
    PayeeFactoryResponse,
    ReconcileFactoryRequest,
    ReconcileFactoryResponse,
    ResetRequest,
    ResetResponse,
    SetRegistrationRequest,
    SetRegistrationResponse,
    TransactionFactoryRequest,
    TransactionFactoryResponse,
    UserFactoryRequest,
    UserFactoryResponse,
)
from src.testing.service import (
    create_test_account,
    create_test_allocation_rule,
    create_test_budget,
    create_test_envelope,
    create_test_envelope_group,
    create_test_location,
    create_test_payee,
    create_test_transaction,
    create_test_user,
    reconcile_test_account,
    reset_schema,
    set_registration_enabled,
    validate_worker_id,
)

router = APIRouter(
    tags=["testing"],
    dependencies=[Depends(require_e2e_environment)],
)


@router.post("/reset", response_model=ResetResponse)
async def reset_worker_schema(
    request: ResetRequest,
    session: Annotated[AsyncSession, Depends(get_async_session)],
) -> ResetResponse:
    """Reset the database schema for a specific worker.

    Drops and recreates the schema, then runs migrations.
    This endpoint is only available when ENV=e2e.
    """
    schema_name = await reset_schema(session, request.worker_id)
    return ResetResponse(schema_name=schema_name, status="reset")


@router.post("/factory/user", response_model=UserFactoryResponse)
async def create_user_factory(
    request: UserFactoryRequest,
    session: Annotated[AsyncSession, Depends(get_async_session)],
) -> UserFactoryResponse:
    """Create a test user with budget and return auth tokens.

    This endpoint is only available when ENV=e2e.
    """
    schema_name = validate_worker_id(request.worker_id)
    result = await create_test_user(
        session,
        schema_name,
        request.username,
        request.password,
        request.is_admin,
    )
    return UserFactoryResponse(
        user_id=result["user_id"],
        budget_id=result["budget_id"],
        access_token=result["access_token"],
        refresh_token=result["refresh_token"],
    )


@router.post("/factory/account", response_model=AccountFactoryResponse)
async def create_account_factory(
    request: AccountFactoryRequest,
    session: Annotated[AsyncSession, Depends(get_async_session)],
) -> AccountFactoryResponse:
    """Create a test account with optional starting balance.

    This endpoint is only available when ENV=e2e.
    """
    schema_name = validate_worker_id(request.worker_id)
    account = await create_test_account(
        session,
        schema_name,
        request.budget_id,
        request.name,
        request.account_type,
        request.include_in_budget,
        request.starting_balance,
    )
    return AccountFactoryResponse(
        id=account.id,
        name=account.name,
        account_type=account.account_type,
        include_in_budget=account.include_in_budget,
        cleared_balance=account.cleared_balance,
        uncleared_balance=account.uncleared_balance,
    )


@router.post("/factory/envelope", response_model=EnvelopeFactoryResponse)
async def create_envelope_factory(
    request: EnvelopeFactoryRequest,
    session: Annotated[AsyncSession, Depends(get_async_session)],
) -> EnvelopeFactoryResponse:
    """Create a test envelope with optional group.

    This endpoint is only available when ENV=e2e.
    """
    schema_name = validate_worker_id(request.worker_id)
    envelope = await create_test_envelope(
        session,
        schema_name,
        request.budget_id,
        request.name,
        request.group_name,
        request.target_balance,
        request.is_starred,
    )
    return EnvelopeFactoryResponse(
        id=envelope.id,
        name=envelope.name,
        envelope_group_id=envelope.envelope_group_id,
        current_balance=envelope.current_balance,
        target_balance=envelope.target_balance,
        is_starred=envelope.is_starred,
    )


@router.post("/factory/envelope-group", response_model=EnvelopeGroupFactoryResponse)
async def create_envelope_group_factory(
    request: EnvelopeGroupFactoryRequest,
    session: Annotated[AsyncSession, Depends(get_async_session)],
) -> EnvelopeGroupFactoryResponse:
    """Create a test envelope group.

    This endpoint is only available when ENV=e2e.
    """
    schema_name = validate_worker_id(request.worker_id)
    group = await create_test_envelope_group(
        session,
        schema_name,
        request.budget_id,
        request.name,
    )
    return EnvelopeGroupFactoryResponse(
        id=group.id,
        name=group.name,
        sort_order=group.sort_order,
    )


@router.post("/factory/payee", response_model=PayeeFactoryResponse)
async def create_payee_factory(
    request: PayeeFactoryRequest,
    session: Annotated[AsyncSession, Depends(get_async_session)],
) -> PayeeFactoryResponse:
    """Create a test payee.

    This endpoint is only available when ENV=e2e.
    """
    schema_name = validate_worker_id(request.worker_id)
    payee = await create_test_payee(
        session,
        schema_name,
        request.budget_id,
        request.name,
    )
    return PayeeFactoryResponse(
        id=payee.id,
        name=payee.name,
    )


@router.post("/factory/transaction", response_model=TransactionFactoryResponse)
async def create_transaction_factory(
    request: TransactionFactoryRequest,
    session: Annotated[AsyncSession, Depends(get_async_session)],
) -> TransactionFactoryResponse:
    """Create a test transaction with optional payee and allocation.

    This endpoint is only available when ENV=e2e.
    """
    schema_name = validate_worker_id(request.worker_id)
    transaction = await create_test_transaction(
        session,
        schema_name,
        request.budget_id,
        request.account_id,
        request.amount,
        request.payee_name,
        request.envelope_id,
        request.transaction_date,
        request.memo,
        request.is_cleared,
    )
    return TransactionFactoryResponse(
        id=transaction.id,
        account_id=transaction.account_id,
        amount=transaction.amount,
        payee_id=transaction.payee_id,
        date=transaction.date,
        is_cleared=transaction.is_cleared,
        is_reconciled=transaction.is_reconciled,
    )


@router.post("/factory/reconcile", response_model=ReconcileFactoryResponse)
async def reconcile_account_factory(
    request: ReconcileFactoryRequest,
    session: Annotated[AsyncSession, Depends(get_async_session)],
) -> ReconcileFactoryResponse:
    """Reconcile an account - marks cleared transactions as reconciled.

    This endpoint is only available when ENV=e2e.
    """
    schema_name = validate_worker_id(request.worker_id)
    result = await reconcile_test_account(
        session,
        schema_name,
        request.budget_id,
        request.account_id,
        request.actual_balance,
    )
    return ReconcileFactoryResponse(
        transactions_reconciled=result["transactions_reconciled"],
        adjustment_transaction_id=result["adjustment_transaction_id"],
    )


@router.post("/factory/budget", response_model=BudgetFactoryResponse)
async def create_budget_factory(
    request: BudgetFactoryRequest,
    session: Annotated[AsyncSession, Depends(get_async_session)],
) -> BudgetFactoryResponse:
    """Create a new budget for an existing user.

    This endpoint is only available when ENV=e2e.
    """
    schema_name = validate_worker_id(request.worker_id)
    budget = await create_test_budget(
        session,
        schema_name,
        request.user_id,
        request.name,
    )
    return BudgetFactoryResponse(
        id=budget.id,
        name=budget.name,
    )


@router.post("/factory/location", response_model=LocationFactoryResponse)
async def create_location_factory(
    request: LocationFactoryRequest,
    session: Annotated[AsyncSession, Depends(get_async_session)],
) -> LocationFactoryResponse:
    """Create a test location.

    This endpoint is only available when ENV=e2e.
    """
    schema_name = validate_worker_id(request.worker_id)
    location = await create_test_location(
        session,
        schema_name,
        request.budget_id,
        request.name,
    )
    return LocationFactoryResponse(
        id=location.id,
        name=location.name,
    )


@router.post("/factory/allocation-rule", response_model=AllocationRuleFactoryResponse)
async def create_allocation_rule_factory(
    request: AllocationRuleFactoryRequest,
    session: Annotated[AsyncSession, Depends(get_async_session)],
) -> AllocationRuleFactoryResponse:
    """Create a test allocation rule.

    This endpoint is only available when ENV=e2e.
    """
    schema_name = validate_worker_id(request.worker_id)
    rule = await create_test_allocation_rule(
        session,
        schema_name,
        request.budget_id,
        request.envelope_id,
        request.rule_type,
        request.amount,
        request.priority,
        request.is_active,
        request.name,
        request.cap_period_value,
        request.cap_period_unit,
    )
    return AllocationRuleFactoryResponse(
        id=rule.id,
        envelope_id=rule.envelope_id,
        rule_type=rule.rule_type,
        amount=rule.amount,
        priority=rule.priority,
        is_active=rule.is_active,
        cap_period_value=rule.cap_period_value,
        cap_period_unit=rule.cap_period_unit,
    )


@router.post("/factory/set-registration", response_model=SetRegistrationResponse)
async def set_registration_factory(
    request: SetRegistrationRequest,
    session: Annotated[AsyncSession, Depends(get_async_session)],
) -> SetRegistrationResponse:
    """Enable or disable user registration for testing.

    This endpoint is only available when ENV=e2e.
    """
    schema_name = validate_worker_id(request.worker_id)
    enabled = await set_registration_enabled(
        session,
        schema_name,
        request.enabled,
    )
    return SetRegistrationResponse(registration_enabled=enabled)
