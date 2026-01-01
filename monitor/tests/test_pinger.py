"""Tests for pinger module"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timezone

from ping_monitor.pinger import Pinger
from ping_monitor.models import Host, PingResult


class TestPinger:
    """Tests for Pinger class"""

    def test_init_defaults(self):
        """Test default initialization values"""
        pinger = Pinger()
        assert pinger.count == 3
        assert pinger.timeout == 2

    def test_init_custom_values(self):
        """Test custom initialization values"""
        pinger = Pinger(count=5, timeout=3)
        assert pinger.count == 5
        assert pinger.timeout == 3

    def test_ping_hosts_empty_list(self):
        """Test pinging empty host list returns empty results"""
        pinger = Pinger()
        results = pinger.ping_hosts([])
        assert results == []

    @patch("ping_monitor.pinger.multiping")
    def test_ping_hosts_success(self, mock_multiping):
        """Test successful ping of multiple hosts"""
        # Create mock icmplib results
        mock_result1 = MagicMock()
        mock_result1.address = "192.168.1.1"
        mock_result1.is_alive = True
        mock_result1.avg_rtt = 5.234
        mock_result1.packet_loss = 0.0
        mock_result1.jitter = 1.23

        mock_result2 = MagicMock()
        mock_result2.address = "192.168.1.2"
        mock_result2.is_alive = True
        mock_result2.avg_rtt = 10.567
        mock_result2.packet_loss = 0.0
        mock_result2.jitter = 2.34

        mock_multiping.return_value = [mock_result1, mock_result2]

        hosts = [
            Host(ip="192.168.1.1", name="router"),
            Host(ip="192.168.1.2", name="switch"),
        ]

        pinger = Pinger(count=3, timeout=2)
        results = pinger.ping_hosts(hosts)

        assert len(results) == 2
        assert results[0].host == "router"
        assert results[0].ip == "192.168.1.1"
        assert results[0].is_up is True
        assert results[0].latency_ms == 5.23
        assert results[0].packet_loss == 0.0
        assert results[0].jitter_ms == 1.23

        mock_multiping.assert_called_once_with(
            ["192.168.1.1", "192.168.1.2"], count=3, timeout=2, privileged=True
        )

    @patch("ping_monitor.pinger.multiping")
    def test_ping_hosts_host_down(self, mock_multiping):
        """Test pinging a host that is down"""
        mock_result = MagicMock()
        mock_result.address = "192.168.1.1"
        mock_result.is_alive = False
        mock_result.avg_rtt = 0
        mock_result.packet_loss = 1.0
        mock_result.jitter = None

        mock_multiping.return_value = [mock_result]

        hosts = [Host(ip="192.168.1.1", name="offline-host")]
        pinger = Pinger()
        results = pinger.ping_hosts(hosts)

        assert len(results) == 1
        assert results[0].is_up is False
        assert results[0].latency_ms is None
        assert results[0].packet_loss == 100.0
        assert results[0].jitter_ms is None

    @patch("ping_monitor.pinger.multiping")
    def test_ping_hosts_partial_packet_loss(self, mock_multiping):
        """Test host with partial packet loss"""
        mock_result = MagicMock()
        mock_result.address = "192.168.1.1"
        mock_result.is_alive = True
        mock_result.avg_rtt = 15.5
        mock_result.packet_loss = 0.333  # 33.3% loss
        mock_result.jitter = 5.0

        mock_multiping.return_value = [mock_result]

        hosts = [Host(ip="192.168.1.1", name="flaky-host")]
        pinger = Pinger()
        results = pinger.ping_hosts(hosts)

        assert len(results) == 1
        assert results[0].is_up is True
        assert results[0].packet_loss == 33.3

    @patch("ping_monitor.pinger.multiping")
    def test_ping_hosts_exception(self, mock_multiping):
        """Test handling of exception during ping"""
        mock_multiping.side_effect = Exception("Network error")

        hosts = [Host(ip="192.168.1.1", name="host")]
        pinger = Pinger()
        results = pinger.ping_hosts(hosts)

        assert results == []

    @patch("ping_monitor.pinger.multiping")
    def test_ping_result_has_timestamp(self, mock_multiping):
        """Test that ping results include timestamp"""
        mock_result = MagicMock()
        mock_result.address = "192.168.1.1"
        mock_result.is_alive = True
        mock_result.avg_rtt = 5.0
        mock_result.packet_loss = 0.0
        mock_result.jitter = 1.0

        mock_multiping.return_value = [mock_result]

        hosts = [Host(ip="192.168.1.1", name="host")]
        pinger = Pinger()
        results = pinger.ping_hosts(hosts)

        assert results[0].timestamp is not None
        assert isinstance(results[0].timestamp, datetime)
