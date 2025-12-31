# Multi-Site Network Monitoring System

A distributed network monitoring system with intelligent anomaly detection and AI-powered analysis using Claude.

## Architecture

This system consists of two main components:

1. **Python Ping Monitor** (`monitor/`) - Lightweight ICMP ping collector deployed at each site
2. **Rails 8 API Headend** (`api/`) - Central data aggregation, analysis, and alerting system

```
┌─────────────────────────────────────────────────────────┐
│         REMOTE SITES (home, cabin, office)              │
│                                                          │
│  Python Monitor → Local Buffer → POST to Rails API      │
│                                ↓                         │
│                         Also → Datadog                   │
└─────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│                 RAILS 8 API HEADEND                     │
│                                                          │
│  • Data aggregation & storage                           │
│  • Baseline calculation                                 │
│  • Anomaly detection                                    │
│  • Site health monitoring                               │
│  • Claude AI analysis with tool calling                 │
│  • Slack alerting                                       │
└─────────────────────────────────────────────────────────┘
```

## Features

### Python Monitor (Per Site)
- 🔔 **ICMP Ping Monitoring** - Concurrent pinging of multiple hosts
- 💾 **Local Buffering** - SQLite buffer when API unreachable
- 📊 **Datadog Integration** - Metrics redundancy
- 🐳 **Docker** - Easy deployment with NET_RAW capability

### Rails API Headend (Future)
- 🏗️ **Rails 8 API-only mode** - RESTful API with Solid Queue
- 📈 **Baseline Calculation** - Rolling statistics for anomaly detection
- 🔍 **Anomaly Detection** - Percentile-based thresholds
- 🏥 **Site Health Monitoring** - Detects when sites stop reporting
- 🤖 **Claude AI Analysis** - Tool calling for active investigation
  - Ping from headend
  - Query historical data
  - Check correlated failures
  - **Tailscale VPN diagnostics** (ISP vs internal issues)
- 📢 **Slack Alerting** - Critical alerts with rate limiting

## Quick Start

### Current: Deploy Monitor (at each site)

```bash
cd monitor/

# Create .env from example
cp .env.example .env

# Edit .env with your settings
nano .env

# Edit hosts.json with your devices
nano hosts.json

# Start container
docker-compose up -d

# View logs
docker-compose logs -f
```

### Future: Deploy Rails Headend

```bash
cd api/
# (To be implemented in Phase 2)
```

## Project Structure

```
.
├── monitor/              # Python ping monitor
│   ├── ping_monitor.py   # Main monitoring script
│   ├── Dockerfile        # Container definition
│   ├── docker-compose.yml
│   ├── requirements.txt
│   ├── hosts.json        # Device list
│   └── .env.example
├── api/                  # Rails 8 API headend (future)
├── docs/                 # Documentation
│   ├── architecture.md   # Architecture review
│   └── enhanced-plan.md  # Original enhancement plan
├── .gitignore
└── README.md
```

## Configuration

### Monitor Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `SITE_NAME` | default | Unique site identifier (home, cabin, office) |
| `RAILS_API_URL` | - | URL of Rails headend API (future) |
| `API_KEY` | - | Authentication key for Rails API (future) |
| `DD_API_KEY` | - | Datadog API key |
| `DD_SITE` | datadoghq.com | Datadog region |
| `PING_INTERVAL` | 60 | Seconds between ping cycles |
| `PING_COUNT` | 3 | ICMP packets per host |
| `PING_TIMEOUT` | 2 | Seconds to wait for response |
| `MAX_WORKERS` | 20 | Concurrent metric submission workers |
| `CONFIG_URL` | - | Optional: Remote hosts.json URL |

### hosts.json Format

```json
[
  {
    "name": "router",
    "ip": "192.168.1.1",
    "description": "Main Router",
    "type": "router",
    "tags": ["critical", "network"]
  },
  {
    "name": "nas",
    "ip": "192.168.1.10",
    "description": "Network Storage",
    "type": "storage",
    "tags": ["critical"]
  }
]
```

**Fields:**
- `name` (required) - Display name (becomes Datadog host)
- `ip` (required) - IP address to ping
- `description` (optional) - Description tag
- `type` (optional) - Device type tag (router, switch, ap, storage, etc.)
- `tags` (optional) - Additional custom tags

## Current Metrics (Datadog)

| Metric | Description |
|--------|-------------|
| `custom.ping.reachable` | 1 = up, 0 = down |
| `custom.ping.latency_ms` | Average round-trip time |
| `custom.ping.packet_loss` | Packet loss percentage (0-100) |
| `custom.ping.jitter_ms` | Latency variation |

All metrics tagged with: `ip`, `site`, `device_type`, `description`, plus custom tags.

## Multi-Site Deployment

The same monitor container can be deployed to multiple sites with different configurations:

**Site 1 (Home):**
```bash
cd monitor/
# Edit .env: SITE_NAME=home
docker-compose up -d
```

**Site 2 (Cabin):**
```bash
cd monitor/
# Edit .env: SITE_NAME=cabin
docker-compose up -d
```

**Site 3 (Office):**
```bash
cd monitor/
# Edit .env: SITE_NAME=office
docker-compose up -d
```

All sites report to the same Datadog dashboard (and future Rails API), filterable by `site` tag.

## Datadog Dashboard

Import the pre-built dashboard:

1. Go to Datadog → Dashboards → New Dashboard
2. Click gear icon → Import dashboard JSON
3. Paste contents of `datadog-dashboard.json`

**Dashboard includes:**
- Hosts Up vs Down count
- Host status map
- All hosts status table
- Latency over time
- Packet loss trends
- Status by site
- Highest latency hosts
- Down hosts timeline

## Documentation

- **[Architecture Review](docs/architecture.md)** - Complete architectural analysis and Rails 8 implementation plan
- **[Enhanced Plan](docs/enhanced-plan.md)** - Original enhancement proposal

## Implementation Status

### ✅ Phase 0: Repository Setup (Current)
- [x] Git repository initialized
- [x] Directory structure created
- [x] Documentation organized
- [x] .gitignore configured
- [x] README files created

### 🚧 Phase 1: Python Monitor with Buffering
- [ ] Refactor monitor for Rails API posting
- [ ] Add local SQLite buffering
- [ ] Implement buffer drain logic
- [ ] Update Docker configuration

### 📋 Phase 2: Rails API Scaffolding
- [ ] Create Rails 8 API-only app
- [ ] Database models and migrations
- [ ] API controllers
- [ ] API key authentication
- [ ] Solid Queue setup

### 📋 Phase 3-9: Advanced Features
See [architecture.md](docs/architecture.md) for complete implementation phases including:
- Baseline calculation
- Anomaly detection
- Site health monitoring
- Slack alerting
- Claude AI integration
- Tailscale VPN diagnostics
- Production deployment

## Technology Stack

### Monitor
- Python 3.12
- icmplib (ICMP pinging)
- requests (HTTP client)
- SQLite (local buffering - future)
- Docker

### Headend (Future)
- Ruby 3.3
- Rails 8 (API-only)
- Solid Queue (background jobs, no Redis)
- SQLite or Postgres
- Anthropic Ruby SDK (Claude)
- Tailscale (VPN diagnostics)
- Kamal 2 (deployment)

## Requirements

### Monitor
- Docker with NET_RAW capability
- Network access to monitored devices
- Internet access for Datadog (and future Rails API)

### Headend (Future)
- VPS or cloud instance ($10-20/month)
- Domain name (optional, for SSL)
- Tailscale account (for VPN diagnostics)

## Alerting (Current)

Create monitors in Datadog:

**Host Down Alert:**
```
Metric: custom.ping.reachable
Alert when: avg by {host} < 1
For: 5 minutes
```

**High Latency Alert:**
```
Metric: custom.ping.latency_ms
Alert when: avg by {host} > 100ms
```

**Packet Loss Alert:**
```
Metric: custom.ping.packet_loss
Alert when: avg by {host} > 10%
```

## Future Enhancements

Once Rails API headend is deployed:
- Local anomaly detection with baselines
- Automatic site health monitoring
- Claude AI-powered root cause analysis
- Intelligent Slack alerting
- Historical data retention (7-30 days)
- Web UI dashboard
- Tailscale VPN diagnostics for differentiating ISP vs internal failures

## Contributing

This is a personal project for monitoring multiple properties.

## License

Private project - All rights reserved

## Support

See documentation in `docs/` or create an issue.
