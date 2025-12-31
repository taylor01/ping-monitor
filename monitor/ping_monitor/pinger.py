"""
ICMP ping functionality using icmplib
"""

import logging
from typing import List
from datetime import datetime, timezone
from icmplib import multiping
from .models import Host, PingResult

logger = logging.getLogger(__name__)


class Pinger:
    """
    Handles concurrent ICMP pinging of multiple hosts
    """

    def __init__(self, count: int = 3, timeout: int = 2):
        """
        Initialize pinger

        Args:
            count: Number of ICMP packets to send per host
            timeout: Timeout in seconds for each packet
        """
        self.count = count
        self.timeout = timeout

    async def ping_hosts(self, hosts: List[Host]) -> List[PingResult]:
        """
        Ping multiple hosts concurrently

        Args:
            hosts: List of Host objects to ping

        Returns:
            List of PingResult objects
        """
        if not hosts:
            return []

        timestamp = datetime.now(timezone.utc)

        # Extract IPs for multiping
        ips = [h.ip for h in hosts]

        logger.debug(f"Pinging {len(hosts)} hosts...")

        try:
            # Concurrent ping using icmplib
            # Note: multiping is synchronous but internally concurrent
            results = multiping(
                ips, count=self.count, timeout=self.timeout, privileged=True
            )

            # Map results back to hosts
            ip_to_result = {r.address: r for r in results}

            # Create PingResult objects
            ping_results = []
            for host in hosts:
                raw_result = ip_to_result.get(host.ip)

                if raw_result:
                    ping_result = PingResult(
                        host=host.name,
                        ip=host.ip,
                        timestamp=timestamp,
                        is_up=raw_result.is_alive,
                        latency_ms=(
                            round(raw_result.avg_rtt, 2) if raw_result.is_alive else None
                        ),
                        packet_loss=(
                            round(raw_result.packet_loss * 100, 2)
                            if raw_result.packet_loss is not None
                            else None
                        ),
                        jitter_ms=(
                            round(raw_result.jitter, 2)
                            if raw_result.is_alive and raw_result.jitter is not None
                            else None
                        ),
                    )

                    # Log result
                    status = "UP" if ping_result.is_up else "DOWN"
                    latency = (
                        f"{ping_result.latency_ms:.1f}ms"
                        if ping_result.latency_ms
                        else "N/A"
                    )
                    loss = (
                        f"{ping_result.packet_loss:.0f}%"
                        if ping_result.packet_loss is not None
                        else "N/A"
                    )

                    logger.info(
                        f"{host.name:20} ({host.ip:15}) - {status:4} | "
                        f"Latency: {latency:8} | Loss: {loss}"
                    )

                    ping_results.append(ping_result)
                else:
                    # No result for this host (shouldn't happen)
                    logger.warning(f"No ping result for {host.name} ({host.ip})")

            logger.info(f"Completed pinging {len(ping_results)} hosts")
            return ping_results

        except Exception as e:
            logger.error(f"Error during ping operation: {e}")
            return []
