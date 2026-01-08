"""
SNMP UPS monitoring functionality using pysnmp
Polls SNMP-enabled UPS devices for power status and battery runtime
"""

from typing import List, Dict, Optional, Tuple
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor, as_completed

from .models import Host, UPSStatus
from .logging_config import get_logger

logger = get_logger(__name__)

# Standard UPS MIB OIDs (RFC 1628 - UPS-MIB)
# These are commonly supported by most UPS devices
UPS_OIDS = {
    # Battery group
    "battery_status": "1.3.6.1.2.1.33.1.2.1.0",       # upsBasicBatteryStatus (1=unknown, 2=normal, 3=low, 4=depleted)
    "seconds_on_battery": "1.3.6.1.2.1.33.1.2.2.0",   # upsSecondsOnBattery
    "estimated_minutes_remaining": "1.3.6.1.2.1.33.1.2.3.0",  # upsEstimatedMinutesRemaining
    "estimated_charge_remaining": "1.3.6.1.2.1.33.1.2.4.0",   # upsEstimatedChargeRemaining (%)
    "battery_voltage": "1.3.6.1.2.1.33.1.2.5.0",      # upsBatteryVoltage (0.1V units)
    "battery_current": "1.3.6.1.2.1.33.1.2.6.0",      # upsBatteryCurrent
    "battery_temperature": "1.3.6.1.2.1.33.1.2.7.0",  # upsBatteryTemperature

    # Input group
    "input_line_bads": "1.3.6.1.2.1.33.1.3.1.0",      # upsInputLineBads
    "input_num_lines": "1.3.6.1.2.1.33.1.3.2.0",      # upsInputNumLines
    "input_voltage": "1.3.6.1.2.1.33.1.3.3.1.3.1",    # upsInputVoltage (first line)
    "input_frequency": "1.3.6.1.2.1.33.1.3.3.1.2.1",  # upsInputFrequency (first line, 0.1Hz)

    # Output group
    "output_source": "1.3.6.1.2.1.33.1.4.1.0",        # upsOutputSource (1=other,2=none,3=normal,4=bypass,5=battery,6=booster,7=reducer)
    "output_frequency": "1.3.6.1.2.1.33.1.4.2.0",     # upsOutputFrequency (0.1Hz)
    "output_num_lines": "1.3.6.1.2.1.33.1.4.3.0",     # upsOutputNumLines
    "output_voltage": "1.3.6.1.2.1.33.1.4.4.1.2.1",   # upsOutputVoltage (first line)
    "output_current": "1.3.6.1.2.1.33.1.4.4.1.3.1",   # upsOutputCurrent (first line, 0.1A)
    "output_power": "1.3.6.1.2.1.33.1.4.4.1.4.1",     # upsOutputPower (first line, watts)
    "output_load": "1.3.6.1.2.1.33.1.4.4.1.5.1",      # upsOutputPercentLoad (first line, %)

    # Identity group
    "ups_manufacturer": "1.3.6.1.2.1.33.1.1.1.0",     # upsIdentManufacturer
    "ups_model": "1.3.6.1.2.1.33.1.1.2.0",            # upsIdentModel
    "ups_software_version": "1.3.6.1.2.1.33.1.1.3.0", # upsIdentUPSSoftwareVersion
    "ups_agent_version": "1.3.6.1.2.1.33.1.1.4.0",    # upsIdentAgentSoftwareVersion
    "ups_name": "1.3.6.1.2.1.33.1.1.5.0",             # upsIdentName
}

# Output source values
OUTPUT_SOURCE_BATTERY = 5
OUTPUT_SOURCE_NORMAL = 3


class SNMPMonitor:
    """
    Handles SNMP polling of UPS devices
    """

    def __init__(
        self,
        default_community: str = "public",
        timeout: int = 2,
        retries: int = 1,
        max_workers: int = 10,
        port: int = 161
    ):
        """
        Initialize SNMP monitor

        Args:
            default_community: Default SNMP community string
            timeout: SNMP request timeout in seconds
            retries: Number of SNMP retries
            max_workers: Maximum concurrent SNMP workers
            port: SNMP port (default 161)
        """
        self.default_community = default_community
        self.timeout = timeout
        self.retries = retries
        self.max_workers = max_workers
        self.port = port
        self._snmp_available = self._check_snmp_available()

    def _check_snmp_available(self) -> bool:
        """Check if pysnmp library is available"""
        try:
            from pysnmp.hlapi import (
                getCmd, SnmpEngine, CommunityData, UdpTransportTarget,
                ContextData, ObjectType, ObjectIdentity
            )
            return True
        except ImportError:
            logger.warning("pysnmp library not available - SNMP monitoring disabled")
            return False

    def _snmp_get(
        self,
        ip: str,
        community: str,
        oids: List[str]
    ) -> Dict[str, Optional[str]]:
        """
        Perform SNMP GET request for multiple OIDs

        Args:
            ip: Target IP address
            community: SNMP community string
            oids: List of OID strings to query

        Returns:
            Dictionary mapping OID names to values (or None if failed)
        """
        if not self._snmp_available:
            return {}

        from pysnmp.hlapi import (
            getCmd, SnmpEngine, CommunityData, UdpTransportTarget,
            ContextData, ObjectType, ObjectIdentity
        )

        results = {}

        # Build object types for all OIDs
        object_types = [ObjectType(ObjectIdentity(oid)) for oid in oids]

        try:
            error_indication, error_status, error_index, var_binds = next(
                getCmd(
                    SnmpEngine(),
                    CommunityData(community, mpModel=1),  # SNMPv2c
                    UdpTransportTarget(
                        (ip, self.port),
                        timeout=self.timeout,
                        retries=self.retries
                    ),
                    ContextData(),
                    *object_types
                )
            )

            if error_indication:
                logger.debug(
                    "snmp_error_indication",
                    ip=ip,
                    error=str(error_indication)
                )
                return {}
            elif error_status:
                logger.debug(
                    "snmp_error_status",
                    ip=ip,
                    error=f"{error_status.prettyPrint()} at {error_index and var_binds[int(error_index) - 1][0] or '?'}"
                )
                return {}
            else:
                for var_bind in var_binds:
                    oid_str = str(var_bind[0])
                    value = var_bind[1]

                    # Find matching OID name
                    for name, oid in UPS_OIDS.items():
                        if oid_str.startswith(oid.rstrip('.0')) or oid == oid_str:
                            # Convert to appropriate Python type
                            try:
                                if hasattr(value, 'prettyPrint'):
                                    results[name] = value.prettyPrint()
                                else:
                                    results[name] = str(value)
                            except Exception:
                                results[name] = None
                            break

        except Exception as e:
            logger.debug("snmp_exception", ip=ip, error=str(e))
            return {}

        return results

    def _poll_single_ups(self, host: Host, timestamp: datetime) -> UPSStatus:
        """
        Poll a single UPS device

        Args:
            host: Host object with SNMP configuration
            timestamp: Timestamp for this poll

        Returns:
            UPSStatus object
        """
        community = host.snmp_community or self.default_community

        # Query key UPS OIDs
        oids_to_query = [
            UPS_OIDS["output_source"],
            UPS_OIDS["estimated_minutes_remaining"],
            UPS_OIDS["estimated_charge_remaining"],
            UPS_OIDS["output_load"],
            UPS_OIDS["input_voltage"],
            UPS_OIDS["output_voltage"],
            UPS_OIDS["battery_voltage"],
            UPS_OIDS["ups_model"],
        ]

        results = self._snmp_get(host.ip, community, oids_to_query)

        if not results:
            return UPSStatus(
                host=host.name,
                ip=host.ip,
                timestamp=timestamp,
                is_reachable=False,
                error_message="SNMP query failed or timed out"
            )

        # Parse results
        try:
            output_source = self._safe_int(results.get("output_source"))
            on_battery = output_source == OUTPUT_SOURCE_BATTERY if output_source else None

            runtime_minutes = self._safe_float(results.get("estimated_minutes_remaining"))
            charge_percent = self._safe_float(results.get("estimated_charge_remaining"))
            load_percent = self._safe_float(results.get("output_load"))
            input_voltage = self._safe_float(results.get("input_voltage"))
            output_voltage = self._safe_float(results.get("output_voltage"))

            # Battery voltage is often in 0.1V units
            battery_voltage_raw = self._safe_float(results.get("battery_voltage"))
            battery_voltage = battery_voltage_raw / 10.0 if battery_voltage_raw else None

            ups_model = results.get("ups_model")

            return UPSStatus(
                host=host.name,
                ip=host.ip,
                timestamp=timestamp,
                is_reachable=True,
                on_battery=on_battery,
                battery_runtime_minutes=runtime_minutes,
                battery_charge_percent=charge_percent,
                output_load_percent=load_percent,
                input_voltage=input_voltage,
                output_voltage=output_voltage,
                battery_voltage=battery_voltage,
                ups_model=ups_model,
            )

        except Exception as e:
            logger.error("ups_parse_error", host=host.name, ip=host.ip, error=str(e))
            return UPSStatus(
                host=host.name,
                ip=host.ip,
                timestamp=timestamp,
                is_reachable=True,
                error_message=f"Error parsing SNMP data: {str(e)}"
            )

    @staticmethod
    def _safe_int(value: Optional[str]) -> Optional[int]:
        """Safely convert string to int"""
        if value is None:
            return None
        try:
            return int(value)
        except (ValueError, TypeError):
            return None

    @staticmethod
    def _safe_float(value: Optional[str]) -> Optional[float]:
        """Safely convert string to float"""
        if value is None:
            return None
        try:
            return float(value)
        except (ValueError, TypeError):
            return None

    def poll_ups_devices(self, hosts: List[Host]) -> List[UPSStatus]:
        """
        Poll multiple UPS devices concurrently

        Args:
            hosts: List of Host objects to poll (only SNMP-enabled hosts are polled)

        Returns:
            List of UPSStatus objects
        """
        # Filter to only SNMP-enabled hosts
        snmp_hosts = [h for h in hosts if h.snmp_enabled]

        if not snmp_hosts:
            logger.debug("no_snmp_hosts_to_poll")
            return []

        if not self._snmp_available:
            logger.warning("snmp_library_not_available")
            timestamp = datetime.now(timezone.utc)
            return [
                UPSStatus(
                    host=h.name,
                    ip=h.ip,
                    timestamp=timestamp,
                    is_reachable=False,
                    error_message="pysnmp library not installed"
                )
                for h in snmp_hosts
            ]

        timestamp = datetime.now(timezone.utc)
        results: List[UPSStatus] = []

        logger.debug(f"Polling {len(snmp_hosts)} UPS devices...")

        # Use thread pool for concurrent polling
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_host = {
                executor.submit(self._poll_single_ups, host, timestamp): host
                for host in snmp_hosts
            }

            for future in as_completed(future_to_host):
                host = future_to_host[future]
                try:
                    status = future.result()
                    results.append(status)

                    # Log result
                    if status.is_reachable:
                        logger.info(
                            "ups_poll_result",
                            host=status.host,
                            ip=status.ip,
                            is_reachable=True,
                            on_battery=status.on_battery,
                            battery_runtime_minutes=status.battery_runtime_minutes,
                            battery_charge_percent=status.battery_charge_percent,
                        )
                    else:
                        logger.warning(
                            "ups_poll_failed",
                            host=status.host,
                            ip=status.ip,
                            error=status.error_message,
                        )

                except Exception as e:
                    logger.error(
                        "ups_poll_exception",
                        host=host.name,
                        ip=host.ip,
                        error=str(e)
                    )
                    results.append(
                        UPSStatus(
                            host=host.name,
                            ip=host.ip,
                            timestamp=timestamp,
                            is_reachable=False,
                            error_message=str(e)
                        )
                    )

        logger.info("ups_poll_batch_complete", ups_count=len(results))
        return results

    @property
    def is_available(self) -> bool:
        """Check if SNMP monitoring is available"""
        return self._snmp_available
