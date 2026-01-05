#!/usr/bin/env python3
"""
NOC Claude (NC) - Intelligent Network Operations Center Agent

Main entry point and core loop.
"""

import time
import signal
import sys
from datetime import datetime

from nc.config import Config
from nc.state import StateManager
from nc.claude_client import ClaudeClient
from nc.tools import ToolExecutor
from nc.time_awareness import TimeAwareness
from nc.output import NCOutput
from nc.api_client import RailsAPIClient, AuthenticationError


class NOCClaude:
    """Main NC agent class."""
    
    def __init__(self, config_path: str = "config.yml"):
        self.config = Config.load(config_path)
        self.output = NCOutput()
        self.time = TimeAwareness(self.config.timezone)
        self.state = StateManager(self.config.database_path)
        self.api = RailsAPIClient(self.config.rails_api)
        self.tools = ToolExecutor(self.config, self.api, self.state, self.output)
        self.claude = ClaudeClient(self.config, self.tools)
        
        self.running = True
        self._setup_signal_handlers()
        
    def _setup_signal_handlers(self):
        """Handle graceful shutdown."""
        signal.signal(signal.SIGINT, self._shutdown)
        signal.signal(signal.SIGTERM, self._shutdown)
        
    def _shutdown(self, signum, frame):
        """Graceful shutdown handler."""
        self.output.system("Shutting down NC...")
        self.running = False
        
    def run(self):
        """Main loop - poll, think, act."""
        self.output.startup_banner()
        self.output.system(f"NC starting up. Timezone: {self.config.timezone}")
        self.output.system(f"Polling interval: {self.config.poll_interval_seconds}s")
        self.output.system(f"Quiet hours: {self.config.quiet_hours_start}:00 - {self.config.quiet_hours_end}:00")

        # Authenticate with Rails API
        self.output.system("Authenticating with Rails API...")
        try:
            self.api.authenticate()
            self.output.system("Authentication successful")
        except AuthenticationError as e:
            self.output.error(f"Authentication failed: {e}")
            self.output.error("NC cannot start without API authentication. Check your agent credentials.")
            return

        # Verify API health
        if not self.api.health_check():
            self.output.warning("API health check failed - API may be unavailable")

        # Track if we've done morning summary today
        last_summary_date = None
        
        while self.running:
            try:
                loop_start = time.time()
                
                # 1. Check if it's time for morning summary
                if self.time.is_summary_time():
                    today = datetime.now(self.time.tz).date()
                    if last_summary_date != today:
                        self._do_morning_summary()
                        last_summary_date = today
                
                # 2. Fetch all active alerts from Rails API
                alerts = self._fetch_alerts()

                # 3. Ingest alerts and reconcile state
                self.state.ingest_alerts(alerts, reconcile=True)
                if alerts:
                    self.output.info(f"Tracking {len(alerts)} active alerts")

                # 4. Reconcile site states (reset sites with no active alerts)
                self.state.reconcile_site_states()
                
                # 5. Check for state transitions (watching -> investigating)
                self._check_state_transitions()

                # 6. For each site needing attention, investigate
                for site in self.state.sites_needing_attention():
                    self._investigate_site(site)

                # 7. Check for auto-recoveries
                self._check_recoveries()

                # 8. Sleep until next poll
                elapsed = time.time() - loop_start
                sleep_time = max(0, self.config.poll_interval_seconds - elapsed)
                time.sleep(sleep_time)
                
            except KeyboardInterrupt:
                break
            except Exception as e:
                self.output.error(f"Loop error: {e}")
                time.sleep(60)  # Back off on errors
                
        self.output.system("NC shutdown complete.")
        
    def _fetch_alerts(self) -> list:
        """Fetch all active alerts from Rails API for full reconciliation."""
        try:
            # Fetch ALL active alerts (no 'since' filter) to properly reconcile state
            alerts = self.api.get_alerts(status="active")
            self.state.update_last_poll_time()
            return alerts
        except Exception as e:
            self.output.error(f"Failed to fetch alerts: {e}")
            return []
            
    def _check_state_transitions(self):
        """Check if any WATCHING sites should escalate."""
        for site in self.state.get_watching_sites():
            context = self.state.get_site_context(site)
            
            # Check for cascade (multiple devices down)
            if len(context.active_alerts) >= 2:
                self.output.site_status(
                    site, "WATCHING", 
                    f"escalating - {len(context.active_alerts)} devices now down"
                )
                self.state.set_concern_level(site, "INVESTIGATING")
                continue
                
            # Check for timeout
            if context.watching_since:
                elapsed = (datetime.utcnow() - context.watching_since).total_seconds()
                if elapsed > self.config.watching_timeout_seconds:
                    self.output.site_status(
                        site, "WATCHING",
                        f"timeout after {int(elapsed)}s - escalating to investigate"
                    )
                    self.state.set_concern_level(site, "INVESTIGATING")
                    
    def _investigate_site(self, site: str):
        """Use Claude to investigate a site."""
        context = self.state.get_site_context(site)
        self.output.site_status(site, "INVESTIGATING", "starting analysis")
        
        # Let Claude reason about the situation
        result = self.claude.investigate(site, context)
        
        # Handle Claude's decision
        if result.action == "wait":
            self.output.site_status(site, "WATCHING", result.reason)
        elif result.action == "escalate":
            self._escalate(site, result)
        elif result.action == "resolved":
            self._mark_auto_resolved(site, result)
            
    def _escalate(self, site: str, result):
        """Escalate an issue to humans."""
        incident = self.state.create_incident(
            site=site,
            summary=result.summary,
            nc_root_cause_guess=result.root_cause_guess,
            devices_affected=result.devices_affected,
            severity=result.severity
        )
        
        self.output.escalate(site, result.summary)
        
        if self.time.is_quiet_hours():
            if result.severity == "major":
                self.output.critical(site, f"CRITICAL during quiet hours: {result.summary}")
            else:
                self.output.waiting(site, "humans likely asleep, queued for morning summary")
        else:
            self.output.attention(site, result.summary)
            
        self.state.set_concern_level(site, "ESCALATED")
        
    def _mark_auto_resolved(self, site: str, result):
        """Mark an incident as auto-resolved."""
        self.state.resolve_incident(
            site=site,
            auto_recovered=True,
            nc_summary=result.summary
        )
        self.output.recovered(site, result.summary)
        self.state.set_concern_level(site, "NORMAL")
        
    def _check_recoveries(self):
        """Check if any escalated sites have recovered."""
        for site in self.state.get_escalated_sites():
            context = self.state.get_site_context(site)
            
            # If all alerts cleared, mark as recovered
            if not context.active_alerts:
                incident = self.state.get_active_incident(site)
                if incident:
                    duration = datetime.utcnow() - incident.started_at
                    self.state.resolve_incident(
                        site=site,
                        auto_recovered=True,
                        nc_summary=f"All devices recovered (duration: {self._format_duration(duration)})"
                    )
                    self.output.recovered(
                        site, 
                        f"all devices back online (duration: {self._format_duration(duration)})"
                    )
                    self.output.pending(site, "need root cause from human")
                self.state.set_concern_level(site, "NORMAL")
                
    def _do_morning_summary(self):
        """Generate and output the morning summary."""
        self.output.morning_summary_header()
        
        summary = self.claude.generate_morning_summary(
            overnight_incidents=self.state.get_incidents_since_last_summary(),
            pending_review=self.state.get_pending_human_review(),
            site_statuses=self.state.get_all_site_statuses()
        )
        
        self.output.morning_summary_body(summary)
        self.state.mark_summary_done()
        
    def _format_duration(self, delta) -> str:
        """Format a timedelta as human-readable string."""
        total_seconds = int(delta.total_seconds())
        hours, remainder = divmod(total_seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        
        if hours > 0:
            return f"{hours}h {minutes}m"
        elif minutes > 0:
            return f"{minutes}m {seconds}s"
        else:
            return f"{seconds}s"


def main():
    """Entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="NOC Claude - Intelligent Network Monitor")
    parser.add_argument("--config", default="config.yml", help="Path to config file")
    parser.add_argument("--cli", action="store_true", help="Run in CLI mode for human input")
    args = parser.parse_args()
    
    if args.cli:
        from nc.cli import run_cli
        run_cli(args.config)
    else:
        nc = NOCClaude(config_path=args.config)
        nc.run()


if __name__ == "__main__":
    main()
