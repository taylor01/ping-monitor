"""Tests for SNMP UPS monitoring module"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timezone

from ping_monitor.snmp_monitor import SNMPMonitor, UPS_OIDS, OUTPUT_SOURCE_BATTERY
from ping_monitor.models import Host, UPSStatus


class TestSNMPMonitor:
    """Tests for SNMPMonitor class"""

    def test_init_defaults(self):
        """Test default initialization values"""
        monitor = SNMPMonitor()
        assert monitor.default_community == "public"
        assert monitor.timeout == 2
        assert monitor.retries == 1
        assert monitor.max_workers == 10
        assert monitor.port == 161

    def test_init_custom_values(self):
        """Test custom initialization values"""
        monitor = SNMPMonitor(
            default_community="private",
            timeout=5,
            retries=3,
            max_workers=20,
            port=1161
        )
        assert monitor.default_community == "private"
        assert monitor.timeout == 5
        assert monitor.retries == 3
        assert monitor.max_workers == 20
        assert monitor.port == 1161

    def test_poll_ups_devices_empty_list(self):
        """Test polling empty host list returns empty results"""
        monitor = SNMPMonitor()
        results = monitor.poll_ups_devices([])
        assert results == []

    def test_poll_ups_devices_no_snmp_hosts(self):
        """Test polling hosts with no SNMP-enabled devices returns empty"""
        monitor = SNMPMonitor()
        hosts = [
            Host(name="router", ip="192.168.1.1", snmp_enabled=False),
            Host(name="switch", ip="192.168.1.2", snmp_enabled=False),
        ]
        results = monitor.poll_ups_devices(hosts)
        assert results == []

    @patch("ping_monitor.snmp_monitor.SNMPMonitor._check_snmp_available")
    def test_poll_ups_devices_snmp_unavailable(self, mock_check):
        """Test polling when pysnmp is not available"""
        mock_check.return_value = False
        monitor = SNMPMonitor()
        monitor._snmp_available = False

        hosts = [
            Host(name="ups1", ip="192.168.1.10", snmp_enabled=True),
        ]
        results = monitor.poll_ups_devices(hosts)

        assert len(results) == 1
        assert results[0].is_reachable is False
        assert "not installed" in results[0].error_message

    @patch("ping_monitor.snmp_monitor.SNMPMonitor._poll_single_ups")
    @patch("ping_monitor.snmp_monitor.SNMPMonitor._check_snmp_available")
    def test_poll_ups_devices_success(self, mock_check, mock_poll):
        """Test successful polling of UPS devices"""
        mock_check.return_value = True

        mock_status = UPSStatus(
            host="ups1",
            ip="192.168.1.10",
            timestamp=datetime.now(timezone.utc),
            is_reachable=True,
            on_battery=False,
            battery_runtime_minutes=60.0,
            battery_charge_percent=100.0,
        )
        mock_poll.return_value = mock_status

        monitor = SNMPMonitor()
        monitor._snmp_available = True

        hosts = [
            Host(name="ups1", ip="192.168.1.10", snmp_enabled=True),
            Host(name="router", ip="192.168.1.1", snmp_enabled=False),
        ]

        results = monitor.poll_ups_devices(hosts)

        assert len(results) == 1
        assert results[0].host == "ups1"
        assert results[0].is_reachable is True
        assert results[0].on_battery is False

    @patch("ping_monitor.snmp_monitor.SNMPMonitor._snmp_get")
    @patch("ping_monitor.snmp_monitor.SNMPMonitor._check_snmp_available")
    def test_poll_single_ups_success(self, mock_check, mock_snmp_get):
        """Test successful single UPS poll"""
        mock_check.return_value = True
        mock_snmp_get.return_value = {
            "output_source": "3",  # Normal (facility power)
            "estimated_minutes_remaining": "120",
            "estimated_charge_remaining": "100",
            "output_load": "25",
            "input_voltage": "120",
            "output_voltage": "120",
            "battery_voltage": "540",  # 54.0V in 0.1V units
            "ups_model": "SmartUPS 1500",
        }

        monitor = SNMPMonitor()
        monitor._snmp_available = True

        host = Host(name="ups1", ip="192.168.1.10", snmp_enabled=True)
        timestamp = datetime.now(timezone.utc)

        result = monitor._poll_single_ups(host, timestamp)

        assert result.host == "ups1"
        assert result.ip == "192.168.1.10"
        assert result.is_reachable is True
        assert result.on_battery is False  # output_source 3 = normal
        assert result.battery_runtime_minutes == 120.0
        assert result.battery_charge_percent == 100.0
        assert result.output_load_percent == 25.0
        assert result.input_voltage == 120.0
        assert result.output_voltage == 120.0
        assert result.battery_voltage == 54.0
        assert result.ups_model == "SmartUPS 1500"

    @patch("ping_monitor.snmp_monitor.SNMPMonitor._snmp_get")
    @patch("ping_monitor.snmp_monitor.SNMPMonitor._check_snmp_available")
    def test_poll_single_ups_on_battery(self, mock_check, mock_snmp_get):
        """Test single UPS poll when on battery"""
        mock_check.return_value = True
        mock_snmp_get.return_value = {
            "output_source": "5",  # Battery
            "estimated_minutes_remaining": "30",
            "estimated_charge_remaining": "75",
            "output_load": "50",
            "input_voltage": "0",
            "output_voltage": "120",
            "battery_voltage": "480",
        }

        monitor = SNMPMonitor()
        monitor._snmp_available = True

        host = Host(name="ups1", ip="192.168.1.10", snmp_enabled=True)
        timestamp = datetime.now(timezone.utc)

        result = monitor._poll_single_ups(host, timestamp)

        assert result.is_reachable is True
        assert result.on_battery is True  # output_source 5 = battery
        assert result.battery_runtime_minutes == 30.0
        assert result.battery_charge_percent == 75.0

    @patch("ping_monitor.snmp_monitor.SNMPMonitor._snmp_get")
    @patch("ping_monitor.snmp_monitor.SNMPMonitor._check_snmp_available")
    def test_poll_single_ups_timeout(self, mock_check, mock_snmp_get):
        """Test single UPS poll when SNMP times out"""
        mock_check.return_value = True
        mock_snmp_get.return_value = {}  # Empty result indicates timeout

        monitor = SNMPMonitor()
        monitor._snmp_available = True

        host = Host(name="ups1", ip="192.168.1.10", snmp_enabled=True)
        timestamp = datetime.now(timezone.utc)

        result = monitor._poll_single_ups(host, timestamp)

        assert result.is_reachable is False
        assert "failed or timed out" in result.error_message

    @patch("ping_monitor.snmp_monitor.SNMPMonitor._check_snmp_available")
    def test_poll_single_ups_custom_community(self, mock_check):
        """Test that custom community string is used"""
        mock_check.return_value = True

        monitor = SNMPMonitor(default_community="public")
        monitor._snmp_available = True

        host = Host(
            name="ups1",
            ip="192.168.1.10",
            snmp_enabled=True,
            snmp_community="private"
        )

        with patch.object(monitor, '_snmp_get', return_value={}) as mock_get:
            timestamp = datetime.now(timezone.utc)
            monitor._poll_single_ups(host, timestamp)
            # Verify the custom community was used
            call_args = mock_get.call_args
            assert call_args[0][1] == "private"  # community is second arg

    def test_safe_int(self):
        """Test _safe_int helper"""
        assert SNMPMonitor._safe_int("123") == 123
        assert SNMPMonitor._safe_int("0") == 0
        assert SNMPMonitor._safe_int(None) is None
        assert SNMPMonitor._safe_int("abc") is None
        assert SNMPMonitor._safe_int("") is None

    def test_safe_float(self):
        """Test _safe_float helper"""
        assert SNMPMonitor._safe_float("123.45") == 123.45
        assert SNMPMonitor._safe_float("0") == 0.0
        assert SNMPMonitor._safe_float(None) is None
        assert SNMPMonitor._safe_float("abc") is None
        assert SNMPMonitor._safe_float("") is None

    def test_is_available_property(self):
        """Test is_available property"""
        monitor = SNMPMonitor()
        # The property should return the internal _snmp_available value
        monitor._snmp_available = True
        assert monitor.is_available is True
        monitor._snmp_available = False
        assert monitor.is_available is False


class TestUPSOIDs:
    """Tests for UPS OID definitions"""

    def test_battery_oids_defined(self):
        """Test that battery OIDs are defined"""
        assert "battery_status" in UPS_OIDS
        assert "estimated_minutes_remaining" in UPS_OIDS
        assert "estimated_charge_remaining" in UPS_OIDS
        assert "battery_voltage" in UPS_OIDS

    def test_input_oids_defined(self):
        """Test that input OIDs are defined"""
        assert "input_voltage" in UPS_OIDS
        assert "input_frequency" in UPS_OIDS

    def test_output_oids_defined(self):
        """Test that output OIDs are defined"""
        assert "output_source" in UPS_OIDS
        assert "output_voltage" in UPS_OIDS
        assert "output_load" in UPS_OIDS

    def test_identity_oids_defined(self):
        """Test that identity OIDs are defined"""
        assert "ups_model" in UPS_OIDS
        assert "ups_manufacturer" in UPS_OIDS

    def test_output_source_battery_constant(self):
        """Test OUTPUT_SOURCE_BATTERY constant"""
        assert OUTPUT_SOURCE_BATTERY == 5
