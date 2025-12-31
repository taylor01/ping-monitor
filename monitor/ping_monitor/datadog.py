"""
Datadog metrics integration
"""

import requests
import logging
import time
from typing import List
from concurrent.futures import ThreadPoolExecutor
from .models import Host, PingResult

logger = logging.getLogger(__name__)


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
            logger.error(f"Failed to send Datadog metrics for {host.name}: {e}")
