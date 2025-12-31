"""
Tests for data models
"""

import pytest
from datetime import datetime, timezone
from ping_monitor.models import Host, PingResult, MeasurementBatch


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
    )
    data = host.to_dict()

    assert len(data) == 5
    assert data["tags"] == ["critical", "network"]


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
