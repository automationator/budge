from datetime import date

from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.accounts.models import Account, AccountType
from src.auth.service import create_access_token
from src.budgets.models import Budget, BudgetMembership, BudgetRole
from src.locations.models import Location
from src.payees.models import Payee
from src.transactions.models import Transaction, TransactionType
from src.users.models import User


async def test_create_transaction(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,
) -> None:
    result = await session.execute(
        select(Budget).where(Budget.owner_id == test_user.id)
    )
    budget = result.scalar_one()

    # Create account (non-budget to skip allocation requirement) and payee
    account = Account(
        budget_id=budget.id,
        name="Checking",
        account_type=AccountType.CHECKING,
        include_in_budget=False,
    )
    payee = Payee(budget_id=budget.id, name="Test Payee")
    session.add(account)
    session.add(payee)
    await session.flush()

    response = await authenticated_client.post(
        f"/api/v1/budgets/{budget.id}/transactions",
        json={
            "account_id": str(account.id),
            "payee_id": str(payee.id),
            "date": "2024-01-15",
            "amount": 5000,
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["account_id"] == str(account.id)
    assert data["payee_id"] == str(payee.id)
    assert data["date"] == "2024-01-15"
    assert data["amount"] == 5000
    assert data["is_cleared"] is False
    assert data["memo"] is None
    assert data["location_id"] is None
    assert data["user_id"] is None
    assert data["budget_id"] == str(budget.id)
    assert data["allocations"] == []


async def test_create_transaction_with_all_fields(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,
) -> None:
    result = await session.execute(
        select(Budget).where(Budget.owner_id == test_user.id)
    )
    budget = result.scalar_one()

    # Create account (non-budget), payee and location
    account = Account(
        budget_id=budget.id,
        name="Credit Card",
        account_type=AccountType.CREDIT_CARD,
        include_in_budget=False,
    )
    payee = Payee(budget_id=budget.id, name="Full Test Payee")
    location = Location(budget_id=budget.id, name="Full Test Location")
    session.add(account)
    session.add(payee)
    session.add(location)
    await session.flush()

    response = await authenticated_client.post(
        f"/api/v1/budgets/{budget.id}/transactions",
        json={
            "account_id": str(account.id),
            "payee_id": str(payee.id),
            "location_id": str(location.id),
            "user_id": str(test_user.id),
            "date": "2024-02-20",
            "amount": -15000,
            "is_cleared": True,
            "memo": "Grocery shopping",
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["account_id"] == str(account.id)
    assert data["payee_id"] == str(payee.id)
    assert data["location_id"] == str(location.id)
    assert data["user_id"] == str(test_user.id)
    assert data["date"] == "2024-02-20"
    assert data["amount"] == -15000
    assert data["is_cleared"] is True
    assert data["memo"] == "Grocery shopping"
    assert data["allocations"] == []


async def test_list_transactions(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,
) -> None:
    result = await session.execute(
        select(Budget).where(Budget.owner_id == test_user.id)
    )
    budget = result.scalar_one()

    # Create account and payee
    account = Account(
        budget_id=budget.id, name="Savings", account_type=AccountType.SAVINGS
    )
    payee = Payee(budget_id=budget.id, name="List Test Payee")
    session.add(account)
    session.add(payee)
    await session.flush()

    # Create transactions with different dates
    transactions = [
        Transaction(
            budget_id=budget.id,
            account_id=account.id,
            payee_id=payee.id,
            date=date(2024, 1, 1),
            amount=1000,
        ),
        Transaction(
            budget_id=budget.id,
            account_id=account.id,
            payee_id=payee.id,
            date=date(2024, 1, 15),
            amount=2000,
        ),
        Transaction(
            budget_id=budget.id,
            account_id=account.id,
            payee_id=payee.id,
            date=date(2024, 1, 10),
            amount=3000,
        ),
    ]
    for txn in transactions:
        session.add(txn)
    await session.flush()

    response = await authenticated_client.get(
        f"/api/v1/budgets/{budget.id}/transactions"
    )
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "has_more" in data
    assert len(data["items"]) >= 3
    # Should be ordered by date descending (newest first)
    dates = [txn["date"] for txn in data["items"][:3]]
    assert dates == ["2024-01-15", "2024-01-10", "2024-01-01"]


async def test_list_transactions_with_limit(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,
) -> None:
    result = await session.execute(
        select(Budget).where(Budget.owner_id == test_user.id)
    )
    budget = result.scalar_one()

    account = Account(
        budget_id=budget.id, name="Limit Test", account_type=AccountType.CHECKING
    )
    payee = Payee(budget_id=budget.id, name="Limit Payee")
    session.add(account)
    session.add(payee)
    await session.flush()

    # Create 5 transactions
    for i in range(5):
        session.add(
            Transaction(
                budget_id=budget.id,
                account_id=account.id,
                payee_id=payee.id,
                date=date(2024, 1, i + 1),
                amount=1000 * (i + 1),
            )
        )
    await session.flush()

    response = await authenticated_client.get(
        f"/api/v1/budgets/{budget.id}/transactions", params={"limit": 3}
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) == 3
    assert data["has_more"] is True
    assert data["next_cursor"] is not None


async def test_list_transactions_cursor_pagination(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,
) -> None:
    result = await session.execute(
        select(Budget).where(Budget.owner_id == test_user.id)
    )
    budget = result.scalar_one()

    account = Account(
        budget_id=budget.id, name="Cursor Test", account_type=AccountType.CHECKING
    )
    payee = Payee(budget_id=budget.id, name="Cursor Payee")
    session.add(account)
    session.add(payee)
    await session.flush()

    # Create 10 transactions
    for i in range(10):
        session.add(
            Transaction(
                budget_id=budget.id,
                account_id=account.id,
                payee_id=payee.id,
                date=date(2024, 2, i + 1),
                amount=1000 * (i + 1),
            )
        )
    await session.flush()

    # Get first page
    response = await authenticated_client.get(
        f"/api/v1/budgets/{budget.id}/transactions", params={"limit": 3}
    )
    assert response.status_code == 200
    page1 = response.json()
    assert len(page1["items"]) == 3
    assert page1["has_more"] is True
    cursor = page1["next_cursor"]

    # Get second page
    response = await authenticated_client.get(
        f"/api/v1/budgets/{budget.id}/transactions",
        params={"limit": 3, "cursor": cursor},
    )
    assert response.status_code == 200
    page2 = response.json()
    assert len(page2["items"]) == 3
    assert page2["has_more"] is True

    # Ensure no overlap between pages
    page1_ids = {item["id"] for item in page1["items"]}
    page2_ids = {item["id"] for item in page2["items"]}
    assert page1_ids.isdisjoint(page2_ids)

    # Verify ordering is maintained (dates should be decreasing)
    all_dates = [item["date"] for item in page1["items"]] + [
        item["date"] for item in page2["items"]
    ]
    assert all_dates == sorted(all_dates, reverse=True)


async def test_list_transactions_account_filter(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,
) -> None:
    result = await session.execute(
        select(Budget).where(Budget.owner_id == test_user.id)
    )
    budget = result.scalar_one()

    account1 = Account(
        budget_id=budget.id, name="Account 1", account_type=AccountType.CHECKING
    )
    account2 = Account(
        budget_id=budget.id, name="Account 2", account_type=AccountType.SAVINGS
    )
    payee = Payee(budget_id=budget.id, name="Filter Payee")
    session.add(account1)
    session.add(account2)
    session.add(payee)
    await session.flush()

    # Create transactions in both accounts
    for i in range(3):
        session.add(
            Transaction(
                budget_id=budget.id,
                account_id=account1.id,
                payee_id=payee.id,
                date=date(2024, 3, i + 1),
                amount=1000,
            )
        )
        session.add(
            Transaction(
                budget_id=budget.id,
                account_id=account2.id,
                payee_id=payee.id,
                date=date(2024, 3, i + 1),
                amount=2000,
            )
        )
    await session.flush()

    # Filter by account1
    response = await authenticated_client.get(
        f"/api/v1/budgets/{budget.id}/transactions",
        params={"account_id": str(account1.id)},
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) == 3
    assert all(item["account_id"] == str(account1.id) for item in data["items"])
    assert all(item["amount"] == 1000 for item in data["items"])


async def test_list_transactions_filter_by_payee(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,
) -> None:
    """Test filtering transactions by payee_id."""
    result = await session.execute(
        select(Budget).where(Budget.owner_id == test_user.id)
    )
    budget = result.scalar_one()

    # Create account and two payees
    account = Account(
        budget_id=budget.id,
        name="Payee Filter Account",
        account_type=AccountType.CHECKING,
    )
    payee1 = Payee(budget_id=budget.id, name="Payee One")
    payee2 = Payee(budget_id=budget.id, name="Payee Two")
    session.add(account)
    session.add(payee1)
    session.add(payee2)
    await session.flush()

    # Create transactions for each payee
    for i in range(3):
        session.add(
            Transaction(
                budget_id=budget.id,
                account_id=account.id,
                payee_id=payee1.id,
                date=date(2024, 5, i + 1),
                amount=1000,
            )
        )
        session.add(
            Transaction(
                budget_id=budget.id,
                account_id=account.id,
                payee_id=payee2.id,
                date=date(2024, 5, i + 1),
                amount=2000,
            )
        )
    await session.flush()

    # Filter by payee1
    response = await authenticated_client.get(
        f"/api/v1/budgets/{budget.id}/transactions",
        params={"payee_id": str(payee1.id)},
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) == 3
    assert all(item["payee_id"] == str(payee1.id) for item in data["items"])
    assert all(item["amount"] == 1000 for item in data["items"])

    # Filter by payee2
    response = await authenticated_client.get(
        f"/api/v1/budgets/{budget.id}/transactions",
        params={"payee_id": str(payee2.id)},
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) == 3
    assert all(item["payee_id"] == str(payee2.id) for item in data["items"])
    assert all(item["amount"] == 2000 for item in data["items"])


async def test_list_transactions_filter_include_in_budget_true(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,
) -> None:
    """Test filtering transactions to only those in budget accounts."""
    result = await session.execute(
        select(Budget).where(Budget.owner_id == test_user.id)
    )
    budget = result.scalar_one()

    # Create budget and tracking accounts
    budget_account = Account(
        budget_id=budget.id,
        name="Budget Account",
        account_type=AccountType.CHECKING,
        include_in_budget=True,
    )
    tracking_account = Account(
        budget_id=budget.id,
        name="Tracking Account",
        account_type=AccountType.INVESTMENT,
        include_in_budget=False,
    )
    payee = Payee(budget_id=budget.id, name="Budget Filter Payee")
    session.add(budget_account)
    session.add(tracking_account)
    session.add(payee)
    await session.flush()

    # Create transactions in both accounts
    budget_txn = Transaction(
        budget_id=budget.id,
        account_id=budget_account.id,
        payee_id=payee.id,
        date=date(2024, 3, 1),
        amount=1000,
    )
    tracking_txn = Transaction(
        budget_id=budget.id,
        account_id=tracking_account.id,
        payee_id=payee.id,
        date=date(2024, 3, 2),
        amount=2000,
    )
    session.add(budget_txn)
    session.add(tracking_txn)
    await session.flush()

    # Filter by include_in_budget=true
    response = await authenticated_client.get(
        f"/api/v1/budgets/{budget.id}/transactions",
        params={"include_in_budget": True},
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) == 1
    assert data["items"][0]["id"] == str(budget_txn.id)
    assert data["items"][0]["account_id"] == str(budget_account.id)


async def test_list_transactions_filter_include_in_budget_false(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,
) -> None:
    """Test filtering transactions to only those in tracking (off-budget) accounts."""
    result = await session.execute(
        select(Budget).where(Budget.owner_id == test_user.id)
    )
    budget = result.scalar_one()

    # Create budget and tracking accounts
    budget_account = Account(
        budget_id=budget.id,
        name="Budget Account 2",
        account_type=AccountType.CHECKING,
        include_in_budget=True,
    )
    tracking_account = Account(
        budget_id=budget.id,
        name="Tracking Account 2",
        account_type=AccountType.INVESTMENT,
        include_in_budget=False,
    )
    payee = Payee(budget_id=budget.id, name="Tracking Filter Payee")
    session.add(budget_account)
    session.add(tracking_account)
    session.add(payee)
    await session.flush()

    # Create transactions in both accounts
    budget_txn = Transaction(
        budget_id=budget.id,
        account_id=budget_account.id,
        payee_id=payee.id,
        date=date(2024, 4, 1),
        amount=3000,
    )
    tracking_txn = Transaction(
        budget_id=budget.id,
        account_id=tracking_account.id,
        payee_id=payee.id,
        date=date(2024, 4, 2),
        amount=4000,
    )
    session.add(budget_txn)
    session.add(tracking_txn)
    await session.flush()

    # Filter by include_in_budget=false
    response = await authenticated_client.get(
        f"/api/v1/budgets/{budget.id}/transactions",
        params={"include_in_budget": False},
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) == 1
    assert data["items"][0]["id"] == str(tracking_txn.id)
    assert data["items"][0]["account_id"] == str(tracking_account.id)


async def test_list_transactions_empty(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,
) -> None:
    result = await session.execute(
        select(Budget).where(Budget.owner_id == test_user.id)
    )
    budget = result.scalar_one()

    response = await authenticated_client.get(
        f"/api/v1/budgets/{budget.id}/transactions"
    )
    assert response.status_code == 200
    data = response.json()
    assert data["items"] == []
    assert data["has_more"] is False
    assert data["next_cursor"] is None


async def test_list_transactions_invalid_cursor(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,
) -> None:
    result = await session.execute(
        select(Budget).where(Budget.owner_id == test_user.id)
    )
    budget = result.scalar_one()

    response = await authenticated_client.get(
        f"/api/v1/budgets/{budget.id}/transactions", params={"cursor": "invalid-cursor"}
    )
    assert response.status_code == 400


async def test_get_transaction(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,
) -> None:
    result = await session.execute(
        select(Budget).where(Budget.owner_id == test_user.id)
    )
    budget = result.scalar_one()

    # Create account, payee and transaction
    account = Account(budget_id=budget.id, name="Cash", account_type=AccountType.CASH)
    payee = Payee(budget_id=budget.id, name="Get Test Payee")
    session.add(account)
    session.add(payee)
    await session.flush()

    transaction = Transaction(
        budget_id=budget.id,
        account_id=account.id,
        payee_id=payee.id,
        date=date(2024, 3, 5),
        amount=7500,
        memo="Test memo",
    )
    session.add(transaction)
    await session.flush()

    response = await authenticated_client.get(
        f"/api/v1/budgets/{budget.id}/transactions/{transaction.id}"
    )
    assert response.status_code == 200
    data = response.json()
    assert data["amount"] == 7500
    assert data["memo"] == "Test memo"


async def test_get_transaction_not_found(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,
) -> None:
    result = await session.execute(
        select(Budget).where(Budget.owner_id == test_user.id)
    )
    budget = result.scalar_one()

    response = await authenticated_client.get(
        f"/api/v1/budgets/{budget.id}/transactions/00000000-0000-0000-0000-000000000000"
    )
    assert response.status_code == 404


async def test_update_transaction(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,
) -> None:
    result = await session.execute(
        select(Budget).where(Budget.owner_id == test_user.id)
    )
    budget = result.scalar_one()

    # Create account, payee and transaction
    account = Account(
        budget_id=budget.id, name="Update Account", account_type=AccountType.CHECKING
    )
    payee = Payee(budget_id=budget.id, name="Update Test Payee")
    session.add(account)
    session.add(payee)
    await session.flush()

    transaction = Transaction(
        budget_id=budget.id,
        account_id=account.id,
        payee_id=payee.id,
        date=date(2024, 4, 10),
        amount=10000,
    )
    session.add(transaction)
    await session.flush()

    response = await authenticated_client.patch(
        f"/api/v1/budgets/{budget.id}/transactions/{transaction.id}",
        json={"amount": 12000, "is_cleared": True, "memo": "Updated memo"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["amount"] == 12000
    assert data["is_cleared"] is True
    assert data["memo"] == "Updated memo"


async def test_delete_transaction(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,
) -> None:
    result = await session.execute(
        select(Budget).where(Budget.owner_id == test_user.id)
    )
    budget = result.scalar_one()

    # Create account, payee and transaction
    account = Account(
        budget_id=budget.id, name="Delete Account", account_type=AccountType.CHECKING
    )
    payee = Payee(budget_id=budget.id, name="Delete Test Payee")
    session.add(account)
    session.add(payee)
    await session.flush()

    transaction = Transaction(
        budget_id=budget.id,
        account_id=account.id,
        payee_id=payee.id,
        date=date(2024, 5, 1),
        amount=5000,
    )
    session.add(transaction)
    await session.flush()
    transaction_id = transaction.id

    response = await authenticated_client.delete(
        f"/api/v1/budgets/{budget.id}/transactions/{transaction_id}"
    )
    assert response.status_code == 204

    # Verify it's gone
    result = await session.execute(
        select(Transaction).where(Transaction.id == transaction_id)
    )
    assert result.scalar_one_or_none() is None


async def test_delete_transaction_not_found(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,
) -> None:
    result = await session.execute(
        select(Budget).where(Budget.owner_id == test_user.id)
    )
    budget = result.scalar_one()

    response = await authenticated_client.delete(
        f"/api/v1/budgets/{budget.id}/transactions/00000000-0000-0000-0000-000000000000"
    )
    assert response.status_code == 404


async def test_transaction_unauthorized(client: AsyncClient) -> None:
    response = await client.get(
        "/api/v1/budgets/00000000-0000-0000-0000-000000000000/transactions"
    )
    assert response.status_code == 401


async def test_transaction_not_budget_member(
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

    response = await client.get(f"/api/v1/budgets/{budget.id}/transactions")
    assert response.status_code == 403


async def test_member_can_create_transaction(
    client: AsyncClient,
    session: AsyncSession,
    test_user: User,
    test_user2: User,
) -> None:
    result = await session.execute(
        select(Budget).where(Budget.owner_id == test_user.id)
    )
    budget = result.scalar_one()

    # Create account (non-budget) and payee
    account = Account(
        budget_id=budget.id,
        name="Member Account",
        account_type=AccountType.CHECKING,
        include_in_budget=False,
    )
    payee = Payee(budget_id=budget.id, name="Member Create Payee")
    session.add(account)
    session.add(payee)

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
        f"/api/v1/budgets/{budget.id}/transactions",
        json={
            "account_id": str(account.id),
            "payee_id": str(payee.id),
            "date": "2024-06-01",
            "amount": 3000,
        },
    )
    assert response.status_code == 201


async def test_member_can_update_transaction(
    client: AsyncClient,
    session: AsyncSession,
    test_user: User,
    test_user2: User,
) -> None:
    result = await session.execute(
        select(Budget).where(Budget.owner_id == test_user.id)
    )
    budget = result.scalar_one()

    # Create account, payee and transaction
    account = Account(
        budget_id=budget.id,
        name="Member Update Account",
        account_type=AccountType.CHECKING,
    )
    payee = Payee(budget_id=budget.id, name="Member Update Payee")
    session.add(account)
    session.add(payee)
    await session.flush()

    transaction = Transaction(
        budget_id=budget.id,
        account_id=account.id,
        payee_id=payee.id,
        date=date(2024, 6, 15),
        amount=4000,
    )
    session.add(transaction)

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

    response = await client.patch(
        f"/api/v1/budgets/{budget.id}/transactions/{transaction.id}",
        json={"amount": 4500},
    )
    assert response.status_code == 200


async def test_member_cannot_delete_transaction(
    client: AsyncClient,
    session: AsyncSession,
    test_user: User,
    test_user2: User,
) -> None:
    result = await session.execute(
        select(Budget).where(Budget.owner_id == test_user.id)
    )
    budget = result.scalar_one()

    # Create account, payee and transaction
    account = Account(
        budget_id=budget.id,
        name="Member Delete Account",
        account_type=AccountType.CHECKING,
    )
    payee = Payee(budget_id=budget.id, name="Member Delete Payee")
    session.add(account)
    session.add(payee)
    await session.flush()

    transaction = Transaction(
        budget_id=budget.id,
        account_id=account.id,
        payee_id=payee.id,
        date=date(2024, 7, 1),
        amount=6000,
    )
    session.add(transaction)

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

    response = await client.delete(
        f"/api/v1/budgets/{budget.id}/transactions/{transaction.id}"
    )
    assert response.status_code == 403


async def test_admin_can_create_transaction(
    client: AsyncClient,
    session: AsyncSession,
    test_user: User,
    test_user2: User,
) -> None:
    result = await session.execute(
        select(Budget).where(Budget.owner_id == test_user.id)
    )
    budget = result.scalar_one()

    # Create account (non-budget) and payee
    account = Account(
        budget_id=budget.id,
        name="Admin Account",
        account_type=AccountType.CHECKING,
        include_in_budget=False,
    )
    payee = Payee(budget_id=budget.id, name="Admin Create Payee")
    session.add(account)
    session.add(payee)

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
        f"/api/v1/budgets/{budget.id}/transactions",
        json={
            "account_id": str(account.id),
            "payee_id": str(payee.id),
            "date": "2024-08-01",
            "amount": 8000,
        },
    )
    assert response.status_code == 201


async def test_admin_cannot_delete_transaction(
    client: AsyncClient,
    session: AsyncSession,
    test_user: User,
    test_user2: User,
) -> None:
    result = await session.execute(
        select(Budget).where(Budget.owner_id == test_user.id)
    )
    budget = result.scalar_one()

    # Create account, payee and transaction
    account = Account(
        budget_id=budget.id,
        name="Admin Delete Account",
        account_type=AccountType.CHECKING,
    )
    payee = Payee(budget_id=budget.id, name="Admin Delete Payee")
    session.add(account)
    session.add(payee)
    await session.flush()

    transaction = Transaction(
        budget_id=budget.id,
        account_id=account.id,
        payee_id=payee.id,
        date=date(2024, 8, 15),
        amount=9000,
    )
    session.add(transaction)

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

    response = await client.delete(
        f"/api/v1/budgets/{budget.id}/transactions/{transaction.id}"
    )
    assert response.status_code == 403


async def test_viewer_can_read_transactions(
    client: AsyncClient,
    session: AsyncSession,
    test_user: User,
    test_user2: User,
) -> None:
    result = await session.execute(
        select(Budget).where(Budget.owner_id == test_user.id)
    )
    budget = result.scalar_one()

    # Add test_user2 as a viewer
    membership = BudgetMembership(
        user_id=test_user2.id,
        budget_id=budget.id,
        role=BudgetRole.VIEWER,
    )
    session.add(membership)
    await session.flush()

    # Authenticate as test_user2
    token = create_access_token(test_user2.id)
    client.headers["Authorization"] = f"Bearer {token}"

    response = await client.get(f"/api/v1/budgets/{budget.id}/transactions")
    assert response.status_code == 200


async def test_viewer_cannot_create_transaction(
    client: AsyncClient,
    session: AsyncSession,
    test_user: User,
    test_user2: User,
) -> None:
    result = await session.execute(
        select(Budget).where(Budget.owner_id == test_user.id)
    )
    budget = result.scalar_one()

    # Create account and payee
    account = Account(
        budget_id=budget.id, name="Viewer Account", account_type=AccountType.CHECKING
    )
    payee = Payee(budget_id=budget.id, name="Viewer Create Payee")
    session.add(account)
    session.add(payee)

    # Add test_user2 as a viewer
    membership = BudgetMembership(
        user_id=test_user2.id,
        budget_id=budget.id,
        role=BudgetRole.VIEWER,
    )
    session.add(membership)
    await session.flush()

    # Authenticate as test_user2
    token = create_access_token(test_user2.id)
    client.headers["Authorization"] = f"Bearer {token}"

    response = await client.post(
        f"/api/v1/budgets/{budget.id}/transactions",
        json={
            "account_id": str(account.id),
            "payee_id": str(payee.id),
            "date": "2024-09-01",
            "amount": 1000,
        },
    )
    assert response.status_code == 403


async def test_cannot_access_other_budget_transactions(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,
    test_user2: User,
) -> None:
    # Get test_user's budget
    result = await session.execute(
        select(Budget).where(Budget.owner_id == test_user.id)
    )
    budget1 = result.scalar_one()

    # Create a budget for test_user2
    budget2 = Budget(name="Other Budget", owner_id=test_user2.id)
    session.add(budget2)
    await session.flush()

    membership = BudgetMembership(
        user_id=test_user2.id,
        budget_id=budget2.id,
        role=BudgetRole.OWNER,
    )
    session.add(membership)

    # Create account, payee and transaction in budget2
    account = Account(
        budget_id=budget2.id, name="Other Account", account_type=AccountType.CHECKING
    )
    payee = Payee(budget_id=budget2.id, name="Other Budget Payee")
    session.add(account)
    session.add(payee)
    await session.flush()

    transaction = Transaction(
        budget_id=budget2.id,
        account_id=account.id,
        payee_id=payee.id,
        date=date(2024, 10, 1),
        amount=5000,
    )
    session.add(transaction)
    await session.flush()

    # Try to access budget2's transactions from test_user (authenticated_client is test_user)
    response = await authenticated_client.get(
        f"/api/v1/budgets/{budget2.id}/transactions"
    )
    assert response.status_code == 403

    # Try to get specific transaction
    response = await authenticated_client.get(
        f"/api/v1/budgets/{budget1.id}/transactions/{transaction.id}"
    )
    assert response.status_code == 404


# Transaction type validation tests


async def test_create_standard_transaction_requires_payee(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,
) -> None:
    """Standard transactions must have a payee_id."""
    result = await session.execute(
        select(Budget).where(Budget.owner_id == test_user.id)
    )
    budget = result.scalar_one()

    account = Account(
        budget_id=budget.id, name="Standard No Payee", account_type=AccountType.CHECKING
    )
    session.add(account)
    await session.flush()

    response = await authenticated_client.post(
        f"/api/v1/budgets/{budget.id}/transactions",
        json={
            "account_id": str(account.id),
            "date": "2024-01-15",
            "amount": 5000,
            "transaction_type": "standard",
            # No payee_id
        },
    )
    assert response.status_code == 422
    assert "payee_id is required" in response.json()["detail"][0]["msg"]


async def test_create_adjustment_transaction_rejects_payee(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,
) -> None:
    """Adjustment transactions must not have a payee_id."""
    result = await session.execute(
        select(Budget).where(Budget.owner_id == test_user.id)
    )
    budget = result.scalar_one()

    account = Account(
        budget_id=budget.id,
        name="Adjustment With Payee",
        account_type=AccountType.CHECKING,
    )
    payee = Payee(budget_id=budget.id, name="Should Not Use")
    session.add(account)
    session.add(payee)
    await session.flush()

    response = await authenticated_client.post(
        f"/api/v1/budgets/{budget.id}/transactions",
        json={
            "account_id": str(account.id),
            "payee_id": str(payee.id),  # Should not be allowed
            "date": "2024-01-15",
            "amount": 5000,
            "transaction_type": "adjustment",
        },
    )
    assert response.status_code == 422
    assert "payee_id must be null" in response.json()["detail"][0]["msg"]


async def test_create_adjustment_transaction_without_payee(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,
) -> None:
    """Adjustment transactions can be created without a payee_id."""
    result = await session.execute(
        select(Budget).where(Budget.owner_id == test_user.id)
    )
    budget = result.scalar_one()

    account = Account(
        budget_id=budget.id, name="Valid Adjustment", account_type=AccountType.CHECKING
    )
    session.add(account)
    await session.flush()

    response = await authenticated_client.post(
        f"/api/v1/budgets/{budget.id}/transactions",
        json={
            "account_id": str(account.id),
            "date": "2024-01-15",
            "amount": 5000,
            "transaction_type": "adjustment",
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["transaction_type"] == "adjustment"
    assert data["payee_id"] is None


async def test_transaction_response_includes_type(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,
) -> None:
    """Transaction responses should include transaction_type."""
    result = await session.execute(
        select(Budget).where(Budget.owner_id == test_user.id)
    )
    budget = result.scalar_one()

    account = Account(
        budget_id=budget.id,
        name="Type Response",
        account_type=AccountType.CHECKING,
        include_in_budget=False,
    )
    payee = Payee(budget_id=budget.id, name="Type Test Payee")
    session.add(account)
    session.add(payee)
    await session.flush()

    response = await authenticated_client.post(
        f"/api/v1/budgets/{budget.id}/transactions",
        json={
            "account_id": str(account.id),
            "payee_id": str(payee.id),
            "date": "2024-01-15",
            "amount": 5000,
        },
    )
    assert response.status_code == 201
    data = response.json()
    # Default type should be standard
    assert data["transaction_type"] == "standard"
    assert data["allocations"] == []


async def test_list_transactions_includes_type(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,
) -> None:
    """Listed transactions should include transaction_type."""
    result = await session.execute(
        select(Budget).where(Budget.owner_id == test_user.id)
    )
    budget = result.scalar_one()

    account = Account(
        budget_id=budget.id, name="List Type Test", account_type=AccountType.CHECKING
    )
    payee = Payee(budget_id=budget.id, name="List Type Payee")
    session.add(account)
    session.add(payee)
    await session.flush()

    # Create a standard transaction
    transaction = Transaction(
        budget_id=budget.id,
        account_id=account.id,
        payee_id=payee.id,
        date=date(2024, 1, 1),
        amount=1000,
        transaction_type=TransactionType.STANDARD,
    )
    session.add(transaction)

    # Create an adjustment transaction
    adjustment = Transaction(
        budget_id=budget.id,
        account_id=account.id,
        payee_id=None,
        date=date(2024, 1, 2),
        amount=500,
        transaction_type=TransactionType.ADJUSTMENT,
    )
    session.add(adjustment)
    await session.flush()

    response = await authenticated_client.get(
        f"/api/v1/budgets/{budget.id}/transactions"
    )
    assert response.status_code == 200
    data = response.json()

    # Find our transactions in the response
    types = {item["transaction_type"] for item in data["items"]}
    assert "standard" in types
    assert "adjustment" in types


# Credit Card Transaction Tests


async def test_cc_spending_creates_envelope_move(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,
) -> None:
    """Spending on a credit card should move money from the expense envelope to CC envelope."""
    from src.envelopes.models import Envelope

    result = await session.execute(
        select(Budget).where(Budget.owner_id == test_user.id)
    )
    budget = result.scalar_one()

    # Create a CC account (which auto-creates the linked envelope)
    response = await authenticated_client.post(
        f"/api/v1/budgets/{budget.id}/accounts",
        json={
            "name": "CC Spending Test",
            "account_type": "credit_card",
        },
    )
    assert response.status_code == 201
    cc_account_id = response.json()["id"]

    # Get the linked CC envelope
    result = await session.execute(
        select(Envelope).where(Envelope.linked_account_id == cc_account_id)
    )
    cc_envelope = result.scalar_one()

    # Create a regular envelope for groceries
    response = await authenticated_client.post(
        f"/api/v1/budgets/{budget.id}/envelopes",
        json={"name": "Groceries"},
    )
    assert response.status_code == 201
    groceries_envelope_id = response.json()["id"]

    # Set some balance in the groceries envelope
    result = await session.execute(
        select(Envelope).where(Envelope.id == groceries_envelope_id)
    )
    groceries_envelope = result.scalar_one()
    groceries_envelope.current_balance = 10000  # $100
    await session.flush()

    # Create a payee
    payee = Payee(budget_id=budget.id, name="Grocery Store")
    session.add(payee)
    await session.flush()

    # Create a CC spending transaction (expense)
    response = await authenticated_client.post(
        f"/api/v1/budgets/{budget.id}/transactions",
        json={
            "account_id": cc_account_id,
            "payee_id": str(payee.id),
            "date": "2024-01-15",
            "amount": -5000,  # $50 expense
            "allocations": [
                {"envelope_id": groceries_envelope_id, "amount": -5000},
            ],
        },
    )
    assert response.status_code == 201

    # Refresh envelopes to see updated balances
    await session.refresh(groceries_envelope)
    await session.refresh(cc_envelope)

    # Groceries should be reduced by $50
    assert groceries_envelope.current_balance == 5000  # $100 - $50

    # CC envelope should be increased by $50
    assert cc_envelope.current_balance == 5000  # $0 + $50


async def test_cc_payment_reduces_cc_envelope(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,
) -> None:
    """Paying a credit card should reduce the CC envelope balance."""
    from src.envelopes.models import Envelope

    result = await session.execute(
        select(Budget).where(Budget.owner_id == test_user.id)
    )
    budget = result.scalar_one()

    # Create a checking account
    checking = Account(
        budget_id=budget.id,
        name="Checking Payment Test",
        account_type=AccountType.CHECKING,
        include_in_budget=True,
        cleared_balance=50000,  # $500
    )
    session.add(checking)
    await session.flush()

    # Create a CC account (which auto-creates the linked envelope)
    response = await authenticated_client.post(
        f"/api/v1/budgets/{budget.id}/accounts",
        json={
            "name": "CC Payment Test",
            "account_type": "credit_card",
        },
    )
    assert response.status_code == 201
    cc_account_id = response.json()["id"]

    # Get the linked CC envelope and set a balance
    result = await session.execute(
        select(Envelope).where(Envelope.linked_account_id == cc_account_id)
    )
    cc_envelope = result.scalar_one()
    cc_envelope.current_balance = 10000  # $100 ready to pay
    await session.flush()

    # Make a CC payment (transfer from checking to CC)
    response = await authenticated_client.post(
        f"/api/v1/budgets/{budget.id}/transactions/transfers",
        json={
            "source_account_id": str(checking.id),
            "destination_account_id": cc_account_id,
            "date": "2024-01-15",
            "amount": 5000,  # $50 payment
        },
    )
    assert response.status_code == 201

    # Refresh to see updated balance
    await session.refresh(cc_envelope)

    # CC envelope should be reduced by the payment amount
    assert cc_envelope.current_balance == 5000  # $100 - $50


async def test_cc_payment_caps_at_envelope_balance(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,
) -> None:
    """CC payment that exceeds envelope balance should only reduce to $0."""
    from src.envelopes.models import Envelope

    result = await session.execute(
        select(Budget).where(Budget.owner_id == test_user.id)
    )
    budget = result.scalar_one()

    # Create a checking account
    checking = Account(
        budget_id=budget.id,
        name="Checking Overpay Test",
        account_type=AccountType.CHECKING,
        include_in_budget=True,
        cleared_balance=50000,  # $500
    )
    session.add(checking)
    await session.flush()

    # Create a CC account
    response = await authenticated_client.post(
        f"/api/v1/budgets/{budget.id}/accounts",
        json={
            "name": "CC Overpay Test",
            "account_type": "credit_card",
        },
    )
    assert response.status_code == 201
    cc_account_id = response.json()["id"]

    # Get the linked CC envelope and set a small balance
    result = await session.execute(
        select(Envelope).where(Envelope.linked_account_id == cc_account_id)
    )
    cc_envelope = result.scalar_one()
    cc_envelope.current_balance = 2000  # $20 ready to pay
    await session.flush()

    # Make a larger CC payment ($50, but only $20 in envelope)
    response = await authenticated_client.post(
        f"/api/v1/budgets/{budget.id}/transactions/transfers",
        json={
            "source_account_id": str(checking.id),
            "destination_account_id": cc_account_id,
            "date": "2024-01-15",
            "amount": 5000,  # $50 payment
        },
    )
    assert response.status_code == 201

    # Refresh to see updated balance
    await session.refresh(cc_envelope)

    # CC envelope should be $0 (not negative)
    assert cc_envelope.current_balance == 0


async def test_update_cc_spending_preserves_cc_envelope_allocation(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,
) -> None:
    """Updating a CC spending transaction should preserve the CC envelope allocation.

    This tests the bug fix where updating allocations on a CC transaction
    would lose the CC envelope allocation, causing Ready to Assign to inflate.
    """
    from src.envelopes.models import Envelope

    result = await session.execute(
        select(Budget).where(Budget.owner_id == test_user.id)
    )
    budget = result.scalar_one()

    # Create a CC account (which auto-creates the linked envelope)
    response = await authenticated_client.post(
        f"/api/v1/budgets/{budget.id}/accounts",
        json={
            "name": "CC Update Test",
            "account_type": "credit_card",
        },
    )
    assert response.status_code == 201
    cc_account_id = response.json()["id"]

    # Get the linked CC envelope
    result = await session.execute(
        select(Envelope).where(Envelope.linked_account_id == cc_account_id)
    )
    cc_envelope = result.scalar_one()

    # Create two regular envelopes
    response = await authenticated_client.post(
        f"/api/v1/budgets/{budget.id}/envelopes",
        json={"name": "Groceries Update"},
    )
    assert response.status_code == 201
    groceries_envelope_id = response.json()["id"]

    response = await authenticated_client.post(
        f"/api/v1/budgets/{budget.id}/envelopes",
        json={"name": "Dining Update"},
    )
    assert response.status_code == 201
    dining_envelope_id = response.json()["id"]

    # Set initial balances in envelopes
    result = await session.execute(
        select(Envelope).where(Envelope.id == groceries_envelope_id)
    )
    groceries_envelope = result.scalar_one()
    groceries_envelope.current_balance = 10000  # $100

    result = await session.execute(
        select(Envelope).where(Envelope.id == dining_envelope_id)
    )
    dining_envelope = result.scalar_one()
    dining_envelope.current_balance = 5000  # $50
    await session.flush()

    # Create a payee
    payee = Payee(budget_id=budget.id, name="Restaurant Update")
    session.add(payee)
    await session.flush()

    # Create a CC spending transaction (expense)
    response = await authenticated_client.post(
        f"/api/v1/budgets/{budget.id}/transactions",
        json={
            "account_id": cc_account_id,
            "payee_id": str(payee.id),
            "date": "2024-01-15",
            "amount": -3000,  # $30 expense
            "allocations": [
                {"envelope_id": groceries_envelope_id, "amount": -3000},
            ],
        },
    )
    assert response.status_code == 201
    txn_id = response.json()["id"]

    # Verify initial state
    await session.refresh(groceries_envelope)
    await session.refresh(cc_envelope)
    assert groceries_envelope.current_balance == 7000  # $100 - $30
    assert cc_envelope.current_balance == 3000  # $0 + $30

    # Now UPDATE the transaction to change the envelope from Groceries to Dining
    response = await authenticated_client.patch(
        f"/api/v1/budgets/{budget.id}/transactions/{txn_id}",
        json={
            "allocations": [
                {"envelope_id": dining_envelope_id, "amount": -3000},
            ],
        },
    )
    assert response.status_code == 200

    # Refresh all envelopes
    await session.refresh(groceries_envelope)
    await session.refresh(dining_envelope)
    await session.refresh(cc_envelope)

    # Groceries should be restored to $100 (allocation removed)
    assert groceries_envelope.current_balance == 10000

    # Dining should be reduced to $20 (new allocation)
    assert dining_envelope.current_balance == 2000  # $50 - $30

    # CC envelope should STILL be $30 (the bug would have reset this to $0)
    assert cc_envelope.current_balance == 3000


async def test_cc_refund_creates_envelope_moves(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,
) -> None:
    """A refund on a credit card should create paired envelope moves.

    When a positive amount (refund) is posted to a CC account, it should
    increase the target envelope and decrease the CC envelope, keeping the
    net envelope change at zero so Ready to Assign is unaffected.
    """
    from src.envelopes.models import Envelope

    result = await session.execute(
        select(Budget).where(Budget.owner_id == test_user.id)
    )
    budget = result.scalar_one()

    # Create a CC account (which auto-creates the linked envelope)
    response = await authenticated_client.post(
        f"/api/v1/budgets/{budget.id}/accounts",
        json={
            "name": "CC Refund Test",
            "account_type": "credit_card",
        },
    )
    assert response.status_code == 201
    cc_account_id = response.json()["id"]

    # Get the linked CC envelope and set a balance (simulating prior spending)
    result = await session.execute(
        select(Envelope).where(Envelope.linked_account_id == cc_account_id)
    )
    cc_envelope = result.scalar_one()
    cc_envelope.current_balance = 10000  # $100 from prior spending
    await session.flush()

    # Create a regular envelope for groceries
    response = await authenticated_client.post(
        f"/api/v1/budgets/{budget.id}/envelopes",
        json={"name": "Groceries Refund"},
    )
    assert response.status_code == 201
    groceries_envelope_id = response.json()["id"]

    result = await session.execute(
        select(Envelope).where(Envelope.id == groceries_envelope_id)
    )
    groceries_envelope = result.scalar_one()
    groceries_envelope.current_balance = 5000  # $50
    await session.flush()

    # Create a payee
    payee = Payee(budget_id=budget.id, name="Grocery Store Refund")
    session.add(payee)
    await session.flush()

    # Create a CC refund transaction (positive amount)
    response = await authenticated_client.post(
        f"/api/v1/budgets/{budget.id}/transactions",
        json={
            "account_id": cc_account_id,
            "payee_id": str(payee.id),
            "date": "2024-01-15",
            "amount": 3000,  # $30 refund
            "allocations": [
                {"envelope_id": groceries_envelope_id, "amount": 3000},
            ],
        },
    )
    assert response.status_code == 201

    # Refresh envelopes to see updated balances
    await session.refresh(groceries_envelope)
    await session.refresh(cc_envelope)

    # Groceries should increase by $30 (refund restores the envelope)
    assert groceries_envelope.current_balance == 8000  # $50 + $30

    # CC envelope should decrease by $30 (refund reduces CC debt tracking)
    assert cc_envelope.current_balance == 7000  # $100 - $30


async def test_cc_refund_with_allocation_rules(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,
) -> None:
    """CC refund with apply_allocation_rules should create paired envelope moves."""
    from src.allocation_rules.models import AllocationRule, AllocationRuleType
    from src.envelopes.models import Envelope

    result = await session.execute(
        select(Budget).where(Budget.owner_id == test_user.id)
    )
    budget = result.scalar_one()

    # Create a CC account
    response = await authenticated_client.post(
        f"/api/v1/budgets/{budget.id}/accounts",
        json={
            "name": "CC Auto-Distribute Test",
            "account_type": "credit_card",
        },
    )
    assert response.status_code == 201
    cc_account_id = response.json()["id"]

    # Get the linked CC envelope and set a balance
    result = await session.execute(
        select(Envelope).where(Envelope.linked_account_id == cc_account_id)
    )
    cc_envelope = result.scalar_one()
    cc_envelope.current_balance = 10000  # $100
    await session.flush()

    # Create a target envelope
    response = await authenticated_client.post(
        f"/api/v1/budgets/{budget.id}/envelopes",
        json={"name": "Savings Auto"},
    )
    assert response.status_code == 201
    savings_envelope_id = response.json()["id"]

    result = await session.execute(
        select(Envelope).where(Envelope.id == savings_envelope_id)
    )
    savings_envelope = result.scalar_one()

    # Create an allocation rule that directs all income to savings
    rule = AllocationRule(
        budget_id=budget.id,
        envelope_id=savings_envelope.id,
        priority=1,
        rule_type=AllocationRuleType.REMAINDER,
        amount=10000,  # 100% weight
        is_active=True,
    )
    session.add(rule)

    # Create a payee (required for standard transactions)
    payee = Payee(budget_id=budget.id, name="Refund Store Auto")
    session.add(payee)
    await session.flush()

    # Create a CC refund with auto-distribution
    response = await authenticated_client.post(
        f"/api/v1/budgets/{budget.id}/transactions",
        json={
            "account_id": cc_account_id,
            "payee_id": str(payee.id),
            "date": "2024-01-15",
            "amount": 5000,  # $50 refund
            "apply_allocation_rules": True,
        },
    )
    assert response.status_code == 201

    await session.refresh(savings_envelope)
    await session.refresh(cc_envelope)

    # Savings should increase by $50 (auto-distributed refund)
    assert savings_envelope.current_balance == 5000  # $0 + $50

    # CC envelope should decrease by $50
    assert cc_envelope.current_balance == 5000  # $100 - $50


async def test_cc_refund_no_rules_falls_back_to_unallocated(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,
) -> None:
    """CC refund with no allocation rules should create paired moves with Unallocated."""
    from src.allocations.models import Allocation
    from src.envelopes.models import Envelope

    result = await session.execute(
        select(Budget).where(Budget.owner_id == test_user.id)
    )
    budget = result.scalar_one()

    # Create a CC account
    response = await authenticated_client.post(
        f"/api/v1/budgets/{budget.id}/accounts",
        json={
            "name": "CC No Rules Test",
            "account_type": "credit_card",
        },
    )
    assert response.status_code == 201
    cc_account_id = response.json()["id"]

    # Get the linked CC envelope and set a balance
    result = await session.execute(
        select(Envelope).where(Envelope.linked_account_id == cc_account_id)
    )
    cc_envelope = result.scalar_one()
    cc_envelope.current_balance = 10000  # $100
    await session.flush()

    # Create a payee (required for standard transactions)
    payee = Payee(budget_id=budget.id, name="Refund Store No Rules")
    session.add(payee)
    await session.flush()

    # Create a CC refund with no rules and no explicit allocations
    response = await authenticated_client.post(
        f"/api/v1/budgets/{budget.id}/transactions",
        json={
            "account_id": cc_account_id,
            "payee_id": str(payee.id),
            "date": "2024-01-15",
            "amount": 5000,  # $50 refund
        },
    )
    assert response.status_code == 201
    txn_id = response.json()["id"]

    await session.refresh(cc_envelope)

    # CC envelope should decrease by $50 (paired move offsets the Unallocated increase)
    assert cc_envelope.current_balance == 5000  # $100 - $50

    # Verify allocations are paired: one to Unallocated (+5000) and one to CC (-5000)
    result = await session.execute(
        select(Allocation).where(Allocation.transaction_id == txn_id)
    )
    allocations = list(result.scalars().all())
    assert len(allocations) == 2

    alloc_amounts = {a.envelope_id: a.amount for a in allocations}
    assert alloc_amounts[cc_envelope.id] == -5000  # CC envelope decreases
    # The other allocation should be +5000 to Unallocated
    other_envelope_id = next(eid for eid in alloc_amounts if eid != cc_envelope.id)
    assert alloc_amounts[other_envelope_id] == 5000


async def test_cc_refund_does_not_affect_ready_to_assign(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,
) -> None:
    """Ready to Assign should not change when a CC refund is created.

    This is the key behavioral test: CC refunds create paired envelope moves
    (target envelope up, CC envelope down) with a net-zero effect on total
    envelope balances, so Ready to Assign remains unchanged.
    """
    from src.envelopes.models import Envelope
    from src.envelopes.service import calculate_unallocated_balance

    result = await session.execute(
        select(Budget).where(Budget.owner_id == test_user.id)
    )
    budget = result.scalar_one()

    # Create a checking account with $1000
    checking = Account(
        budget_id=budget.id,
        name="Checking RTA",
        account_type=AccountType.CHECKING,
        include_in_budget=True,
        cleared_balance=100000,  # $1000
    )
    session.add(checking)
    await session.flush()

    # Create a CC account
    response = await authenticated_client.post(
        f"/api/v1/budgets/{budget.id}/accounts",
        json={
            "name": "CC RTA Test",
            "account_type": "credit_card",
        },
    )
    assert response.status_code == 201
    cc_account_id = response.json()["id"]

    # Get the linked CC envelope and set a balance
    result = await session.execute(
        select(Envelope).where(Envelope.linked_account_id == cc_account_id)
    )
    cc_envelope = result.scalar_one()
    cc_envelope.current_balance = 10000  # $100 from prior spending
    await session.flush()

    # Create a target envelope with some balance
    response = await authenticated_client.post(
        f"/api/v1/budgets/{budget.id}/envelopes",
        json={"name": "Groceries RTA"},
    )
    assert response.status_code == 201
    groceries_envelope_id = response.json()["id"]

    result = await session.execute(
        select(Envelope).where(Envelope.id == groceries_envelope_id)
    )
    groceries_envelope = result.scalar_one()
    groceries_envelope.current_balance = 50000  # $500
    await session.flush()

    # Calculate Ready to Assign before the refund
    rta_before = await calculate_unallocated_balance(session, budget.id)

    # Create a payee
    payee = Payee(budget_id=budget.id, name="Store RTA")
    session.add(payee)
    await session.flush()

    # Create a CC refund
    response = await authenticated_client.post(
        f"/api/v1/budgets/{budget.id}/transactions",
        json={
            "account_id": cc_account_id,
            "payee_id": str(payee.id),
            "date": "2024-01-15",
            "amount": 5000,  # $50 refund
            "allocations": [
                {"envelope_id": groceries_envelope_id, "amount": 5000},
            ],
        },
    )
    assert response.status_code == 201

    # Calculate Ready to Assign after the refund
    rta_after = await calculate_unallocated_balance(session, budget.id)

    # Ready to Assign should be unchanged
    assert rta_after == rta_before


async def test_unallocated_count_excludes_income(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,
) -> None:
    """Unallocated count excludes income transactions (positive amounts).

    Income transactions are expected to be in Unallocated as they represent
    new money that needs to be distributed to envelopes. Only expenses
    (negative amounts) should be counted as "needing review".
    """
    from src.allocations.models import Allocation
    from src.envelopes.service import ensure_unallocated_envelope

    result = await session.execute(
        select(Budget).where(Budget.owner_id == test_user.id)
    )
    budget = result.scalar_one()

    # Create a budget account
    account = Account(
        budget_id=budget.id,
        name="Checking",
        account_type=AccountType.CHECKING,
        include_in_budget=True,
    )
    payee = Payee(budget_id=budget.id, name="Test Payee")
    session.add(account)
    session.add(payee)
    await session.flush()

    # Create the Unallocated envelope
    unallocated = await ensure_unallocated_envelope(session, budget.id)

    # Create an expense transaction directly in DB allocated to Unallocated
    # (simulating legacy data or manual allocation)
    expense_txn = Transaction(
        budget_id=budget.id,
        account_id=account.id,
        payee_id=payee.id,
        date=date(2024, 1, 15),
        amount=-5000,
    )
    session.add(expense_txn)
    await session.flush()

    expense_allocation = Allocation(
        budget_id=budget.id,
        transaction_id=expense_txn.id,
        envelope_id=unallocated.id,
        group_id=expense_txn.id,
        amount=-5000,
        date=expense_txn.date,
    )
    session.add(expense_allocation)
    await session.flush()

    # Create an income transaction (should NOT be counted)
    response = await authenticated_client.post(
        f"/api/v1/budgets/{budget.id}/transactions",
        json={
            "account_id": str(account.id),
            "payee_id": str(payee.id),
            "date": "2024-01-16",
            "amount": 10000,  # Income
        },
    )
    assert response.status_code == 201

    # Check unallocated count - should only count the expense
    response = await authenticated_client.get(
        f"/api/v1/budgets/{budget.id}/transactions/unallocated-count"
    )
    assert response.status_code == 200
    assert response.json()["count"] == 1  # Only the expense


async def test_unallocated_count_excludes_off_budget_accounts(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,
) -> None:
    """Unallocated count excludes transactions on off-budget (tracking) accounts.

    Off-budget accounts are not part of the envelope budgeting system, so their
    transactions shouldn't appear in the "to review" count.
    """
    from src.allocations.models import Allocation
    from src.envelopes.service import ensure_unallocated_envelope

    result = await session.execute(
        select(Budget).where(Budget.owner_id == test_user.id)
    )
    budget = result.scalar_one()

    # Create a budget account and an off-budget account
    budget_account = Account(
        budget_id=budget.id,
        name="Checking",
        account_type=AccountType.CHECKING,
        include_in_budget=True,
    )
    tracking_account = Account(
        budget_id=budget.id,
        name="Investment",
        account_type=AccountType.INVESTMENT,
        include_in_budget=False,  # Off-budget
    )
    payee = Payee(budget_id=budget.id, name="Test Payee")
    session.add(budget_account)
    session.add(tracking_account)
    session.add(payee)
    await session.flush()

    # Create the Unallocated envelope
    unallocated = await ensure_unallocated_envelope(session, budget.id)

    # Create expense on budget account directly in DB allocated to Unallocated
    # (simulating legacy data or manual allocation)
    expense_txn = Transaction(
        budget_id=budget.id,
        account_id=budget_account.id,
        payee_id=payee.id,
        date=date(2024, 1, 15),
        amount=-5000,
    )
    session.add(expense_txn)
    await session.flush()

    expense_allocation = Allocation(
        budget_id=budget.id,
        transaction_id=expense_txn.id,
        envelope_id=unallocated.id,
        group_id=expense_txn.id,
        amount=-5000,
        date=expense_txn.date,
    )
    session.add(expense_allocation)
    await session.flush()

    # Create expense on off-budget account (should NOT be counted)
    response = await authenticated_client.post(
        f"/api/v1/budgets/{budget.id}/transactions",
        json={
            "account_id": str(tracking_account.id),
            "payee_id": str(payee.id),
            "date": "2024-01-16",
            "amount": -3000,
        },
    )
    assert response.status_code == 201

    # Check unallocated count - should only count the budget account expense
    response = await authenticated_client.get(
        f"/api/v1/budgets/{budget.id}/transactions/unallocated-count"
    )
    assert response.status_code == 200
    assert response.json()["count"] == 1  # Only the budget account expense


async def test_list_transactions_expenses_only(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,
) -> None:
    """expenses_only=true filters to only negative amount transactions."""
    from src.envelopes.models import Envelope

    result = await session.execute(
        select(Budget).where(Budget.owner_id == test_user.id)
    )
    budget = result.scalar_one()

    # Create a budget account and envelope
    account = Account(
        budget_id=budget.id,
        name="Checking",
        account_type=AccountType.CHECKING,
        include_in_budget=True,
    )
    payee = Payee(budget_id=budget.id, name="Test Payee")
    envelope = Envelope(budget_id=budget.id, name="Groceries", current_balance=10000)
    session.add(account)
    session.add(payee)
    session.add(envelope)
    await session.flush()

    # Create an income transaction (positive amount)
    response = await authenticated_client.post(
        f"/api/v1/budgets/{budget.id}/transactions",
        json={
            "account_id": str(account.id),
            "payee_id": str(payee.id),
            "date": "2024-01-15",
            "amount": 10000,  # Income
        },
    )
    assert response.status_code == 201

    # Create an expense transaction with allocation (negative amount)
    response = await authenticated_client.post(
        f"/api/v1/budgets/{budget.id}/transactions",
        json={
            "account_id": str(account.id),
            "payee_id": str(payee.id),
            "date": "2024-01-16",
            "amount": -5000,  # Expense
            "allocations": [{"envelope_id": str(envelope.id), "amount": -5000}],
        },
    )
    assert response.status_code == 201

    # Without filter - should return both transactions
    response = await authenticated_client.get(
        f"/api/v1/budgets/{budget.id}/transactions"
    )
    assert response.status_code == 200
    assert len(response.json()["items"]) == 2

    # With expenses_only=true - should return only the expense
    response = await authenticated_client.get(
        f"/api/v1/budgets/{budget.id}/transactions?expenses_only=true"
    )
    assert response.status_code == 200
    items = response.json()["items"]
    assert len(items) == 1
    assert items[0]["amount"] == -5000  # Only the expense


async def test_list_transactions_exclude_adjustments(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,
) -> None:
    """exclude_adjustments=true filters out adjustment transactions."""
    from src.envelopes.models import Envelope

    result = await session.execute(
        select(Budget).where(Budget.owner_id == test_user.id)
    )
    budget = result.scalar_one()

    # Create a budget account and envelope
    account = Account(
        budget_id=budget.id,
        name="Checking",
        account_type=AccountType.CHECKING,
        include_in_budget=True,
    )
    payee = Payee(budget_id=budget.id, name="Test Payee")
    envelope = Envelope(budget_id=budget.id, name="Groceries", current_balance=10000)
    session.add(account)
    session.add(payee)
    session.add(envelope)
    await session.flush()

    # Create a standard transaction with allocation
    response = await authenticated_client.post(
        f"/api/v1/budgets/{budget.id}/transactions",
        json={
            "account_id": str(account.id),
            "payee_id": str(payee.id),
            "date": "2024-01-15",
            "amount": -5000,
            "allocations": [{"envelope_id": str(envelope.id), "amount": -5000}],
        },
    )
    assert response.status_code == 201

    # Create an adjustment transaction (no payee, transaction_type=adjustment)
    response = await authenticated_client.post(
        f"/api/v1/budgets/{budget.id}/transactions",
        json={
            "account_id": str(account.id),
            "date": "2024-01-16",
            "amount": -1000,
            "transaction_type": "adjustment",
        },
    )
    assert response.status_code == 201

    # Without filter - should return both transactions
    response = await authenticated_client.get(
        f"/api/v1/budgets/{budget.id}/transactions"
    )
    assert response.status_code == 200
    assert len(response.json()["items"]) == 2

    # With exclude_adjustments=true - should return only the standard transaction
    response = await authenticated_client.get(
        f"/api/v1/budgets/{budget.id}/transactions?exclude_adjustments=true"
    )
    assert response.status_code == 200
    items = response.json()["items"]
    assert len(items) == 1
    assert items[0]["transaction_type"] == "standard"


async def test_unallocated_count_excludes_adjustments(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,
) -> None:
    """Unallocated count excludes adjustment transactions."""
    from src.allocations.models import Allocation
    from src.envelopes.service import ensure_unallocated_envelope

    result = await session.execute(
        select(Budget).where(Budget.owner_id == test_user.id)
    )
    budget = result.scalar_one()

    # Create a budget account
    account = Account(
        budget_id=budget.id,
        name="Checking",
        account_type=AccountType.CHECKING,
        include_in_budget=True,
    )
    payee = Payee(budget_id=budget.id, name="Test Payee")
    session.add(account)
    session.add(payee)
    await session.flush()

    # Create the Unallocated envelope
    unallocated = await ensure_unallocated_envelope(session, budget.id)

    # Create a standard expense transaction directly in DB allocated to Unallocated
    # (simulating legacy data or manual allocation)
    expense_txn = Transaction(
        budget_id=budget.id,
        account_id=account.id,
        payee_id=payee.id,
        date=date(2024, 1, 15),
        amount=-5000,
    )
    session.add(expense_txn)
    await session.flush()

    expense_allocation = Allocation(
        budget_id=budget.id,
        transaction_id=expense_txn.id,
        envelope_id=unallocated.id,
        group_id=expense_txn.id,
        amount=-5000,
        date=expense_txn.date,
    )
    session.add(expense_allocation)
    await session.flush()

    # Create an adjustment transaction (should NOT be counted)
    response = await authenticated_client.post(
        f"/api/v1/budgets/{budget.id}/transactions",
        json={
            "account_id": str(account.id),
            "date": "2024-01-16",
            "amount": -1000,
            "transaction_type": "adjustment",
        },
    )
    assert response.status_code == 201

    # Check unallocated count - should only count the standard transaction
    response = await authenticated_client.get(
        f"/api/v1/budgets/{budget.id}/transactions/unallocated-count"
    )
    assert response.status_code == 200
    assert response.json()["count"] == 1  # Only the standard expense


# Transfer Envelope Tests


async def test_transfer_budget_to_tracking_requires_envelope(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,
) -> None:
    """Transfers from budget account to tracking account require an envelope_id."""
    from src.budgets.models import Budget

    result = await session.execute(
        select(Budget).where(Budget.owner_id == test_user.id)
    )
    budget = result.scalar_one()

    # Create budget account and tracking account
    budget_account = Account(
        budget_id=budget.id,
        name="Budget Account",
        account_type=AccountType.CHECKING,
        include_in_budget=True,
        cleared_balance=50000,
    )
    tracking_account = Account(
        budget_id=budget.id,
        name="Tracking Account",
        account_type=AccountType.INVESTMENT,
        include_in_budget=False,
    )
    session.add(budget_account)
    session.add(tracking_account)
    await session.flush()

    # Try to create transfer without envelope_id - should fail
    response = await authenticated_client.post(
        f"/api/v1/budgets/{budget.id}/transactions/transfers",
        json={
            "source_account_id": str(budget_account.id),
            "destination_account_id": str(tracking_account.id),
            "date": "2024-01-15",
            "amount": 10000,
        },
    )
    assert response.status_code == 400
    assert "envelope_id is required" in response.json()["detail"]


async def test_transfer_budget_to_tracking_with_envelope(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,
) -> None:
    """Transfers from budget to tracking with envelope_id creates allocation."""
    from src.budgets.models import Budget
    from src.envelopes.models import Envelope

    result = await session.execute(
        select(Budget).where(Budget.owner_id == test_user.id)
    )
    budget = result.scalar_one()

    # Create budget account and tracking account
    budget_account = Account(
        budget_id=budget.id,
        name="Budget Account",
        account_type=AccountType.CHECKING,
        include_in_budget=True,
        cleared_balance=50000,
    )
    tracking_account = Account(
        budget_id=budget.id,
        name="Tracking Account",
        account_type=AccountType.INVESTMENT,
        include_in_budget=False,
    )
    session.add(budget_account)
    session.add(tracking_account)
    await session.flush()

    # Create an envelope
    envelope = Envelope(budget_id=budget.id, name="Investments", current_balance=20000)
    session.add(envelope)
    await session.flush()

    # Create transfer with envelope_id
    response = await authenticated_client.post(
        f"/api/v1/budgets/{budget.id}/transactions/transfers",
        json={
            "source_account_id": str(budget_account.id),
            "destination_account_id": str(tracking_account.id),
            "date": "2024-01-15",
            "amount": 10000,
            "envelope_id": str(envelope.id),
        },
    )
    assert response.status_code == 201
    data = response.json()

    # Verify source transaction has allocation
    source_txn = data["source_transaction"]
    assert len(source_txn["allocations"]) == 1
    assert source_txn["allocations"][0]["envelope_id"] == str(envelope.id)
    assert source_txn["allocations"][0]["amount"] == -10000  # Negative for expense

    # Verify envelope balance was reduced
    await session.refresh(envelope)
    assert envelope.current_balance == 10000  # 20000 - 10000


async def test_transfer_budget_to_budget_no_envelope_required(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,
) -> None:
    """Transfers between two budget accounts do not require envelope_id."""
    from src.budgets.models import Budget

    result = await session.execute(
        select(Budget).where(Budget.owner_id == test_user.id)
    )
    budget = result.scalar_one()

    # Create two budget accounts
    budget_account1 = Account(
        budget_id=budget.id,
        name="Checking",
        account_type=AccountType.CHECKING,
        include_in_budget=True,
        cleared_balance=50000,
    )
    budget_account2 = Account(
        budget_id=budget.id,
        name="Savings",
        account_type=AccountType.SAVINGS,
        include_in_budget=True,
    )
    session.add(budget_account1)
    session.add(budget_account2)
    await session.flush()

    # Create transfer without envelope_id - should succeed
    response = await authenticated_client.post(
        f"/api/v1/budgets/{budget.id}/transactions/transfers",
        json={
            "source_account_id": str(budget_account1.id),
            "destination_account_id": str(budget_account2.id),
            "date": "2024-01-15",
            "amount": 10000,
        },
    )
    assert response.status_code == 201
    data = response.json()

    # Verify no allocations on source transaction
    assert data["source_transaction"]["allocations"] == []
    assert data["destination_transaction"]["allocations"] == []


async def test_transfer_tracking_to_budget_no_envelope_required(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,
) -> None:
    """Transfers from tracking to budget account do not require envelope_id."""
    from src.budgets.models import Budget

    result = await session.execute(
        select(Budget).where(Budget.owner_id == test_user.id)
    )
    budget = result.scalar_one()

    # Create tracking and budget accounts
    tracking_account = Account(
        budget_id=budget.id,
        name="Investment",
        account_type=AccountType.INVESTMENT,
        include_in_budget=False,
        cleared_balance=50000,
    )
    budget_account = Account(
        budget_id=budget.id,
        name="Checking",
        account_type=AccountType.CHECKING,
        include_in_budget=True,
    )
    session.add(tracking_account)
    session.add(budget_account)
    await session.flush()

    # Create transfer without envelope_id - should succeed
    response = await authenticated_client.post(
        f"/api/v1/budgets/{budget.id}/transactions/transfers",
        json={
            "source_account_id": str(tracking_account.id),
            "destination_account_id": str(budget_account.id),
            "date": "2024-01-15",
            "amount": 10000,
        },
    )
    assert response.status_code == 201
    data = response.json()

    # Verify no allocations
    assert data["source_transaction"]["allocations"] == []
    assert data["destination_transaction"]["allocations"] == []


async def test_transfer_tracking_to_tracking_no_envelope_required(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,
) -> None:
    """Transfers between tracking accounts do not require envelope_id."""
    from src.budgets.models import Budget

    result = await session.execute(
        select(Budget).where(Budget.owner_id == test_user.id)
    )
    budget = result.scalar_one()

    # Create two tracking accounts
    tracking_account1 = Account(
        budget_id=budget.id,
        name="Investment 1",
        account_type=AccountType.INVESTMENT,
        include_in_budget=False,
        cleared_balance=50000,
    )
    tracking_account2 = Account(
        budget_id=budget.id,
        name="Investment 2",
        account_type=AccountType.INVESTMENT,
        include_in_budget=False,
    )
    session.add(tracking_account1)
    session.add(tracking_account2)
    await session.flush()

    # Create transfer without envelope_id - should succeed
    response = await authenticated_client.post(
        f"/api/v1/budgets/{budget.id}/transactions/transfers",
        json={
            "source_account_id": str(tracking_account1.id),
            "destination_account_id": str(tracking_account2.id),
            "date": "2024-01-15",
            "amount": 10000,
        },
    )
    assert response.status_code == 201


# Expense Allocation Requirement Tests


async def test_expense_in_budget_account_requires_allocation(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,
) -> None:
    """Expenses in budget accounts require an envelope allocation."""
    result = await session.execute(
        select(Budget).where(Budget.owner_id == test_user.id)
    )
    budget = result.scalar_one()

    # Create a budget account and payee
    account = Account(
        budget_id=budget.id,
        name="Budget Checking",
        account_type=AccountType.CHECKING,
        include_in_budget=True,
    )
    payee = Payee(budget_id=budget.id, name="Test Payee")
    session.add(account)
    session.add(payee)
    await session.flush()

    # Try to create expense without allocation - should fail
    response = await authenticated_client.post(
        f"/api/v1/budgets/{budget.id}/transactions",
        json={
            "account_id": str(account.id),
            "payee_id": str(payee.id),
            "date": "2024-01-15",
            "amount": -5000,  # Expense
        },
    )
    assert response.status_code == 400
    assert "Envelope allocation is required for expenses" in response.json()["detail"]


async def test_expense_in_budget_account_with_allocation_succeeds(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,
) -> None:
    """Expenses in budget accounts with explicit allocation succeed."""
    from src.envelopes.models import Envelope

    result = await session.execute(
        select(Budget).where(Budget.owner_id == test_user.id)
    )
    budget = result.scalar_one()

    # Create a budget account, payee, and envelope
    account = Account(
        budget_id=budget.id,
        name="Budget Checking",
        account_type=AccountType.CHECKING,
        include_in_budget=True,
    )
    payee = Payee(budget_id=budget.id, name="Test Payee")
    envelope = Envelope(budget_id=budget.id, name="Groceries", current_balance=10000)
    session.add(account)
    session.add(payee)
    session.add(envelope)
    await session.flush()

    # Create expense with allocation - should succeed
    response = await authenticated_client.post(
        f"/api/v1/budgets/{budget.id}/transactions",
        json={
            "account_id": str(account.id),
            "payee_id": str(payee.id),
            "date": "2024-01-15",
            "amount": -5000,  # Expense
            "allocations": [{"envelope_id": str(envelope.id), "amount": -5000}],
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert len(data["allocations"]) == 1
    assert data["allocations"][0]["envelope_id"] == str(envelope.id)


async def test_income_in_budget_account_defaults_to_unallocated(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,
) -> None:
    """Income in budget accounts defaults to Unallocated envelope."""
    from src.envelopes.models import Envelope

    result = await session.execute(
        select(Budget).where(Budget.owner_id == test_user.id)
    )
    budget = result.scalar_one()

    # Create a budget account and payee
    account = Account(
        budget_id=budget.id,
        name="Budget Checking",
        account_type=AccountType.CHECKING,
        include_in_budget=True,
    )
    payee = Payee(budget_id=budget.id, name="Test Payee")
    session.add(account)
    session.add(payee)
    await session.flush()

    # Create income without allocation - should succeed and default to Unallocated
    response = await authenticated_client.post(
        f"/api/v1/budgets/{budget.id}/transactions",
        json={
            "account_id": str(account.id),
            "payee_id": str(payee.id),
            "date": "2024-01-15",
            "amount": 10000,  # Income
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert len(data["allocations"]) == 1

    # Verify it's allocated to the Unallocated envelope
    envelope_result = await session.execute(
        select(Envelope).where(
            Envelope.budget_id == budget.id,
            Envelope.is_unallocated == True,  # noqa: E712
        )
    )
    unallocated = envelope_result.scalar_one()
    assert data["allocations"][0]["envelope_id"] == str(unallocated.id)


async def test_expense_in_tracking_account_no_allocation_required(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,
) -> None:
    """Expenses in tracking accounts do not require allocations."""
    result = await session.execute(
        select(Budget).where(Budget.owner_id == test_user.id)
    )
    budget = result.scalar_one()

    # Create a tracking (off-budget) account and payee
    account = Account(
        budget_id=budget.id,
        name="Investment",
        account_type=AccountType.INVESTMENT,
        include_in_budget=False,
    )
    payee = Payee(budget_id=budget.id, name="Test Payee")
    session.add(account)
    session.add(payee)
    await session.flush()

    # Create expense without allocation - should succeed
    response = await authenticated_client.post(
        f"/api/v1/budgets/{budget.id}/transactions",
        json={
            "account_id": str(account.id),
            "payee_id": str(payee.id),
            "date": "2024-01-15",
            "amount": -5000,  # Expense
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["allocations"] == []


# Independent Cleared Status Tests


async def test_update_transaction_cleared_does_not_affect_linked_transfer(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,
) -> None:
    """Toggling is_cleared on one side of a transfer does NOT mirror to the other."""
    result = await session.execute(
        select(Budget).where(Budget.owner_id == test_user.id)
    )
    budget = result.scalar_one()

    checking = Account(
        budget_id=budget.id,
        name="Checking",
        account_type=AccountType.CHECKING,
        include_in_budget=False,
    )
    savings = Account(
        budget_id=budget.id,
        name="Savings",
        account_type=AccountType.SAVINGS,
        include_in_budget=False,
    )
    session.add(checking)
    session.add(savings)
    await session.flush()

    # Create a transfer (both sides start uncleared)
    response = await authenticated_client.post(
        f"/api/v1/budgets/{budget.id}/transactions/transfers",
        json={
            "source_account_id": str(checking.id),
            "destination_account_id": str(savings.id),
            "date": "2024-01-15",
            "amount": 10000,
        },
    )
    assert response.status_code == 201
    data = response.json()
    source_id = data["source_transaction"]["id"]
    dest_id = data["destination_transaction"]["id"]
    assert data["source_transaction"]["is_cleared"] is False
    assert data["destination_transaction"]["is_cleared"] is False

    # Clear only the source side via PATCH /transactions/{id}
    response = await authenticated_client.patch(
        f"/api/v1/budgets/{budget.id}/transactions/{source_id}",
        json={"is_cleared": True},
    )
    assert response.status_code == 200
    assert response.json()["is_cleared"] is True

    # Verify the destination side is still uncleared
    response = await authenticated_client.get(
        f"/api/v1/budgets/{budget.id}/transactions/{dest_id}",
    )
    assert response.status_code == 200
    assert response.json()["is_cleared"] is False


async def test_update_transaction_cleared_updates_correct_balance_only(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,
) -> None:
    """Clearing one side of a transfer only updates that account's balance."""
    result = await session.execute(
        select(Budget).where(Budget.owner_id == test_user.id)
    )
    budget = result.scalar_one()

    checking = Account(
        budget_id=budget.id,
        name="Checking",
        account_type=AccountType.CHECKING,
        include_in_budget=False,
        cleared_balance=0,
        uncleared_balance=0,
    )
    savings = Account(
        budget_id=budget.id,
        name="Savings",
        account_type=AccountType.SAVINGS,
        include_in_budget=False,
        cleared_balance=0,
        uncleared_balance=0,
    )
    session.add(checking)
    session.add(savings)
    await session.flush()

    # Create transfer: checking -> savings, 10000, uncleared
    response = await authenticated_client.post(
        f"/api/v1/budgets/{budget.id}/transactions/transfers",
        json={
            "source_account_id": str(checking.id),
            "destination_account_id": str(savings.id),
            "date": "2024-01-15",
            "amount": 10000,
        },
    )
    assert response.status_code == 201
    data = response.json()
    source_id = data["source_transaction"]["id"]

    await session.refresh(checking)
    await session.refresh(savings)
    assert checking.uncleared_balance == -10000
    assert checking.cleared_balance == 0
    assert savings.uncleared_balance == 10000
    assert savings.cleared_balance == 0

    # Clear only the source (checking) side
    response = await authenticated_client.patch(
        f"/api/v1/budgets/{budget.id}/transactions/{source_id}",
        json={"is_cleared": True},
    )
    assert response.status_code == 200

    await session.refresh(checking)
    await session.refresh(savings)
    # Checking: moved from uncleared to cleared
    assert checking.uncleared_balance == 0
    assert checking.cleared_balance == -10000
    # Savings: unchanged (still uncleared)
    assert savings.uncleared_balance == 10000
    assert savings.cleared_balance == 0


async def test_update_transfer_independent_cleared_status(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,
) -> None:
    """source_is_cleared and destination_is_cleared work independently via transfer endpoint."""
    result = await session.execute(
        select(Budget).where(Budget.owner_id == test_user.id)
    )
    budget = result.scalar_one()

    checking = Account(
        budget_id=budget.id,
        name="Checking",
        account_type=AccountType.CHECKING,
        include_in_budget=False,
        cleared_balance=0,
        uncleared_balance=0,
    )
    credit_card = Account(
        budget_id=budget.id,
        name="Credit Card",
        account_type=AccountType.CREDIT_CARD,
        include_in_budget=False,
        cleared_balance=0,
        uncleared_balance=0,
    )
    session.add(checking)
    session.add(credit_card)
    await session.flush()

    # Create transfer (both uncleared)
    response = await authenticated_client.post(
        f"/api/v1/budgets/{budget.id}/transactions/transfers",
        json={
            "source_account_id": str(checking.id),
            "destination_account_id": str(credit_card.id),
            "date": "2024-01-15",
            "amount": 5000,
        },
    )
    assert response.status_code == 201
    data = response.json()
    source_id = data["source_transaction"]["id"]

    # Clear only the source side via transfer endpoint
    response = await authenticated_client.patch(
        f"/api/v1/budgets/{budget.id}/transactions/transfers/{source_id}",
        json={"source_is_cleared": True},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["source_transaction"]["is_cleared"] is True
    assert data["destination_transaction"]["is_cleared"] is False

    await session.refresh(checking)
    await session.refresh(credit_card)
    assert checking.cleared_balance == -5000
    assert checking.uncleared_balance == 0
    assert credit_card.uncleared_balance == 5000
    assert credit_card.cleared_balance == 0

    # Now clear the destination side too
    response = await authenticated_client.patch(
        f"/api/v1/budgets/{budget.id}/transactions/transfers/{source_id}",
        json={"destination_is_cleared": True},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["source_transaction"]["is_cleared"] is True
    assert data["destination_transaction"]["is_cleared"] is True

    await session.refresh(checking)
    await session.refresh(credit_card)
    assert checking.cleared_balance == -5000
    assert checking.uncleared_balance == 0
    assert credit_card.cleared_balance == 5000
    assert credit_card.uncleared_balance == 0


async def test_update_transfer_clear_both_sides_at_once(
    authenticated_client: AsyncClient,
    session: AsyncSession,
    test_user: User,
) -> None:
    """Both sides can be cleared in a single update."""
    result = await session.execute(
        select(Budget).where(Budget.owner_id == test_user.id)
    )
    budget = result.scalar_one()

    checking = Account(
        budget_id=budget.id,
        name="Checking",
        account_type=AccountType.CHECKING,
        include_in_budget=False,
        cleared_balance=0,
        uncleared_balance=0,
    )
    savings = Account(
        budget_id=budget.id,
        name="Savings",
        account_type=AccountType.SAVINGS,
        include_in_budget=False,
        cleared_balance=0,
        uncleared_balance=0,
    )
    session.add(checking)
    session.add(savings)
    await session.flush()

    # Create transfer (uncleared)
    response = await authenticated_client.post(
        f"/api/v1/budgets/{budget.id}/transactions/transfers",
        json={
            "source_account_id": str(checking.id),
            "destination_account_id": str(savings.id),
            "date": "2024-01-15",
            "amount": 8000,
        },
    )
    assert response.status_code == 201
    data = response.json()
    source_id = data["source_transaction"]["id"]

    # Clear both sides at once
    response = await authenticated_client.patch(
        f"/api/v1/budgets/{budget.id}/transactions/transfers/{source_id}",
        json={"source_is_cleared": True, "destination_is_cleared": True},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["source_transaction"]["is_cleared"] is True
    assert data["destination_transaction"]["is_cleared"] is True

    await session.refresh(checking)
    await session.refresh(savings)
    assert checking.cleared_balance == -8000
    assert checking.uncleared_balance == 0
    assert savings.cleared_balance == 8000
    assert savings.uncleared_balance == 0
