"""
ICMP ping functionality using icmplib
"""

from typing import List
from datetime import datetime, timezone
from icmplib import multiping
from .models import Host, PingResult
from .logging_config import get_logger

logger = get_logger(__name__)


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

    def ping_hosts(self, hosts: List[Host]) -> List[PingResult]:
        """
        Ping multiple hosts concurrently (using icmplib's internal concurrency)

        Args:
            hosts: List of Host objects to ping

        Returns:
            List of PingResult objects

        Note:
            This is a synchronous method because icmplib.multiping() is synchronous
            but handles concurrency internally. We wrap this in asyncio.to_thread()
            when calling from async code.
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

                    # Log result with structured logging
                    logger.info(
                        "host_ping_result",
                        host=host.name,
                        ip=host.ip,
                        is_up=ping_result.is_up,
                        latency_ms=ping_result.latency_ms,
                        packet_loss=ping_result.packet_loss,
                        jitter_ms=ping_result.jitter_ms,
                    )

                    ping_results.append(ping_result)
                else:
                    # No result for this host (shouldn't happen)
                    logger.warning("no_ping_result", host=host.name, ip=host.ip)

            logger.info("ping_batch_complete", host_count=len(ping_results))
            return ping_results

        except Exception as e:
            logger.error("ping_operation_error", error=str(e))
            return []
