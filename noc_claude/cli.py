"""
NC CLI Module

Allows humans to interact with NC via command line.
"""

import sys
import json
from datetime import datetime
from anthropic import Anthropic

from nc.config import Config
from nc.state import StateManager
from nc.output import NCOutput
from nc.api_client import RailsAPIClient, AuthenticationError


def run_cli(config_path: str):
    """Run NC in CLI mode for human interaction."""

    config = Config.load(config_path)
    state = StateManager(config.database_path)
    output = NCOutput(config.timezone)
    client = Anthropic()
    api = RailsAPIClient(config.rails_api)

    print()
    print("=" * 60)
    print("   NC CLI - Human Interface")
    print("=" * 60)
    print()

    # Authenticate with Rails API
    print("Authenticating with Rails API...")
    try:
        api.authenticate()
        print("Authentication successful")
    except AuthenticationError as e:
        print(f"Warning: Authentication failed: {e}")
        print("Some commands may not work without API access.")

    print()
    print("Commands:")
    print("  status                    - Show current status of all sites")
    print("  status <site>             - Show detailed status for a site")
    print("  resolve <id> <cause>      - Mark incident resolved with root cause")
    print("  learn <pattern>           - Teach NC a pattern")
    print("  ask <question>            - Ask NC a question")
    print("  incidents                 - Show pending incidents")
    print("  patterns <site>           - Show learned patterns for a site")
    print("  quit                      - Exit")
    print()
    
    while True:
        try:
            line = input("nc> ").strip()
            
            if not line:
                continue
                
            parts = line.split(maxsplit=1)
            cmd = parts[0].lower()
            args = parts[1] if len(parts) > 1 else ""
            
            if cmd == "quit" or cmd == "exit":
                print("Goodbye!")
                break
                
            elif cmd == "status":
                _cmd_status(state, output, args)
                
            elif cmd == "resolve":
                _cmd_resolve(state, output, args)
                
            elif cmd == "learn":
                _cmd_learn(state, output, args, client, config)
                
            elif cmd == "ask":
                _cmd_ask(state, output, args, client, config)
                
            elif cmd == "incidents":
                _cmd_incidents(state, output)
                
            elif cmd == "patterns":
                _cmd_patterns(state, output, args)
                
            else:
                print(f"Unknown command: {cmd}")
                print("Type 'help' for available commands.")
                
        except KeyboardInterrupt:
            print("\nGoodbye!")
            break
        except EOFError:
            break
        except Exception as e:
            print(f"Error: {e}")


def _cmd_status(state: StateManager, output: NCOutput, args: str):
    """Show status for sites."""
    
    if args:
        # Detailed status for one site
        site = args.strip()
        context = state.get_site_context(site)
        
        print(f"\n{'=' * 50}")
        print(f"Site: {site}")
        print(f"Concern Level: {context.concern_level}")
        print(f"{'=' * 50}")
        
        if context.active_alerts:
            print(f"\nActive Alerts ({len(context.active_alerts)}):")
            for alert in context.active_alerts:
                print(f"  🔴 {alert.device}: {alert.alert_type} since {alert.started_at.strftime('%H:%M:%S')}")
        else:
            print("\n✅ No active alerts")
            
        if context.learned_patterns:
            print(f"\nLearned Patterns ({len(context.learned_patterns)}):")
            for pattern in context.learned_patterns:
                device = pattern.device or "(site-wide)"
                print(f"  • {device}: {pattern.description} ({pattern.confidence:.0%})")
                
        if context.inferred_topology:
            print(f"\nInferred Topology:")
            for upstream, downstream in context.inferred_topology.items():
                print(f"  • {upstream} → {', '.join(downstream)}")
                
        print()
        
    else:
        # Summary of all sites
        statuses = state.get_all_site_statuses()
        
        if not statuses:
            print("No sites being monitored.")
            return
            
        print(f"\n{'Site':<20} {'Status':<15} {'Active Alerts'}")
        print("-" * 50)
        
        for site, level in sorted(statuses.items()):
            alerts = state.get_active_alerts(site)
            emoji = {"NORMAL": "✅", "WATCHING": "🟡", "INVESTIGATING": "🔍", "ESCALATED": "🚨"}.get(level, "?")
            print(f"{site:<20} {emoji} {level:<12} {len(alerts)}")
            
        print()


def _cmd_resolve(state: StateManager, output: NCOutput, args: str):
    """Resolve an incident."""
    
    parts = args.split(maxsplit=1)
    if len(parts) < 2:
        print("Usage: resolve <incident_id> <root cause>")
        return
        
    try:
        incident_id = int(parts[0])
    except ValueError:
        print("Invalid incident ID")
        return
        
    root_cause = parts[1]
    
    incident = state.get_incident(incident_id)
    if not incident:
        print(f"Incident {incident_id} not found")
        return
        
    # Update the incident with human root cause
    with state._get_conn() as conn:
        conn.execute("""
            UPDATE incidents 
            SET human_root_cause = ?,
                human_reviewed_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (root_cause, incident_id))
        
    output.nc_reply(f"✅ Incident #{incident_id} marked resolved. Root cause: {root_cause}")
    output.nc_reply("💡 I'll remember this for future similar issues.")


def _cmd_learn(state: StateManager, output: NCOutput, args: str, client, config):
    """Teach NC a pattern."""
    
    if not args:
        print("Usage: learn <pattern description>")
        print("Example: learn nas.home reboots daily at 3:00 AM for backups")
        return
        
    # Use Claude to parse the learning into structured pattern
    response = client.messages.create(
        model=config.claude_model,
        max_tokens=500,
        system="""Parse the user's pattern description into structured data.
        
Respond with JSON only, no other text:
{
    "site": "site name",
    "device": "device name or null if site-wide",
    "pattern_type": "scheduled_downtime|normal_reboot|flaky|cascade_source|weather_sensitive",
    "description": "human readable description",
    "time_pattern": "HH:MM-HH:MM or null if not time-based"
}""",
        messages=[{
            "role": "user",
            "content": f"Parse this pattern: {args}"
        }]
    )
    
    try:
        # Extract JSON from response
        text = response.content[0].text.strip()
        # Handle potential markdown code blocks
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        pattern_data = json.loads(text)
        
        state.record_pattern(
            site=pattern_data.get('site', 'unknown'),
            device=pattern_data.get('device'),
            pattern_type=pattern_data.get('pattern_type', 'scheduled_downtime'),
            description=pattern_data.get('description', args),
            time_pattern=pattern_data.get('time_pattern')
        )
        
        output.nc_reply(f"✅ Learned: {pattern_data.get('description', args)}")
        
    except (json.JSONDecodeError, KeyError, IndexError) as e:
        print(f"Failed to parse pattern: {e}")
        print("Try being more specific, e.g., 'nas.home reboots daily at 3:00 AM'")


def _cmd_ask(state: StateManager, output: NCOutput, args: str, client, config):
    """Ask NC a question."""
    
    if not args:
        print("Usage: ask <question>")
        return
        
    # Gather context
    all_statuses = state.get_all_site_statuses()
    pending = state.get_pending_human_review()
    
    context = f"""Current site statuses: {json.dumps(all_statuses)}
    
Pending incidents needing review: {len(pending)}"""
    
    response = client.messages.create(
        model=config.claude_model,
        max_tokens=1000,
        system="""You are NC (NOC Claude), answering a question from a human operator.
Be concise and helpful. You have access to monitoring data for multiple sites.""",
        messages=[{
            "role": "user",
            "content": f"""Context:
{context}

Question: {args}"""
        }]
    )
    
    print()
    output.nc_reply(response.content[0].text)
    print()


def _cmd_incidents(state: StateManager, output: NCOutput):
    """Show pending incidents."""
    
    pending = state.get_pending_human_review()
    
    if not pending:
        print("✅ No incidents pending review.")
        return
        
    print(f"\nPending Incidents ({len(pending)}):")
    print("-" * 60)
    
    for incident in pending:
        duration = ""
        if incident.resolved_at and incident.started_at:
            delta = incident.resolved_at - incident.started_at
            duration = f" ({int(delta.total_seconds() / 60)}m)"
            
        status = "auto-recovered" if incident.auto_recovered else "unresolved"
        
        print(f"\n#{incident.id} [{incident.site}] {incident.started_at.strftime('%Y-%m-%d %H:%M')}{duration}")
        print(f"   Status: {status}")
        print(f"   NC's guess: {incident.nc_root_cause_guess or 'unknown'}")
        print(f"   Devices: {', '.join(incident.devices_affected)}")
        if incident.nc_summary:
            print(f"   Summary: {incident.nc_summary}")
            
    print()
    print("Use 'resolve <id> <root cause>' to close an incident.")
    print()


def _cmd_patterns(state: StateManager, output: NCOutput, args: str):
    """Show learned patterns for a site."""
    
    if not args:
        print("Usage: patterns <site>")
        return
        
    site = args.strip()
    patterns = state.get_learned_patterns(site)
    
    if not patterns:
        print(f"No learned patterns for site '{site}'")
        return
        
    print(f"\nLearned Patterns for {site}:")
    print("-" * 50)
    
    for pattern in patterns:
        device = pattern.device or "(site-wide)"
        print(f"\n[{pattern.pattern_type}] {device}")
        print(f"  {pattern.description}")
        print(f"  Confidence: {pattern.confidence:.0%} (seen {pattern.occurrences}x)")
        if pattern.time_pattern:
            print(f"  Time window: {pattern.time_pattern}")
            
    print()


if __name__ == "__main__":
    import sys
    config_path = sys.argv[1] if len(sys.argv) > 1 else "config.yml"
    run_cli(config_path)
