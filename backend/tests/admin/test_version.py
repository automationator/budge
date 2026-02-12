from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from httpx import AsyncClient
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from src.admin.service import (
    _is_newer,
    check_version,
)
from src.users.models import User


def _make_mock_response(status_code: int, json_data: dict | None = None) -> MagicMock:
    """Create a mock httpx response (json() is sync in httpx)."""
    resp = MagicMock()
    resp.status_code = status_code
    if json_data is not None:
        resp.json.return_value = json_data
    return resp


def _make_mock_client(mock_response=None, side_effect=None) -> AsyncMock:
    """Create a mock httpx.AsyncClient context manager."""
    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    if side_effect:
        mock_client.get = AsyncMock(side_effect=side_effect)
    else:
        mock_client.get = AsyncMock(return_value=mock_response)
    return mock_client


class TestIsNewer:
    def test_newer_date(self) -> None:
        assert _is_newer("2026.02.13", "2026.02.12") is True

    def test_older_date(self) -> None:
        assert _is_newer("2026.02.11", "2026.02.12") is False

    def test_equal_versions(self) -> None:
        assert _is_newer("2026.02.12", "2026.02.12") is False

    def test_same_day_suffix_newer(self) -> None:
        assert _is_newer("2026.02.12.2", "2026.02.12") is True

    def test_same_day_suffix_increment(self) -> None:
        assert _is_newer("2026.02.12.3", "2026.02.12.2") is True

    def test_same_day_suffix_older(self) -> None:
        assert _is_newer("2026.02.12", "2026.02.12.2") is False

    def test_different_month(self) -> None:
        assert _is_newer("2026.03.01", "2026.02.28") is True

    def test_different_year(self) -> None:
        assert _is_newer("2027.01.01", "2026.12.31") is True

    def test_invalid_version_string(self) -> None:
        assert _is_newer("invalid", "2026.02.12") is False

    def test_dev_version(self) -> None:
        assert _is_newer("2026.02.12", "dev") is False


class TestCheckVersion:
    @pytest.fixture(autouse=True)
    def _reset_cache(self) -> None:
        """Reset the module-level cache before each test."""
        import src.admin.service as svc

        svc._version_cache = None
        svc._version_cache_time = 0.0

    @patch("src.admin.service.settings")
    async def test_dev_version_skips_api(self, mock_settings: MagicMock) -> None:
        mock_settings.app_version = "dev"
        result = await check_version()
        assert result.current_version == "dev"
        assert result.error == "Running development build"
        assert result.update_available is False
        assert result.latest_version is None

    @patch("src.admin.service.settings")
    async def test_success_update_available(self, mock_settings: MagicMock) -> None:
        mock_settings.app_version = "2026.02.10"
        mock_settings.github_repo = "automationator/budge"

        mock_response = _make_mock_response(
            200,
            {
                "tag_name": "2026.02.12",
                "html_url": "https://github.com/automationator/budge/releases/tag/2026.02.12",
            },
        )
        mock_client = _make_mock_client(mock_response)

        with patch("src.admin.service.httpx.AsyncClient", return_value=mock_client):
            result = await check_version()

        assert result.current_version == "2026.02.10"
        assert result.latest_version == "2026.02.12"
        assert result.update_available is True
        assert result.release_url is not None
        assert result.error is None

    @patch("src.admin.service.settings")
    async def test_success_up_to_date(self, mock_settings: MagicMock) -> None:
        mock_settings.app_version = "2026.02.12"
        mock_settings.github_repo = "automationator/budge"

        mock_response = _make_mock_response(
            200,
            {
                "tag_name": "2026.02.12",
                "html_url": "https://github.com/automationator/budge/releases/tag/2026.02.12",
            },
        )
        mock_client = _make_mock_client(mock_response)

        with patch("src.admin.service.httpx.AsyncClient", return_value=mock_client):
            result = await check_version()

        assert result.current_version == "2026.02.12"
        assert result.latest_version == "2026.02.12"
        assert result.update_available is False

    @patch("src.admin.service.settings")
    async def test_404_no_releases(self, mock_settings: MagicMock) -> None:
        mock_settings.app_version = "2026.02.12"
        mock_settings.github_repo = "automationator/budge"

        mock_response = _make_mock_response(404)
        mock_client = _make_mock_client(mock_response)

        with patch("src.admin.service.httpx.AsyncClient", return_value=mock_client):
            result = await check_version()

        assert result.error == "No releases found"
        assert result.update_available is False

    @patch("src.admin.service.settings")
    async def test_403_rate_limited(self, mock_settings: MagicMock) -> None:
        mock_settings.app_version = "2026.02.12"
        mock_settings.github_repo = "automationator/budge"

        mock_response = _make_mock_response(403)
        mock_client = _make_mock_client(mock_response)

        with patch("src.admin.service.httpx.AsyncClient", return_value=mock_client):
            result = await check_version()

        assert result.error == "GitHub API rate limited"

    @patch("src.admin.service.settings")
    async def test_connection_error(self, mock_settings: MagicMock) -> None:
        mock_settings.app_version = "2026.02.12"
        mock_settings.github_repo = "automationator/budge"

        mock_client = _make_mock_client(
            side_effect=httpx.ConnectError("Connection refused")
        )

        with patch("src.admin.service.httpx.AsyncClient", return_value=mock_client):
            result = await check_version()

        assert result.error == "Could not connect to GitHub"

    @patch("src.admin.service.settings")
    async def test_cache_prevents_second_request(
        self, mock_settings: MagicMock
    ) -> None:
        mock_settings.app_version = "2026.02.10"
        mock_settings.github_repo = "automationator/budge"

        mock_response = _make_mock_response(
            200,
            {
                "tag_name": "2026.02.12",
                "html_url": "https://github.com/automationator/budge/releases/tag/2026.02.12",
            },
        )
        mock_client = _make_mock_client(mock_response)

        with patch("src.admin.service.httpx.AsyncClient", return_value=mock_client):
            # First call should hit the API
            result1 = await check_version()
            assert result1.update_available is True

            # Second call should use cache (no new HTTP call)
            result2 = await check_version()
            assert result2.update_available is True

            # Only one HTTP call should have been made
            assert mock_client.get.call_count == 1

    @patch("src.admin.service.settings")
    async def test_rate_limit_returns_stale_cache(
        self, mock_settings: MagicMock
    ) -> None:
        import src.admin.service as svc

        mock_settings.app_version = "2026.02.10"
        mock_settings.github_repo = "automationator/budge"

        # Pre-populate stale cache
        from src.admin.schemas import VersionResponse

        svc._version_cache = VersionResponse(
            current_version="2026.02.10",
            latest_version="2026.02.11",
            update_available=True,
            release_url="https://github.com/automationator/budge/releases/tag/2026.02.11",
        )
        svc._version_cache_time = 0.0  # Expired

        mock_response = _make_mock_response(403)
        mock_client = _make_mock_client(mock_response)

        with patch("src.admin.service.httpx.AsyncClient", return_value=mock_client):
            result = await check_version()

        assert result.latest_version == "2026.02.11"
        assert result.update_available is True
        assert "rate limited" in result.error


class TestVersionEndpoint:
    async def test_non_admin_gets_403(self, authenticated_client: AsyncClient) -> None:
        response = await authenticated_client.get("/api/v1/admin/version")
        assert response.status_code == 403

    async def test_admin_gets_version(
        self,
        authenticated_client: AsyncClient,
        session: AsyncSession,
        test_user: User,
    ) -> None:
        # Make user admin via SQL so the function-scoped session sees it
        await session.execute(
            update(User).where(User.id == test_user.id).values(is_admin=True)
        )
        await session.flush()
        response = await authenticated_client.get("/api/v1/admin/version")
        assert response.status_code == 200
        data = response.json()
        assert "current_version" in data
        assert "update_available" in data
