# Rails 8 API Headend

**Status: Not yet implemented (Phase 2)**

This directory will contain the Rails 8 API-only application that serves as the central headend for the multi-site monitoring system.

## Planned Features

- RESTful API for measurement ingestion from monitors
- Site health monitoring (detects when sites stop reporting)
- Baseline calculation (rolling statistics)
- Anomaly detection (percentile-based thresholds)
- Claude AI integration with tool calling
- Slack alerting
- Background job processing (Solid Queue)
- Kamal 2 deployment configuration

## Technology Stack

- Ruby 3.3
- Rails 8 (API-only mode)
- Solid Queue (background jobs, no Redis needed)
- SQLite or Postgres
- Anthropic Ruby SDK (Claude)
- Tailscale (VPN diagnostics)

## Implementation Plan

See [Architecture Documentation](../docs/architecture.md) for detailed implementation phases.

### Phase 2: Rails API Scaffolding (Planned)
- [ ] `rails new ping-monitor-api --api`
- [ ] Database models (Site, Measurement, Baseline, Anomaly, AnalysisLog)
- [ ] Migrations
- [ ] API controllers
- [ ] API key authentication
- [ ] Solid Queue setup

### Future Phases
- Background jobs
- Baseline calculation
- Anomaly detection
- Site health monitoring
- Claude integration with tools
- Tailscale VPN integration
- Production deployment (Kamal 2)

## API Endpoints (Planned)

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/measurements` | Ingest measurements from monitors |
| GET | `/api/v1/sites` | List all sites with status |
| GET | `/api/v1/sites/:id` | Site details and recent activity |
| GET | `/api/v1/anomalies` | Active anomalies (filterable) |
| GET | `/api/v1/baselines/:host` | Baseline stats for host |
| POST | `/api/v1/analyze` | Trigger Claude analysis |

## Database Schema (Planned)

- `sites` - Site registry with health status
- `measurements` - Raw ping measurements
- `baselines` - Calculated baseline statistics
- `anomalies` - Detected anomalies with context
- `analysis_logs` - Claude analysis history

## Development

Will be initialized in Phase 2:

```bash
cd api/

# Initialize Rails app
rails new ping-monitor-api --api

# Set up database
bin/rails db:create db:migrate

# Start server
bin/rails server
```

## Deployment

Will use Kamal 2 for zero-downtime deployment:

```bash
# Initial deploy
kamal setup

# Deploy updates
kamal deploy

# View logs
kamal app logs -f
```

## See Also

- [Main README](../README.md) - Overall system architecture
- [Architecture Doc](../docs/architecture.md) - Complete design and phases
