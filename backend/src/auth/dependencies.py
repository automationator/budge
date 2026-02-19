from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.service import decode_access_token
from src.database import get_async_session
from src.users.models import User
from src.users.service import get_user_by_id

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/token", auto_error=False)


async def get_current_user(
    request: Request,
    token: Annotated[str | None, Depends(oauth2_scheme)],
    session: Annotated[AsyncSession, Depends(get_async_session)],
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    # Try Bearer token first (Swagger UI / backend tests), fall back to cookie
    if not token:
        token = request.cookies.get("access_token")
    if not token:
        raise credentials_exception

    token_data = decode_access_token(token)
    if token_data is None or token_data.user_id is None:
        raise credentials_exception

    try:
        user = await get_user_by_id(session, token_data.user_id)
    except Exception:
        raise credentials_exception from None

    return user


async def get_current_active_user(
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user",
        )
    return current_user
