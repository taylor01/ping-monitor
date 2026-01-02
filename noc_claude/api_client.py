"""
NC Rails API Client

Communicates with the ping-monitor Rails API.
"""

import requests
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any

from nc.state import Alert


class RailsAPIClient:
    """Client for the ping-monitor Rails API."""
    
    def __init__(self, config):
        """
        Initialize API client.
        
        Args:
            config: RailsAPIConfig with url, api_key, timeout_seconds
        """
        self.base_url = config.url.rstrip('/')
        self.api_key = config.api_key
        self.timeout = config.timeout_seconds
        
    def _headers(self) -> Dict[str, str]:
        """Get request headers."""
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers
        
    def _get(self, endpoint: str, params: Dict = None) -> Dict:
        """Make GET request to API."""
        url = f"{self.base_url}{endpoint}"
        response = requests.get(
            url,
            headers=self._headers(),
            params=params,
            timeout=self.timeout
        )
        response.raise_for_status()
        return response.json()
        
    def _post(self, endpoint: str, data: Dict) -> Dict:
        """Make POST request to API."""
        url = f"{self.base_url}{endpoint}"
        response = requests.post(
            url,
            headers=self._headers(),
            json=data,
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

    def _parse_jsonapi_anomaly(self, item: Dict, site_name: str = '') -> Dict:
        """Parse a JSON:API anomaly item into NC alert format."""
        attrs = item.get('attributes', {})
        return {
            'id': item.get('id'),
            'site': site_name,
            'device': attrs.get('host', ''),
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
        params = {}

        if status:
            params['status'] = status
        if since:
            params['since'] = since.isoformat()
        if since_minutes:
            since_dt = datetime.utcnow() - timedelta(minutes=since_minutes)
            params['since'] = since_dt.isoformat()

        # Call the Rails anomalies endpoint (JSON:API format)
        response = self._get("/api/v1/anomalies", params)

        # Parse JSON:API format
        alerts = []
        for item in response.get('data', []):
            alert_data = self._parse_jsonapi_anomaly(item, site or '')
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
        
    # =========================================================================
    # Metrics/Status Endpoints
    # =========================================================================

    def get_site_status(self, site_id: str) -> Dict[str, Any]:
        """
        Get current status for a site.

        Args:
            site_id: Site ID (from JWT context or known ID)

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
            since_dt = datetime.utcnow() - timedelta(minutes=since_minutes)
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
        """Check if the API is reachable."""
        try:
            self._get("/health")
            return True
        except Exception:
            return False


class MockRailsAPIClient:
    """Mock API client for testing without a real Rails API."""
    
    def __init__(self, config=None):
        self.alerts = []
        self.history = {}
        
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
        
    def health_check(self) -> bool:
        """Always healthy in mock mode."""
        return True
