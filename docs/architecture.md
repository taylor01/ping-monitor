# Ping Monitor Enhancement Plan - Multi-Site Rails Architecture

## Executive Summary

After architectural review, we're pivoting to a **multi-site architecture** using **Rails 8 API-only mode** as the headend. This approach provides superior scalability, separation of concerns, and intelligent monitoring capabilities compared to the original self-contained Python approach.

**Key Decision**: Deploy lightweight Python ping monitors at each site (3 houses) that report to a centralized Rails 8 API headend with intelligent Claude-powered analysis and site health monitoring.

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                      REMOTE SITES (3 Houses)                        │
└─────────────────────────────────────────────────────────────────────┘

Site: home                Site: cabin              Site: office
┌──────────────┐         ┌──────────────┐         ┌──────────────┐
│Ping Monitor  │         │Ping Monitor  │         │Ping Monitor  │
│(Python)      │         │(Python)      │         │(Python)      │
│              │         │              │         │              │
│• Pings hosts │         │• Pings hosts │         │• Pings hosts │
│  every 60s   │         │  every 60s   │         │  every 60s   │
│              │         │              │         │              │
│• Local SQLite│         │• Local SQLite│         │• Local SQLite│
│  buffer      │         │  buffer      │         │  buffer      │
│              │         │              │         │              │
│• POST → API  │         │• POST → API  │         │• POST → API  │
│  (when up)   │         │  (when up)   │         │  (when up)   │
│              │         │              │         │              │
│• Datadog     │         │• Datadog     │         │• Datadog     │
└──────┬───────┘         └──────┬───────┘         └──────┬───────┘
       │                        │                        │
       │ POST /api/v1/measurements                      │
       └────────────────────────┼────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│               HEADEND (Rails 8 API - Separate Container)            │
│                                                                     │
│  ┌──────────────────────────────────────────────────────────┐     │
│  │                   RESTful API (Rails)                     │     │
│  │  POST   /api/v1/measurements    # Ingest from monitors   │     │
│  │  GET    /api/v1/sites           # All sites status       │     │
│  │  GET    /api/v1/sites/:id       # Site details           │     │
│  │  GET    /api/v1/anomalies       # Active anomalies       │     │
│  │  POST   /api/v1/analyze         # Trigger analysis       │     │
│  └──────────────────────────────────────────────────────────┘     │
│                                                                     │
│  ┌──────────────────────────────────────────────────────────┐     │
│  │              Database (SQLite/Postgres)                   │     │
│  │  • sites (name, last_heartbeat, status)                  │     │
│  │  • measurements (site, host, timestamp, latency, ...)    │     │
│  │  • baselines (site, host, stats)                         │     │
│  │  • anomalies (site, host, type, severity)                │     │
│  │  • analysis_logs (claude responses, tool calls)          │     │
│  └──────────────────────────────────────────────────────────┘     │
│                                                                     │
│  ┌──────────────────────────────────────────────────────────┐     │
│  │    Background Jobs (Solid Queue - no Redis needed!)      │     │
│  │                                                           │     │
│  │  MeasurementIngestionJob     # Store incoming data       │     │
│  │  BaselineCalculationJob      # Every 15 min             │     │
│  │  AnomalyDetectionJob         # After ingestion          │     │
│  │  SiteHealthCheckJob          # Every 5 min ⭐           │     │
│  │  ClaudeAnalysisJob           # When triggered ⭐        │     │
│  │  DataRetentionJob            # Daily cleanup            │     │
│  └──────────────────────────────────────────────────────────┘     │
│                                                                     │
└─────────────────────────────┬───────────────────────────────────────┘
                              │
                    ┌─────────┴──────────┐
                    ▼                    ▼
          ┌────────────────────┐   ┌──────────────┐
          │  Claude with Tools │   │ Slack Alerts │
          │                    │   └──────────────┘
          │  Available Tools:  │
          │  • ping_from_head  │
          │  • query_data      │
          │  • check_site      │
          │  • tailscale_ping  │⭐
          │  • get_topology    │
          └────────────────────┘
```

---

## Current State Analysis

**Strengths of existing implementation**:
- Clean, functional 171-line Python script
- Reliable concurrent ICMP monitoring with icmplib
- Successful Datadog integration (37 hosts, 60s intervals)
- Docker-ready with proper NET_RAW capabilities
- Battle-tested in production

**Why Multi-Site Architecture?**
- User has **3 houses** to monitor (home, cabin, office)
- Need centralized visibility across all sites
- Want intelligent analysis when entire sites go offline
- Separation allows independent scaling and deployment
- Rails 8 features (Solid Queue, Kamal) are perfect for this

---

## Architecture Decisions

### Core Architecture: Multi-Site with Rails Headend

| Component | Technology | Rationale |
|-----------|-----------|-----------|
| **Ping Monitors** (3x) | Python + icmplib | Lightweight, battle-tested, minimal dependencies |
| **Local Buffering** | SQLite per site | Resilient when headend unreachable |
| **Headend API** | Rails 8 API-only | RESTful conventions, Solid Queue, Kamal deployment |
| **Background Jobs** | Solid Queue | No Redis dependency, built into Rails 8 |
| **Database** | SQLite or Postgres | SQLite for simplicity, Postgres for scale |
| **Claude Integration** | Anthropic Ruby SDK | Tool calling for active investigation |
| **Alerting** | Slack webhooks | Simple, effective, no extra services |
| **Deployment** | Kamal 2 | Zero-downtime deploys, simple config |

### Why Rails 8 Instead of Python FastAPI?

**Advantages of Rails**:
✅ **Multi-site native** - RESTful API perfect for multiple collectors
✅ **Solid Queue** - Background jobs without Redis
✅ **Conventions** - RESTful routing, migrations, ActiveRecord
✅ **Web UI future** - Trivial to add later (just enable views)
✅ **Kamal 2** - Deployment is dead simple
✅ **Maturity** - Proven at scale for 20+ years
✅ **Separation** - Collectors and analysis are independent

**Tradeoff**:
⚠️ Language mix (Python + Ruby) - requires both skill sets
⚠️ Two applications to manage instead of one
⚠️ Network dependency between monitor and API

**Decision**: Rails is the right choice for multi-site architecture with future web UI.

---

## Component Design

### 1. Python Ping Monitor (Per Site)

**Purpose**: Lightweight ICMP collector with local buffering

**Key Features**:
- Pings hosts every 60 seconds
- Posts results to Rails API via HTTP
- Buffers to local SQLite when API unreachable
- Drains buffer when API returns
- Still posts to Datadog (redundancy)

**Technology Stack**:
- Python 3.12
- icmplib (ICMP pinging)
- httpx (async HTTP client)
- SQLite (local buffer)

**Docker per site**:
```yaml
services:
  ping-monitor:
    build: .
    environment:
      - SITE_NAME=home  # or cabin, office
      - RAILS_API_URL=https://monitoring.yourdomain.com
      - API_KEY_FILE=/run/secrets/api_key
    cap_add:
      - NET_RAW
    volumes:
      - ./hosts.json:/config/hosts.json:ro
      - ping-buffer:/data
    restart: unless-stopped
```

**Key Code Pattern**:
```python
async def run():
    while True:
        # Ping all hosts
        results = await ping_hosts()

        # Try posting to Rails API
        success = await post_to_api(results)

        if not success:
            buffer_locally(results)
        else:
            drain_buffer()  # Send buffered data

        # Also send to Datadog
        await send_to_datadog(results)

        await asyncio.sleep(60)
```

---

### 2. Rails 8 API Headend

**Purpose**: Central data aggregation, analysis, alerting

**Key Features**:
- RESTful API for measurement ingestion
- Site health monitoring (detects when sites stop reporting)
- Baseline calculation (rolling statistics)
- Anomaly detection (percentile-based)
- Claude integration with tool calling
- Slack alerting with batching
- Background job processing (Solid Queue)

**Technology Stack**:
- Ruby 3.3
- Rails 8 (API-only mode)
- Solid Queue (background jobs)
- SQLite or Postgres
- Anthropic Ruby SDK (Claude)

**Key Models**:
```ruby
# app/models/site.rb
class Site < ApplicationRecord
  has_many :measurements
  has_many :anomalies
  has_many :baselines

  def healthy?
    last_heartbeat && last_heartbeat > 5.minutes.ago
  end

  def status
    return "offline" unless healthy?
    return "critical" if active_critical_anomalies.any?
    return "warning" if active_warning_anomalies.any?
    "healthy"
  end
end

# app/models/measurement.rb
class Measurement < ApplicationRecord
  belongs_to :site

  after_create :update_site_heartbeat
  after_create :trigger_anomaly_detection
end

# app/models/anomaly.rb
class Anomaly < ApplicationRecord
  belongs_to :site

  enum severity: { info: 0, warning: 1, critical: 2 }
  enum anomaly_type: {
    host_down: 0,
    host_recovery: 1,
    latency_spike: 2,
    packet_loss: 3,
    site_offline: 4  # Entire site stopped reporting
  }

  after_create :send_alert, if: :critical?
  after_create :maybe_trigger_claude_analysis
end
```

**Critical Background Jobs**:

```ruby
# app/jobs/site_health_check_job.rb
# Runs every 5 minutes via cron
class SiteHealthCheckJob < ApplicationJob
  def perform
    Site.find_each do |site|
      next if site.healthy?

      # Site hasn't reported in >5 minutes
      create_site_offline_anomaly(site)
      trigger_claude_investigation(site)
    end
  end
end

# app/jobs/claude_analysis_job.rb
class ClaudeAnalysisJob < ApplicationJob
  def perform(anomaly_id:, use_tools: false)
    context = build_context(anomaly_id)
    tools = define_tools if use_tools

    response = anthropic_client.messages.create(
      model: "claude-3-5-sonnet-20241022",
      max_tokens: 2000,
      tools: tools,
      messages: [{ role: "user", content: context }]
    )

    process_response_and_tool_calls(response)
  end
end
```

---

### 3. Claude Tool Calling System

**Purpose**: Enable Claude to actively investigate network issues

**Available Tools**:

#### 1. `ping_from_headend`
```ruby
{
  name: "ping_from_headend",
  description: "Ping a host from the Rails server to check external reachability",
  input_schema: {
    type: "object",
    properties: {
      ip: { type: "string", description: "IP address to ping" },
      count: { type: "integer", default: 3 }
    },
    required: ["ip"]
  }
}

# Implementation
def execute_ping_from_headend(ip, count)
  result = `ping -c #{count} #{ip} 2>&1`
  {
    ip: ip,
    reachable: $?.success?,
    output: result,
    latency_ms: parse_latency(result)
  }
end
```

#### 2. `tailscale_ping` ⭐ NEW
```ruby
{
  name: "tailscale_ping",
  description: "Connect via Tailscale VPN to ping a host on the internal site network",
  input_schema: {
    type: "object",
    properties: {
      site: { type: "string", description: "Site name (home, cabin, office)" },
      ip: { type: "string", description: "Internal IP address" },
      count: { type: "integer", default: 3 }
    },
    required: ["site", "ip"]
  }
}

# Implementation
def execute_tailscale_ping(site, ip, count)
  # Use Tailscale to reach internal network
  # Assumes headend container has Tailscale installed
  tailscale_ip = TAILSCALE_EXIT_NODES[site]

  result = `tailscale ping --c #{count} --exit-node=#{tailscale_ip} #{ip} 2>&1`
  {
    site: site,
    ip: ip,
    reachable_via_tailscale: $?.success?,
    output: result
  }
end
```

#### 3. `query_recent_measurements`
```ruby
{
  name: "query_recent_measurements",
  description: "Query measurement history for a site or specific host",
  input_schema: {
    type: "object",
    properties: {
      site: { type: "string" },
      host: { type: "string" },
      since_minutes: { type: "integer", default: 60 }
    },
    required: ["site"]
  }
}

# Implementation
def query_recent_measurements(site:, host: nil, since_minutes: 60)
  query = Measurement.where(site: Site.find_by(name: site))
                    .where("timestamp > ?", since_minutes.minutes.ago)
  query = query.where(host: host) if host
  query.order(timestamp: :desc).limit(100).to_json
end
```

#### 4. `check_correlated_failures`
```ruby
{
  name: "check_correlated_failures",
  description: "Check if multiple hosts at a site are down (indicates network/power issue)",
  input_schema: {
    type: "object",
    properties: {
      site: { type: "string" }
    },
    required: ["site"]
  }
}

# Implementation
def check_correlated_failures(site)
  site_obj = Site.find_by(name: site)
  recent = site_obj.measurements.where("timestamp > ?", 10.minutes.ago)

  {
    total_hosts: site_obj.measurements.select(:host).distinct.count,
    hosts_down: recent.where(is_up: false).select(:host).distinct.count,
    all_affected: recent.where(is_up: false).count == recent.count
  }
end
```

#### 5. `get_site_topology`
```ruby
{
  name: "get_site_topology",
  description: "Get network topology (router, switches, APs, dependencies)",
  input_schema: {
    type: "object",
    properties: {
      site: { type: "string" }
    },
    required: ["site"]
  }
}
```

**Example Claude Investigation Flow**:

```
User: Site "home" is offline

[SiteHealthCheckJob detects no heartbeat for 8 minutes]
[Creates site_offline anomaly, triggers ClaudeAnalysisJob]

Claude: I'll investigate why the 'home' site stopped reporting.

[Tool: check_correlated_failures("home")]
→ Result: {"total_hosts": 37, "hosts_down": 37, "all_affected": true}

Claude: All hosts down simultaneously. Site-wide issue. Checking external reachability...

[Tool: ping_from_headend("home-router-external-ip")]
→ Result: {"reachable": false, "output": "100% packet loss"}

Claude: Router unreachable from internet. Let me try via Tailscale VPN...

[Tool: tailscale_ping("home", "192.168.1.1")]
→ Result: {"reachable_via_tailscale": true, "latency_ms": 45}

Claude: ✅ Router IS reachable via Tailscale VPN!

Analysis:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🟡 PARTIAL OUTAGE: Home Network

Root Cause: ISP connection loss, but internal network operational

Evidence:
• All hosts unreachable from internet (external ping failed)
• Router accessible via Tailscale VPN (internal network up)
• Ping monitor at site can't reach API (no internet)
• Pattern indicates ISP outage, NOT power loss

Recommended Actions:
1. Check ISP status page
2. Modem power cycle (if remote access available)
3. Monitoring will resume when ISP restored

Impact: Site monitoring offline, but devices functional internally
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

## Database Schema (Rails Migrations)

```ruby
# db/migrate/001_create_sites.rb
create_table :sites do |t|
  t.string :name, null: false, index: { unique: true }
  t.datetime :last_heartbeat
  t.string :status, default: "unknown"
  t.jsonb :topology_data
  t.timestamps
end

# db/migrate/002_create_measurements.rb
create_table :measurements do |t|
  t.references :site, null: false, foreign_key: true
  t.datetime :timestamp, null: false, index: true
  t.string :host, null: false
  t.string :ip, null: false
  t.float :latency_ms
  t.float :packet_loss
  t.float :jitter_ms
  t.boolean :is_up, null: false
  t.timestamps
end

add_index :measurements, [:site_id, :host, :timestamp]
add_index :measurements, [:site_id, :timestamp]

# db/migrate/003_create_baselines.rb
create_table :baselines do |t|
  t.references :site, null: false, foreign_key: true
  t.string :host, null: false
  t.string :ip
  t.float :latency_mean
  t.float :latency_stddev
  t.float :latency_p95
  t.float :latency_p99
  t.integer :sample_count
  t.datetime :window_start
  t.datetime :window_end
  t.timestamps
end

add_index :baselines, [:site_id, :host], unique: true

# db/migrate/004_create_anomalies.rb
create_table :anomalies do |t|
  t.references :site, null: false, foreign_key: true
  t.references :measurement, foreign_key: true
  t.string :host
  t.integer :anomaly_type, null: false
  t.integer :severity, null: false
  t.float :current_value
  t.float :baseline_value
  t.text :message
  t.jsonb :context_snapshot
  t.datetime :resolved_at
  t.timestamps
end

add_index :anomalies, [:site_id, :created_at]
add_index :anomalies, :resolved_at
add_index :anomalies, [:severity, :created_at], where: "resolved_at IS NULL"

# db/migrate/005_create_analysis_logs.rb
create_table :analysis_logs do |t|
  t.references :anomaly, foreign_key: true
  t.string :trigger_type
  t.string :claude_model
  t.integer :prompt_tokens
  t.integer :completion_tokens
  t.text :analysis_text
  t.jsonb :tool_calls
  t.jsonb :recommended_actions
  t.timestamps
end
```

---

## Implementation Phases

### Phase 1: Python Monitor with Buffering (Week 1)
**Goal**: Get lightweight monitors running at each site

**Tasks**:
- [ ] Create Python ping monitor (refactor existing)
- [ ] Add local SQLite buffering
- [ ] Implement HTTP POST to Rails API
- [ ] Add buffer drain logic
- [ ] Keep Datadog integration
- [ ] Docker Compose per site

**Deliverables**:
- `ping-monitor/` Python package
- `docker-compose.yml` per site
- Local buffer working when API down

**Acceptance**: Monitor pings hosts, posts to API (mock), buffers when offline

---

### Phase 2: Rails API Scaffolding (Week 1-2)
**Goal**: Rails 8 API accepting measurements

**Tasks**:
- [ ] `rails new ping-monitor-api --api`
- [ ] Create models (Site, Measurement, Baseline, Anomaly, AnalysisLog)
- [ ] Database migrations
- [ ] API controllers (measurements#create, sites#index, sites#show)
- [ ] API key authentication
- [ ] Solid Queue setup

**Deliverables**:
- Rails API accepting POST /api/v1/measurements
- Database schema complete
- API authentication working

**Acceptance**: Python monitors can post to Rails, data stored

---

### Phase 3: Background Jobs & Baselines (Week 2)
**Goal**: Automated baseline calculation

**Tasks**:
- [ ] MeasurementIngestionJob (async storage)
- [ ] BaselineCalculationJob (every 15 min)
- [ ] Implement incremental baseline calculation
- [ ] Add cron schedule for jobs
- [ ] `/api/v1/baselines` endpoint

**Deliverables**:
- Baselines calculated automatically
- Background job processing working

**Acceptance**: Baselines appear after 1 hour of data collection

---

### Phase 4: Anomaly Detection (Week 3)
**Goal**: Detect and store anomalies

**Tasks**:
- [ ] AnomalyDetectionJob (triggered after ingestion)
- [ ] Percentile-based thresholds (p95/p99)
- [ ] Host down/recovery detection
- [ ] Cold start fallback (absolute thresholds)
- [ ] `/api/v1/anomalies` endpoint

**Deliverables**:
- Anomalies detected and stored
- API endpoint to query anomalies

**Acceptance**: Anomalies detected within 1 ping cycle (60s)

---

### Phase 5: Site Health Monitoring (Week 3)
**Goal**: Headend monitors site heartbeats

**Tasks**:
- [ ] SiteHealthCheckJob (every 5 min)
- [ ] Site.healthy? logic
- [ ] Create site_offline anomalies
- [ ] Update site status field
- [ ] `/api/v1/sites` status dashboard endpoint

**Deliverables**:
- Headend detects when sites stop reporting
- Site status tracked (healthy/warning/critical/offline)

**Acceptance**: When monitor stops, headend detects within 5 min

---

### Phase 6: Basic Slack Alerting (Week 4)
**Goal**: Critical alerts to Slack

**Tasks**:
- [ ] Slack webhook integration
- [ ] Alert on critical anomalies (host_down for critical hosts)
- [ ] Alert on site_offline
- [ ] Rate limiting (max 1/min per anomaly)
- [ ] Message formatting

**Deliverables**:
- Slack notifications for critical events
- Rate limiting prevents spam

**Acceptance**: Slack message sent within 60s of critical anomaly

---

### Phase 7: Claude Integration with Tools (Week 4-5)
**Goal**: AI-powered analysis with active investigation

**Tasks**:
- [ ] ClaudeAnalysisJob
- [ ] Tool definitions (ping_from_headend, query_data, check_correlated)
- [ ] Tool execution handlers
- [ ] Response parsing and storage
- [ ] `/api/v1/analyze` endpoint
- [ ] Token usage tracking

**Deliverables**:
- Claude can investigate anomalies
- Tool calls execute successfully
- Analysis stored in database

**Acceptance**: Claude provides actionable analysis using tools

---

### Phase 8: Tailscale Integration (Week 5)
**Goal**: Claude can check internal network via VPN

**Tasks**:
- [ ] Install Tailscale in Rails container
- [ ] Configure exit nodes per site
- [ ] `tailscale_ping` tool implementation
- [ ] Test VPN connectivity from headend
- [ ] Add to Claude tool list

**Deliverables**:
- Tailscale connection from headend to sites
- Claude can diagnose ISP vs internal issues

**Acceptance**: Claude successfully uses Tailscale to reach internal hosts

---

### Phase 9: Deployment & Monitoring (Week 6)
**Goal**: Production deployment with observability

**Tasks**:
- [ ] Kamal 2 configuration
- [ ] Deploy Rails to production environment
- [ ] Configure domain and SSL (Let's Encrypt)
- [ ] Structured logging (Rails logger → JSON)
- [ ] Health check endpoints
- [ ] Monitor the monitor (headend health)
- [ ] Database backups (daily)

**Deliverables**:
- Rails API deployed and accessible
- Zero-downtime deployment working
- Logs structured and searchable

**Acceptance**: All 3 sites reporting to production API

---

## Deployment Strategy

### Kamal 2 Configuration

```yaml
# config/deploy.yml
service: ping-monitor-api
image: your-registry/ping-monitor-api

servers:
  web:
    hosts:
      - monitoring.yourdomain.com
    labels:
      traefik.http.routers.api.rule: Host(`monitoring.yourdomain.com`)
    options:
      network: "private"

env:
  clear:
    RAILS_ENV: production
  secret:
    - RAILS_MASTER_KEY
    - DATABASE_URL
    - ANTHROPIC_API_KEY
    - SLACK_WEBHOOK_URL
    - TAILSCALE_AUTH_KEY

volumes:
  - "ping-monitor-data:/rails/storage"

accessories:
  worker:
    image: your-registry/ping-monitor-api
    cmd: bundle exec rake solid_queue:start
    hosts:
      - monitoring.yourdomain.com

  tailscale:
    image: tailscale/tailscale:latest
    cmd: tailscaled
    volumes:
      - "tailscale-data:/var/lib/tailscale"
```

### Deployment Commands

```bash
# Initial deploy
kamal setup

# Deploy updates (zero downtime)
kamal deploy

# View logs
kamal app logs -f

# Run Rails console
kamal app exec -i 'bin/rails console'

# Database migrations
kamal app exec 'bin/rails db:migrate'
```

---

## Technology Stack Summary

### Python Ping Monitor (Per Site)
- Python 3.12
- icmplib (ICMP)
- httpx (async HTTP)
- SQLite (local buffer)
- Docker with NET_RAW

### Rails 8 Headend
- Ruby 3.3
- Rails 8 (API-only)
- Solid Queue (background jobs)
- SQLite or Postgres
- Anthropic Ruby SDK
- Tailscale
- Kamal 2 (deployment)

### External Services
- Datadog (metrics redundancy)
- Slack (alerting)
- Claude API (analysis)
- Tailscale (VPN for diagnostics)

---

## Success Metrics

**Performance**:
- Anomalies detected within 1 ping cycle (60s)
- Site offline detected within 5 minutes
- API response time <100ms p95
- Background jobs process within 30s

**Reliability**:
- False positive rate <5%
- 99.9% uptime for headend API
- Monitors buffer successfully during API outages
- Graceful degradation when external services fail

**Cost**:
- Claude API <$50/month (with tool calling)
- Database size <1GB after 30 days (3 sites)
- Headend runs on modest VPS ($10-20/month)

**Intelligence**:
- Claude provides actionable analysis
- Tailscale diagnostics distinguish ISP vs internal failures
- Correlation detection identifies cascading failures

---

## Open Questions & Decisions

### 1. Headend Database
**Options**:
- **SQLite**: Simplest, sufficient for 3 sites
- **Postgres**: More robust, better for future scale

**Recommendation**: Start with SQLite, migrate to Postgres if >5 sites

### 2. Headend Hosting
**Options**:
- VPS (DigitalOcean, Linode, Hetzner)
- Cloud (AWS, GCP, Fly.io)
- Self-hosted (one of your houses)

**Recommendation**: VPS ($10-20/month) for reliability

### 3. Tailscale Exit Nodes
**Setup Required**:
- Install Tailscale at each site
- Configure as exit node
- Map site name → Tailscale IP in Rails config

**Recommendation**: Set up during Phase 8

### 4. Authentication
**Options**:
- API key (simple, shared across monitors)
- Per-site API keys (more secure)
- OAuth (overkill for 3 monitors)

**Recommendation**: Single API key initially, per-site later if needed

### 5. Future Web UI
**When**: After Phase 9 (post-MVP)

**Effort**: 1-2 weeks (Rails makes this trivial)
- Enable Rails views
- Add Hotwire/Turbo for real-time updates
- Dashboard showing all sites
- Anomaly timeline
- Analysis history

---

## Migration from Current System

**Clean Cut Approach** (Recommended):

1. **Deploy Rails headend** (Phases 1-9)
2. **Update Python monitors** at each site to POST to Rails
3. **Run parallel** for 24 hours (posting to both Datadog and Rails)
4. **Verify** data in Rails matches Datadog
5. **Cut over** - rely on Rails for alerting
6. **Keep Datadog** for redundancy

**Rollback Plan**:
- Keep existing monitors running
- Datadog integration stays active
- Can roll back API URL to disable Rails posting

---

## Next Steps

1. **User confirmation**: Approve Rails 8 multi-site architecture
2. **Answer open questions**: Database, hosting, Tailscale setup
3. **Phase 1 start**: Create Python monitor with buffering
4. **Phase 2 start**: Rails API scaffolding

Ready to begin implementation! 🚀
