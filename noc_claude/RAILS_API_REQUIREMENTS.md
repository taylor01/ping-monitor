# Rails API Endpoints Required for NC

This document specifies the API endpoints that NC (NOC Claude) expects from the ping-monitor Rails API.

## Phase 1: Essential Endpoints

These are required for NC to function.

### GET /api/v1/alerts

Fetch alerts from the monitoring system.

**Query Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `site` | string | No | Filter by site name |
| `status` | string | No | `active`, `resolved`, or `all` (default: `active`) |
| `since` | ISO8601 | No | Only alerts created/updated after this time |

**Response:**
```json
{
  "alerts": [
    {
      "id": 123,
      "site": "home",
      "device": "nas",
      "alert_type": "down",
      "severity": "warning",
      "message": "Device unreachable for 5 minutes",
      "started_at": "2025-01-02T02:15:00Z",
      "resolved_at": null
    },
    {
      "id": 124,
      "site": "home",
      "device": "ap-garage",
      "alert_type": "down",
      "severity": "warning",
      "message": "Device unreachable for 5 minutes",
      "started_at": "2025-01-02T02:15:05Z",
      "resolved_at": null
    }
  ],
  "meta": {
    "total": 2,
    "active": 2,
    "resolved": 0
  }
}
```

**Alert Types:**
- `down` - Device not responding to ping
- `high_latency` - Latency above threshold
- `packet_loss` - Packet loss above threshold
- `recovered` - Device came back online (resolved_at will be set)

**Severity Levels:**
- `info` - Informational
- `warning` - Needs attention
- `critical` - Requires immediate attention

### GET /health

Simple health check endpoint.

**Response:**
```json
{
  "status": "ok",
  "timestamp": "2025-01-02T12:00:00Z"
}
```

---

## Phase 2: Enhanced Endpoints

These enable richer NC functionality.

### GET /api/v1/alerts/history

Get historical alerts for a specific device.

**Query Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `device` | string | Yes | Device name |
| `site` | string | Yes | Site name |
| `days` | integer | No | Lookback period (default: 7) |

**Response:**
```json
{
  "device": "nas",
  "site": "home",
  "history": [
    {
      "id": 100,
      "alert_type": "down",
      "started_at": "2025-01-01T03:00:00Z",
      "resolved_at": "2025-01-01T03:05:00Z",
      "duration": "5m"
    },
    {
      "id": 95,
      "alert_type": "high_latency",
      "started_at": "2024-12-28T14:30:00Z",
      "resolved_at": "2024-12-28T14:35:00Z",
      "duration": "5m"
    }
  ]
}
```

### GET /api/v1/sites/:site/status

Get current status summary for a site.

**Response:**
```json
{
  "site": "home",
  "status": "degraded",
  "devices": {
    "total": 15,
    "up": 12,
    "down": 3
  },
  "active_alerts": 3,
  "last_data_at": "2025-01-02T12:00:00Z",
  "devices_status": [
    {
      "name": "router",
      "ip": "192.168.1.1",
      "status": "up",
      "latency_ms": 1.2,
      "packet_loss": 0
    },
    {
      "name": "nas",
      "ip": "192.168.1.10",
      "status": "down",
      "last_seen": "2025-01-02T11:55:00Z"
    }
  ]
}
```

### GET /api/v1/anomalies

Get anomalies detected by baseline analysis.

**Query Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `site` | string | No | Filter by site |
| `since_minutes` | integer | No | Lookback period (default: 30) |

**Response:**
```json
{
  "anomalies": [
    {
      "id": 50,
      "site": "home",
      "device": "ap-garage",
      "anomaly_type": "latency_spike",
      "message": "Latency 150ms, baseline is 5ms (30x higher)",
      "detected_at": "2025-01-02T11:45:00Z",
      "current_value": 150,
      "baseline_value": 5,
      "deviation_factor": 30
    }
  ]
}
```

---

## Phase 3: Future Endpoints

Nice-to-have for advanced features.

### GET /api/v1/sites/:site/devices/:device/metrics

Get recent metrics for a device.

**Query Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `duration` | integer | No | Minutes of data (default: 60) |

**Response:**
```json
{
  "device": "router",
  "site": "home",
  "period": {
    "start": "2025-01-02T11:00:00Z",
    "end": "2025-01-02T12:00:00Z"
  },
  "metrics": {
    "availability": 100.0,
    "avg_latency_ms": 1.5,
    "max_latency_ms": 3.2,
    "min_latency_ms": 0.8,
    "packet_loss_pct": 0.0
  },
  "data_points": 60
}
```

### POST /api/v1/incidents (optional)

Allow NC to create incidents in the Rails system.

**Request:**
```json
{
  "site": "home",
  "summary": "switch-main.home failure affecting 4 devices",
  "severity": "normal",
  "devices_affected": ["switch-main", "ap-garage", "ap-living", "camera-front"],
  "nc_analysis": "VPN healthy, likely internal switch failure"
}
```

**Response:**
```json
{
  "id": 200,
  "created_at": "2025-01-02T12:00:00Z"
}
```

---

## Authentication

NC uses JWT authentication with the Agent authenticatable type.

### Getting a Token

```bash
# Authenticate as an agent
curl -X POST https://api.example.com/api/v1/auth/token \
  -H "Content-Type: application/json" \
  -d '{
    "authenticatable_type": "agent",
    "identifier": "noc-claude",
    "secret": "your-agent-secret"
  }'

# Response:
{
  "data": {
    "access_token": "eyJ...",
    "refresh_token": "eyJ...",
    "token_type": "Bearer",
    "expires_in": 3600,
    "scopes": ["sites:read", "anomalies:read", "anomalies:write"]
  }
}
```

### Using the Token

All API endpoints require Bearer token authentication:

```
Authorization: Bearer <access_token>
```

Endpoints should return:
- `401 Unauthorized` if no token or token expired
- `403 Forbidden` if token lacks required scope

### Token Refresh

Access tokens expire after 1 hour. Use the refresh token to get new tokens:

```bash
curl -X POST https://api.example.com/api/v1/auth/refresh \
  -H "Content-Type: application/json" \
  -d '{"refresh_token": "eyJ..."}'
```

NC handles token refresh automatically.

---

## Implementation Notes

### For the Rails Side

1. **Alert Generation**: Create alerts when:
   - Device goes from UP to DOWN (or vice versa)
   - Latency exceeds threshold (configurable per-device)
   - Packet loss exceeds threshold

2. **Alert Resolution**: Auto-resolve alerts when:
   - DOWN device comes back UP
   - Latency/packet_loss returns to normal

3. **Include `since` filtering**: NC polls frequently, so efficient filtering is important.

4. **Timestamps**: Use ISO8601 format with timezone (UTC preferred).

### Example Rails Controller

```ruby
# app/controllers/api/v1/alerts_controller.rb
class Api::V1::AlertsController < ApplicationController
  before_action :authenticate_api_key!
  
  def index
    alerts = Alert.all
    
    alerts = alerts.where(site: params[:site]) if params[:site]
    
    case params[:status]
    when 'active'
      alerts = alerts.where(resolved_at: nil)
    when 'resolved'
      alerts = alerts.where.not(resolved_at: nil)
    end
    
    if params[:since]
      since = Time.parse(params[:since])
      alerts = alerts.where('updated_at > ?', since)
    end
    
    render json: {
      alerts: alerts.map { |a| alert_json(a) },
      meta: {
        total: alerts.count,
        active: alerts.where(resolved_at: nil).count,
        resolved: alerts.where.not(resolved_at: nil).count
      }
    }
  end
  
  private
  
  def alert_json(alert)
    {
      id: alert.id,
      site: alert.site,
      device: alert.device,
      alert_type: alert.alert_type,
      severity: alert.severity,
      message: alert.message,
      started_at: alert.started_at.iso8601,
      resolved_at: alert.resolved_at&.iso8601
    }
  end
end
```

---

## Testing NC Without Rails

NC includes a `MockRailsAPIClient` for testing:

```python
from nc.api_client import MockRailsAPIClient
from nc.state import Alert
from datetime import datetime

mock = MockRailsAPIClient()
mock.add_mock_alert(Alert(
    id="1",
    site="home",
    device="nas",
    alert_type="down",
    severity="warning",
    message="Test alert",
    started_at=datetime.utcnow()
))

# NC can now use mock.get_alerts()
```
