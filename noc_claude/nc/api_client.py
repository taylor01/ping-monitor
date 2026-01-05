"""
NC Rails API Client

Communicates with the ping-monitor Rails API using JWT authentication.
"""

import requests
import threading
import time
import logging
from datetime import datetime, timedelta, timezone
from typing import List, Optional, Dict, Any

from nc.state import Alert

logger = logging.getLogger(__name__)


class AuthenticationError(Exception):
    """Raised when authentication fails."""
    pass


class TokenExpiredError(Exception):
    """Raised when token has expired and refresh failed."""
    pass


class RailsAPIClient:
    """Client for the ping-monitor Rails API with JWT authentication."""

    # Refresh token 5 minutes before expiry
    TOKEN_REFRESH_BUFFER_SECONDS = 300

    def __init__(self, config):
        """
        Initialize API client.

        Args:
            config: RailsAPIConfig with url, agent_name, agent_secret, timeout_seconds
        """
        self.base_url = config.url.rstrip('/')
        self.agent_name = config.agent_name
        self.agent_secret = config.agent_secret
        self.timeout = config.timeout_seconds

        # Token state
        self._access_token: Optional[str] = None
        self._refresh_token: Optional[str] = None
        self._token_expires_at: Optional[datetime] = None
        self._scopes: List[str] = []
        self._lock = threading.Lock()

    # =========================================================================
    # Authentication
    # =========================================================================

    def authenticate(self) -> bool:
        """
        Authenticate with the Rails API and obtain JWT tokens.

        Returns:
            True if authentication succeeded

        Raises:
            AuthenticationError: If authentication fails
        """
        url = f"{self.base_url}/api/v1/auth/token"

        try:
            response = requests.post(
                url,
                json={
                    "authenticatable_type": "agent",
                    "identifier": self.agent_name,
                    "secret": self.agent_secret
                },
                headers={
                    "Content-Type": "application/json",
                    "Accept": "application/json"
                },
                timeout=self.timeout
            )

            if response.status_code == 401:
                raise AuthenticationError("Invalid agent credentials")
            elif response.status_code == 403:
                raise AuthenticationError("Agent account is not active")

            response.raise_for_status()
            data = response.json().get("data", {})

            with self._lock:
                self._access_token = data.get("access_token")
                self._refresh_token = data.get("refresh_token")
                self._scopes = data.get("scopes", [])

                # Calculate expiration time
                expires_in = data.get("expires_in", 3600)
                self._token_expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in)

            logger.info(f"Authenticated as agent '{self.agent_name}' with scopes: {self._scopes}")
            return True

        except requests.exceptions.RequestException as e:
            raise AuthenticationError(f"Failed to authenticate: {e}")

    def refresh_access_token(self) -> bool:
        """
        Refresh the access token using the refresh token.

        Returns:
            True if refresh succeeded

        Raises:
            TokenExpiredError: If refresh token is invalid/expired
        """
        if not self._refresh_token:
            raise TokenExpiredError("No refresh token available")

        url = f"{self.base_url}/api/v1/auth/refresh"

        try:
            response = requests.post(
                url,
                json={"refresh_token": self._refresh_token},
                headers={
                    "Content-Type": "application/json",
                    "Accept": "application/json"
                },
                timeout=self.timeout
            )

            if response.status_code in (401, 403):
                raise TokenExpiredError("Refresh token expired or invalid")

            response.raise_for_status()
            data = response.json().get("data", {})

            with self._lock:
                self._access_token = data.get("access_token")
                self._refresh_token = data.get("refresh_token")
                self._scopes = data.get("scopes", [])

                expires_in = data.get("expires_in", 3600)
                self._token_expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in)

            logger.debug("Access token refreshed successfully")
            return True

        except requests.exceptions.RequestException as e:
            raise TokenExpiredError(f"Failed to refresh token: {e}")

    def ensure_authenticated(self):
        """
        Ensure we have a valid access token, authenticating or refreshing if needed.

        Raises:
            AuthenticationError: If authentication fails
            TokenExpiredError: If token refresh fails
        """
        with self._lock:
            has_token = self._access_token is not None
            is_expired = (
                self._token_expires_at is None or
                datetime.now(timezone.utc) >= self._token_expires_at - timedelta(seconds=self.TOKEN_REFRESH_BUFFER_SECONDS)
            )

        if not has_token:
            # No token yet, authenticate
            self.authenticate()
        elif is_expired:
            # Token expired or expiring soon, try to refresh
            try:
                self.refresh_access_token()
            except TokenExpiredError:
                # Refresh failed, re-authenticate
                logger.info("Refresh token expired, re-authenticating...")
                self.authenticate()

    @property
    def is_authenticated(self) -> bool:
        """Check if we have a valid (non-expired) access token."""
        with self._lock:
            if not self._access_token:
                return False
            if not self._token_expires_at:
                return False
            return datetime.now(timezone.utc) < self._token_expires_at

    # =========================================================================
    # HTTP Methods
    # =========================================================================

    def _headers(self) -> Dict[str, str]:
        """Get request headers with JWT authentication."""
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        with self._lock:
            if self._access_token:
                headers["Authorization"] = f"Bearer {self._access_token}"
        return headers

    def _get(self, endpoint: str, params: Dict = None) -> Dict:
        """Make authenticated GET request to API."""
        self.ensure_authenticated()

        url = f"{self.base_url}{endpoint}"
        response = requests.get(
            url,
            headers=self._headers(),
            params=params,
            timeout=self.timeout
        )

        # Handle token expiration mid-request
        if response.status_code == 401:
            logger.debug("Got 401, attempting re-authentication...")
            self.authenticate()
            response = requests.get(
                url,
                headers=self._headers(),
                params=params,
                timeout=self.timeout
            )

        response.raise_for_status()
        return response.json()

    def _post(self, endpoint: str, data: Dict) -> Dict:
        """Make authenticated POST request to API."""
        self.ensure_authenticated()

        url = f"{self.base_url}{endpoint}"
        response = requests.post(
            url,
            headers=self._headers(),
            json=data,
            timeout=self.timeout
        )

        # Handle token expiration mid-request
        if response.status_code == 401:
            logger.debug("Got 401, attempting re-authentication...")
            self.authenticate()
            response = requests.post(
                url,
                headers=self._headers(),
                json=data,
                timeout=self.timeout
            )

        response.raise_for_status()
        return response.json()

    def _patch(self, endpoint: str, data: Dict = None) -> Dict:
        """Make authenticated PATCH request to API."""
        self.ensure_authenticated()

        url = f"{self.base_url}{endpoint}"
        response = requests.patch(
            url,
            headers=self._headers(),
            json=data or {},
            timeout=self.timeout
        )

        # Handle token expiration mid-request
        if response.status_code == 401:
            logger.debug("Got 401, attempting re-authentication...")
            self.authenticate()
            response = requests.patch(
                url,
                headers=self._headers(),
                json=data or {},
                timeout=self.timeout
            )

        response.raise_for_status()
        return response.json()

    # =========================================================================
    # Alert Endpoints (consuming Rails anomalies as alerts)
    # =========================================================================

    def _map_anomaly_type(self, anomaly_type: str) -> str:
        """Map Rails anomaly types to NC alert types."""
        mapping = {
            'host_down': 'down',
            'latency_spike': 'high_latency',
            'packet_loss': 'packet_loss'
        }
        return mapping.get(anomaly_type, anomaly_type)

    def _build_included_lookup(self, included: List[Dict]) -> Dict[str, Dict]:
        """
        Build a lookup dict from JSON:API included resources.

        Returns:
            Dict mapping "type:id" -> resource attributes
        """
        lookup = {}
        for resource in included:
            res_type = resource.get('type', '')
            res_id = str(resource.get('id', ''))
            key = f"{res_type}:{res_id}"
            lookup[key] = resource.get('attributes', {})
        return lookup

    def _parse_jsonapi_anomaly(self, item: Dict, included_lookup: Dict[str, Dict]) -> Dict:
        """Parse a JSON:API anomaly item into NC alert format."""
        attrs = item.get('attributes', {})

        # Get site name from included resources via relationship
        site_name = ''
        relationships = item.get('relationships', {})
        site_rel = relationships.get('site', {}).get('data', {})
        if site_rel:
            site_key = f"{site_rel.get('type', 'sites')}:{site_rel.get('id', '')}"
            site_attrs = included_lookup.get(site_key, {})
            site_name = site_attrs.get('name', '')

        # For site-level anomalies (site_offline), host may be null
        device = attrs.get('host') or '[site]'

        return {
            'id': item.get('id'),
            'site': site_name,
            'device': device,
            'alert_type': self._map_anomaly_type(attrs.get('anomaly_type', 'unknown')),
            'severity': attrs.get('severity', 'warning'),
            'message': attrs.get('message', ''),
            'started_at': attrs.get('created_at'),
            'resolved_at': attrs.get('resolved_at')
        }

    def get_alerts(self, site: str = None, status: str = "active",
                   since: datetime = None, since_minutes: int = None) -> List[Alert]:
        """
        Fetch alerts (anomalies) from the API.

        Args:
            site: Filter by site name (note: API uses JWT site context)
            status: 'active', 'resolved', or 'all'
            since: Only alerts since this datetime
            since_minutes: Only alerts from last N minutes

        Returns:
            List of Alert objects
        """
        params = {
            'include': 'site'  # JSON:API include for site data
        }

        if status:
            params['status'] = status
        if since:
            params['since'] = since.isoformat()
        if since_minutes:
            since_dt = datetime.now(timezone.utc) - timedelta(minutes=since_minutes)
            params['since'] = since_dt.isoformat()

        # Call the Rails anomalies endpoint (JSON:API format)
        response = self._get("/api/v1/anomalies", params)

        # Build lookup from included resources
        included_lookup = self._build_included_lookup(response.get('included', []))

        # Parse JSON:API format
        alerts = []
        for item in response.get('data', []):
            alert_data = self._parse_jsonapi_anomaly(item, included_lookup)
            alerts.append(Alert.from_api(alert_data))

        return alerts

    def get_device_history(self, device: str, site: str, days: int = 7) -> List[Dict]:
        """
        Get alert history for a device.

        Args:
            device: Device name (host)
            site: Site name (for context, API uses JWT)
            days: Number of days to look back

        Returns:
            List of alert history entries
        """
        params = {
            'host': device,
            'days': days
        }

        # Call the Rails anomalies history endpoint (JSON:API format)
        response = self._get("/api/v1/anomalies/history", params)

        # Parse JSON:API format
        history = []
        for item in response.get('data', []):
            attrs = item.get('attributes', {})
            history.append({
                'id': item.get('id'),
                'alert_type': self._map_anomaly_type(attrs.get('anomaly_type', '')),
                'started_at': attrs.get('created_at'),
                'resolved_at': attrs.get('resolved_at'),
                'duration': attrs.get('duration')
            })

        return history

    def resolve_anomaly(self, anomaly_id: str, resolution_note: str = None) -> Dict:
        """
        Mark an anomaly as resolved.

        Args:
            anomaly_id: The anomaly ID to resolve
            resolution_note: Optional note about the resolution

        Returns:
            The updated anomaly data
        """
        data = {}
        if resolution_note:
            data['resolution_note'] = resolution_note

        response = self._patch(f"/api/v1/anomalies/{anomaly_id}/resolve", data)
        return response.get('data', {})

    # =========================================================================
    # Metrics/Status Endpoints
    # =========================================================================

    def get_site_status(self, site_id: str) -> Dict[str, Any]:
        """
        Get current status for a site.

        Args:
            site_id: Site ID

        Returns dict with device statuses, latencies, etc.
        Parses JSON:API format response.
        """
        response = self._get(f"/api/v1/sites/{site_id}/status")

        # Parse JSON:API format
        data = response.get('data', {})
        attrs = data.get('attributes', {})
        return {
            'site': attrs.get('name', ''),
            'status': attrs.get('status', 'unknown'),
            'devices': {
                'total': attrs.get('devices_total', 0),
                'up': attrs.get('devices_up', 0),
                'down': attrs.get('devices_down', 0)
            },
            'active_alerts': attrs.get('active_anomalies', 0),
            'last_data_at': attrs.get('last_data_at'),
            'devices_status': attrs.get('devices', [])
        }

    def get_sites(self) -> List[Dict[str, Any]]:
        """
        Get all sites accessible to this agent.

        Returns:
            List of site data dicts
        """
        response = self._get("/api/v1/sites")

        sites = []
        for item in response.get('data', []):
            attrs = item.get('attributes', {})
            sites.append({
                'id': item.get('id'),
                'name': attrs.get('name', ''),
                'healthy': attrs.get('healthy', False),
                'last_heartbeat': attrs.get('last_heartbeat')
            })
        return sites

    def get_device_metrics(self, site: str, device: str,
                          duration_minutes: int = 60) -> Dict[str, Any]:
        """
        Get recent metrics for a device.

        Returns latency, packet loss, availability over the time period.
        """
        params = {'duration': duration_minutes}
        data = self._get(f"/api/v1/sites/{site}/devices/{device}/metrics", params)
        return data

    # =========================================================================
    # Baseline/Anomaly Endpoints
    # =========================================================================

    def get_anomalies(self, site: str = None, since_minutes: int = 30) -> List[Dict]:
        """
        Get recent anomalies detected by the Rails API.

        These are baseline deviations, not just down/up alerts.
        Parses JSON:API format response.
        """
        params = {}
        if since_minutes:
            since_dt = datetime.now(timezone.utc) - timedelta(minutes=since_minutes)
            params['since'] = since_dt.isoformat()

        response = self._get("/api/v1/anomalies", params)

        # Parse JSON:API format
        anomalies = []
        for item in response.get('data', []):
            attrs = item.get('attributes', {})
            anomalies.append({
                'id': item.get('id'),
                'host': attrs.get('host', ''),
                'anomaly_type': attrs.get('anomaly_type', ''),
                'severity': attrs.get('severity', 'warning'),
                'message': attrs.get('message', ''),
                'current_value': attrs.get('current_value'),
                'baseline_value': attrs.get('baseline_value'),
                'created_at': attrs.get('created_at'),
                'resolved_at': attrs.get('resolved_at')
            })

        return anomalies

    # =========================================================================
    # Health Check
    # =========================================================================

    def health_check(self) -> bool:
        """Check if the API is reachable (no auth required)."""
        try:
            url = f"{self.base_url}/health"
            response = requests.get(url, timeout=self.timeout)
            return response.status_code == 200
        except Exception:
            return False


class MockRailsAPIClient:
    """Mock API client for testing without a real Rails API."""

    def __init__(self, config=None):
        self.alerts = []
        self.history = {}
        self._authenticated = False

    def authenticate(self) -> bool:
        """Mock authentication."""
        self._authenticated = True
        return True

    def ensure_authenticated(self):
        """Mock ensure authenticated."""
        if not self._authenticated:
            self.authenticate()

    @property
    def is_authenticated(self) -> bool:
        return self._authenticated

    def add_mock_alert(self, alert: Alert):
        """Add a mock alert for testing."""
        self.alerts.append(alert)

    def get_alerts(self, site: str = None, status: str = "active",
                   since: datetime = None, since_minutes: int = None) -> List[Alert]:
        """Return mock alerts."""
        result = self.alerts

        if site:
            result = [a for a in result if a.site == site]
        if status == "active":
            result = [a for a in result if a.resolved_at is None]
        elif status == "resolved":
            result = [a for a in result if a.resolved_at is not None]

        return result

    def get_device_history(self, device: str, site: str, days: int = 7) -> List[Dict]:
        """Return mock device history."""
        key = f"{device}@{site}"
        return self.history.get(key, [])

    def get_sites(self) -> List[Dict[str, Any]]:
        """Return mock sites."""
        return [
            {'id': '1', 'name': 'home', 'healthy': True, 'last_heartbeat': None},
            {'id': '2', 'name': 'cabin', 'healthy': True, 'last_heartbeat': None}
        ]

    def health_check(self) -> bool:
        """Always healthy in mock mode."""
        return True
