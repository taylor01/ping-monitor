"""
Datadog metrics and logs integration
"""

import requests
import time
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor
from .models import Host, PingResult
from .logging_config import get_logger, get_correlation_id

logger = get_logger(__name__)


class DatadogClient:
    """
    Synchronous Datadog API client for sending ping metrics
    """

    def __init__(
        self,
        api_key: str,
        site: str = "datadoghq.com",
        site_name: str = "default",
        max_workers: int = 20,
    ):
        """
        Initialize Datadog client

        Args:
            api_key: Datadog API key
            site: Datadog site (datadoghq.com or datadoghq.eu)
            site_name: Site name tag
            max_workers: Max concurrent metric submissions
        """
        self.api_key = api_key
        self.site = site
        self.site_name = site_name
        self.max_workers = max_workers
        self.api_url = f"https://api.{site}/api/v1/series"

    def send_measurements(
        self, hosts: List[Host], results: List[PingResult]
    ) -> None:
        """
        Send ping results to Datadog as metrics

        Args:
            hosts: List of Host objects
            results: List of PingResult objects
        """
        # Map results by host name for lookup
        result_map = {r.host: r for r in results}

        # Send metrics concurrently
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            for host in hosts:
                result = result_map.get(host.name)
                if result:
                    executor.submit(self._send_host_metrics, host, result)

        logger.info(
            f"Submitted {len(results)} measurements to Datadog (site: {self.site_name})"
        )

    def _send_host_metrics(self, host: Host, result: PingResult) -> None:
        """
        Send metrics for a single host

        Args:
            host: Host object
            result: PingResult for the host
        """
        timestamp = int(result.timestamp.timestamp())

        # Build tags
        tags = [
            f"ip:{host.ip}",
            f"site:{self.site_name}",
            f"device_type:{host.type or 'unknown'}",
        ]

        # Add description tag
        if host.description:
            desc = host.description.replace(" ", "_").replace(":", "-")
            tags.append(f"description:{desc}")

        # Add custom tags
        if host.tags:
            tags.extend(host.tags)

        # Build metrics series
        series = [
            {
                "metric": "custom.ping.reachable",
                "type": "gauge",
                "points": [[timestamp, 1 if result.is_up else 0]],
                "host": host.name,
                "tags": tags,
            },
            {
                "metric": "custom.ping.latency_ms",
                "type": "gauge",
                "points": [[timestamp, result.latency_ms or 0]],
                "host": host.name,
                "tags": tags,
            },
            {
                "metric": "custom.ping.packet_loss",
                "type": "gauge",
                "points": [[timestamp, result.packet_loss or 0]],
                "host": host.name,
                "tags": tags,
            },
            {
                "metric": "custom.ping.jitter_ms",
                "type": "gauge",
                "points": [[timestamp, result.jitter_ms or 0]],
                "host": host.name,
                "tags": tags,
            },
        ]

        try:
            response = requests.post(
                self.api_url,
                headers={
                    "DD-API-KEY": self.api_key,
                    "Content-Type": "application/json",
                },
                json={"series": series},
                timeout=10,
            )

            if not response.ok:
                logger.error(
                    f"Datadog API error for {host.name}: "
                    f"{response.status_code} - {response.text}"
                )
        except Exception as e:
            logger.error("datadog_metric_error", host=host.name, error=str(e))


class DatadogLogsClient:
    """
    Datadog Logs API client for sending structured logs (US only)
    """

    def __init__(
        self,
        api_key: str,
        site_name: str = "default",
        service: str = "ping-monitor",
    ):
        """
        Initialize Datadog Logs client

        Args:
            api_key: Datadog API key
            site_name: Site name tag
            service: Service name for logs
        """
        self.api_key = api_key
        self.site_name = site_name
        self.service = service
        self.logs_url = "https://http-intake.logs.datadoghq.com/api/v2/logs"

    def send_log(
        self,
        message: str,
        status: str = "info",
        attributes: Optional[Dict[str, Any]] = None,
        tags: Optional[List[str]] = None,
    ) -> bool:
        """
        Send a structured log to Datadog

        Args:
            message: Log message
            status: Log status (info, warning, error)
            attributes: Additional structured attributes
            tags: List of tags

        Returns:
            True if successful, False otherwise
        """
        # Get correlation ID from context
        correlation_id = get_correlation_id()

        # Build log payload
        log_entry = {
            "message": message,
            "ddsource": "ping-monitor",
            "ddtags": f"env:production,site:{self.site_name},service:{self.service}",
            "service": self.service,
            "status": status,
            "timestamp": int(datetime.now(timezone.utc).timestamp() * 1000),
        }

        # Add correlation ID
        if correlation_id:
            log_entry["correlation_id"] = correlation_id

        # Add custom attributes
        if attributes:
            log_entry.update(attributes)

        # Add custom tags
        if tags:
            existing_tags = log_entry["ddtags"]
            log_entry["ddtags"] = f"{existing_tags},{','.join(tags)}"

        try:
            response = requests.post(
                self.logs_url,
                headers={
                    "DD-API-KEY": self.api_key,
                    "Content-Type": "application/json",
                },
                json=[log_entry],
                timeout=5,
            )

            if not response.ok:
                logger.error(
                    "datadog_logs_error",
                    status_code=response.status_code,
                    response=response.text,
                )
                return False

            return True

        except Exception as e:
            logger.error("datadog_logs_send_failed", error=str(e))
            return False

    def log_state_change(
        self,
        host: str,
        ip: str,
        previous_state: str,
        current_state: str,
        latency_ms: Optional[float] = None,
        packet_loss: Optional[float] = None,
    ) -> None:
        """
        Log a host state change event

        Args:
            host: Host name
            ip: Host IP address
            previous_state: Previous state (up/down)
            current_state: Current state (up/down)
            latency_ms: Current latency if up
            packet_loss: Current packet loss if up
        """
        status = "error" if current_state == "down" else "info"

        message = f"Host state change: {host} ({ip}) {previous_state} → {current_state}"

        attributes = {
            "host_name": host,
            "host_ip": ip,
            "previous_state": previous_state,
            "current_state": current_state,
            "event_type": "state_change",
        }

        if latency_ms is not None:
            attributes["latency_ms"] = latency_ms
        if packet_loss is not None:
            attributes["packet_loss_pct"] = packet_loss

        tags = [f"host:{host}", f"ip:{ip}", f"transition:{previous_state}_to_{current_state}"]

        self.send_log(message, status, attributes, tags)

    def log_ping_cycle(
        self,
        total_hosts: int,
        hosts_up: int,
        hosts_down: int,
        avg_latency_ms: float,
        duration_seconds: float,
    ) -> None:
        """
        Log a ping cycle summary

        Args:
            total_hosts: Total number of hosts pinged
            hosts_up: Number of hosts up
            hosts_down: Number of hosts down
            avg_latency_ms: Average latency for hosts that are up
            duration_seconds: Time taken for ping cycle
        """
        message = f"Ping cycle: {hosts_up}/{total_hosts} hosts up, avg latency {avg_latency_ms:.1f}ms"

        attributes = {
            "event_type": "ping_cycle",
            "total_hosts": total_hosts,
            "hosts_up": hosts_up,
            "hosts_down": hosts_down,
            "avg_latency_ms": round(avg_latency_ms, 2),
            "duration_seconds": round(duration_seconds, 2),
        }

        status = "warning" if hosts_down > 0 else "info"

        self.send_log(message, status, attributes)

    def log_monitor_event(
        self,
        event_type: str,
        message: str,
        status: str = "info",
        attributes: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Log a monitor lifecycle event (startup, shutdown, error, config_change)

        Args:
            event_type: Type of event
            message: Event message
            status: Log status
            attributes: Additional attributes
        """
        attrs = {"event_type": event_type}
        if attributes:
            attrs.update(attributes)

        tags = [f"event:{event_type}"]

        self.send_log(message, status, attrs, tags)
