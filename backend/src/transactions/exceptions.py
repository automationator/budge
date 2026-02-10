from uuid import UUID

from src.exceptions import NotFoundError


class TransactionNotFoundError(NotFoundError):
    def __init__(self, transaction_id: UUID | None = None):
        detail = (
            f"Transaction {transaction_id} not found"
            if transaction_id
            else "Transaction not found"
        )
        super().__init__(detail=detail)
