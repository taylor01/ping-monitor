"""
Tests for JSON:API formatter
"""

import pytest
from datetime import datetime, timezone
from ping_monitor.models import PingResult, MeasurementBatch, UPSStatus, UPSBatch
from ping_monitor.jsonapi import (
    format_measurement_batch,
    format_ups_batch,
    parse_jsonapi_response,
    format_error_response,
)


def test_format_measurement_batch():
    """Test JSON:API formatting of measurement batch"""
    timestamp = datetime(2025, 12, 31, 12, 0, 0, tzinfo=timezone.utc)
    results = [
        PingResult("router", "192.168.1.1", timestamp, True, 5.2, 0.0, 0.5),
        PingResult("nas", "192.168.1.10", timestamp, False, None, 100.0, None),
    ]

    batch = MeasurementBatch(site="home", timestamp=timestamp, measurements=results)
    payload = format_measurement_batch(batch)

    # Check JSON:API structure
    assert "data" in payload
    assert payload["data"]["type"] == "measurement-batches"
    assert "attributes" in payload["data"]

    # Check attributes
    attrs = payload["data"]["attributes"]
    assert attrs["site"] == "home"
    assert attrs["timestamp"] == "2025-12-31T12:00:00+00:00"
    assert len(attrs["measurements"]) == 2

    # Check first measurement
    m1 = attrs["measurements"][0]
    assert m1["host"] == "router"
    assert m1["is_up"] is True
    assert m1["latency_ms"] == 5.2

    # Check second measurement (down)
    m2 = attrs["measurements"][1]
    assert m2["host"] == "nas"
    assert m2["is_up"] is False
    assert m2["latency_ms"] is None


def test_parse_jsonapi_success_response():
    """Test parsing successful JSON:API response"""
    response_data = {
        "data": {
            "type": "measurement-batches",
            "id": "123",
            "attributes": {"status": "accepted"},
        },
        "meta": {"processed_count": 2},
    }

    parsed = parse_jsonapi_response(response_data)

    assert parsed["success"] is True
    assert parsed["data"]["id"] == "123"
    assert parsed["meta"]["processed_count"] == 2


def test_parse_jsonapi_error_response():
    """Test parsing error JSON:API response"""
    response_data = {
        "errors": [
            {
                "status": "400",
                "title": "Validation Error",
                "detail": "Site is required",
            }
        ]
    }

    parsed = parse_jsonapi_response(response_data)

    assert parsed["success"] is False
    assert len(parsed["errors"]) == 1
    assert parsed["errors"][0]["title"] == "Validation Error"


def test_format_error_response():
    """Test formatting error as JSON:API"""
    error = format_error_response("Connection timeout", 503)

    assert "errors" in error
    assert len(error["errors"]) == 1
    assert error["errors"][0]["status"] == "503"
    assert error["errors"][0]["detail"] == "Connection timeout"


def test_format_ups_batch():
    """Test JSON:API formatting of UPS batch"""
    timestamp = datetime(2025, 12, 31, 12, 0, 0, tzinfo=timezone.utc)
    statuses = [
        UPSStatus(
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
            battery_voltage=54.0,
            ups_model="SmartUPS 1500",
        ),
        UPSStatus(
            host="ups2",
            ip="192.168.1.51",
            timestamp=timestamp,
            is_reachable=False,
            error_message="SNMP timeout",
        ),
    ]

    batch = UPSBatch(site="home", timestamp=timestamp, ups_statuses=statuses)
    payload = format_ups_batch(batch)

    # Check JSON:API structure
    assert "data" in payload
    assert payload["data"]["type"] == "ups-batches"
    assert "attributes" in payload["data"]

    # Check attributes
    attrs = payload["data"]["attributes"]
    assert attrs["site"] == "home"
    assert attrs["timestamp"] == "2025-12-31T12:00:00+00:00"
    assert len(attrs["ups_statuses"]) == 2

    # Check first UPS status (reachable, on facility power)
    s1 = attrs["ups_statuses"][0]
    assert s1["host"] == "ups1"
    assert s1["is_reachable"] is True
    assert s1["on_battery"] is False
    assert s1["battery_runtime_minutes"] == 120.0
    assert s1["battery_charge_percent"] == 100.0
    assert s1["output_load_percent"] == 25.0
    assert s1["input_voltage"] == 120.0
    assert s1["ups_model"] == "SmartUPS 1500"

    # Check second UPS status (unreachable)
    s2 = attrs["ups_statuses"][1]
    assert s2["host"] == "ups2"
    assert s2["is_reachable"] is False
    assert s2["error_message"] == "SNMP timeout"


def test_format_ups_batch_on_battery():
    """Test JSON:API formatting when UPS is on battery"""
    timestamp = datetime(2025, 12, 31, 12, 0, 0, tzinfo=timezone.utc)
    statuses = [
        UPSStatus(
            host="ups1",
            ip="192.168.1.50",
            timestamp=timestamp,
            is_reachable=True,
            on_battery=True,
            battery_runtime_minutes=30.0,
            battery_charge_percent=75.0,
            input_voltage=0.0,
            output_voltage=120.0,
        ),
    ]

    batch = UPSBatch(site="home", timestamp=timestamp, ups_statuses=statuses)
    payload = format_ups_batch(batch)

    attrs = payload["data"]["attributes"]
    s1 = attrs["ups_statuses"][0]
    assert s1["on_battery"] is True
    assert s1["battery_runtime_minutes"] == 30.0
    assert s1["battery_charge_percent"] == 75.0
    assert s1["input_voltage"] == 0.0
