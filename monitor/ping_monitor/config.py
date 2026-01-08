"""
Configuration management for ping monitor
"""

import os
from pathlib import Path
from typing import Optional
from dataclasses import dataclass


@dataclass
class Config:
    """Monitor configuration loaded from environment variables"""

    # Site identification
    site_name: str = "default"

    # Rails API (Phase 1)
    rails_api_url: Optional[str] = None
    site_secret: Optional[str] = None

    # Datadog
    dd_api_key: Optional[str] = None
    dd_site: str = "datadoghq.com"

    # Ping settings
    ping_interval: int = 60
    ping_count: int = 3
    ping_timeout: int = 2
    max_workers: int = 20

    # SNMP UPS monitoring settings
    snmp_enabled: bool = True
    snmp_interval: int = 60
    snmp_default_community: str = "public"
    snmp_timeout: int = 2
    snmp_retries: int = 1
    snmp_max_workers: int = 10

    # Paths
    buffer_db_path: Path = Path("/data/buffer.db")
    hosts_config_path: Path = Path("/config/hosts.json")
    hosts_cache_path: Path = Path("/data/hosts-cache.json")

    # Remote config
    config_url: Optional[str] = None

    @classmethod
    def from_env(cls) -> "Config":
        """
        Load configuration from environment variables

        Returns:
            Config instance
        """
        return cls(
            site_name=os.getenv("SITE_NAME", "default"),
            rails_api_url=os.getenv("RAILS_API_URL"),
            site_secret=cls._read_secret("SITE_SECRET"),
            dd_api_key=cls._read_secret("DD_API_KEY"),
            dd_site=os.getenv("DD_SITE", "datadoghq.com"),
            ping_interval=int(os.getenv("PING_INTERVAL", "60")),
            ping_count=int(os.getenv("PING_COUNT", "3")),
            ping_timeout=int(os.getenv("PING_TIMEOUT", "2")),
            max_workers=int(os.getenv("MAX_WORKERS", "20")),
            snmp_enabled=os.getenv("SNMP_ENABLED", "true").lower() in ("true", "1", "yes"),
            snmp_interval=int(os.getenv("SNMP_INTERVAL", "60")),
            snmp_default_community=os.getenv("SNMP_DEFAULT_COMMUNITY", "public"),
            snmp_timeout=int(os.getenv("SNMP_TIMEOUT", "2")),
            snmp_retries=int(os.getenv("SNMP_RETRIES", "1")),
            snmp_max_workers=int(os.getenv("SNMP_MAX_WORKERS", "10")),
            buffer_db_path=Path(os.getenv("BUFFER_DB_PATH", "/data/buffer.db")),
            hosts_config_path=Path(os.getenv("LOCAL_HOSTS", "/config/hosts.json")),
            hosts_cache_path=Path(os.getenv("LOCAL_CACHE", "/data/hosts-cache.json")),
            config_url=os.getenv("CONFIG_URL"),
        )

    @staticmethod
    def _read_secret(env_var: str) -> Optional[str]:
        """
        Read secret from environment variable or Docker secret file

        Supports both direct env vars and Docker secrets pattern (_FILE suffix)

        Args:
            env_var: Environment variable name

        Returns:
            Secret value or None
        """
        # Check for _FILE variant (Docker secrets)
        file_var = f"{env_var}_FILE"
        if file_var in os.environ:
            secret_path = Path(os.environ[file_var])
            if secret_path.exists():
                return secret_path.read_text().strip()

        # Direct environment variable
        return os.getenv(env_var)

    @property
    def has_rails_api(self) -> bool:
        """Check if Rails API is configured"""
        return bool(self.rails_api_url and self.site_secret)

    @property
    def has_datadog(self) -> bool:
        """Check if Datadog is configured"""
        return bool(self.dd_api_key)

    @property
    def has_snmp(self) -> bool:
        """Check if SNMP monitoring is enabled"""
        return self.snmp_enabled

    def validate(self) -> None:
        """
        Validate configuration

        Raises:
            ValueError: If configuration is invalid
        """
        if not self.has_rails_api and not self.has_datadog:
            raise ValueError(
                "At least one output must be configured: RAILS_API_URL or DD_API_KEY"
            )

        if self.ping_interval < 10:
            raise ValueError("PING_INTERVAL must be at least 10 seconds")

        if self.ping_count < 1:
            raise ValueError("PING_COUNT must be at least 1")

        if self.snmp_enabled and self.snmp_interval < 10:
            raise ValueError("SNMP_INTERVAL must be at least 10 seconds")
