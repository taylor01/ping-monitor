"""
Main orchestration for ping monitor with buffering and async API posting
"""

import asyncio
import json
import logging
import signal
import sys
from pathlib import Path
from datetime import datetime, timezone
from typing import List, Optional

from .config import Config
from .models import Host, MeasurementBatch
from .pinger import Pinger
from .buffer import MeasurementBuffer
from .api_client import RailsAPIClient
from .datadog import DatadogClient

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s - %(name)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S UTC",
)
logger = logging.getLogger(__name__)


class PingMonitor:
    """
    Main ping monitor orchestrator with Rails API integration and local buffering
    """

    def __init__(self, config: Config):
        """
        Initialize monitor

        Args:
            config: Configuration object
        """
        self.config = config
        self.running = False
        self.shutdown_event = asyncio.Event()

        # Initialize components
        self.pinger = Pinger(
            count=config.ping_count, timeout=config.ping_timeout
        )
        self.buffer = MeasurementBuffer(config.buffer_db_path)

        # Optional components based on config
        self.api_client: Optional[RailsAPIClient] = None
        if config.has_rails_api:
            self.api_client = RailsAPIClient(
                base_url=config.rails_api_url, api_key=config.api_key
            )

        self.datadog_client: Optional[DatadogClient] = None
        if config.has_datadog:
            self.datadog_client = DatadogClient(
                api_key=config.dd_api_key,
                site=config.dd_site,
                site_name=config.site_name,
                max_workers=config.max_workers,
            )

    async def initialize(self) -> None:
        """Initialize monitor (database, etc.)"""
        logger.info("Initializing ping monitor...")
        await self.buffer.initialize()
        logger.info(f"Buffer initialized at {self.config.buffer_db_path}")

    async def load_hosts(self) -> List[Host]:
        """
        Load hosts from configuration file

        Returns:
            List of Host objects
        """
        # Try local config first
        hosts_path = self.config.hosts_config_path

        if not hosts_path.exists():
            logger.error(f"Hosts configuration not found: {hosts_path}")
            return []

        try:
            with open(hosts_path) as f:
                hosts_data = json.load(f)

            hosts = [
                Host(
                    name=h["name"],
                    ip=h["ip"],
                    description=h.get("description"),
                    type=h.get("type"),
                    tags=h.get("tags"),
                )
                for h in hosts_data
            ]

            logger.info(f"Loaded {len(hosts)} hosts from {hosts_path}")
            return hosts

        except Exception as e:
            logger.error(f"Failed to load hosts: {e}")
            return []

    async def ping_cycle(self) -> None:
        """Execute one ping cycle"""
        # Load hosts
        hosts = await self.load_hosts()
        if not hosts:
            logger.warning("No hosts to ping")
            return

        # Ping all hosts
        results = await asyncio.to_thread(self.pinger.ping_hosts, hosts)
        if not results:
            logger.warning("No ping results")
            return

        # Create measurement batch
        batch = MeasurementBatch(
            site=self.config.site_name,
            timestamp=datetime.now(timezone.utc),
            measurements=results,
        )

        logger.info(
            f"Ping cycle complete: {batch.hosts_up}/{batch.count} hosts up"
        )

        # Post to Rails API (with buffering on failure)
        if self.api_client:
            await self._post_to_api(batch)

        # Post to Datadog (fire and forget)
        if self.datadog_client:
            await asyncio.to_thread(
                self.datadog_client.send_measurements, hosts, results
            )

        # Drain buffer if API is available
        if self.api_client:
            await self._drain_buffer()

    async def _post_to_api(self, batch: MeasurementBatch) -> None:
        """
        Post measurements to Rails API with buffering on failure

        Args:
            batch: MeasurementBatch to post
        """
        try:
            response = await self.api_client.post_measurements(batch)

            if response["success"]:
                logger.info(
                    f"Posted {batch.count} measurements to Rails API successfully"
                )
            else:
                # API returned error
                errors = response.get("errors", [])
                error_msg = errors[0].get("detail", "Unknown error") if errors else "Unknown error"
                logger.error(f"Rails API returned error: {error_msg}")
                # Buffer for retry
                await self.buffer.add(batch)
                logger.info(f"Buffered {batch.count} measurements for retry")

        except Exception as e:
            # Network or unexpected error
            logger.error(f"Failed to post to Rails API: {e}")
            # Buffer for retry
            await self.buffer.add(batch)
            logger.info(f"Buffered {batch.count} measurements for retry")

    async def _drain_buffer(self) -> None:
        """Drain buffered measurements to Rails API"""
        pending_count = await self.buffer.count_pending()
        if pending_count == 0:
            return

        logger.info(f"Draining buffer: {pending_count} pending measurements")

        pending = await self.buffer.get_pending(limit=10)

        for record in pending:
            try:
                response = await self.api_client.post_buffered_measurement(
                    record["payload"]
                )

                if response["success"]:
                    await self.buffer.mark_posted(record["id"])
                    logger.info(f"Drained buffered measurement {record['id']}")
                else:
                    errors = response.get("errors", [])
                    error_msg = errors[0].get("detail", "Unknown") if errors else "Unknown"
                    await self.buffer.mark_failed(record["id"], error_msg)
                    logger.warning(
                        f"Failed to drain buffered measurement {record['id']}: {error_msg}"
                    )

            except Exception as e:
                await self.buffer.mark_failed(record["id"], str(e))
                logger.error(f"Error draining buffered measurement {record['id']}: {e}")

    async def run(self) -> None:
        """Main monitoring loop"""
        self.running = True
        logger.info("=" * 60)
        logger.info("Ping Monitor Starting")
        logger.info(f"Site: {self.config.site_name}")
        logger.info(f"Ping Interval: {self.config.ping_interval}s")
        logger.info(f"Rails API: {'Enabled' if self.api_client else 'Disabled'}")
        logger.info(f"Datadog: {'Enabled' if self.datadog_client else 'Disabled'}")
        logger.info("=" * 60)

        try:
            while self.running and not self.shutdown_event.is_set():
                await self.ping_cycle()

                # Wait for next cycle or shutdown
                try:
                    await asyncio.wait_for(
                        self.shutdown_event.wait(),
                        timeout=self.config.ping_interval,
                    )
                except asyncio.TimeoutError:
                    # Timeout is expected, continue to next cycle
                    pass

        except Exception as e:
            logger.error(f"Error in main loop: {e}", exc_info=True)
        finally:
            await self.shutdown()

    async def shutdown(self) -> None:
        """Graceful shutdown"""
        if not self.running:
            return

        logger.info("Shutting down...")
        self.running = False

        # Show buffer stats
        stats = await self.buffer.get_stats()
        logger.info(f"Buffer stats: {stats}")

        # Close API client
        if self.api_client:
            await self.api_client.close()

        logger.info("Shutdown complete")

    def handle_signal(self, sig) -> None:
        """Handle shutdown signals"""
        logger.info(f"Received signal {sig}, initiating shutdown...")
        self.shutdown_event.set()


async def main() -> None:
    """Main entry point"""
    # Load configuration
    try:
        config = Config.from_env()
        config.validate()
    except Exception as e:
        logger.error(f"Configuration error: {e}")
        sys.exit(1)

    # Create monitor
    monitor = PingMonitor(config)

    # Set up signal handlers
    loop = asyncio.get_event_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, lambda: monitor.handle_signal(sig))

    # Initialize and run
    try:
        await monitor.initialize()
        await monitor.run()
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
