from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.schemas import LoginRequest, RefreshTokenRequest, Token
from src.auth.service import (
    authenticate_user,
    create_access_token,
    create_refresh_token,
    revoke_refresh_token,
    validate_refresh_token,
)
from src.config import settings
from src.database import get_async_session
from src.rate_limit import limiter

router = APIRouter(prefix="/auth", tags=["auth"])


def _set_auth_cookies(
    response: Response, access_token: str, refresh_token: str
) -> None:
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        secure=settings.cookie_secure,
        samesite=settings.cookie_samesite,
        domain=settings.cookie_domain,
        path=settings.cookie_path,
        max_age=settings.jwt_access_token_expire_minutes * 60,
    )
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=settings.cookie_secure,
        samesite=settings.cookie_samesite,
        domain=settings.cookie_domain,
        path="/api/v1/auth",
        max_age=settings.jwt_refresh_token_expire_days * 86400,
    )


def _clear_auth_cookies(response: Response) -> None:
    response.delete_cookie(
        key="access_token",
        path=settings.cookie_path,
        domain=settings.cookie_domain,
    )
    response.delete_cookie(
        key="refresh_token",
        path="/api/v1/auth",
        domain=settings.cookie_domain,
    )


@router.post("/token", response_model=Token)
@limiter.limit("10/minute")
async def login_for_access_token(
    request: Request,  # noqa: ARG001 - required by slowapi limiter
    response: Response,
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    session: Annotated[AsyncSession, Depends(get_async_session)],
) -> Token:
    """OAuth2 compatible token endpoint for Swagger UI."""
    user = await authenticate_user(session, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user",
        )
    access_token = create_access_token(user.id)
    refresh_token = await create_refresh_token(session, user.id)
    _set_auth_cookies(response, access_token, refresh_token)
    return Token(access_token=access_token, refresh_token=refresh_token)


@router.post("/login", response_model=Token)
@limiter.limit("10/minute")
async def login(
    request: Request,  # noqa: ARG001 - required by slowapi limiter
    response: Response,
    credentials: LoginRequest,
    session: Annotated[AsyncSession, Depends(get_async_session)],
) -> Token:
    """JSON login endpoint."""
    user = await authenticate_user(session, credentials.username, credentials.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user",
        )
    access_token = create_access_token(user.id)
    refresh_token = await create_refresh_token(session, user.id)
    _set_auth_cookies(response, access_token, refresh_token)
    return Token(access_token=access_token, refresh_token=refresh_token)


@router.post("/refresh", response_model=Token)
@limiter.limit("20/minute")
async def refresh(
    request: Request,
    response: Response,
    request_body: RefreshTokenRequest | None = None,
    session: AsyncSession = Depends(get_async_session),
) -> Token:
    """Get new access and refresh tokens using a valid refresh token."""
    # Try request body first, then fall back to cookie
    token = request_body.refresh_token if request_body else None
    if not token:
        token = request.cookies.get("refresh_token")
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No refresh token provided",
        )

    user = await validate_refresh_token(session, token)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user",
        )

    # Revoke old refresh token and issue new ones
    await revoke_refresh_token(session, token)
    access_token = create_access_token(user.id)
    new_refresh_token = await create_refresh_token(session, user.id)
    _set_auth_cookies(response, access_token, new_refresh_token)
    return Token(access_token=access_token, refresh_token=new_refresh_token)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit("20/minute")
async def logout(
    request: Request,
    response: Response,
    request_body: RefreshTokenRequest | None = None,
    session: AsyncSession = Depends(get_async_session),
) -> None:
    """Revoke a refresh token."""
    # Try request body first, then fall back to cookie
    token = request_body.refresh_token if request_body else None
    if not token:
        token = request.cookies.get("refresh_token")
    if token:
        await revoke_refresh_token(session, token)
    _clear_auth_cookies(response)
