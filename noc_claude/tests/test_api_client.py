"""Tests for the Rails API client."""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch

from nc.api_client import (
    RailsAPIClient,
    MockRailsAPIClient,
    AuthenticationError,
    TokenExpiredError,
)
from nc.config import RailsAPIConfig


@pytest.fixture
def api_config():
    """Create a test API configuration."""
    return RailsAPIConfig(
        url="http://test-api.example.com",
        agent_name="test-agent",
        agent_secret="test-secret",
        timeout_seconds=10
    )


@pytest.fixture
def api_client(api_config):
    """Create a test API client."""
    return RailsAPIClient(api_config)


class TestRailsAPIClientInit:
    """Test API client initialization."""

    def test_init_strips_trailing_slash(self, api_config):
        """URL should have trailing slash stripped."""
        api_config.url = "http://test.com/"
        client = RailsAPIClient(api_config)
        assert client.base_url == "http://test.com"

    def test_init_stores_credentials(self, api_client):
        """Agent credentials should be stored."""
        assert api_client.agent_name == "test-agent"
        assert api_client.agent_secret == "test-secret"

    def test_init_no_token(self, api_client):
        """Client should start without a token."""
        assert api_client._access_token is None
        assert api_client._refresh_token is None
        assert not api_client.is_authenticated


class TestAuthentication:
    """Test JWT authentication flow."""

    def test_authenticate_success(self, api_client):
        """Successful authentication stores tokens."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": {
                "access_token": "test-access-token",
                "refresh_token": "test-refresh-token",
                "expires_in": 3600,
                "scopes": ["sites:read", "anomalies:read"]
            }
        }

        with patch("requests.post", return_value=mock_response):
            result = api_client.authenticate()

        assert result is True
        assert api_client._access_token == "test-access-token"
        assert api_client._refresh_token == "test-refresh-token"
        assert api_client._scopes == ["sites:read", "anomalies:read"]
        assert api_client.is_authenticated

    def test_authenticate_invalid_credentials(self, api_client):
        """Invalid credentials raise AuthenticationError."""
        mock_response = Mock()
        mock_response.status_code = 401

        with patch("requests.post", return_value=mock_response):
            with pytest.raises(AuthenticationError, match="Invalid agent credentials"):
                api_client.authenticate()

    def test_authenticate_inactive_account(self, api_client):
        """Inactive account raises AuthenticationError."""
        mock_response = Mock()
        mock_response.status_code = 403

        with patch("requests.post", return_value=mock_response):
            with pytest.raises(AuthenticationError, match="not active"):
                api_client.authenticate()


class TestTokenRefresh:
    """Test token refresh flow."""

    def test_refresh_success(self, api_client):
        """Successful refresh updates tokens."""
        api_client._refresh_token = "old-refresh-token"

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": {
                "access_token": "new-access-token",
                "refresh_token": "new-refresh-token",
                "expires_in": 3600,
                "scopes": ["sites:read"]
            }
        }

        with patch("requests.post", return_value=mock_response):
            result = api_client.refresh_access_token()

        assert result is True
        assert api_client._access_token == "new-access-token"
        assert api_client._refresh_token == "new-refresh-token"

    def test_refresh_no_token(self, api_client):
        """Refresh without token raises TokenExpiredError."""
        with pytest.raises(TokenExpiredError, match="No refresh token"):
            api_client.refresh_access_token()

    def test_refresh_expired_token(self, api_client):
        """Expired refresh token raises TokenExpiredError."""
        api_client._refresh_token = "expired-token"

        mock_response = Mock()
        mock_response.status_code = 401

        with patch("requests.post", return_value=mock_response):
            with pytest.raises(TokenExpiredError):
                api_client.refresh_access_token()


class TestMockClient:
    """Test mock API client for development."""

    def test_mock_authenticate(self):
        """Mock client can authenticate."""
        client = MockRailsAPIClient()
        assert client.authenticate() is True
        assert client.is_authenticated

    def test_mock_get_sites(self):
        """Mock client returns mock sites."""
        client = MockRailsAPIClient()
        sites = client.get_sites()
        assert len(sites) == 2
        assert sites[0]["name"] == "home"

    def test_mock_health_check(self):
        """Mock client always passes health check."""
        client = MockRailsAPIClient()
        assert client.health_check() is True
