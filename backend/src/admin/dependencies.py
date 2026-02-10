from typing import Annotated

from fastapi import Depends

from src.admin.exceptions import AdminRequiredError
from src.auth.dependencies import get_current_active_user
from src.users.models import User


async def require_admin(
    current_user: Annotated[User, Depends(get_current_active_user)],
) -> User:
    """Dependency that ensures the current user is an admin."""
    if not current_user.is_admin:
        raise AdminRequiredError()
    return current_user
