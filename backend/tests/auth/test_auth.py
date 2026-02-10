from httpx import AsyncClient

from src.users.models import User
from tests.utils import TEST_USER_PASSWORD


async def test_login(client: AsyncClient, test_user: User) -> None:
    response = await client.post(
        "/api/v1/auth/login",
        json={"username": test_user.username, "password": TEST_USER_PASSWORD},
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"


async def test_login_wrong_username(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/auth/login",
        json={"username": "nonexistentuser", "password": TEST_USER_PASSWORD},
    )
    assert response.status_code == 401


async def test_login_wrong_password(client: AsyncClient, test_user: User) -> None:
    response = await client.post(
        "/api/v1/auth/login",
        json={"username": test_user.username, "password": "wrongpassword"},
    )
    assert response.status_code == 401


async def test_refresh_token(client: AsyncClient, test_user: User) -> None:
    login_response = await client.post(
        "/api/v1/auth/login",
        json={"username": test_user.username, "password": TEST_USER_PASSWORD},
    )
    tokens = login_response.json()

    response = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": tokens["refresh_token"]},
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["refresh_token"] != tokens["refresh_token"]


async def test_refresh_token_invalid(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": "invalid_token"},
    )
    assert response.status_code == 401


async def test_refresh_token_reuse_rejected(
    client: AsyncClient, test_user: User
) -> None:
    login_response = await client.post(
        "/api/v1/auth/login",
        json={"username": test_user.username, "password": TEST_USER_PASSWORD},
    )
    tokens = login_response.json()

    # Use refresh token once
    response = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": tokens["refresh_token"]},
    )
    assert response.status_code == 200

    # Try to use same refresh token again - should fail
    response = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": tokens["refresh_token"]},
    )
    assert response.status_code == 401


async def test_logout(client: AsyncClient, test_user: User) -> None:
    login_response = await client.post(
        "/api/v1/auth/login",
        json={"username": test_user.username, "password": TEST_USER_PASSWORD},
    )
    tokens = login_response.json()

    response = await client.post(
        "/api/v1/auth/logout",
        json={"refresh_token": tokens["refresh_token"]},
    )
    assert response.status_code == 204

    # Try to use refresh token after logout - should fail
    refresh_response = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": tokens["refresh_token"]},
    )
    assert refresh_response.status_code == 401


async def test_oauth2_token_endpoint(client: AsyncClient, test_user: User) -> None:
    """Test the OAuth2 compatible /token endpoint."""
    response = await client.post(
        "/api/v1/auth/token",
        data={"username": test_user.username, "password": TEST_USER_PASSWORD},
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
