from uuid import UUID

from httpx import AsyncClient

from src.users.models import User


async def test_create_user(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/users",
        json={
            "username": "testcreate",
            "password": "password123",
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["username"] == "testcreate"
    assert data["is_active"] is True
    assert "id" in data
    UUID(data["id"])
    assert "hashed_password" not in data
    assert data["created_at"]


async def test_create_user_short_password(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/users",
        json={
            "username": "shortpw",
            "password": "short",
        },
    )
    assert response.status_code == 422


async def test_get_me(authenticated_client: AsyncClient, test_user: User) -> None:
    response = await authenticated_client.get("/api/v1/users/me")
    assert response.status_code == 200
    assert response.json()["username"] == test_user.username


async def test_get_me_unauthorized(client: AsyncClient) -> None:
    response = await client.get("/api/v1/users/me")
    assert response.status_code == 401


async def test_update_me(authenticated_client: AsyncClient) -> None:
    response = await authenticated_client.patch(
        "/api/v1/users/me",
        json={"username": "updateduser"},
    )
    assert response.status_code == 200
    assert response.json()["username"] == "updateduser"


async def test_update_me_unauthorized(client: AsyncClient) -> None:
    response = await client.patch(
        "/api/v1/users/me",
        json={"username": "updateduser"},
    )
    assert response.status_code == 401


async def test_delete_me(authenticated_client: AsyncClient) -> None:
    response = await authenticated_client.delete("/api/v1/users/me")
    assert response.status_code == 204

    # Verify we can no longer access /me (token should be invalid)
    get_response = await authenticated_client.get("/api/v1/users/me")
    assert get_response.status_code == 401


async def test_delete_me_unauthorized(client: AsyncClient) -> None:
    response = await client.delete("/api/v1/users/me")
    assert response.status_code == 401
