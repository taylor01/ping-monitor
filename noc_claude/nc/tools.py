"""
NC Tool Implementations

Executes tools that Claude can call during investigations.
"""

import subprocess
import json
from typing import Any, Dict, Optional
from datetime import datetime, timedelta


class ToolExecutor:
    """Executes NC's investigation tools."""
    
    def __init__(self, config, api_client, state_manager, output):
        self.config = config
        self.api = api_client
        self.state = state_manager
        self.output = output
        
    def execute(self, tool_name: str, params: Dict[str, Any]) -> str:
        """Execute a tool and return result as string."""
        
        self.output.tool_call(tool_name, params)
        
        try:
            if tool_name == "ping_device":
                result = self._ping_device(params)
            elif tool_name == "check_tailscale_status":
                result = self._check_tailscale_status(params)
            elif tool_name == "query_alerts":
                result = self._query_alerts(params)
            elif tool_name == "get_device_history":
                result = self._get_device_history(params)
            elif tool_name == "check_learned_patterns":
                result = self._check_learned_patterns(params)
            elif tool_name == "search_past_incidents":
                result = self._search_past_incidents(params)
            elif tool_name == "infer_topology":
                result = self._infer_topology(params)
            elif tool_name == "record_pattern":
                result = self._record_pattern(params)
            else:
                result = f"Unknown tool: {tool_name}"
                
            self.output.tool_result(tool_name, result)
            return result
            
        except Exception as e:
            error_msg = f"Tool error: {str(e)}"
            self.output.tool_result(tool_name, error_msg)
            return error_msg
            
    def _ping_device(self, params: Dict[str, Any]) -> str:
        """Ping a device and return results."""
        host = params.get("host")
        host_ip = params.get("host_ip")
        site = params.get("site")

        # Debug: log received parameters
        self.output.debug(f"ping_device params: host={host}, host_ip={host_ip}, site={site}")

        if not host and not host_ip:
            return "Error: host or host_ip parameter required"

        # Prefer IP address over hostname to avoid DNS resolution issues
        ping_target = host_ip if host_ip else host
        display_name = f"{host} ({host_ip})" if host_ip and host else (host or host_ip)

        # Debug: log what we're actually pinging
        if host_ip:
            self.output.debug(f"Using IP address: {ping_target}")
        else:
            self.output.warning(f"No host_ip provided, falling back to hostname: {ping_target}")

        try:
            cmd = ["ping", "-c", "3", "-W", "2", ping_target]
            self.output.debug(f"Executing: {' '.join(cmd)}")

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode == 0:
                # Parse latency from output
                lines = result.stdout.strip().split('\n')
                stats_line = [l for l in lines if 'avg' in l.lower() or 'rtt' in l.lower()]
                if stats_line:
                    return f"REACHABLE: {display_name} is responding. {stats_line[-1]}"
                return f"REACHABLE: {display_name} is responding."
            else:
                return f"UNREACHABLE: {display_name} is not responding to ping."

        except subprocess.TimeoutExpired:
            return f"TIMEOUT: {display_name} ping timed out after 10 seconds."
        except FileNotFoundError:
            return f"ERROR: ping command not available."
        except Exception as e:
            return f"ERROR: Failed to ping {display_name}: {str(e)}"
            
    def _check_tailscale_status(self, params: Dict[str, Any]) -> str:
        """Check Tailscale status for a site."""
        site = params.get("site")
        
        if not site:
            return "Error: site parameter required"
            
        site_config = self.config.get_site(site)
        if not site_config or not site_config.tailscale_ip:
            return f"No Tailscale IP configured for site '{site}'"
            
        # Ping the Tailscale IP
        try:
            result = subprocess.run(
                ["ping", "-c", "2", "-W", "2", site_config.tailscale_ip],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                return f"VPN ONLINE: Site '{site}' Tailscale endpoint ({site_config.tailscale_ip}) is reachable. ISP connectivity appears healthy."
            else:
                return f"VPN OFFLINE: Site '{site}' Tailscale endpoint ({site_config.tailscale_ip}) is UNREACHABLE. Possible ISP outage or site-wide power loss."
                
        except subprocess.TimeoutExpired:
            return f"VPN TIMEOUT: Site '{site}' Tailscale endpoint not responding. Possible ISP issue."
        except Exception as e:
            return f"ERROR: Failed to check Tailscale for {site}: {str(e)}"
            
    def _query_alerts(self, params: Dict[str, Any]) -> str:
        """Query alerts from Rails API."""
        site = params.get("site")
        status = params.get("status", "active")
        since_minutes = params.get("since_minutes")
        
        try:
            alerts = self.api.get_alerts(
                site=site,
                status=status,
                since_minutes=since_minutes
            )
            
            if not alerts:
                return f"No {status} alerts found" + (f" for site '{site}'" if site else "")
                
            result_lines = [f"Found {len(alerts)} {status} alert(s):"]
            for alert in alerts:
                result_lines.append(
                    f"  - {alert.device}@{alert.site}: {alert.alert_type} "
                    f"(since {alert.started_at.strftime('%H:%M:%S')})"
                )
                
            return "\n".join(result_lines)
            
        except Exception as e:
            # Fallback to local state if API fails
            local_alerts = self.state.get_active_alerts(site)
            if not local_alerts:
                return f"API unavailable, no cached alerts for site '{site}'"
                
            result_lines = [f"(from cache) Found {len(local_alerts)} active alert(s):"]
            for alert in local_alerts:
                result_lines.append(f"  - {alert.device}@{alert.site}: {alert.alert_type}")
            return "\n".join(result_lines)
            
    def _get_device_history(self, params: Dict[str, Any]) -> str:
        """Get alert history for a device."""
        device = params.get("device")
        site = params.get("site")
        days = params.get("days", 7)
        
        if not device or not site:
            return "Error: device and site parameters required"
            
        try:
            history = self.api.get_device_history(device, site, days)
            
            if not history:
                return f"No alert history for {device}@{site} in the last {days} days."
                
            result_lines = [f"Alert history for {device}@{site} (last {days} days):"]
            for entry in history[:10]:  # Limit to 10 most recent
                result_lines.append(
                    f"  - {entry['started_at']}: {entry['alert_type']} "
                    f"({entry.get('duration', 'unknown duration')})"
                )
                
            if len(history) > 10:
                result_lines.append(f"  ... and {len(history) - 10} more")
                
            return "\n".join(result_lines)
            
        except Exception as e:
            return f"Error fetching device history: {str(e)}"
            
    def _check_learned_patterns(self, params: Dict[str, Any]) -> str:
        """Check for learned patterns."""
        site = params.get("site")
        device = params.get("device")
        
        if not site:
            return "Error: site parameter required"
            
        patterns = self.state.get_learned_patterns(site, device)
        
        if not patterns:
            target = f"{device}@{site}" if device else f"site '{site}'"
            return f"No learned patterns for {target}."
            
        result_lines = [f"Known patterns for {device or 'site'} at {site}:"]
        for pattern in patterns:
            result_lines.append(
                f"  - [{pattern.pattern_type}] {pattern.description} "
                f"(confidence: {pattern.confidence:.0%}, seen {pattern.occurrences}x)"
            )
            if pattern.time_pattern:
                result_lines.append(f"    Time window: {pattern.time_pattern}")
                
        return "\n".join(result_lines)
        
    def _search_past_incidents(self, params: Dict[str, Any]) -> str:
        """Search past incidents."""
        site = params.get("site")
        query = params.get("query", "")
        
        if not site:
            return "Error: site parameter required"
            
        incidents = self.state.get_recent_incidents(site, days=90)
        
        # Simple search - filter by query terms in summary/root cause
        if query:
            query_lower = query.lower()
            incidents = [
                i for i in incidents
                if query_lower in (i.nc_summary or "").lower()
                or query_lower in (i.human_root_cause or "").lower()
                or query_lower in (i.nc_root_cause_guess or "").lower()
                or any(query_lower in d.lower() for d in i.devices_affected)
            ]
            
        if not incidents:
            return f"No past incidents found for site '{site}'" + (f" matching '{query}'" if query else "")
            
        result_lines = [f"Past incidents at {site}" + (f" matching '{query}'" if query else "") + ":"]
        for incident in incidents[:5]:
            status = "resolved" if incident.resolved_at else "active"
            duration = ""
            if incident.resolved_at and incident.started_at:
                delta = incident.resolved_at - incident.started_at
                duration = f", duration: {int(delta.total_seconds() / 60)}m"
                
            root_cause = incident.human_root_cause or incident.nc_root_cause_guess or "unknown"
            result_lines.append(
                f"  - {incident.started_at.strftime('%Y-%m-%d %H:%M')}: "
                f"{root_cause} ({status}{duration})"
            )
            if incident.devices_affected:
                result_lines.append(f"    Devices: {', '.join(incident.devices_affected)}")
                
        if len(incidents) > 5:
            result_lines.append(f"  ... and {len(incidents) - 5} more incidents")
            
        return "\n".join(result_lines)
        
    def _infer_topology(self, params: Dict[str, Any]) -> str:
        """Record inferred topology relationship."""
        site = params.get("site")
        upstream = params.get("upstream_device")
        downstream = params.get("downstream_devices", [])
        
        if not site or not upstream or not downstream:
            return "Error: site, upstream_device, and downstream_devices required"
            
        self.state.record_topology_inference(site, upstream, downstream)
        
        return (
            f"Recorded topology inference: {upstream} appears to be upstream of "
            f"{', '.join(downstream)} at site '{site}'"
        )
        
    def _record_pattern(self, params: Dict[str, Any]) -> str:
        """Record a learned pattern."""
        site = params.get("site")
        device = params.get("device")
        pattern_type = params.get("pattern_type")
        description = params.get("description")
        time_pattern = params.get("time_pattern")
        
        if not site or not pattern_type or not description:
            return "Error: site, pattern_type, and description required"
            
        self.state.record_pattern(
            site=site,
            device=device,
            pattern_type=pattern_type,
            description=description,
            time_pattern=time_pattern
        )
        
        target = f"{device}@{site}" if device else f"site '{site}'"
        return f"Recorded pattern for {target}: [{pattern_type}] {description}"
