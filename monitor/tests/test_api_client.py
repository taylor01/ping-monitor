"""Tests for Rails API client with JWT authentication"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime, timezone
import httpx
import time

from ping_monitor.api_client import RailsAPIClient, AuthenticationError
from ping_monitor.models import PingResult, MeasurementBatch


class TestRailsAPIClient:
    """Tests for RailsAPIClient"""

    def test_init(self):
        """Test client initialization"""
        client = RailsAPIClient(
            base_url="https://api.example.com/",
            site_name="test-site",
            site_secret="test-secret",
            timeout=15.0,
            max_retries=5,
        )
        assert client.base_url == "https://api.example.com"
        assert client.site_name == "test-site"
        assert client.site_secret == "test-secret"
        assert client.timeout == 15.0
        assert client.max_retries == 5

    def test_init_defaults(self):
        """Test client initialization with defaults"""
        client = RailsAPIClient(
            base_url="https://api.example.com",
            site_name="site",
            site_secret="secret",
        )
        assert client.timeout == 10.0
        assert client.max_retries == 3

    def test_is_authenticated_no_token(self):
        """Test is_authenticated returns False when no token"""
        client = RailsAPIClient(
            base_url="https://api.example.com",
            site_name="site",
            site_secret="secret",
        )
        assert client.is_authenticated is False

    def test_is_authenticated_with_valid_token(self):
        """Test is_authenticated returns True with valid token"""
        client = RailsAPIClient(
            base_url="https://api.example.com",
            site_name="site",
            site_secret="secret",
        )
        client._access_token = "valid-token"
        client._token_expires_at = time.time() + 3600  # 1 hour from now
        assert client.is_authenticated is True

    def test_is_authenticated_expired_token(self):
        """Test is_authenticated returns False when token expired"""
        client = RailsAPIClient(
            base_url="https://api.example.com",
            site_name="site",
            site_secret="secret",
        )
        client._access_token = "expired-token"
        client._token_expires_at = time.time() - 100  # Expired
        assert client.is_authenticated is False

    @pytest.fixture
    def sample_batch(self):
        """Create a sample measurement batch"""
        measurements = [
            PingResult(
                host="router",
                ip="192.168.1.1",
                timestamp=datetime.now(timezone.utc),
                is_up=True,
                latency_ms=5.0,
                packet_loss=0.0,
                jitter_ms=1.0,
            ),
        ]
        return MeasurementBatch(
            site="test-site",
            timestamp=datetime.now(timezone.utc),
            measurements=measurements,
        )

    @pytest.mark.asyncio
    async def test_authenticate_success(self):
        """Test successful authentication"""
        client = RailsAPIClient(
            base_url="https://api.example.com",
            site_name="test-site",
            site_secret="secret",
        )

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": {
                "access_token": "access-123",
                "refresh_token": "refresh-456",
                "expires_in": 3600,
            }
        }

        with patch.object(client.client, "post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_response
            result = await client.authenticate()

        assert result is True
        assert client._access_token == "access-123"
        assert client._refresh_token == "refresh-456"
        mock_post.assert_called_once()

    @pytest.mark.asyncio
    async def test_authenticate_failure(self):
        """Test failed authentication"""
        client = RailsAPIClient(
            base_url="https://api.example.com",
            site_name="test-site",
            site_secret="wrong-secret",
        )

        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.text = "Invalid credentials"

        with patch.object(client.client, "post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_response
            result = await client.authenticate()

        assert result is False
        assert client._access_token is None

    @pytest.mark.asyncio
    async def test_refresh_access_token_success(self):
        """Test successful token refresh"""
        client = RailsAPIClient(
            base_url="https://api.example.com",
            site_name="test-site",
            site_secret="secret",
        )
        client._refresh_token = "old-refresh-token"

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": {
                "access_token": "new-access-123",
                "refresh_token": "new-refresh-456",
                "expires_in": 3600,
            }
        }

        with patch.object(client.client, "post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_response
            result = await client.refresh_access_token()

        assert result is True
        assert client._access_token == "new-access-123"
        assert client._refresh_token == "new-refresh-456"

    @pytest.mark.asyncio
    async def test_post_measurements_success(self, sample_batch):
        """Test successful measurement post with authentication"""
        client = RailsAPIClient(
            base_url="https://api.example.com",
            site_name="test-site",
            site_secret="secret",
        )
        # Pre-authenticate
        client._access_token = "valid-token"
        client._token_expires_at = time.time() + 3600

        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.json.return_value = {
            "data": {
                "type": "measurement-batches",
                "id": "123",
                "attributes": {"count": 1, "site_name": "test-site"},
            }
        }
        mock_response.raise_for_status = MagicMock()

        with patch.object(client.client, "post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_response
            result = await client.post_measurements(sample_batch)

        assert result["success"] is True
        mock_post.assert_called_once()
        # Verify auth header was included
        call_kwargs = mock_post.call_args[1]
        assert call_kwargs["headers"]["Authorization"] == "Bearer valid-token"

    @pytest.mark.asyncio
    async def test_post_measurements_auto_authenticates(self, sample_batch):
        """Test that post_measurements authenticates if needed"""
        client = RailsAPIClient(
            base_url="https://api.example.com",
            site_name="test-site",
            site_secret="secret",
        )

        auth_response = MagicMock()
        auth_response.status_code = 200
        auth_response.json.return_value = {
            "data": {
                "access_token": "new-token",
                "refresh_token": "refresh-token",
                "expires_in": 3600,
            }
        }

        post_response = MagicMock()
        post_response.status_code = 201
        post_response.json.return_value = {
            "data": {"type": "measurement-batches", "id": "123"}
        }
        post_response.raise_for_status = MagicMock()

        with patch.object(client.client, "post", new_callable=AsyncMock) as mock_post:
            mock_post.side_effect = [auth_response, post_response]
            result = await client.post_measurements(sample_batch)

        assert result["success"] is True
        assert mock_post.call_count == 2  # auth + post

    @pytest.mark.asyncio
    async def test_post_measurements_retries_on_401(self, sample_batch):
        """Test that 401 triggers token refresh and retry"""
        client = RailsAPIClient(
            base_url="https://api.example.com",
            site_name="test-site",
            site_secret="secret",
        )
        client._access_token = "expired-token"
        client._refresh_token = "refresh-token"
        client._token_expires_at = time.time() + 3600

        # First post returns 401
        unauthorized_response = MagicMock()
        unauthorized_response.status_code = 401

        # Refresh succeeds
        refresh_response = MagicMock()
        refresh_response.status_code = 200
        refresh_response.json.return_value = {
            "data": {
                "access_token": "new-token",
                "refresh_token": "new-refresh",
                "expires_in": 3600,
            }
        }

        # Retry succeeds
        success_response = MagicMock()
        success_response.status_code = 201
        success_response.json.return_value = {
            "data": {"type": "measurement-batches", "id": "123"}
        }
        success_response.raise_for_status = MagicMock()

        with patch.object(client.client, "post", new_callable=AsyncMock) as mock_post:
            mock_post.side_effect = [
                unauthorized_response,
                refresh_response,
                success_response,
            ]
            result = await client.post_measurements(sample_batch)

        assert result["success"] is True
        assert mock_post.call_count == 3

    @pytest.mark.asyncio
    async def test_post_measurements_network_error(self, sample_batch):
        """Test handling of network error"""
        client = RailsAPIClient(
            base_url="https://api.example.com",
            site_name="test-site",
            site_secret="secret",
        )
        client._access_token = "valid-token"
        client._token_expires_at = time.time() + 3600

        with patch.object(client.client, "post", new_callable=AsyncMock) as mock_post:
            mock_post.side_effect = httpx.RequestError("Connection failed")
            result = await client.post_measurements(sample_batch)

        assert result["success"] is False
        assert result["errors"][0]["title"] == "Network Error"

    @pytest.mark.asyncio
    async def test_health_check_success(self):
        """Test successful health check"""
        client = RailsAPIClient(
            base_url="https://api.example.com",
            site_name="site",
            site_secret="secret",
        )

        mock_response = MagicMock()
        mock_response.status_code = 200

        with patch.object(client.client, "get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_response
            result = await client.health_check()

        assert result is True

    @pytest.mark.asyncio
    async def test_health_check_failure(self):
        """Test failed health check"""
        client = RailsAPIClient(
            base_url="https://api.example.com",
            site_name="site",
            site_secret="secret",
        )

        with patch.object(client.client, "get", new_callable=AsyncMock) as mock_get:
            mock_get.side_effect = Exception("Connection refused")
            result = await client.health_check()

        assert result is False

    @pytest.mark.asyncio
    async def test_context_manager(self):
        """Test async context manager"""
        async with RailsAPIClient(
            base_url="https://api.example.com",
            site_name="site",
            site_secret="secret",
        ) as client:
            assert client is not None
            assert hasattr(client, "client")

    @pytest.mark.asyncio
    async def test_post_buffered_measurement_success(self):
        """Test posting buffered measurement from JSON string"""
        client = RailsAPIClient(
            base_url="https://api.example.com",
            site_name="site",
            site_secret="secret",
        )
        client._access_token = "valid-token"
        client._token_expires_at = time.time() + 3600

        payload_json = '{"data": {"type": "measurements", "attributes": {}}}'

        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.json.return_value = {"data": {"id": "123"}}
        mock_response.raise_for_status = MagicMock()

        with patch.object(client.client, "post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_response
            result = await client.post_buffered_measurement(payload_json)

        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_post_buffered_measurement_invalid_json(self):
        """Test posting invalid JSON from buffer"""
        client = RailsAPIClient(
            base_url="https://api.example.com",
            site_name="site",
            site_secret="secret",
        )
        client._access_token = "valid-token"
        client._token_expires_at = time.time() + 3600

        result = await client.post_buffered_measurement("not valid json")

        assert result["success"] is False
        assert "Post Error" in result["errors"][0]["title"]
