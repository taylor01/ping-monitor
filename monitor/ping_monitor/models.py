"""
Data models for ping measurements and configuration
"""

from dataclasses import dataclass, asdict
from typing import List, Optional
from datetime import datetime, timezone


@dataclass
class Host:
    """Represents a host to monitor"""
    name: str
    ip: str
    description: Optional[str] = None
    type: Optional[str] = None
    tags: Optional[List[str]] = None
    snmp_enabled: bool = False
    snmp_community: Optional[str] = None
    snmp_version: str = "2c"

    def to_dict(self) -> dict:
        """Convert to dictionary, excluding None values"""
        return {k: v for k, v in asdict(self).items() if v is not None}


@dataclass
class PingResult:
    """Result of pinging a single host"""
    host: str
    ip: str
    timestamp: datetime
    is_up: bool
    latency_ms: Optional[float] = None
    packet_loss: Optional[float] = None
    jitter_ms: Optional[float] = None

    def to_dict(self) -> dict:
        """Convert to dictionary with ISO timestamp"""
        data = asdict(self)
        data['timestamp'] = self.timestamp.isoformat()
        return {k: v for k, v in data.items() if v is not None}


@dataclass
class MeasurementBatch:
    """A batch of measurements from one ping cycle"""
    site: str
    timestamp: datetime
    measurements: List[PingResult]

    def to_dict(self) -> dict:
        """Convert to dictionary"""
        return {
            'site': self.site,
            'timestamp': self.timestamp.isoformat(),
            'measurements': [m.to_dict() for m in self.measurements]
        }

    @property
    def count(self) -> int:
        """Number of measurements in batch"""
        return len(self.measurements)

    @property
    def hosts_up(self) -> int:
        """Number of hosts that are up"""
        return sum(1 for m in self.measurements if m.is_up)

    @property
    def hosts_down(self) -> int:
        """Number of hosts that are down"""
        return self.count - self.hosts_up


@dataclass
class UPSStatus:
    """Result of SNMP polling a single UPS device"""
    host: str
    ip: str
    timestamp: datetime
    is_reachable: bool
    on_battery: Optional[bool] = None
    battery_runtime_minutes: Optional[float] = None
    battery_charge_percent: Optional[float] = None
    output_load_percent: Optional[float] = None
    input_voltage: Optional[float] = None
    output_voltage: Optional[float] = None
    battery_voltage: Optional[float] = None
    ups_model: Optional[str] = None
    error_message: Optional[str] = None

    def to_dict(self) -> dict:
        """Convert to dictionary with ISO timestamp"""
        data = asdict(self)
        data['timestamp'] = self.timestamp.isoformat()
        return {k: v for k, v in data.items() if v is not None}


@dataclass
class UPSBatch:
    """A batch of UPS status readings from one polling cycle"""
    site: str
    timestamp: datetime
    ups_statuses: List[UPSStatus]

    def to_dict(self) -> dict:
        """Convert to dictionary"""
        return {
            'site': self.site,
            'timestamp': self.timestamp.isoformat(),
            'ups_statuses': [s.to_dict() for s in self.ups_statuses]
        }

    @property
    def count(self) -> int:
        """Number of UPS devices in batch"""
        return len(self.ups_statuses)

    @property
    def ups_reachable(self) -> int:
        """Number of UPS devices that are reachable"""
        return sum(1 for s in self.ups_statuses if s.is_reachable)

    @property
    def ups_on_battery(self) -> int:
        """Number of UPS devices running on battery"""
        return sum(1 for s in self.ups_statuses if s.is_reachable and s.on_battery)
