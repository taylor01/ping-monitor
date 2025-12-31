# Python Ping Monitor

Lightweight ICMP ping monitoring container that sends metrics to Datadog and (future) Rails API.

## Quick Start

```bash
# Create .env file
cp .env.example .env

# Edit configuration
nano .env
nano hosts.json

# Start monitor
docker-compose up -d

# View logs
docker-compose logs -f
```

## Files

| File | Description |
|------|-------------|
| `ping_monitor.py` | Main monitoring script |
| `Dockerfile` | Container image definition |
| `docker-compose.yml` | Docker Compose configuration |
| `requirements.txt` | Python dependencies |
| `hosts.json` | List of devices to monitor |
| `.env.example` | Environment variable template |

## Configuration

### Environment Variables (.env)

See `.env.example` for all available options.

**Required:**
- `DD_API_KEY` - Your Datadog API key
- `SITE_NAME` - Unique identifier for this site (e.g., "home", "cabin", "office")

**Optional:**
- `RAILS_API_URL` - Future: URL of Rails headend API
- `API_KEY` - Future: Authentication for Rails API
- `PING_INTERVAL` - Seconds between ping cycles (default: 60)
- `PING_COUNT` - ICMP packets per host (default: 3)
- `PING_TIMEOUT` - Timeout in seconds (default: 2)

### hosts.json Format

```json
[
  {
    "name": "router",
    "ip": "192.168.1.1",
    "description": "Main Router",
    "type": "router",
    "tags": ["critical"]
  }
]
```

**Fields:**
- `name` (required) - Display name
- `ip` (required) - IP address to ping
- `description` (optional) - Device description
- `type` (optional) - Device type (router, switch, ap, camera, nas, etc.)
- `tags` (optional) - Additional tags array

## Current Behavior

1. Loads hosts from `hosts.json`
2. Pings all hosts concurrently every 60 seconds (configurable)
3. Sends 4 metrics per host to Datadog:
   - `custom.ping.reachable` (1/0)
   - `custom.ping.latency_ms`
   - `custom.ping.packet_loss`
   - `custom.ping.jitter_ms`

## Future Behavior

Once Rails API is deployed:

1. Posts measurements to Rails API
2. Buffers locally (SQLite) when API unreachable
3. Drains buffer when API returns
4. Still sends to Datadog (redundancy)

## Docker Requirements

- Requires `NET_RAW` capability for ICMP pinging
- Must run as root (required for raw sockets)
- See `docker-compose.yml` for configuration

## Troubleshooting

**No metrics in Datadog:**
- Check `DD_API_KEY` is correct
- Verify network connectivity: `docker-compose logs`
- Ensure `DD_SITE` matches your Datadog region

**Ping failures:**
- Verify hosts.json IPs are correct
- Check network connectivity from container
- Ensure NET_RAW capability is granted

**Container won't start:**
- Check `.env` file exists
- Verify hosts.json is valid JSON
- Review logs: `docker-compose logs`

## Development

```bash
# Test locally without Docker
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Set environment variables
export DD_API_KEY=your_key
export SITE_NAME=dev

# Run
python ping_monitor.py
```

## See Also

- [Main README](../README.md) - Overall system architecture
- [Architecture Doc](../docs/architecture.md) - Rails 8 headend design
