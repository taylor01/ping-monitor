"""
NC Output Module

Structured logging to stdout with timestamps and formatting.
"""

from datetime import datetime
from zoneinfo import ZoneInfo


class NCOutput:
    """Handles formatted output to stdout."""
    
    def __init__(self, timezone: str = "America/New_York"):
        self.tz = ZoneInfo(timezone)
        
    def _timestamp(self) -> str:
        """Get formatted timestamp."""
        return datetime.now(self.tz).strftime("%Y-%m-%d %H:%M:%S")
        
    def _log(self, emoji: str, level: str, site: str, message: str):
        """Core logging function."""
        ts = self._timestamp()
        if site:
            print(f"[{ts}] {emoji} {level} {site}: {message}")
        else:
            print(f"[{ts}] {emoji} {level}: {message}")
            
    # =========================================================================
    # Site Status Messages
    # =========================================================================
    
    def site_status(self, site: str, level: str, message: str):
        """Log a site status update."""
        emoji_map = {
            "NORMAL": "✅",
            "WATCHING": "🟡",
            "INVESTIGATING": "🔍",
            "ESCALATED": "🚨"
        }
        emoji = emoji_map.get(level, "ℹ️")
        self._log(emoji, level, site, message)
        
    def watching(self, site: str, message: str):
        """Log WATCHING status."""
        self._log("🟡", "WATCHING", site, message)
        
    def investigating(self, site: str, message: str):
        """Log INVESTIGATING status."""
        self._log("🔍", "INVESTIGATING", site, message)
        
    def escalate(self, site: str, message: str):
        """Log escalation."""
        self._log("🚨", "ESCALATED", site, message)
        
    def critical(self, site: str, message: str):
        """Log critical issue (wakes humans)."""
        self._log("🔥", "CRITICAL", site, message)
        
    def waiting(self, site: str, message: str):
        """Log waiting status (quiet hours)."""
        self._log("⏳", "WAITING", site, message)
        
    def recovered(self, site: str, message: str):
        """Log recovery."""
        self._log("✅", "RECOVERED", site, message)
        
    def pending(self, site: str, message: str):
        """Log pending human input."""
        self._log("📝", "PENDING", site, message)
        
    def attention(self, site: str, message: str):
        """Log attention needed (non-quiet hours)."""
        self._log("👀", "ATTENTION", site, message)
        
    # =========================================================================
    # Tool Execution
    # =========================================================================
    
    def tool_call(self, tool_name: str, params: dict):
        """Log a tool being called."""
        params_str = ", ".join(f"{k}={v}" for k, v in params.items())
        self._log("🔧", "TOOL", None, f"{tool_name}({params_str})")
        
    def tool_result(self, tool_name: str, result: str):
        """Log tool result (abbreviated)."""
        # Truncate long results
        if len(result) > 100:
            result_short = result[:100] + "..."
        else:
            result_short = result
        self._log("📤", "RESULT", None, f"{tool_name} → {result_short}")
        
    # =========================================================================
    # System Messages
    # =========================================================================
    
    def system(self, message: str):
        """Log system message."""
        self._log("⚙️", "SYSTEM", None, message)
        
    def info(self, message: str):
        """Log info message."""
        self._log("ℹ️", "INFO", None, message)
        
    def error(self, message: str):
        """Log error message."""
        self._log("❌", "ERROR", None, message)
        
    def startup_banner(self):
        """Print startup banner."""
        print()
        print("=" * 60)
        print("   NC (NOC Claude) - Intelligent Network Monitor")
        print("=" * 60)
        print()
        
    # =========================================================================
    # Morning Summary
    # =========================================================================
    
    def morning_summary_header(self):
        """Print morning summary header."""
        ts = self._timestamp()
        print()
        print("=" * 70)
        print(f"[{ts}] ☀️ MORNING SUMMARY (Eastern)")
        print("=" * 70)
        print()
        
    def morning_summary_body(self, summary: str):
        """Print morning summary body."""
        print(summary)
        print()
        print("=" * 70)
        print()
        
    # =========================================================================
    # Human Interaction (CLI)
    # =========================================================================
    
    def human_response(self, message: str):
        """Log human response/command."""
        self._log("👤", "HUMAN", None, message)
        
    def nc_reply(self, message: str):
        """Log NC's reply to human."""
        self._log("🤖", "NC", None, message)
