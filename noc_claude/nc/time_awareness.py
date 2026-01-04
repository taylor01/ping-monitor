"""
NC Time Awareness

Handles timezone, quiet hours, and morning summary scheduling.
"""

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo


class TimeAwareness:
    """Manages time-related awareness for NC."""
    
    def __init__(self, timezone: str = "America/New_York",
                 summary_hour: int = 7,
                 quiet_start: int = 22,
                 quiet_end: int = 7):
        self.tz = ZoneInfo(timezone)
        self.summary_hour = summary_hour
        self.quiet_start = quiet_start
        self.quiet_end = quiet_end
        
    def now(self) -> datetime:
        """Get current time in configured timezone."""
        return datetime.now(self.tz)
        
    def current_hour(self) -> int:
        """Get current hour in configured timezone."""
        return self.now().hour
        
    def is_quiet_hours(self) -> bool:
        """Check if we're in quiet hours (humans sleeping)."""
        hour = self.current_hour()
        
        if self.quiet_start > self.quiet_end:
            # Wraps around midnight (e.g., 22:00 - 07:00)
            return hour >= self.quiet_start or hour < self.quiet_end
        else:
            # Same day (e.g., 02:00 - 06:00)
            return self.quiet_start <= hour < self.quiet_end
            
    def is_summary_time(self) -> bool:
        """Check if it's time for morning summary (within first 5 minutes of summary hour)."""
        now = self.now()
        return now.hour == self.summary_hour and now.minute < 5
        
    def time_until_summary(self) -> timedelta:
        """Get time until next morning summary."""
        now = self.now()
        
        # Calculate next summary time
        next_summary = now.replace(
            hour=self.summary_hour,
            minute=0,
            second=0,
            microsecond=0
        )
        
        # If we're past summary time today, it's tomorrow
        if now.hour >= self.summary_hour:
            next_summary += timedelta(days=1)
            
        return next_summary - now
        
    def format_time_until_summary(self) -> str:
        """Human-readable time until next summary."""
        delta = self.time_until_summary()
        hours = int(delta.total_seconds() // 3600)
        minutes = int((delta.total_seconds() % 3600) // 60)
        
        if hours > 0:
            return f"{hours}h {minutes}m"
        else:
            return f"{minutes}m"
            
    def last_summary_time(self) -> datetime:
        """Get the time of the last morning summary."""
        now = self.now()
        
        last_summary = now.replace(
            hour=self.summary_hour,
            minute=0,
            second=0,
            microsecond=0
        )
        
        # If we haven't had today's summary yet, use yesterday's
        if now.hour < self.summary_hour:
            last_summary -= timedelta(days=1)
            
        return last_summary
        
    def human_status(self) -> str:
        """Get human-readable status of humans."""
        if self.is_quiet_hours():
            return f"likely asleep (quiet hours: {self.quiet_start}:00-{self.quiet_end}:00)"
        else:
            return "likely awake"
            
    def should_wake_humans(self, severity: str) -> bool:
        """Determine if we should wake humans for an issue."""
        # Always wake for major incidents
        if severity == "major":
            return True
            
        # During normal hours, always notify
        if not self.is_quiet_hours():
            return True
            
        # During quiet hours, only wake for major
        return False
