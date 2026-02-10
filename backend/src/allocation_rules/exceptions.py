from uuid import UUID

from src.exceptions import BadRequestError, NotFoundError


class AllocationRuleNotFoundError(NotFoundError):
    def __init__(self, rule_id: UUID | None = None) -> None:
        detail = (
            f"Allocation rule {rule_id} not found"
            if rule_id
            else "Allocation rule not found"
        )
        super().__init__(detail=detail)


class InvalidRuleConfigurationError(BadRequestError):
    def __init__(self, detail: str) -> None:
        super().__init__(detail=detail)


class NoUnallocatedMoneyError(BadRequestError):
    def __init__(self) -> None:
        super().__init__(detail="No unallocated money available to distribute")


class NoActiveRulesError(BadRequestError):
    def __init__(self) -> None:
        super().__init__(detail="No active allocation rules configured")


class DuplicatePeriodCapError(BadRequestError):
    def __init__(self) -> None:
        super().__init__(
            detail="This envelope already has a period_cap rule. "
            "Only one period_cap rule is allowed per envelope."
        )
