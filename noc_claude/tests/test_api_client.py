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


class TestJSONAPIParsing:
    """Test JSON:API response parsing."""

    def test_build_included_lookup(self, api_client):
        """Builds lookup from included resources."""
        included = [
            {
                "id": "1",
                "type": "sites",
                "attributes": {"name": "home", "status": "active"}
            },
            {
                "id": "2",
                "type": "sites",
                "attributes": {"name": "cabin", "status": "active"}
            }
        ]

        lookup = api_client._build_included_lookup(included)

        assert lookup["sites:1"]["name"] == "home"
        assert lookup["sites:2"]["name"] == "cabin"

    def test_parse_jsonapi_anomaly_with_site(self, api_client):
        """Parses anomaly with site from included lookup."""
        included_lookup = {
            "sites:1": {"name": "home", "status": "active"}
        }

        item = {
            "id": "123",
            "type": "anomalies",
            "attributes": {
                "host": "router",
                "anomaly_type": "host_down",
                "severity": "critical",
                "message": "Host is down",
                "created_at": "2024-01-15T10:30:00Z",
                "resolved_at": None
            },
            "relationships": {
                "site": {
                    "data": {"id": "1", "type": "sites"}
                }
            }
        }

        result = api_client._parse_jsonapi_anomaly(item, included_lookup)

        assert result["id"] == "123"
        assert result["site"] == "home"
        assert result["device"] == "router"
        assert result["alert_type"] == "down"
        assert result["severity"] == "critical"

    def test_parse_jsonapi_anomaly_without_site_relationship(self, api_client):
        """Handles anomaly without site relationship gracefully."""
        included_lookup = {}

        item = {
            "id": "123",
            "type": "anomalies",
            "attributes": {
                "host": "router",
                "anomaly_type": "host_down",
                "severity": "warning",
                "message": "Host is down",
                "created_at": "2024-01-15T10:30:00Z",
                "resolved_at": None
            },
            "relationships": {}
        }

        result = api_client._parse_jsonapi_anomaly(item, included_lookup)

        assert result["site"] == ""
        assert result["device"] == "router"

    def test_parse_jsonapi_anomaly_site_not_in_included(self, api_client):
        """Handles missing site in included lookup."""
        included_lookup = {}  # Empty lookup

        item = {
            "id": "123",
            "type": "anomalies",
            "attributes": {
                "host": "router",
                "anomaly_type": "host_down",
                "severity": "warning",
                "message": "Host is down",
                "created_at": "2024-01-15T10:30:00Z",
                "resolved_at": None
            },
            "relationships": {
                "site": {
                    "data": {"id": "999", "type": "sites"}
                }
            }
        }

        result = api_client._parse_jsonapi_anomaly(item, included_lookup)

        assert result["site"] == ""

    def test_get_alerts_requests_include_site(self, api_client):
        """get_alerts requests site include."""
        mock_auth_response = Mock()
        mock_auth_response.status_code = 200
        mock_auth_response.json.return_value = {
            "data": {
                "access_token": "test-token",
                "refresh_token": "test-refresh",
                "expires_in": 3600,
                "scopes": []
            }
        }

        mock_alerts_response = Mock()
        mock_alerts_response.status_code = 200
        mock_alerts_response.json.return_value = {
            "data": [
                {
                    "id": "1",
                    "type": "anomalies",
                    "attributes": {
                        "host": "router",
                        "anomaly_type": "host_down",
                        "severity": "critical",
                        "message": "Down",
                        "created_at": "2024-01-15T10:30:00Z",
                        "resolved_at": None
                    },
                    "relationships": {
                        "site": {"data": {"id": "1", "type": "sites"}}
                    }
                }
            ],
            "included": [
                {
                    "id": "1",
                    "type": "sites",
                    "attributes": {"name": "home"}
                }
            ]
        }

        with patch("requests.post", return_value=mock_auth_response):
            with patch("requests.get", return_value=mock_alerts_response) as mock_get:
                alerts = api_client.get_alerts()

                # Verify include=site was passed
                call_args = mock_get.call_args
                assert call_args[1]["params"]["include"] == "site"

                # Verify site name was parsed correctly
                assert len(alerts) == 1
                assert alerts[0].site == "home"


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
