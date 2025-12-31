# Documentation

This directory contains planning and architectural documentation for the multi-site monitoring system.

## Documents

### [architecture.md](architecture.md)
**Status: Complete**

Comprehensive architectural review and implementation plan for the Rails 8 multi-site monitoring system.

**Contents:**
- Executive summary and architecture overview
- Multi-site design with Rails headend
- Python monitor with local buffering
- Claude tool calling system (including Tailscale VPN)
- Database schema and migrations
- 9-phase implementation plan
- Technology stack decisions
- Deployment strategy (Kamal 2)
- Success metrics and open questions

**Key Decisions:**
- Rails 8 API-only mode for headend
- Solid Queue for background jobs (no Redis)
- Percentile-based anomaly detection
- Claude AI with diagnostic tools
- Tailscale integration for ISP vs internal failure diagnosis

### [enhanced-plan.md](enhanced-plan.md)
**Status: Historical reference**

Original enhancement proposal before pivoting to Rails 8 multi-site architecture.

**Contents:**
- Initial self-contained Python approach
- SQLite-based local storage
- FastAPI for HTTP endpoints
- Anomaly detection algorithms
- Claude integration concepts

**Note:** This was the starting point that evolved into the Rails architecture after determining multi-site support was a core requirement.

## Architecture Evolution

1. **Original**: Single-file Python script posting to Datadog
2. **Enhanced Plan**: Self-contained Python + FastAPI + SQLite
3. **Current**: Multi-site with Python monitors + Rails 8 headend ✅

The pivot to Rails 8 was driven by:
- Need to support 3 houses (home, cabin, office)
- Desire for centralized visibility and analysis
- Site health monitoring (detect when entire site goes offline)
- Claude tool calling benefits from headend perspective
- Future web UI requirements
- Rails 8 features (Solid Queue, Kamal) perfect for this use case

## Quick Reference

### Current Status: Phase 0
✅ Repository structure established
✅ Documentation complete
🚧 Python monitor exists but needs buffering logic
📋 Rails API not yet created

### Next Steps
1. **Phase 1**: Add buffering to Python monitor
2. **Phase 2**: Create Rails 8 API headend
3. **Phase 3-9**: See architecture.md for remaining phases

## Key Concepts

### Multi-Site Architecture
- Lightweight Python monitors at each physical location
- Central Rails API for aggregation and analysis
- Local buffering when API unreachable
- Datadog integration maintained for redundancy

### Intelligent Monitoring
- Baseline calculation (rolling statistics)
- Anomaly detection (percentile-based)
- Site health monitoring (headend detects offline sites)
- Claude AI with tool calling for investigation
- Tailscale VPN for diagnosing ISP vs internal failures

### Technology Choices
- **Monitor**: Python (proven, lightweight, NET_RAW compatible)
- **Headend**: Rails 8 (conventions, Solid Queue, web UI future)
- **Jobs**: Solid Queue (no Redis dependency)
- **Deployment**: Kamal 2 (zero-downtime)
- **AI**: Claude (tool calling for active investigation)
- **VPN**: Tailscale (diagnostic connectivity)

## See Also

- [Main README](../README.md) - Quick start and overview
- [Monitor README](../monitor/README.md) - Python monitor details
- [API README](../api/README.md) - Rails headend (future)
