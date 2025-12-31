# Enhanced Ping Monitor with Anomaly Detection

## Overview

Enhance the existing ping-monitor to store historical data, calculate baselines, detect anomalies, and provide context for AI-powered analysis. The system should be self-contained, deployable via Docker, and integrate with Datadog for metrics and Claude for intelligent alerting.

## Current State

Working ping-monitor that:
- Pings 37 hosts concurrently using icmplib
- Sends metrics to Datadog (custom.ping.*)
- Runs in Docker with NET_RAW capability
- Reads host config from hosts.json

## Goals

1. Store measurement history in SQLite (7-day retention)
2. Calculate rolling baselines per host
3. Detect anomalies in real-time
4. Build context snapshots for Claude analysis
5. Send intelligent alerts via Slack
6. Expose HTTP API for querying status and triggering analysis

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     ping-monitor container                       │
│                                                                  │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐  │
│  │  Pinger  │───▶│ Storage  │───▶│ Anomaly  │───▶│ Alerter  │  │
│  │          │    │ (SQLite) │    │ Detector │    │          │  │
│  └──────────┘    └──────────┘    └──────────┘    └──────────┘  │
│       │               │               │               │         │
│       │               │               │               ▼         │
│       │               │               │         ┌──────────┐   │
│       │               │               │         │  Slack   │   │
│       │               │               │         └──────────┘   │
│       │               │               │               │         │
│       ▼               ▼               ▼               ▼         │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                    HTTP API (FastAPI)                    │   │
│  │  GET /health, /status, /anomalies, /context, /analyze   │   │
│  └─────────────────────────────────────────────────────────┘   │
│       │                                                         │
└───────┼─────────────────────────────────────────────────────────┘
        │
        ▼
   ┌──────────┐     ┌──────────┐
   │ Datadog  │     │  Claude  │
   │  API     │     │   API    │
   └──────────┘     └──────────┘
```

## Database Schema

File: `schema.sql`

```sql
-- Enable WAL mode for better concurrent access
PRAGMA journal_mode=WAL;

-- Raw measurements (pruned to 7 days)
CREATE TABLE IF NOT EXISTS measurements (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp DATETIME DEFAULT (datetime('now')),
    host TEXT NOT NULL,
    ip TEXT NOT NULL,
    latency_ms REAL,
    packet_loss REAL,
    jitter_ms REAL,
    is_up INTEGER NOT NULL,
    site TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_measurements_host_ts ON measurements(host, timestamp);
CREATE INDEX IF NOT EXISTS idx_measurements_ts ON measurements(timestamp);

-- Rolling baselines per host
CREATE TABLE IF NOT EXISTS baselines (
    host TEXT PRIMARY KEY,
    ip TEXT NOT NULL,
    site TEXT NOT NULL,
    latency_mean REAL,
    latency_stddev REAL,
    latency_min REAL,
    latency_max REAL,
    latency_p50 REAL,
    latency_p95 REAL,
    latency_p99 REAL,
    typical_packet_loss REAL,
    typical_jitter REAL,
    uptime_pct REAL,
    sample_count INTEGER,
    first_seen DATETIME,
    updated_at DATETIME DEFAULT (datetime('now'))
);

-- Anomaly log
CREATE TABLE IF NOT EXISTS anomalies (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp DATETIME DEFAULT (datetime('now')),
    host TEXT NOT NULL,
    ip TEXT,
    site TEXT,
    anomaly_type TEXT NOT NULL,  -- latency_spike, packet_loss, host_down, host_recovery, jitter_spike
    severity TEXT NOT NULL,       -- info, warning, critical
    current_value REAL,
    baseline_value REAL,
    threshold REAL,
    deviation_factor REAL,
    message TEXT,
    context_snapshot TEXT,        -- JSON blob of related data at time of anomaly
    resolved_at DATETIME,
    resolution_duration_sec INTEGER,
    notified_at DATETIME,
    notification_channel TEXT
);

CREATE INDEX IF NOT EXISTS idx_anomalies_host_ts ON anomalies(host, timestamp);
CREATE INDEX IF NOT EXISTS idx_anomalies_unresolved ON anomalies(resolved_at) WHERE resolved_at IS NULL;

-- External events (UniFi, syslog, manual)
CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp DATETIME DEFAULT (datetime('now')),
    source TEXT NOT NULL,         -- unifi, syslog, manual, ping-monitor
    event_type TEXT NOT NULL,
    host TEXT,
    ip TEXT,
    site TEXT,
    message TEXT,
    raw_data TEXT,                -- JSON blob
    correlation_id TEXT           -- Link related events
);

CREATE INDEX IF NOT EXISTS idx_events_ts ON events(timestamp);
CREATE INDEX IF NOT EXISTS idx_events_host ON events(host);

-- Host topology/metadata (enriches hosts.json)
CREATE TABLE IF NOT EXISTS topology (
    host TEXT PRIMARY KEY,
    ip TEXT NOT NULL,
    site TEXT,
    device_type TEXT,
    connection_type TEXT,         -- wired, wifi
    upstream_switch TEXT,
    upstream_ap TEXT,
    upstream_port INTEGER,
    vlan INTEGER,
    mac_address TEXT,
    manufacturer TEXT,
    model TEXT,
    firmware TEXT,
    location TEXT,
    is_critical INTEGER DEFAULT 0,
    notes TEXT,
    updated_at DATETIME DEFAULT (datetime('now'))
);

-- Analysis history (Claude responses)
CREATE TABLE IF NOT EXISTS analysis_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp DATETIME DEFAULT (datetime('now')),
    trigger_type TEXT,            -- scheduled, manual, anomaly_threshold
    anomaly_count INTEGER,
    context_summary TEXT,
    claude_model TEXT,
    prompt_tokens INTEGER,
    completion_tokens INTEGER,
    analysis_text TEXT,
    recommended_actions TEXT,     -- JSON array
    acknowledged_at DATETIME,
    acknowledged_by TEXT
);
```

## Project Structure

```
ping-monitor/
├── ping_monitor/
│   ├── __init__.py
│   ├── main.py              # Entry point, orchestration
│   ├── config.py            # Settings via pydantic-settings
│   ├── models.py            # Pydantic models for data structures
│   ├── database.py          # SQLite connection, migrations
│   ├── pinger.py            # Concurrent ping logic (existing, refactored)
│   ├── storage.py           # Measurement storage, baseline calculation
│   ├── anomaly.py           # Anomaly detection logic
│   ├── alerter.py           # Slack notifications
│   ├── analyzer.py          # Claude API integration
│   ├── api.py               # FastAPI routes
│   └── utils.py             # Helpers (timestamp formatting, etc.)
├── schema.sql
├── hosts.json
├── topology.json            # Optional: enriched host metadata
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── .env.example
└── README.md
```

## Configuration

File: `config.py`

Environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| SITE_NAME | default | Unique identifier for this deployment |
| PING_INTERVAL | 60 | Seconds between ping cycles |
| PING_COUNT | 3 | ICMP packets per host |
| PING_TIMEOUT | 2 | Seconds to wait for response |
| DB_PATH | /data/ping-monitor.db | SQLite database location |
| DD_API_KEY | | Datadog API key |
| DD_SITE | datadoghq.com | Datadog region |
| ANTHROPIC_API_KEY | | Claude API key |
| SLACK_WEBHOOK_URL | | Slack incoming webhook |
| BASELINE_WINDOW_HOURS | 168 | Hours of history for baseline (7 days) |
| BASELINE_MIN_SAMPLES | 60 | Minimum samples before baseline is valid |
| ANOMALY_LATENCY_STDDEV | 3.0 | Stddev threshold for latency anomaly |
| ANOMALY_LOSS_THRESHOLD | 10 | Packet loss % to trigger anomaly |
| RETENTION_DAYS | 7 | Days to keep raw measurements |
| API_PORT | 8080 | HTTP API port |
| LOG_LEVEL | INFO | Logging verbosity |

## Implementation Phases

### Phase 1: Database & Storage

1. Set up SQLite with schema
2. Refactor pinger to store measurements after each cycle
3. Add data retention job (prune measurements older than 7 days)
4. Verify data is being stored correctly

Acceptance criteria:
- `measurements` table populated after each ping cycle
- Old data pruned automatically
- Database survives container restart (volume mount)

### Phase 2: Baseline Calculation

1. Implement baseline calculation using numpy/statistics
2. Run baseline update after each ping cycle (or every N cycles)
3. Calculate: mean, stddev, min, max, p50, p95, p99, uptime %
4. Store in `baselines` table

Acceptance criteria:
- Baselines calculated after minimum sample threshold met
- Baselines update incrementally (not full recalc each time)
- New hosts get baselines after ~1 hour of data

### Phase 3: Anomaly Detection

1. After each ping cycle, compare results to baselines
2. Detect anomaly types:
   - `host_down`: Host was up (per baseline), now unreachable
   - `host_recovery`: Host was down, now up
   - `latency_spike`: Latency > baseline_mean + (N * stddev)
   - `packet_loss`: Loss > threshold when baseline is 0
   - `jitter_spike`: Jitter significantly higher than normal
3. Store anomalies with context snapshot
4. Track resolution (when host recovers or returns to normal)

Anomaly severity logic:
```python
def calculate_severity(anomaly_type: str, deviation: float, baseline: Baseline) -> str:
    if anomaly_type == "host_down":
        return "critical" if baseline.is_critical else "warning"
    if anomaly_type == "latency_spike":
        if deviation > 10:
            return "critical"
        if deviation > 5:
            return "warning"
        return "info"
    if anomaly_type == "packet_loss":
        if current_loss > 50:
            return "critical"
        return "warning"
    return "info"
```

Acceptance criteria:
- Anomalies logged to database with context
- No duplicate anomalies for ongoing issues
- Resolved anomalies marked with resolution time

### Phase 4: HTTP API

FastAPI endpoints:

| Endpoint | Method | Description |
|----------|--------|-------------|
| /health | GET | Liveness check |
| /status | GET | Current status of all hosts |
| /status/{host} | GET | Detailed status for one host |
| /anomalies | GET | List anomalies (filters: active, severity, host, since) |
| /anomalies/{id}/resolve | POST | Manually resolve anomaly |
| /baselines | GET | Current baselines for all hosts |
| /baselines/{host} | GET | Baseline for one host |
| /context | GET | Build context blob for Claude |
| /analyze | POST | Trigger Claude analysis |
| /events | GET | List recent events |
| /events | POST | Add manual event |

Acceptance criteria:
- All endpoints return JSON
- Proper error handling and HTTP status codes
- Basic request validation

### Phase 5: Claude Integration

1. Build context generator that pulls:
   - Active anomalies with details
   - Affected host baselines
   - Correlated hosts (same switch/AP)
   - Recent events (last 1 hour)
   - Time-of-day context
2. Create prompt template for analysis
3. Implement Claude API call with retry logic
4. Parse response and store in `analysis_log`

Context format for Claude:
```markdown
## Network Anomaly Report
Generated: {timestamp}
Site: {site_name}

### Active Anomalies ({count})

| Host | Type | Severity | Current | Baseline | Duration |
|------|------|----------|---------|----------|----------|
| Living-Room-ATV | latency_spike | warning | 156ms | 5.2ms ±1.1 | 5m 30s |

### Topology Correlation
- Affected devices share upstream: Downstairs-Closet-AP
- Other devices on same AP: Sonos-3 (normal), Entertainment-Room-1 (normal)

### Recent Events
- 14:25:00 - unifi - AP channel changed (Downstairs-Closet-AP, 36 -> 44)
- 14:20:00 - ping-monitor - Baseline updated for 37 hosts

### Host Details

**Living-Room-ATV**
- IP: 192.168.1.38
- Type: media (Apple TV)
- Connection: wifi via Downstairs-Closet-AP
- Baseline: 5.2ms (σ=1.1ms, p95=7.8ms)
- Current: 156ms (30x stddev)
- History: Typically stable, last anomaly 3 days ago

### Time Context
- Local time: 2:30 PM Tuesday
- No scheduled maintenance windows
- Backup jobs run at 2:00 AM (not relevant)
```

Acceptance criteria:
- Context includes all relevant diagnostic info
- Claude response parsed and stored
- Analysis triggered automatically when critical anomalies accumulate

### Phase 6: Slack Alerting

1. Implement Slack webhook integration
2. Alert types:
   - Immediate: Critical anomalies (host_down on critical device)
   - Batched: Warning anomalies (digest every 5 minutes)
   - Analysis: When Claude analysis is triggered
3. Include action buttons (if using Slack app instead of webhook):
   - Acknowledge
   - View details (link to API)
   - Trigger analysis

Message format:
```
🔴 Critical: NAS1 is DOWN

Host: NAS1 (192.168.1.220)
Site: tay
Duration: 2m 15s
Last seen: 2025-12-31 14:30:42 UTC

This host is marked as critical.
Baseline uptime: 99.98%
```

Acceptance criteria:
- Critical alerts sent immediately
- Warnings batched to avoid spam
- Rate limiting to prevent flood

### Phase 7: Refinements

1. Add topology.json support for enriched host metadata
2. UniFi API integration for events (optional, Phase 2 project)
3. Prometheus metrics endpoint (/metrics)
4. Web UI for status dashboard (optional)
5. Historical analysis queries ("show me all anomalies last week")

## Docker Setup

File: `Dockerfile`

```dockerfile
FROM python:3.12-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY ping_monitor/ ./ping_monitor/
COPY schema.sql .

# Create data directory
RUN mkdir -p /data /config

ENV PYTHONUNBUFFERED=1

EXPOSE 8080

CMD ["python", "-m", "ping_monitor.main"]
```

File: `requirements.txt`

```
icmplib>=3.0
requests>=2.31
pydantic>=2.0
pydantic-settings>=2.0
fastapi>=0.109
uvicorn>=0.27
httpx>=0.26
numpy>=1.26
anthropic>=0.18
```

File: `docker-compose.yml`

```yaml
services:
  ping-monitor:
    build: .
    container_name: ping-monitor
    user: root
    cap_add:
      - NET_RAW
    ports:
      - "8080:8080"
    volumes:
      - ./hosts.json:/config/hosts.json:ro,z
      - ./topology.json:/config/topology.json:ro,z
      - ping-data:/data
    env_file:
      - .env
    restart: unless-stopped

volumes:
  ping-data:
```

## Testing

1. Unit tests for anomaly detection logic
2. Integration tests for database operations
3. Mock ping results for reproducible testing
4. Load test with simulated 30 hosts

Test scenarios:
- Host goes down and recovers
- Gradual latency increase (baseline shift)
- Sudden latency spike
- Packet loss event
- Multiple correlated failures (AP issue)

## Success Metrics

1. Anomalies detected within 1 ping cycle (60s)
2. False positive rate < 5%
3. Claude analysis provides actionable insights
4. Alert fatigue minimized via batching/dedup

## Open Questions

1. Should baselines adapt to time-of-day patterns? (e.g., higher latency during peak hours)
2. Integrate with Home Assistant for smart home context?
3. Add support for TCP/HTTP checks in addition to ICMP?
4. Multi-site aggregation in single dashboard?

## References

- Existing ping_monitor.py (working version)
- hosts.json format
- Datadog custom metrics API
- Anthropic Claude API docs
- FastAPI documentation
