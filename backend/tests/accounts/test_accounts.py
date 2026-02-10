from datetime import date

from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.accounts.models import Account, AccountType
from src.auth.service import create_access_token
from src.budgets.models import Budget, BudgetMembership, BudgetRole
from src.envelopes.models import Envelope
from src.transactions.models import Transaction, TransactionType
from src.users.models import User


async def test_create_account(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,
) -> None:
    result = await session.execute(
        select(Budget).where(Budget.owner_id == test_user.id)
    )
    budget = result.scalar_one()

    response = await authenticated_client.post(
        f"/api/v1/budgets/{budget.id}/accounts",
        json={
            "name": "My Checking",
            "account_type": "checking",
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "My Checking"
    assert data["account_type"] == "checking"
    assert data["cleared_balance"] == 0
    assert data["uncleared_balance"] == 0
    assert data["include_in_budget"] is True
    assert data["is_active"] is True


async def test_create_account_with_all_fields(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,
) -> None:
    result = await session.execute(
        select(Budget).where(Budget.owner_id == test_user.id)
    )
    budget = result.scalar_one()

    response = await authenticated_client.post(
        f"/api/v1/budgets/{budget.id}/accounts",
        json={
            "name": "Savings Account",
            "account_type": "savings",
            "icon": "💰",
            "description": "My emergency fund",
            "sort_order": 5,
            "include_in_budget": False,
            "is_active": True,
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Savings Account"
    assert data["account_type"] == "savings"
    assert data["icon"] == "💰"
    assert data["description"] == "My emergency fund"
    assert data["sort_order"] == 5
    assert data["include_in_budget"] is False


async def test_create_duplicate_account_name(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,
) -> None:
    result = await session.execute(
        select(Budget).where(Budget.owner_id == test_user.id)
    )
    budget = result.scalar_one()

    # Create first account
    account = Account(
        budget_id=budget.id,
        name="Duplicate Test",
        account_type=AccountType.CHECKING,
    )
    session.add(account)
    await session.flush()

    # Try to create account with same name
    response = await authenticated_client.post(
        f"/api/v1/budgets/{budget.id}/accounts",
        json={
            "name": "Duplicate Test",
            "account_type": "savings",
        },
    )
    assert response.status_code == 409
    assert "already exists" in response.json()["detail"].lower()


async def test_list_accounts(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,
) -> None:
    result = await session.execute(
        select(Budget).where(Budget.owner_id == test_user.id)
    )
    budget = result.scalar_one()

    # Create some accounts
    accounts = [
        Account(
            budget_id=budget.id,
            name="Account B",
            account_type=AccountType.CHECKING,
            sort_order=2,
        ),
        Account(
            budget_id=budget.id,
            name="Account A",
            account_type=AccountType.SAVINGS,
            sort_order=1,
        ),
        Account(
            budget_id=budget.id,
            name="Account C",
            account_type=AccountType.CASH,
            sort_order=1,
        ),
    ]
    for acc in accounts:
        session.add(acc)
    await session.flush()

    response = await authenticated_client.get(f"/api/v1/budgets/{budget.id}/accounts")
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 3
    # Should be ordered by sort_order, then name
    names = [a["name"] for a in data[-3:]]
    assert names == ["Account A", "Account C", "Account B"]


async def test_get_account(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,
) -> None:
    result = await session.execute(
        select(Budget).where(Budget.owner_id == test_user.id)
    )
    budget = result.scalar_one()

    account = Account(
        budget_id=budget.id,
        name="Get Test Account",
        account_type=AccountType.CREDIT_CARD,
        icon="💳",
    )
    session.add(account)
    await session.flush()

    response = await authenticated_client.get(
        f"/api/v1/budgets/{budget.id}/accounts/{account.id}"
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Get Test Account"
    assert data["account_type"] == "credit_card"
    assert data["icon"] == "💳"


async def test_get_account_not_found(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,
) -> None:
    result = await session.execute(
        select(Budget).where(Budget.owner_id == test_user.id)
    )
    budget = result.scalar_one()

    response = await authenticated_client.get(
        f"/api/v1/budgets/{budget.id}/accounts/00000000-0000-0000-0000-000000000000"
    )
    assert response.status_code == 404


async def test_update_account(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,
) -> None:
    result = await session.execute(
        select(Budget).where(Budget.owner_id == test_user.id)
    )
    budget = result.scalar_one()

    account = Account(
        budget_id=budget.id,
        name="Update Test",
        account_type=AccountType.CHECKING,
    )
    session.add(account)
    await session.flush()

    response = await authenticated_client.patch(
        f"/api/v1/budgets/{budget.id}/accounts/{account.id}",
        json={
            "name": "Updated Name",
            "icon": "🏦",
            "include_in_budget": False,
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Updated Name"
    assert data["icon"] == "🏦"
    assert data["include_in_budget"] is False
    # Unchanged fields should remain
    assert data["account_type"] == "checking"


async def test_update_account_duplicate_name(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,
) -> None:
    result = await session.execute(
        select(Budget).where(Budget.owner_id == test_user.id)
    )
    budget = result.scalar_one()

    # Create two accounts
    account1 = Account(
        budget_id=budget.id,
        name="First Account",
        account_type=AccountType.CHECKING,
    )
    account2 = Account(
        budget_id=budget.id,
        name="Second Account",
        account_type=AccountType.SAVINGS,
    )
    session.add(account1)
    session.add(account2)
    await session.flush()

    # Try to rename account2 to account1's name
    response = await authenticated_client.patch(
        f"/api/v1/budgets/{budget.id}/accounts/{account2.id}",
        json={"name": "First Account"},
    )
    assert response.status_code == 409
    assert "already exists" in response.json()["detail"].lower()


async def test_delete_account(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,
) -> None:
    result = await session.execute(
        select(Budget).where(Budget.owner_id == test_user.id)
    )
    budget = result.scalar_one()

    account = Account(
        budget_id=budget.id,
        name="Delete Test",
        account_type=AccountType.CASH,
    )
    session.add(account)
    await session.flush()
    account_id = account.id

    response = await authenticated_client.delete(
        f"/api/v1/budgets/{budget.id}/accounts/{account_id}"
    )
    assert response.status_code == 204

    # Verify it's gone
    result = await session.execute(select(Account).where(Account.id == account_id))
    assert result.scalar_one_or_none() is None


async def test_delete_account_not_found(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,
) -> None:
    result = await session.execute(
        select(Budget).where(Budget.owner_id == test_user.id)
    )
    budget = result.scalar_one()

    response = await authenticated_client.delete(
        f"/api/v1/budgets/{budget.id}/accounts/00000000-0000-0000-0000-000000000000"
    )
    assert response.status_code == 404


async def test_account_unauthorized(client: AsyncClient) -> None:
    response = await client.get(
        "/api/v1/budgets/00000000-0000-0000-0000-000000000000/accounts"
    )
    assert response.status_code == 401


async def test_account_not_budget_member(
    client: AsyncClient,
    session: AsyncSession,
    test_user: User,
    test_user2: User,
) -> None:
    result = await session.execute(
        select(Budget).where(Budget.owner_id == test_user.id)
    )
    budget = result.scalar_one()

    # Authenticate as test_user2 (not a member)
    token = create_access_token(test_user2.id)
    client.headers["Authorization"] = f"Bearer {token}"

    response = await client.get(f"/api/v1/budgets/{budget.id}/accounts")
    assert response.status_code == 403


async def test_member_can_read_accounts(
    client: AsyncClient,
    session: AsyncSession,
    test_user: User,
    test_user2: User,
) -> None:
    result = await session.execute(
        select(Budget).where(Budget.owner_id == test_user.id)
    )
    budget = result.scalar_one()

    # Add test_user2 as a member
    membership = BudgetMembership(
        user_id=test_user2.id,
        budget_id=budget.id,
        role=BudgetRole.MEMBER,
    )
    session.add(membership)
    await session.flush()

    # Authenticate as test_user2
    token = create_access_token(test_user2.id)
    client.headers["Authorization"] = f"Bearer {token}"

    response = await client.get(f"/api/v1/budgets/{budget.id}/accounts")
    assert response.status_code == 200


async def test_member_cannot_create_account(
    client: AsyncClient,
    session: AsyncSession,
    test_user: User,
    test_user2: User,
) -> None:
    result = await session.execute(
        select(Budget).where(Budget.owner_id == test_user.id)
    )
    budget = result.scalar_one()

    # Add test_user2 as a member
    membership = BudgetMembership(
        user_id=test_user2.id,
        budget_id=budget.id,
        role=BudgetRole.MEMBER,
    )
    session.add(membership)
    await session.flush()

    # Authenticate as test_user2
    token = create_access_token(test_user2.id)
    client.headers["Authorization"] = f"Bearer {token}"

    response = await client.post(
        f"/api/v1/budgets/{budget.id}/accounts",
        json={"name": "New Account", "account_type": "checking"},
    )
    assert response.status_code == 403


async def test_admin_can_create_account(
    client: AsyncClient,
    session: AsyncSession,
    test_user: User,
    test_user2: User,
) -> None:
    result = await session.execute(
        select(Budget).where(Budget.owner_id == test_user.id)
    )
    budget = result.scalar_one()

    # Add test_user2 as an admin
    membership = BudgetMembership(
        user_id=test_user2.id,
        budget_id=budget.id,
        role=BudgetRole.ADMIN,
    )
    session.add(membership)
    await session.flush()

    # Authenticate as test_user2
    token = create_access_token(test_user2.id)
    client.headers["Authorization"] = f"Bearer {token}"

    response = await client.post(
        f"/api/v1/budgets/{budget.id}/accounts",
        json={"name": "Admin Created Account", "account_type": "checking"},
    )
    assert response.status_code == 201


async def test_admin_cannot_delete_account(
    client: AsyncClient,
    session: AsyncSession,
    test_user: User,
    test_user2: User,
) -> None:
    result = await session.execute(
        select(Budget).where(Budget.owner_id == test_user.id)
    )
    budget = result.scalar_one()

    # Create an account
    account = Account(
        budget_id=budget.id,
        name="Admin Delete Test",
        account_type=AccountType.CHECKING,
    )
    session.add(account)

    # Add test_user2 as an admin
    membership = BudgetMembership(
        user_id=test_user2.id,
        budget_id=budget.id,
        role=BudgetRole.ADMIN,
    )
    session.add(membership)
    await session.flush()

    # Authenticate as test_user2
    token = create_access_token(test_user2.id)
    client.headers["Authorization"] = f"Bearer {token}"

    response = await client.delete(f"/api/v1/budgets/{budget.id}/accounts/{account.id}")
    assert response.status_code == 403


# Reconciliation tests


async def test_reconcile_account_positive_adjustment(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,
) -> None:
    """Test reconciling when actual balance is higher than current balance."""
    result = await session.execute(
        select(Budget).where(Budget.owner_id == test_user.id)
    )
    budget = result.scalar_one()

    # Create account with cleared_balance of 10000 (100.00)
    account = Account(
        budget_id=budget.id,
        name="Reconcile Test",
        account_type=AccountType.CHECKING,
        cleared_balance=10000,
    )
    session.add(account)
    await session.flush()

    # Reconcile to actual balance of 15000 (150.00)
    response = await authenticated_client.post(
        f"/api/v1/budgets/{budget.id}/accounts/{account.id}/reconcile",
        json={"actual_balance": 15000},
    )
    assert response.status_code == 200
    data = response.json()

    # Should return reconcile response with adjustment transaction
    assert data["transactions_reconciled"] == 1  # Just the adjustment
    assert data["adjustment_transaction"] is not None
    adj = data["adjustment_transaction"]
    assert adj["amount"] == 5000  # 15000 - 10000
    assert adj["transaction_type"] == "adjustment"
    assert adj["payee_id"] is None
    assert adj["account_id"] == str(account.id)
    assert adj["is_cleared"] is True
    assert adj["is_reconciled"] is True
    assert adj["memo"] == "Balance adjustment"


async def test_reconcile_account_negative_adjustment(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,
) -> None:
    """Test reconciling when actual balance is lower than current balance."""
    result = await session.execute(
        select(Budget).where(Budget.owner_id == test_user.id)
    )
    budget = result.scalar_one()

    # Create account with cleared_balance of 20000 (200.00)
    account = Account(
        budget_id=budget.id,
        name="Reconcile Negative Test",
        account_type=AccountType.CHECKING,
        cleared_balance=20000,
    )
    session.add(account)
    await session.flush()

    # Reconcile to actual balance of 15000 (150.00)
    response = await authenticated_client.post(
        f"/api/v1/budgets/{budget.id}/accounts/{account.id}/reconcile",
        json={"actual_balance": 15000},
    )
    assert response.status_code == 200
    data = response.json()

    # Should create a negative adjustment
    assert data["adjustment_transaction"] is not None
    assert data["adjustment_transaction"]["amount"] == -5000  # 15000 - 20000
    assert data["adjustment_transaction"]["transaction_type"] == "adjustment"
    assert data["adjustment_transaction"]["is_reconciled"] is True


async def test_reconcile_account_already_balanced_no_transactions(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,
) -> None:
    """Test reconciling when balance already matches still succeeds but no adjustment."""
    result = await session.execute(
        select(Budget).where(Budget.owner_id == test_user.id)
    )
    budget = result.scalar_one()

    account = Account(
        budget_id=budget.id,
        name="Already Balanced",
        account_type=AccountType.CHECKING,
        cleared_balance=10000,
    )
    session.add(account)
    await session.flush()

    response = await authenticated_client.post(
        f"/api/v1/budgets/{budget.id}/accounts/{account.id}/reconcile",
        json={"actual_balance": 10000},
    )
    assert response.status_code == 200
    data = response.json()
    # No adjustment needed, no transactions to mark
    assert data["transactions_reconciled"] == 0
    assert data["adjustment_transaction"] is None


async def test_reconcile_account_not_found(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,
) -> None:
    result = await session.execute(
        select(Budget).where(Budget.owner_id == test_user.id)
    )
    budget = result.scalar_one()

    response = await authenticated_client.post(
        f"/api/v1/budgets/{budget.id}/accounts/00000000-0000-0000-0000-000000000000/reconcile",
        json={"actual_balance": 10000},
    )
    assert response.status_code == 404


async def test_reconcile_account_unauthorized(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/budgets/00000000-0000-0000-0000-000000000000/accounts/00000000-0000-0000-0000-000000000000/reconcile",
        json={"actual_balance": 10000},
    )
    assert response.status_code == 401


async def test_member_cannot_reconcile_account(
    client: AsyncClient,
    session: AsyncSession,
    test_user: User,
    test_user2: User,
) -> None:
    """Members don't have ACCOUNTS_UPDATE scope, so cannot reconcile."""
    result = await session.execute(
        select(Budget).where(Budget.owner_id == test_user.id)
    )
    budget = result.scalar_one()

    account = Account(
        budget_id=budget.id,
        name="Member Reconcile Test",
        account_type=AccountType.CHECKING,
        cleared_balance=10000,
    )
    session.add(account)

    # Add test_user2 as a member
    membership = BudgetMembership(
        user_id=test_user2.id,
        budget_id=budget.id,
        role=BudgetRole.MEMBER,
    )
    session.add(membership)
    await session.flush()

    # Authenticate as test_user2
    token = create_access_token(test_user2.id)
    client.headers["Authorization"] = f"Bearer {token}"

    response = await client.post(
        f"/api/v1/budgets/{budget.id}/accounts/{account.id}/reconcile",
        json={"actual_balance": 15000},
    )
    assert response.status_code == 403


async def test_admin_can_reconcile_account(
    client: AsyncClient,
    session: AsyncSession,
    test_user: User,
    test_user2: User,
) -> None:
    """Admins have both ACCOUNTS_UPDATE and TRANSACTIONS_CREATE scopes."""
    result = await session.execute(
        select(Budget).where(Budget.owner_id == test_user.id)
    )
    budget = result.scalar_one()

    account = Account(
        budget_id=budget.id,
        name="Admin Reconcile Test",
        account_type=AccountType.CHECKING,
        cleared_balance=10000,
    )
    session.add(account)

    # Add test_user2 as an admin
    membership = BudgetMembership(
        user_id=test_user2.id,
        budget_id=budget.id,
        role=BudgetRole.ADMIN,
    )
    session.add(membership)
    await session.flush()

    # Authenticate as test_user2
    token = create_access_token(test_user2.id)
    client.headers["Authorization"] = f"Bearer {token}"

    response = await client.post(
        f"/api/v1/budgets/{budget.id}/accounts/{account.id}/reconcile",
        json={"actual_balance": 15000},
    )
    assert response.status_code == 200


async def test_reconcile_marks_cleared_transactions_as_reconciled(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,
) -> None:
    """Test that reconciliation marks cleared transactions as reconciled."""
    result = await session.execute(
        select(Budget).where(Budget.owner_id == test_user.id)
    )
    budget = result.scalar_one()

    account = Account(
        budget_id=budget.id,
        name="Reconcile Mark Test",
        account_type=AccountType.CHECKING,
        cleared_balance=10000,
        uncleared_balance=5000,
    )
    session.add(account)
    await session.flush()

    # Create some transactions - 2 cleared, 1 uncleared
    from src.payees.models import Payee

    payee = Payee(budget_id=budget.id, name="Test Payee")
    session.add(payee)
    await session.flush()

    txn1 = Transaction(
        budget_id=budget.id,
        account_id=account.id,
        payee_id=payee.id,
        date=date.today(),
        amount=5000,
        is_cleared=True,
        is_reconciled=False,
    )
    txn2 = Transaction(
        budget_id=budget.id,
        account_id=account.id,
        payee_id=payee.id,
        date=date.today(),
        amount=5000,
        is_cleared=True,
        is_reconciled=False,
    )
    txn3 = Transaction(
        budget_id=budget.id,
        account_id=account.id,
        payee_id=payee.id,
        date=date.today(),
        amount=5000,
        is_cleared=False,  # Uncleared
        is_reconciled=False,
    )
    session.add_all([txn1, txn2, txn3])
    await session.flush()

    # Reconcile (cleared balance matches, no adjustment needed)
    response = await authenticated_client.post(
        f"/api/v1/budgets/{budget.id}/accounts/{account.id}/reconcile",
        json={"actual_balance": 10000},
    )
    assert response.status_code == 200
    data = response.json()

    # Should have marked 2 cleared transactions as reconciled
    assert data["transactions_reconciled"] == 2
    assert data["adjustment_transaction"] is None

    # Verify in database
    await session.refresh(txn1)
    await session.refresh(txn2)
    await session.refresh(txn3)
    assert txn1.is_reconciled is True
    assert txn2.is_reconciled is True
    assert txn3.is_reconciled is False  # Uncleared should not be reconciled


async def test_reconcile_only_affects_account_transactions(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,
) -> None:
    """Test that reconciliation only marks transactions for the specified account."""
    result = await session.execute(
        select(Budget).where(Budget.owner_id == test_user.id)
    )
    budget = result.scalar_one()

    account1 = Account(
        budget_id=budget.id,
        name="Account 1",
        account_type=AccountType.CHECKING,
        cleared_balance=5000,
    )
    account2 = Account(
        budget_id=budget.id,
        name="Account 2",
        account_type=AccountType.CHECKING,
        cleared_balance=5000,
    )
    session.add_all([account1, account2])
    await session.flush()

    from src.payees.models import Payee

    payee = Payee(budget_id=budget.id, name="Test Payee")
    session.add(payee)
    await session.flush()

    # Create cleared transactions for both accounts
    txn1 = Transaction(
        budget_id=budget.id,
        account_id=account1.id,
        payee_id=payee.id,
        date=date.today(),
        amount=5000,
        is_cleared=True,
        is_reconciled=False,
    )
    txn2 = Transaction(
        budget_id=budget.id,
        account_id=account2.id,
        payee_id=payee.id,
        date=date.today(),
        amount=5000,
        is_cleared=True,
        is_reconciled=False,
    )
    session.add_all([txn1, txn2])
    await session.flush()

    # Reconcile account1 only
    response = await authenticated_client.post(
        f"/api/v1/budgets/{budget.id}/accounts/{account1.id}/reconcile",
        json={"actual_balance": 5000},
    )
    assert response.status_code == 200

    # Verify only account1's transaction was marked reconciled
    await session.refresh(txn1)
    await session.refresh(txn2)
    assert txn1.is_reconciled is True
    assert txn2.is_reconciled is False


async def test_reconcile_creates_adjustment_in_database(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,
) -> None:
    """Verify the adjustment transaction is actually created in the database."""
    result = await session.execute(
        select(Budget).where(Budget.owner_id == test_user.id)
    )
    budget = result.scalar_one()

    account = Account(
        budget_id=budget.id,
        name="DB Reconcile Test",
        account_type=AccountType.CHECKING,
        cleared_balance=5000,
    )
    session.add(account)
    await session.flush()

    response = await authenticated_client.post(
        f"/api/v1/budgets/{budget.id}/accounts/{account.id}/reconcile",
        json={"actual_balance": 8000},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["adjustment_transaction"] is not None
    transaction_id = data["adjustment_transaction"]["id"]

    # Verify in database
    result = await session.execute(
        select(Transaction).where(Transaction.id == transaction_id)
    )
    transaction = result.scalar_one()
    assert transaction.amount == 3000
    assert transaction.transaction_type == TransactionType.ADJUSTMENT
    assert transaction.payee_id is None
    assert transaction.account_id == account.id
    assert transaction.is_reconciled is True


# Credit Card Envelope Auto-Creation Tests


async def test_create_credit_card_account_creates_linked_envelope(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,
) -> None:
    """Creating a credit card account should auto-create a linked envelope."""
    result = await session.execute(
        select(Budget).where(Budget.owner_id == test_user.id)
    )
    budget = result.scalar_one()

    response = await authenticated_client.post(
        f"/api/v1/budgets/{budget.id}/accounts",
        json={
            "name": "My Credit Card",
            "account_type": "credit_card",
        },
    )
    assert response.status_code == 201
    account_id = response.json()["id"]

    # Verify the linked envelope was created
    result = await session.execute(
        select(Envelope).where(
            Envelope.budget_id == budget.id,
            Envelope.linked_account_id == account_id,
        )
    )
    linked_envelope = result.scalar_one_or_none()
    assert linked_envelope is not None
    assert linked_envelope.name == "My Credit Card"


async def test_create_non_credit_card_account_does_not_create_envelope(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,
) -> None:
    """Creating a non-CC account should not create a linked envelope."""
    result = await session.execute(
        select(Budget).where(Budget.owner_id == test_user.id)
    )
    budget = result.scalar_one()

    response = await authenticated_client.post(
        f"/api/v1/budgets/{budget.id}/accounts",
        json={
            "name": "My Checking",
            "account_type": "checking",
        },
    )
    assert response.status_code == 201
    account_id = response.json()["id"]

    # Verify no linked envelope was created
    result = await session.execute(
        select(Envelope).where(
            Envelope.budget_id == budget.id,
            Envelope.linked_account_id == account_id,
        )
    )
    linked_envelope = result.scalar_one_or_none()
    assert linked_envelope is None


async def test_delete_credit_card_account_deletes_linked_envelope(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,
) -> None:
    """Deleting a credit card account should cascade delete the linked envelope."""
    result = await session.execute(
        select(Budget).where(Budget.owner_id == test_user.id)
    )
    budget = result.scalar_one()

    # Create a CC account
    response = await authenticated_client.post(
        f"/api/v1/budgets/{budget.id}/accounts",
        json={
            "name": "Delete CC Test",
            "account_type": "credit_card",
        },
    )
    assert response.status_code == 201
    account_id = response.json()["id"]

    # Verify the linked envelope exists
    result = await session.execute(
        select(Envelope).where(Envelope.linked_account_id == account_id)
    )
    linked_envelope = result.scalar_one()
    envelope_id = linked_envelope.id

    # Delete the account
    response = await authenticated_client.delete(
        f"/api/v1/budgets/{budget.id}/accounts/{account_id}"
    )
    assert response.status_code == 204

    # Verify the linked envelope was also deleted
    result = await session.execute(select(Envelope).where(Envelope.id == envelope_id))
    assert result.scalar_one_or_none() is None


# Account Type Change Tests


async def test_change_account_type_to_credit_card_creates_envelope(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,
) -> None:
    """Changing account type to credit_card should create linked envelope."""
    result = await session.execute(
        select(Budget).where(Budget.owner_id == test_user.id)
    )
    budget = result.scalar_one()

    # Create a checking account
    account = Account(
        budget_id=budget.id,
        name="To Be Credit Card",
        account_type=AccountType.CHECKING,
    )
    session.add(account)
    await session.flush()

    # Verify no linked envelope exists
    result = await session.execute(
        select(Envelope).where(Envelope.linked_account_id == account.id)
    )
    assert result.scalar_one_or_none() is None

    # Change type to credit_card
    response = await authenticated_client.patch(
        f"/api/v1/budgets/{budget.id}/accounts/{account.id}",
        json={"account_type": "credit_card"},
    )
    assert response.status_code == 200

    # Verify linked envelope was created
    result = await session.execute(
        select(Envelope).where(Envelope.linked_account_id == account.id)
    )
    linked_envelope = result.scalar_one()
    assert linked_envelope.name == "To Be Credit Card"


async def test_change_account_type_from_credit_card_deletes_envelope(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,
) -> None:
    """Changing account type from credit_card should delete linked envelope."""
    result = await session.execute(
        select(Budget).where(Budget.owner_id == test_user.id)
    )
    budget = result.scalar_one()

    # Create a credit card account (which auto-creates envelope)
    response = await authenticated_client.post(
        f"/api/v1/budgets/{budget.id}/accounts",
        json={
            "name": "Was Credit Card",
            "account_type": "credit_card",
        },
    )
    assert response.status_code == 201
    account_id = response.json()["id"]

    # Verify linked envelope exists
    result = await session.execute(
        select(Envelope).where(Envelope.linked_account_id == account_id)
    )
    envelope = result.scalar_one()
    envelope_id = envelope.id

    # Change type to checking
    response = await authenticated_client.patch(
        f"/api/v1/budgets/{budget.id}/accounts/{account_id}",
        json={"account_type": "checking"},
    )
    assert response.status_code == 200

    # Verify linked envelope was deleted
    result = await session.execute(select(Envelope).where(Envelope.id == envelope_id))
    assert result.scalar_one_or_none() is None


async def test_rename_credit_card_account_renames_envelope(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,
) -> None:
    """Renaming a credit card account should also rename its linked envelope."""
    result = await session.execute(
        select(Budget).where(Budget.owner_id == test_user.id)
    )
    budget = result.scalar_one()

    # Create a credit card account
    response = await authenticated_client.post(
        f"/api/v1/budgets/{budget.id}/accounts",
        json={
            "name": "Old CC Name",
            "account_type": "credit_card",
        },
    )
    assert response.status_code == 201
    account_id = response.json()["id"]

    # Rename the account
    response = await authenticated_client.patch(
        f"/api/v1/budgets/{budget.id}/accounts/{account_id}",
        json={"name": "New CC Name"},
    )
    assert response.status_code == 200

    # Verify envelope was also renamed
    result = await session.execute(
        select(Envelope).where(Envelope.linked_account_id == account_id)
    )
    envelope = result.scalar_one()
    assert envelope.name == "New CC Name"


async def test_change_to_credit_card_fails_if_envelope_name_exists(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,
) -> None:
    """Type change to CC should fail if envelope with same name exists."""
    result = await session.execute(
        select(Budget).where(Budget.owner_id == test_user.id)
    )
    budget = result.scalar_one()

    # Create a checking account
    account = Account(
        budget_id=budget.id,
        name="Conflicting Name",
        account_type=AccountType.CHECKING,
    )
    session.add(account)

    # Create an envelope with the same name
    envelope = Envelope(
        budget_id=budget.id,
        name="Conflicting Name",
    )
    session.add(envelope)
    await session.flush()

    # Try to change type to credit_card
    response = await authenticated_client.patch(
        f"/api/v1/budgets/{budget.id}/accounts/{account.id}",
        json={"account_type": "credit_card"},
    )
    assert response.status_code == 409
    assert "already exists" in response.json()["detail"].lower()


async def test_rename_credit_card_fails_if_envelope_name_exists(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,
) -> None:
    """Renaming CC account should fail if envelope with new name exists."""
    result = await session.execute(
        select(Budget).where(Budget.owner_id == test_user.id)
    )
    budget = result.scalar_one()

    # Create a credit card account
    response = await authenticated_client.post(
        f"/api/v1/budgets/{budget.id}/accounts",
        json={
            "name": "My Credit Card",
            "account_type": "credit_card",
        },
    )
    assert response.status_code == 201
    account_id = response.json()["id"]

    # Create an envelope with a different name
    envelope = Envelope(
        budget_id=budget.id,
        name="Taken Name",
    )
    session.add(envelope)
    await session.flush()

    # Try to rename to the taken name
    response = await authenticated_client.patch(
        f"/api/v1/budgets/{budget.id}/accounts/{account_id}",
        json={"name": "Taken Name"},
    )
    assert response.status_code == 409
