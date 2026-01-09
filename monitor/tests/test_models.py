"""
Tests for data models
"""

import pytest
from datetime import datetime, timezone
from ping_monitor.models import Host, PingResult, MeasurementBatch, UPSStatus, UPSBatch


def test_host_to_dict():
    """Test Host.to_dict() excludes None values"""
    host = Host(name="router", ip="192.168.1.1", description="Main Router")
    data = host.to_dict()

    assert data["name"] == "router"
    assert data["ip"] == "192.168.1.1"
    assert data["description"] == "Main Router"
    assert "type" not in data  # Should be excluded (None)
    assert "tags" not in data  # Should be excluded (None)


def test_host_with_all_fields():
    """Test Host with all fields populated"""
    host = Host(
        name="switch",
        ip="192.168.1.2",
        description="Core Switch",
        type="switch",
        tags=["critical", "network"],
        snmp_enabled=True,
        snmp_community="private",
        snmp_version="2c",
    )
    data = host.to_dict()

    assert len(data) == 8  # All fields populated
    assert data["tags"] == ["critical", "network"]
    assert data["snmp_enabled"] is True
    assert data["snmp_community"] == "private"


def test_ping_result_to_dict():
    """Test PingResult.to_dict() with ISO timestamp"""
    timestamp = datetime(2025, 12, 31, 12, 0, 0, tzinfo=timezone.utc)
    result = PingResult(
        host="router",
        ip="192.168.1.1",
        timestamp=timestamp,
        is_up=True,
        latency_ms=5.2,
        packet_loss=0.0,
        jitter_ms=0.5,
    )
    data = result.to_dict()

    assert data["host"] == "router"
    assert data["timestamp"] == "2025-12-31T12:00:00+00:00"
    assert data["is_up"] is True
    assert data["latency_ms"] == 5.2


def test_ping_result_host_down():
    """Test PingResult for down host (None latency)"""
    timestamp = datetime.now(timezone.utc)
    result = PingResult(
        host="nas",
        ip="192.168.1.10",
        timestamp=timestamp,
        is_up=False,
        latency_ms=None,
        packet_loss=100.0,
        jitter_ms=None,
    )
    data = result.to_dict()

    assert data["is_up"] is False
    assert "latency_ms" not in data  # Excluded (None)
    assert data["packet_loss"] == 100.0
    assert "jitter_ms" not in data  # Excluded (None)


def test_measurement_batch_counts():
    """Test MeasurementBatch host counts"""
    timestamp = datetime.now(timezone.utc)
    results = [
        PingResult("host1", "192.168.1.1", timestamp, True, 5.0, 0.0, 0.5),
        PingResult("host2", "192.168.1.2", timestamp, False, None, 100.0, None),
        PingResult("host3", "192.168.1.3", timestamp, True, 10.0, 0.0, 1.0),
    ]

    batch = MeasurementBatch(site="home", timestamp=timestamp, measurements=results)

    assert batch.count == 3
    assert batch.hosts_up == 2
    assert batch.hosts_down == 1


def test_measurement_batch_to_dict():
    """Test MeasurementBatch.to_dict()"""
    timestamp = datetime(2025, 12, 31, 12, 0, 0, tzinfo=timezone.utc)
    results = [
        PingResult("router", "192.168.1.1", timestamp, True, 5.2, 0.0, 0.5),
    ]

    batch = MeasurementBatch(site="home", timestamp=timestamp, measurements=results)
    data = batch.to_dict()

    assert data["site"] == "home"
    assert data["timestamp"] == "2025-12-31T12:00:00+00:00"
    assert len(data["measurements"]) == 1
    assert data["measurements"][0]["host"] == "router"


def test_host_with_snmp_fields():
    """Test Host with SNMP fields populated"""
    host = Host(
        name="ups",
        ip="192.168.1.50",
        description="Main UPS",
        type="ups",
        snmp_enabled=True,
        snmp_community="private",
        snmp_version="2c",
    )
    data = host.to_dict()

    assert data["name"] == "ups"
    assert data["snmp_enabled"] is True
    assert data["snmp_community"] == "private"
    assert data["snmp_version"] == "2c"


def test_host_snmp_defaults():
    """Test Host SNMP default values"""
    host = Host(name="router", ip="192.168.1.1")

    assert host.snmp_enabled is False
    assert host.snmp_community is None
    assert host.snmp_version == "2c"


def test_ups_status_to_dict():
    """Test UPSStatus.to_dict() with ISO timestamp"""
    timestamp = datetime(2025, 12, 31, 12, 0, 0, tzinfo=timezone.utc)
    status = UPSStatus(
        host="ups1",
        ip="192.168.1.50",
        timestamp=timestamp,
        is_reachable=True,
        on_battery=False,
        battery_runtime_minutes=120.0,
        battery_charge_percent=100.0,
        output_load_percent=25.0,
        input_voltage=120.0,
        output_voltage=120.0,
        ups_model="SmartUPS 1500",
    )
    data = status.to_dict()

    assert data["host"] == "ups1"
    assert data["timestamp"] == "2025-12-31T12:00:00+00:00"
    assert data["is_reachable"] is True
    assert data["on_battery"] is False
    assert data["battery_runtime_minutes"] == 120.0
    assert data["battery_charge_percent"] == 100.0
    assert data["output_load_percent"] == 25.0


def test_ups_status_unreachable():
    """Test UPSStatus for unreachable UPS (None values excluded)"""
    timestamp = datetime.now(timezone.utc)
    status = UPSStatus(
        host="ups1",
        ip="192.168.1.50",
        timestamp=timestamp,
        is_reachable=False,
        error_message="SNMP timeout",
    )
    data = status.to_dict()

    assert data["is_reachable"] is False
    assert data["error_message"] == "SNMP timeout"
    assert "on_battery" not in data  # Excluded (None)
    assert "battery_runtime_minutes" not in data  # Excluded (None)


def test_ups_status_on_battery():
    """Test UPSStatus when UPS is on battery"""
    timestamp = datetime.now(timezone.utc)
    status = UPSStatus(
        host="ups1",
        ip="192.168.1.50",
        timestamp=timestamp,
        is_reachable=True,
        on_battery=True,
        battery_runtime_minutes=30.0,
        battery_charge_percent=75.0,
        input_voltage=0.0,  # No input power
    )
    data = status.to_dict()

    assert data["on_battery"] is True
    assert data["battery_runtime_minutes"] == 30.0
    assert data["battery_charge_percent"] == 75.0
    assert data["input_voltage"] == 0.0


def test_ups_batch_counts():
    """Test UPSBatch counts"""
    timestamp = datetime.now(timezone.utc)
    statuses = [
        UPSStatus("ups1", "192.168.1.50", timestamp, True, on_battery=False),
        UPSStatus("ups2", "192.168.1.51", timestamp, True, on_battery=True),
        UPSStatus("ups3", "192.168.1.52", timestamp, False),  # Unreachable
    ]

    batch = UPSBatch(site="home", timestamp=timestamp, ups_statuses=statuses)

    assert batch.count == 3
    assert batch.ups_reachable == 2
    assert batch.ups_on_battery == 1


def test_ups_batch_to_dict():
    """Test UPSBatch.to_dict()"""
    timestamp = datetime(2025, 12, 31, 12, 0, 0, tzinfo=timezone.utc)
    statuses = [
        UPSStatus("ups1", "192.168.1.50", timestamp, True, on_battery=False),
    ]

    batch = UPSBatch(site="home", timestamp=timestamp, ups_statuses=statuses)
    data = batch.to_dict()

    assert data["site"] == "home"
    assert data["timestamp"] == "2025-12-31T12:00:00+00:00"
    assert len(data["ups_statuses"]) == 1
    assert data["ups_statuses"][0]["host"] == "ups1"


def test_ups_batch_all_on_facility():
    """Test UPSBatch when all UPS devices are on facility power"""
    timestamp = datetime.now(timezone.utc)
    statuses = [
        UPSStatus("ups1", "192.168.1.50", timestamp, True, on_battery=False),
        UPSStatus("ups2", "192.168.1.51", timestamp, True, on_battery=False),
    ]

    batch = UPSBatch(site="home", timestamp=timestamp, ups_statuses=statuses)

    assert batch.ups_on_battery == 0
    assert batch.ups_reachable == 2
