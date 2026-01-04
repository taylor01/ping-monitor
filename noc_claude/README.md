# NC (NOC Claude)

An intelligent Network Operations Center agent that monitors your infrastructure, investigates alerts, and learns patterns over time.

## Overview

NC acts as a virtual NOC engineer:
- **Watches** for alerts from your ping-monitor Rails API
- **Correlates** events to identify cascading failures
- **Investigates** using tools (ping, VPN checks, history queries)
- **Learns** patterns from observations and human feedback
- **Escalates** with context when human attention is needed
- **Summarizes** overnight activity each morning

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                         NC Container                        │
│                                                             │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐     │
│  │  Main Loop  │───▶│   Claude    │───▶│   Tools     │     │
│  │  (poll)     │    │  Reasoning  │    │  Executor   │     │
│  └─────────────┘    └─────────────┘    └─────────────┘     │
│         │                                     │             │
│         ▼                                     ▼             │
│  ┌─────────────┐                      ┌─────────────┐      │
│  │   State     │◀─────────────────────│   SQLite    │      │
│  │  Manager    │                      │   (nc.db)   │      │
│  └─────────────┘                      └─────────────┘      │
│         │                                                   │
└─────────│───────────────────────────────────────────────────┘
          │
          ▼
    ┌─────────────┐
    │  Rails API  │
    │ (ping-monitor)
    └─────────────┘
```

## Quick Start

```bash
# 1. Clone and configure
cp .env.example .env
# Edit .env with your API keys

# 2. Create an Agent in the Rails API
# In Rails console:
#   Agent.create!(name: "noc-claude", secret: "your-secure-secret")
# Add the secret to your .env file

# 3. Edit config.yml with your sites and Tailscale IPs

# 4. Start NC
docker-compose up -d

# 5. View logs
docker-compose logs -f nc

# 6. Interact via CLI (optional)
docker-compose --profile cli run --rm nc-cli
```

## Configuration

### Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `ANTHROPIC_API_KEY` | Yes | Your Anthropic API key |
| `NC_AGENT_NAME` | Yes | Agent name registered in Rails (default: noc-claude) |
| `NC_AGENT_SECRET` | Yes | Agent secret for JWT authentication |

### config.yml

```yaml
rails_api:
  url: "http://ping-monitor-api:3000"
  agent_name: "${NC_AGENT_NAME}"
  agent_secret: "${NC_AGENT_SECRET}"

timezone: "America/New_York"

schedule:
  poll_interval_seconds: 30
  morning_summary_hour: 7
  quiet_hours_start: 22
  quiet_hours_end: 7

thresholds:
  watching_timeout_seconds: 120
  cascade_window_seconds: 30

sites:
  - name: home
    tailscale_ip: "100.x.x.x"
    critical_devices: [router, switch-main]
```

## Concern Levels

NC tracks each site's status:

| Level | Meaning |
|-------|---------|
| `NORMAL` | No active issues |
| `WATCHING` | Single alert, waiting to see if transient |
| `INVESTIGATING` | Multiple alerts or timeout, actively diagnosing |
| `ESCALATED` | Issue confirmed, humans notified |

## CLI Commands

When running in CLI mode:

```
status                    - Show current status of all sites
status <site>             - Show detailed status for a site
resolve <id> <cause>      - Mark incident resolved with root cause
learn <pattern>           - Teach NC a pattern
ask <question>            - Ask NC a question
incidents                 - Show pending incidents
patterns <site>           - Show learned patterns for a site
```

### Examples

```bash
# Mark an incident resolved
nc> resolve 1 "switch overheated, added fan"

# Teach NC a pattern
nc> learn nas.home reboots daily at 3:00 AM for backups

# Ask about recent activity
nc> ask what happened at cabin this week?
```

## Output Format

NC logs to stdout with structured formatting:

```
[2025-01-02 02:15:03] 🟡 WATCHING home: nas.home went DOWN
[2025-01-02 02:17:05] 🟡 WATCHING home: escalating - 3 more devices down
[2025-01-02 02:17:30] 🔍 INVESTIGATING home: ping switch-main.home FAILED
[2025-01-02 02:17:33] 🚨 ESCALATED home: switch-main.home down, 4 devices affected
[2025-01-02 07:00:00] ☀️ MORNING SUMMARY (Eastern)
```

## Morning Summary

At 7 AM (configurable), NC generates a summary:

```
═══════════════════════════════════════════════════════════════
☀️ MORNING SUMMARY (Eastern)
═══════════════════════════════════════════════════════════════

Good morning! Here's what happened overnight:

HOME:
  • 02:15-03:15 AM: switch-main.home failure (58 min)
    - 4 devices affected: nas, ap-garage, ap-living, camera-front
    - Recovered automatically
    - ❓ Root cause unknown - please advise

CABIN:
  • All clear overnight ✓

PENDING ACTIONS:
  1. [home] What caused switch-main.home to fail?
═══════════════════════════════════════════════════════════════
```

## Learning

NC learns in two ways:

### Automatic Learning
- **Cascade patterns**: When devices fail together, NC infers topology
- **Recovery patterns**: Devices that auto-recover within consistent timeframes

### Human Teaching
```bash
nc> learn nas.home reboots at 3 AM daily for backups
nc> learn cabin loses power during storms
```

## Rails API Requirements

NC expects these endpoints from your ping-monitor Rails API:

### Required (Phase 1)

```
GET /api/v1/alerts
  ?site=<site>           # Optional: filter by site
  ?status=active|resolved|all
  ?since=<ISO8601>       # Optional: only alerts since timestamp
  
Response:
{
  "alerts": [
    {
      "id": 123,
      "site": "home",
      "device": "nas",
      "alert_type": "down",
      "severity": "warning",
      "message": "Device unreachable",
      "started_at": "2025-01-02T02:15:00Z",
      "resolved_at": null
    }
  ]
}
```

### Optional (Phase 2)

```
GET /api/v1/alerts/history
  ?device=<device>
  ?site=<site>
  ?days=<int>

GET /api/v1/sites/<site>/status
GET /api/v1/anomalies
GET /health
```

## Development

```bash
# Run locally without Docker
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Run NC
python -m nc.main

# Run CLI
python -m nc.main --cli

# Run tests
pytest tests/
```

## Future Enhancements

- [ ] Slack integration for alerts and responses
- [ ] ServiceNow ticket creation
- [ ] UPS status checking
- [ ] Weather correlation
- [ ] Web dashboard
- [ ] Multi-site correlation (ISP-level issues)

## License

Private project - All rights reserved
