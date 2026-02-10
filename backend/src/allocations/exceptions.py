from uuid import UUID

from src.exceptions import BadRequestError, NotFoundError


class AllocationNotFoundError(NotFoundError):
    def __init__(self, allocation_id: UUID | None = None):
        detail = (
            f"Allocation {allocation_id} not found"
            if allocation_id
            else "Allocation not found"
        )
        super().__init__(detail=detail)


class SameEnvelopeTransferError(BadRequestError):
    def __init__(self):
        super().__init__(detail="Source and destination envelopes must be different")


class AllocationAmountMismatchError(BadRequestError):
    def __init__(self, transaction_amount: int, allocation_sum: int):
        super().__init__(
            detail=f"Allocation amounts ({allocation_sum}) must equal transaction amount ({transaction_amount})"
        )


class AllocationsRequiredError(BadRequestError):
    def __init__(self):
        super().__init__(
            detail="Transactions in budget accounts require envelope allocations"
        )
