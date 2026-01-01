"""Tests for Rails API client"""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime, timezone
import httpx

from ping_monitor.api_client import RailsAPIClient
from ping_monitor.models import Host, PingResult, MeasurementBatch


class TestRailsAPIClient:
    """Tests for RailsAPIClient"""

    def test_init(self):
        """Test client initialization"""
        client = RailsAPIClient(
            base_url="https://api.example.com/",
            api_key="test-key",
            timeout=15.0,
            max_retries=5,
        )
        assert client.base_url == "https://api.example.com"  # trailing slash removed
        assert client.api_key == "test-key"
        assert client.timeout == 15.0
        assert client.max_retries == 5

    def test_init_defaults(self):
        """Test client initialization with defaults"""
        client = RailsAPIClient(base_url="https://api.example.com", api_key="key")
        assert client.timeout == 10.0
        assert client.max_retries == 3

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
            PingResult(
                host="switch",
                ip="192.168.1.2",
                timestamp=datetime.now(timezone.utc),
                is_up=False,
                latency_ms=None,
                packet_loss=100.0,
                jitter_ms=None,
            ),
        ]
        return MeasurementBatch(site="test-site", timestamp=datetime.now(timezone.utc), measurements=measurements)

    @pytest.mark.asyncio
    async def test_post_measurements_success(self, sample_batch):
        """Test successful measurement post"""
        client = RailsAPIClient(base_url="https://api.example.com", api_key="key")

        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.json.return_value = {
            "data": {
                "type": "measurement-batches",
                "id": "123",
                "attributes": {"count": 2, "site_name": "test-site"},
            }
        }
        mock_response.raise_for_status = MagicMock()

        with patch.object(client.client, "post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_response
            result = await client.post_measurements(sample_batch)

        assert result["success"] is True
        assert result["data"]["attributes"]["count"] == 2
        mock_post.assert_called_once()

    @pytest.mark.asyncio
    async def test_post_measurements_http_error(self, sample_batch):
        """Test handling of HTTP error response"""
        client = RailsAPIClient(base_url="https://api.example.com", api_key="key")

        mock_response = MagicMock()
        mock_response.status_code = 422
        mock_response.json.return_value = {
            "errors": [{"status": "422", "title": "Validation Error", "detail": "Invalid data"}]
        }

        http_error = httpx.HTTPStatusError(
            "422 Error", request=MagicMock(), response=mock_response
        )
        mock_response.raise_for_status.side_effect = http_error

        with patch.object(client.client, "post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_response
            result = await client.post_measurements(sample_batch)

        assert result["success"] is False
        assert len(result["errors"]) == 1
        assert result["errors"][0]["status"] == "422"

    @pytest.mark.asyncio
    async def test_post_measurements_network_error(self, sample_batch):
        """Test handling of network error"""
        client = RailsAPIClient(base_url="https://api.example.com", api_key="key")

        with patch.object(client.client, "post", new_callable=AsyncMock) as mock_post:
            mock_post.side_effect = httpx.RequestError("Connection failed")
            result = await client.post_measurements(sample_batch)

        assert result["success"] is False
        assert result["errors"][0]["title"] == "Network Error"

    @pytest.mark.asyncio
    async def test_health_check_success(self):
        """Test successful health check"""
        client = RailsAPIClient(base_url="https://api.example.com", api_key="key")

        mock_response = MagicMock()
        mock_response.status_code = 200

        with patch.object(client.client, "get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_response
            result = await client.health_check()

        assert result is True

    @pytest.mark.asyncio
    async def test_health_check_failure(self):
        """Test failed health check"""
        client = RailsAPIClient(base_url="https://api.example.com", api_key="key")

        with patch.object(client.client, "get", new_callable=AsyncMock) as mock_get:
            mock_get.side_effect = Exception("Connection refused")
            result = await client.health_check()

        assert result is False

    @pytest.mark.asyncio
    async def test_context_manager(self):
        """Test async context manager"""
        async with RailsAPIClient(
            base_url="https://api.example.com", api_key="key"
        ) as client:
            assert client is not None
            assert hasattr(client, "client")

    @pytest.mark.asyncio
    async def test_post_buffered_measurement_success(self):
        """Test posting buffered measurement from JSON string"""
        client = RailsAPIClient(base_url="https://api.example.com", api_key="key")

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
        client = RailsAPIClient(base_url="https://api.example.com", api_key="key")

        result = await client.post_buffered_measurement("not valid json")

        assert result["success"] is False
        assert "Post Error" in result["errors"][0]["title"]
