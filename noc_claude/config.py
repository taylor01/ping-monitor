"""
NC Configuration Management
"""

import os
import yaml
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class RailsAPIConfig:
    """Rails API connection settings."""
    url: str
    agent_name: str
    agent_secret: str
    timeout_seconds: int = 30


@dataclass 
class SiteConfig:
    """Per-site configuration."""
    name: str
    tailscale_ip: Optional[str] = None
    critical_devices: List[str] = field(default_factory=list)
    

@dataclass
class Config:
    """Main NC configuration."""
    
    # Rails API
    rails_api: RailsAPIConfig
    
    # Timezone and schedule
    timezone: str = "America/New_York"
    poll_interval_seconds: int = 30
    morning_summary_hour: int = 7
    quiet_hours_start: int = 22
    quiet_hours_end: int = 7
    
    # Thresholds
    watching_timeout_seconds: int = 120
    cascade_window_seconds: int = 30
    pattern_confidence_threshold: float = 0.7
    
    # Sites
    sites: List[SiteConfig] = field(default_factory=list)
    
    # Database
    database_path: str = "data/nc.db"
    
    # Claude
    claude_model: str = "claude-sonnet-4-20250514"
    
    @classmethod
    def load(cls, path: str) -> "Config":
        """Load configuration from YAML file with environment variable substitution."""
        
        with open(path, 'r') as f:
            raw = yaml.safe_load(f)
            
        # Substitute environment variables
        raw = cls._substitute_env_vars(raw)
        
        # Build RailsAPIConfig
        rails_cfg = raw.get('rails_api', {})
        rails_api = RailsAPIConfig(
            url=rails_cfg.get('url', 'http://localhost:3000'),
            agent_name=rails_cfg.get('agent_name', 'noc-claude'),
            agent_secret=rails_cfg.get('agent_secret', ''),
            timeout_seconds=rails_cfg.get('timeout_seconds', 30)
        )
        
        # Build site configs
        sites = []
        for site_raw in raw.get('sites', []):
            sites.append(SiteConfig(
                name=site_raw.get('name'),
                tailscale_ip=site_raw.get('tailscale_ip'),
                critical_devices=site_raw.get('critical_devices', [])
            ))
            
        # Build schedule config
        schedule = raw.get('schedule', {})
        thresholds = raw.get('thresholds', {})
        
        return cls(
            rails_api=rails_api,
            timezone=raw.get('timezone', 'America/New_York'),
            poll_interval_seconds=schedule.get('poll_interval_seconds', 30),
            morning_summary_hour=schedule.get('morning_summary_hour', 7),
            quiet_hours_start=schedule.get('quiet_hours_start', 22),
            quiet_hours_end=schedule.get('quiet_hours_end', 7),
            watching_timeout_seconds=thresholds.get('watching_timeout_seconds', 120),
            cascade_window_seconds=thresholds.get('cascade_window_seconds', 30),
            pattern_confidence_threshold=thresholds.get('pattern_confidence_threshold', 0.7),
            sites=sites,
            database_path=raw.get('database_path', 'data/nc.db'),
            claude_model=raw.get('claude_model', 'claude-sonnet-4-20250514')
        )
        
    @classmethod
    def _substitute_env_vars(cls, obj):
        """Recursively substitute ${VAR} patterns with environment variables."""
        if isinstance(obj, str):
            if obj.startswith('${') and obj.endswith('}'):
                var_name = obj[2:-1]
                return os.environ.get(var_name, '')
            return obj
        elif isinstance(obj, dict):
            return {k: cls._substitute_env_vars(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [cls._substitute_env_vars(item) for item in obj]
        return obj
    
    def get_site(self, name: str) -> Optional[SiteConfig]:
        """Get site config by name."""
        for site in self.sites:
            if site.name == name:
                return site
        return None
    
    def is_critical_device(self, site: str, device: str) -> bool:
        """Check if a device is marked critical for a site."""
        site_cfg = self.get_site(site)
        if site_cfg:
            return device in site_cfg.critical_devices
        return False
