from uuid import UUID

from src.exceptions import BadRequestError, ForbiddenError, NotFoundError


class BudgetNotFoundError(NotFoundError):
    def __init__(self, budget_id: UUID | None = None):
        detail = f"Budget {budget_id} not found" if budget_id else "Budget not found"
        super().__init__(detail=detail)


class NotBudgetOwnerError(ForbiddenError):
    def __init__(self) -> None:
        super().__init__(detail="Only the budget owner can perform this action")


class UserAlreadyBudgetMemberError(BadRequestError):
    def __init__(self, username_or_email: str) -> None:
        super().__init__(
            detail=f"User {username_or_email} is already a member of this budget"
        )


class UserNotBudgetMemberError(BadRequestError):
    def __init__(self, username_or_email: str) -> None:
        super().__init__(
            detail=f"User {username_or_email} is not a member of this budget"
        )


class CannotRemoveBudgetOwnerError(BadRequestError):
    def __init__(self) -> None:
        super().__init__(detail="Cannot remove the budget owner from their own budget")


class NotBudgetMemberError(ForbiddenError):
    def __init__(self) -> None:
        super().__init__(detail="You are not a member of this budget")


class InsufficientPermissionsError(ForbiddenError):
    def __init__(self, missing_scopes: list[str]) -> None:
        super().__init__(
            detail=f"Insufficient permissions. Missing scopes: {', '.join(missing_scopes)}"
        )


class CannotModifyOwnerRoleError(BadRequestError):
    def __init__(self) -> None:
        super().__init__(detail="Cannot modify the budget owner's role")


class CannotAssignOwnerRoleError(BadRequestError):
    def __init__(self) -> None:
        super().__init__(detail="Owner role cannot be assigned directly")
