# Ping Monitor - Future Architecture Ideas

## Overview

This document captures architectural ideas for evolving the ping monitor from a simple single-site tool into an intelligent, auto-scaling, multi-site monitoring platform with Claude as the NOC engineer.

---

## 1. Tailscale Integration for Diagnostics

### Problem
When a site stops reporting, we can't distinguish between:
- Monitor container crashed
- Docker daemon issue
- ISP outage
- Power outage
- Hardware failure

### Solution
Install Tailscale at the OS level (not in container) on each Docker host. This provides an independent network path for diagnostics.

### Failure Matrix

| Monitor Reporting | Tailscale Reachable | Diagnosis |
|-------------------|---------------------|-----------|
| ✅ Yes | ✅ Yes | Normal operation |
| ❌ No | ✅ Yes | Container/Docker issue, monitor crashed |
| ❌ No | ❌ No | ISP outage, power outage, or host down |
| ✅ Yes | ❌ No | Tailscale issue (rare edge case) |

### Setup

```
Site: cabin
┌─────────────────────────────┐
│  Fedora CoreOS Host         │
│  • Tailscale (OS level)     │  ◄── 100.x.x.x (cabin-beelink)
│  • Docker                   │
│    └── ping-monitor         │  ◄── Posts to Rails API
└─────────────────────────────┘

Headend
┌─────────────────────────────┐
│  VPS                        │
│  • Tailscale (OS level)     │  ◄── 100.x.x.x (headend)
│  • Docker                   │
│    └── rails-api            │
└─────────────────────────────┘
```

### Claude's Diagnostic Flow

```
Site "cabin" stopped reporting 5 minutes ago
  │
  ├─▶ tailscale ping cabin-docker-host
  │     │
  │     ├─▶ SUCCESS: "Host is up, but monitor isn't posting"
  │     │     → Container crashed? Docker daemon issue?
  │     │     → Alert: "Cabin monitor down, host reachable via Tailscale"
  │     │
  │     └─▶ TIMEOUT: "Can't reach host at all"
  │           → ISP down? Power outage? Hardware failure?
  │           → Alert: "Cabin site unreachable (ISP or power issue)"
```

---

## 2. Claude as SSH-Enabled NOC Engineer

### Concept
Give Claude an SSH key so it can actively investigate and remediate issues on remote hosts.

### Tool Expansion

```ruby
tools = [
  # Network diagnostics
  { name: "tailscale_ping", desc: "Check if host is reachable via VPN" },
  { name: "ping_from_headend", desc: "ICMP ping from headend" },
  
  # SSH-based investigation
  { name: "ssh_exec", desc: "Run command on remote host via SSH" },
]
```

### Diagnostic Escalation Example

```
Site "cabin" stopped reporting
  │
  ├─▶ tailscale ping cabin-beelink → SUCCESS
  │
  ├─▶ ssh_exec cabin-beelink "docker ps -a --filter name=ping"
  │     → "ping-monitor  Exited (137) 10 minutes ago"
  │
  ├─▶ ssh_exec cabin-beelink "docker logs --tail 50 ping-monitor"
  │     → "Killed - OOM"
  │
  └─▶ Claude's analysis:
        "Cabin monitor was OOM-killed 10 minutes ago. 
         Recommend increasing memory limit or investigating leak.
         Want me to restart it?"
```

### Auto-Remediation

```bash
ssh_exec cabin-beelink "docker compose -f ~/ping-monitor/docker-compose.yml up -d"
```

### Security Considerations

Create a dedicated `claude-ops` user with limited sudo access:

```bash
# /etc/sudoers.d/claude-ops
claude-ops ALL=(ALL) NOPASSWD: /usr/bin/docker ps *
claude-ops ALL=(ALL) NOPASSWD: /usr/bin/docker logs *
claude-ops ALL=(ALL) NOPASSWD: /usr/bin/docker compose up -d
claude-ops ALL=(ALL) NOPASSWD: /usr/bin/docker compose restart
claude-ops ALL=(ALL) NOPASSWD: /usr/bin/systemctl status *
```

Additional security measures:
- Dedicated SSH key for Claude only
- Restrict to specific commands via SSH forced command or sudo rules
- Audit log all SSH sessions
- Consider requiring human approval for write actions (restart, etc.)

---

## 3. Multi-Collector Architecture

### Problem
Additional checks (SNMP, HTTP) may not complete within the same 60-second window as ping. Need independent timing.

### Solution
Run each collector on its own async loop with a shared result queue:

```python
async def main():
    tasks = []
    
    if config.ping_enabled:
        tasks.append(asyncio.create_task(ping_loop()))
    
    if config.snmp_enabled:
        tasks.append(asyncio.create_task(snmp_loop()))
    
    if config.http_enabled:
        tasks.append(asyncio.create_task(http_loop()))
    
    # Shared buffer drain loop
    tasks.append(asyncio.create_task(buffer_drain_loop()))
    
    await asyncio.gather(*tasks)


async def ping_loop():
    collector = PingCollector(config.ping_hosts)
    while True:
        start = time.time()
        results = await collector.collect()
        await result_queue.put(results)
        elapsed = time.time() - start
        await asyncio.sleep(max(0, config.ping_interval - elapsed))


async def snmp_loop():
    collector = SNMPCollector(config.snmp_hosts)
    while True:
        start = time.time()
        results = await collector.collect()  # might take 30s
        await result_queue.put(results)
        elapsed = time.time() - start
        await asyncio.sleep(max(0, config.snmp_interval - elapsed))


async def buffer_drain_loop():
    """Collects results from all collectors and posts to API"""
    while True:
        batch = []
        while not result_queue.empty():
            batch.extend(await result_queue.get())
        
        if batch:
            success = await post_to_api(batch)
            if not success:
                buffer_locally(batch)
            else:
                await drain_buffer()
        
        await asyncio.sleep(5)  # Drain every 5s
```

### Project Structure

```
site-agent/
├── collectors/
│   ├── __init__.py
│   ├── base.py          # Abstract collector
│   ├── ping.py          # ICMP ping
│   ├── snmp.py          # SNMP polling
│   └── http.py          # HTTP endpoint checks
├── main.py
├── buffer.py            # Local SQLite buffer
└── config.py
```

### Timing Independence

Each collector runs independently:
- Ping: every 60s, takes ~2s
- SNMP: every 60s, takes ~30s  
- HTTP: every 30s, takes ~10s

All feed into a shared queue, single drain loop posts to Rails. They don't block each other.

---

## 4. Headend-Assigned Host Distribution

### Problem
For sites with hundreds/thousands of hosts, a single pinger can't keep up. Need to distribute work across multiple containers without manual config.

### Solution
Rails headend manages host assignments. Agents register and receive their host list dynamically.

### Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         Rails Headend                            │
│                                                                  │
│  sites:                                                         │
│    - home (150 hosts)                                           │
│                                                                  │
│  agents:                                                        │
│    - home-pinger-1 (registered, last_seen: 5s ago)              │
│    - home-pinger-2 (registered, last_seen: 3s ago)              │
│    - home-pinger-3 (registered, last_seen: 4s ago)              │
│                                                                  │
│  assignments:                                                    │
│    - home-pinger-1 → hosts 1-50                                 │
│    - home-pinger-2 → hosts 51-100                               │
│    - home-pinger-3 → hosts 101-150                              │
└─────────────────────────────────────────────────────────────────┘
```

### Agent Lifecycle

```python
async def main():
    # 1. Register with headend
    agent_id = await register_agent(site=SITE_NAME)
    
    # 2. Fetch assigned hosts (not local file)
    hosts = await get_my_assignments(agent_id)
    
    # 3. Main loop
    while True:
        results = await ping_hosts(hosts)
        await post_results(agent_id, results)
        
        # 4. Refresh assignments periodically (handles rebalancing)
        if time_to_refresh():
            hosts = await get_my_assignments(agent_id)
        
        await asyncio.sleep(interval)


async def register_agent(site: str) -> str:
    """Register with headend, get unique agent ID"""
    resp = await client.post("/api/v1/agents/register", json={
        "site": site,
        "hostname": socket.gethostname(),
        "capabilities": ["ping", "snmp"],  # what this agent can do
    })
    return resp.json()["agent_id"]


async def get_my_assignments(agent_id: str) -> list[Host]:
    """Fetch hosts assigned to this agent"""
    resp = await client.get(f"/api/v1/agents/{agent_id}/assignments")
    return resp.json()["hosts"]
```

### Rails Side

```ruby
# app/models/agent.rb
class Agent < ApplicationRecord
  belongs_to :site
  has_many :host_assignments
  
  scope :active, -> { where("last_heartbeat > ?", 2.minutes.ago) }
  
  def self.rebalance!(site)
    agents = site.agents.active.order(:id)
    return if agents.empty?
    
    hosts = site.hosts.order(:id)
    
    # Clear existing assignments
    HostAssignment.where(agent: agents).delete_all
    
    # Round-robin distribute
    hosts.each_with_index do |host, i|
      agent = agents[i % agents.count]
      HostAssignment.create!(agent: agent, host: host)
    end
  end
end

# app/controllers/api/v1/agents_controller.rb
class Api::V1::AgentsController < ApplicationController
  def register
    agent = Agent.find_or_create_by!(
      site: Site.find_by!(name: params[:site]),
      hostname: params[:hostname]
    )
    agent.update!(
      last_heartbeat: Time.current,
      capabilities: params[:capabilities]
    )
    
    # Trigger rebalance when new agent joins
    Agent.rebalance!(agent.site)
    
    render json: { agent_id: agent.id }
  end
  
  def assignments
    agent = Agent.find(params[:id])
    agent.touch(:last_heartbeat)
    
    hosts = agent.host_assignments.includes(:host).map(&:host)
    render json: { hosts: hosts }
  end
end
```

### Auto-Rebalancing on Agent Failure

```ruby
# app/jobs/agent_health_check_job.rb
class AgentHealthCheckJob < ApplicationJob
  def perform
    # Find agents that stopped reporting
    dead_agents = Agent.where("last_heartbeat < ?", 2.minutes.ago)
    
    dead_agents.find_each do |agent|
      agent.update!(status: "offline")
      
      # Redistribute their hosts to remaining agents
      Agent.rebalance!(agent.site)
      
      # Alert
      SlackNotifier.agent_offline(agent)
    end
  end
end
```

### Smart Distribution Strategies

```ruby
def self.rebalance!(site, strategy: :round_robin)
  case strategy
  when :round_robin
    # Simple even distribution
    
  when :subnet_aware
    # Keep hosts on same subnet together (reduces ARP noise)
    hosts.group_by { |h| h.ip.split('.')[0..2].join('.') }
         .each { |subnet, subnet_hosts| assign_to_one_agent(subnet_hosts) }
    
  when :capability_matched
    # SNMP hosts only go to agents with SNMP capability
    hosts.group_by(&:check_type).each do |type, type_hosts|
      capable_agents = agents.select { |a| a.capabilities.include?(type) }
      distribute(type_hosts, capable_agents)
    end
  end
end
```

### Result

- Spin up 5 pinger containers, they auto-register and split the work
- One dies, others absorb its hosts within 2 minutes
- Add more hosts to Rails, they get distributed on next refresh
- No manual config per container—just `SITE_NAME` and `API_URL`

---

## 5. Claude-Driven Auto-Scaling

### Concept
Claude monitors agent performance metrics and automatically scales agents up/down based on headroom.

### New Metrics to Track

```ruby
# Agent heartbeat includes timing data
POST /api/v1/agents/:id/heartbeat
{
  "cycle_duration_ms": 45000,  # How long the ping cycle took
  "host_count": 150,
  "interval_ms": 60000,
  "headroom_pct": 25,          # 15s remaining = 25% headroom
  "queue_depth": 0              # Backlog if falling behind
}
```

### Claude's Scaling Tools

```ruby
tools = [
  # Existing diagnostic tools
  { name: "tailscale_ping" },
  { name: "ssh_exec" },
  
  # New scaling tools
  {
    name: "get_agent_metrics",
    description: "Get timing metrics for all agents at a site",
    parameters: { site: "string" }
  },
  {
    name: "scale_agents",
    description: "Add or remove ping agents at a site",
    parameters: { 
      site: "string",
      action: "enum: add, remove",
      count: "integer"
    }
  },
  {
    name: "get_scaling_recommendation",
    description: "Analyze current load and recommend scaling action"
  }
]
```

### Tool Implementation

```ruby
# app/services/claude_tools/scale_agents.rb
class ClaudeTools::ScaleAgents
  def execute(site:, action:, count:)
    site_config = Site.find_by!(name: site)
    docker_host = site_config.docker_host  # Tailscale IP
    
    case action
    when "add"
      count.times do |i|
        ssh_exec(docker_host, <<~CMD)
          docker run -d \
            --name ping-agent-#{SecureRandom.hex(4)} \
            --cap-add NET_RAW \
            -e SITE_NAME=#{site} \
            -e API_URL=#{ENV['API_URL']} \
            -e API_KEY=#{ENV['AGENT_API_KEY']} \
            ping-monitor:latest
        CMD
      end
      
      "Started #{count} new agents at #{site}"
      
    when "remove"
      # Find agents with lowest host count (least disruptive)
      agents = Agent.where(site: site_config)
                    .active
                    .order(:host_count)
                    .limit(count)
      
      agents.each do |agent|
        ssh_exec(docker_host, "docker stop #{agent.container_id}")
      end
      
      "Removed #{count} agents at #{site}"
    end
  end
end
```

### Claude's Decision Prompt

```ruby
# app/jobs/capacity_analysis_job.rb
class CapacityAnalysisJob < ApplicationJob
  def perform
    sites_needing_review = Site.joins(:agents)
      .where("agents.headroom_pct < 20 OR agents.headroom_pct > 80")
      .distinct
    
    return if sites_needing_review.empty?
    
    context = build_capacity_context(sites_needing_review)
    
    response = Claude.chat(
      system: <<~PROMPT,
        You are a NOC engineer responsible for capacity management.
        
        Scaling rules:
        - If any agent has <15% headroom, consider adding agents
        - If all agents have >70% headroom, consider removing agents
        - Minimum 1 agent per site
        - Maximum 10 agents per site
        - Prefer to scale by 1 at a time unless urgent
        - Consider time of day (don't scale down during business hours)
        
        Use tools to investigate and take action.
      PROMPT
      messages: [{ role: "user", content: context }],
      tools: scaling_tools
    )
    
    execute_tool_calls(response)
  end
end
```

### Example Claude Interaction

```
CONTEXT:
Site: warehouse
Agents: 3
  - warehouse-pinger-1: 58s cycle, 150 hosts, 3% headroom ⚠️
  - warehouse-pinger-2: 55s cycle, 150 hosts, 8% headroom ⚠️  
  - warehouse-pinger-3: 52s cycle, 150 hosts, 13% headroom

CLAUDE THINKING:
"All three agents are running hot - under 15% headroom. At this rate 
they'll start missing cycles. The warehouse site has 450 hosts across 
3 agents. Adding 2 more agents would bring each down to ~90 hosts, 
giving roughly 50% headroom."

CLAUDE ACTIONS:
1. get_agent_metrics(site: "warehouse")  # Verify current state
2. scale_agents(site: "warehouse", action: "add", count: 2)

CLAUDE RESPONSE:
"Added 2 ping agents to warehouse site. Previous agents were at 
3-13% headroom with 150 hosts each. After rebalancing, each agent 
will handle ~90 hosts with estimated 50% headroom. Will monitor 
next 3 cycles to confirm improvement."
```

### Guardrails

```ruby
class ClaudeTools::ScaleAgents
  MAX_AGENTS_PER_SITE = 10
  MIN_AGENTS_PER_SITE = 1
  MAX_SCALE_PER_ACTION = 3
  COOLDOWN_MINUTES = 15
  
  def execute(site:, action:, count:)
    # Enforce limits
    if count > MAX_SCALE_PER_ACTION
      return "Denied: Max #{MAX_SCALE_PER_ACTION} agents per action"
    end
    
    if action == "add" && current_count + count > MAX_AGENTS_PER_SITE
      return "Denied: Would exceed max #{MAX_AGENTS_PER_SITE} agents"
    end
    
    if action == "remove" && current_count - count < MIN_AGENTS_PER_SITE
      return "Denied: Must maintain at least #{MIN_AGENTS_PER_SITE} agent"
    end
    
    if recent_scaling_action?(site)
      return "Denied: Cooldown active, last scaling was #{minutes_ago}m ago"
    end
    
    # Proceed with scaling...
  end
end
```

### The Full Auto-Scaling Loop

```
Metrics collected every 60s
        │
        ▼
CapacityAnalysisJob runs every 5 min
        │
        ▼
Claude analyzes headroom across sites
        │
        ├─▶ Headroom OK → No action
        │
        └─▶ Headroom low/high → Use tools to scale
                │
                ▼
        Agents auto-rebalance hosts
                │
                ▼
        Slack notification: "Scaled warehouse from 3→5 agents"
```

---

## Summary

This architecture evolves the ping monitor into an intelligent, self-managing monitoring platform:

| Layer | Responsibility |
|-------|----------------|
| **Site Agents** | Lightweight collectors, local buffering, POST to API |
| **Rails Headend** | Data aggregation, baseline calculation, anomaly detection |
| **Tailscale** | Independent diagnostic network path |
| **Claude** | Investigation, root cause analysis, auto-remediation, auto-scaling |
| **Slack** | Human notification and approval workflows |

The key insight is that Claude becomes the NOC engineer—not just analyzing data, but actively investigating issues via SSH, making scaling decisions, and optionally remediating problems automatically.

---

## Implementation Priority

1. **Phase 1**: Multi-site with Rails headend (current plan)
2. **Phase 2**: Tailscale diagnostics
3. **Phase 3**: Claude SSH investigation
4. **Phase 4**: Multi-collector support
5. **Phase 5**: Dynamic host assignment
6. **Phase 6**: Claude auto-scaling

Each phase builds on the previous, and the system remains useful at each stage.
