"""
NC Claude Client

Handles interactions with Claude API including system prompt and tool execution.
"""

from dataclasses import dataclass
from typing import List, Optional
from anthropic import Anthropic

from nc.state import SiteContext


NC_SYSTEM_PROMPT = """You are NC (NOC Claude), an intelligent network operations center engineer.
You monitor multiple sites and investigate alerts methodically.

YOUR APPROACH:
1. Don't panic at single alerts - wait to see if it's transient (humans expect ~2 min grace period)
2. Look for cascade patterns - multiple devices failing within seconds suggests upstream issue
3. Use tools to diagnose: ping devices, check VPN status, look at history
4. Learn from patterns - note recurring behaviors for future reference
5. When escalating, provide clear context for humans
6. Be concise but thorough in your reasoning

CONCERN LEVELS:
- NORMAL: No active issues
- WATCHING: Single alert, waiting to see if transient
- INVESTIGATING: Multiple alerts or timeout, actively diagnosing
- ESCALATED: Issue confirmed, humans notified

DECISION FRAMEWORK:
When investigating, work through this checklist:
1. What devices are affected? Just one or multiple?
2. If multiple, did they fail together? (suggests upstream device)
3. Can I reach the site's VPN endpoint? (distinguishes ISP vs internal)
4. Is this a known pattern? (scheduled reboots, flaky device)
5. Is there historical context that helps? (similar past incidents)

TOPOLOGY INFERENCE:
When multiple devices go down within ~30 seconds of each other:
- The FIRST device to go down is likely upstream
- Devices that follow are likely downstream of it
- Use infer_topology tool to record this relationship

TIME AWARENESS:
- Current timezone is Eastern US
- Humans are likely asleep 10 PM - 7 AM
- Non-critical issues during quiet hours queue for morning summary
- Critical issues (site-wide outage, critical device) still get flagged immediately

WHEN YOU REACH A DECISION:
Your response must end with a clear decision in this format:

DECISION: wait|escalate|resolved
REASON: <one line explanation>
SEVERITY: normal|major (only for escalate)
SUMMARY: <brief summary for humans> (only for escalate/resolved)
ROOT_CAUSE_GUESS: <your best guess> (optional)
DEVICES: <comma-separated list> (only for escalate)

EXAMPLE INVESTIGATION:

Situation: ap-garage.home DOWN, then ap-living.home DOWN 5 seconds later

My thinking:
- Two devices down within seconds - likely related
- Both are access points - could be upstream switch or power
- Let me ping the likely upstream device
[uses ping_device on switch-main.home]
- Switch is also unreachable
- Let me check if the site itself is reachable
[uses check_tailscale_status for home]
- VPN endpoint is up, so ISP is fine
- This looks like switch-main failure affecting downstream APs

DECISION: escalate
REASON: switch-main.home unreachable, causing cascade to 2 APs
SEVERITY: normal
SUMMARY: switch-main.home appears down, affecting ap-garage and ap-living. VPN healthy, likely internal switch issue.
ROOT_CAUSE_GUESS: switch-main.home failure
DEVICES: switch-main.home, ap-garage.home, ap-living.home
"""


NC_TOOLS = [
    {
        "name": "ping_device",
        "description": "ICMP ping a device to check if it's reachable from NC's location. Use this to verify if a device is actually down or if it's a monitoring issue. Always prefer using host_ip over host to avoid DNS resolution issues.",
        "input_schema": {
            "type": "object",
            "properties": {
                "host": {
                    "type": "string",
                    "description": "Device hostname/name (for display purposes)"
                },
                "host_ip": {
                    "type": "string",
                    "description": "IP address to ping (preferred over hostname)"
                },
                "site": {
                    "type": "string",
                    "description": "Site name (for Tailscale routing if needed)"
                }
            },
            "required": []
        }
    },
    {
        "name": "check_tailscale_status",
        "description": "Check if a site's Tailscale VPN endpoint is online. This helps distinguish between ISP issues (VPN down) vs internal network issues (VPN up but devices down).",
        "input_schema": {
            "type": "object",
            "properties": {
                "site": {
                    "type": "string",
                    "description": "Site name to check"
                }
            },
            "required": ["site"]
        }
    },
    {
        "name": "query_alerts",
        "description": "Get alerts from the Rails monitoring API. Use to see current active alerts or recent alert history.",
        "input_schema": {
            "type": "object",
            "properties": {
                "site": {
                    "type": "string",
                    "description": "Filter by site name (optional)"
                },
                "status": {
                    "type": "string",
                    "enum": ["active", "resolved", "all"],
                    "description": "Alert status filter"
                },
                "since_minutes": {
                    "type": "integer",
                    "description": "Only alerts from last N minutes"
                }
            }
        }
    },
    {
        "name": "get_device_history",
        "description": "Get recent alert history for a specific device. Helps identify if a device is flaky or has recurring issues.",
        "input_schema": {
            "type": "object",
            "properties": {
                "device": {
                    "type": "string",
                    "description": "Device name"
                },
                "site": {
                    "type": "string",
                    "description": "Site name"
                },
                "days": {
                    "type": "integer",
                    "description": "How many days of history (default 7)"
                }
            },
            "required": ["device", "site"]
        }
    },
    {
        "name": "check_learned_patterns",
        "description": "Check if there are known patterns for a device or time. For example, a device that always reboots at 3 AM.",
        "input_schema": {
            "type": "object",
            "properties": {
                "site": {
                    "type": "string",
                    "description": "Site name"
                },
                "device": {
                    "type": "string",
                    "description": "Device name (optional, omit for site-wide patterns)"
                }
            },
            "required": ["site"]
        }
    },
    {
        "name": "search_past_incidents",
        "description": "Search resolved incidents for similar patterns. Helps identify if this is a recurring issue with a known resolution.",
        "input_schema": {
            "type": "object",
            "properties": {
                "site": {
                    "type": "string",
                    "description": "Site name"
                },
                "query": {
                    "type": "string",
                    "description": "Search terms (device names, symptoms, root causes)"
                }
            },
            "required": ["site"]
        }
    },
    {
        "name": "infer_topology",
        "description": "Record an inferred topology relationship. Use when you observe a cascade pattern where one device going down causes others to become unreachable.",
        "input_schema": {
            "type": "object",
            "properties": {
                "site": {
                    "type": "string",
                    "description": "Site name"
                },
                "upstream_device": {
                    "type": "string",
                    "description": "The device that appears to be upstream (failed first)"
                },
                "downstream_devices": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Devices that appear to be downstream (failed after)"
                }
            },
            "required": ["site", "upstream_device", "downstream_devices"]
        }
    },
    {
        "name": "record_pattern",
        "description": "Record a learned pattern for future reference. Use when you identify a recurring behavior.",
        "input_schema": {
            "type": "object",
            "properties": {
                "site": {
                    "type": "string",
                    "description": "Site name"
                },
                "device": {
                    "type": "string",
                    "description": "Device name (optional for site-wide patterns)"
                },
                "pattern_type": {
                    "type": "string",
                    "enum": ["scheduled_downtime", "cascade_source", "flaky", "normal_reboot", "weather_sensitive"],
                    "description": "Type of pattern"
                },
                "description": {
                    "type": "string",
                    "description": "Human-readable description of the pattern"
                },
                "time_pattern": {
                    "type": "string",
                    "description": "Time pattern if applicable (e.g., '03:00-03:10' for daily window)"
                }
            },
            "required": ["site", "pattern_type", "description"]
        }
    }
]


@dataclass
class InvestigationResult:
    """Result of Claude's investigation."""
    action: str  # wait, escalate, resolved
    reason: str
    severity: str = "normal"
    summary: str = ""
    root_cause_guess: str = ""
    devices_affected: List[str] = None
    
    def __post_init__(self):
        if self.devices_affected is None:
            self.devices_affected = []


class ClaudeClient:
    """Wrapper for Claude API interactions."""
    
    def __init__(self, config, tools):
        self.client = Anthropic()
        self.model = config.claude_model
        self.tools = tools  # ToolExecutor instance
        
    def investigate(self, site: str, context: SiteContext) -> InvestigationResult:
        """Have Claude investigate a site's current state."""
        
        messages = [{
            "role": "user",
            "content": f"""Investigate the current situation at site '{site}'.

Current Context:
{context.to_prompt()}

Use tools as needed to diagnose the issue, then provide your decision.
Remember to end with a clear DECISION block."""
        }]
        
        # Agentic loop - let Claude use tools until it reaches a decision
        max_iterations = 10
        for _ in range(max_iterations):
            response = self.client.messages.create(
                model=self.model,
                max_tokens=4096,
                system=NC_SYSTEM_PROMPT,
                tools=NC_TOOLS,
                messages=messages
            )
            
            # Check if Claude wants to use tools
            if response.stop_reason == "tool_use":
                # Execute tool calls and continue conversation
                tool_results = []
                assistant_content = response.content
                
                for block in response.content:
                    if block.type == "tool_use":
                        result = self.tools.execute(block.name, block.input)
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": result
                        })
                        
                messages.append({"role": "assistant", "content": assistant_content})
                messages.append({"role": "user", "content": tool_results})
                
            else:
                # Claude is done - parse the decision
                final_text = ""
                for block in response.content:
                    if hasattr(block, "text"):
                        final_text += block.text
                        
                return self._parse_decision(final_text)
                
        # Fallback if we hit max iterations
        return InvestigationResult(
            action="wait",
            reason="Investigation inconclusive after max iterations"
        )
        
    def _parse_decision(self, text: str) -> InvestigationResult:
        """Parse Claude's decision block from response."""
        lines = text.strip().split('\n')
        
        result = InvestigationResult(action="wait", reason="Could not parse decision")
        
        for line in lines:
            line = line.strip()
            if line.startswith("DECISION:"):
                result.action = line.split(":", 1)[1].strip().lower()
            elif line.startswith("REASON:"):
                result.reason = line.split(":", 1)[1].strip()
            elif line.startswith("SEVERITY:"):
                result.severity = line.split(":", 1)[1].strip().lower()
            elif line.startswith("SUMMARY:"):
                result.summary = line.split(":", 1)[1].strip()
            elif line.startswith("ROOT_CAUSE_GUESS:"):
                result.root_cause_guess = line.split(":", 1)[1].strip()
            elif line.startswith("DEVICES:"):
                devices_str = line.split(":", 1)[1].strip()
                result.devices_affected = [d.strip() for d in devices_str.split(",")]
                
        return result
        
    def generate_morning_summary(self, overnight_incidents: list, 
                                  pending_review: list, site_statuses: dict) -> str:
        """Generate the morning summary."""
        
        import json
        
        response = self.client.messages.create(
            model=self.model,
            max_tokens=2048,
            system="""You are NC, writing a morning summary for the NOC team.
            
Be concise but complete. Structure your summary as:
1. Brief overnight overview (one sentence)
2. Per-site breakdown of any incidents
3. Pending items requiring human input (numbered list)

Use these formatting conventions:
- ✓ for all-clear
- ❓ for items needing human input
- Keep it scannable - humans are drinking coffee

End with any pending action items clearly numbered.""",
            messages=[{
                "role": "user",
                "content": f"""Write a morning summary for the NOC team.

Overnight incidents:
{json.dumps([_incident_to_dict(i) for i in overnight_incidents], indent=2, default=str)}

Items pending human review:
{json.dumps([_incident_to_dict(i) for i in pending_review], indent=2, default=str)}

Current site statuses:
{json.dumps(site_statuses, indent=2)}

Remember: Be concise, humans are just waking up."""
            }]
        )
        
        for block in response.content:
            if hasattr(block, "text"):
                return block.text
                
        return "Error generating morning summary."


def _incident_to_dict(incident) -> dict:
    """Convert incident to dict for JSON serialization."""
    return {
        "id": incident.id,
        "site": incident.site,
        "started_at": incident.started_at.isoformat() if incident.started_at else None,
        "resolved_at": incident.resolved_at.isoformat() if incident.resolved_at else None,
        "auto_recovered": incident.auto_recovered,
        "nc_summary": incident.nc_summary,
        "nc_root_cause_guess": incident.nc_root_cause_guess,
        "devices_affected": incident.devices_affected,
        "human_root_cause": incident.human_root_cause,
        "severity": incident.severity
    }
