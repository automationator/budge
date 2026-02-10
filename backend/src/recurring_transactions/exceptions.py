from uuid import UUID

from src.exceptions import NotFoundError


class RecurringTransactionNotFoundError(NotFoundError):
    def __init__(self, recurring_transaction_id: UUID | None = None):
        detail = (
            f"Recurring transaction {recurring_transaction_id} not found"
            if recurring_transaction_id
            else "Recurring transaction not found"
        )
        super().__init__(detail=detail)
