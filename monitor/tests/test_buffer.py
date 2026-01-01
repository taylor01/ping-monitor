"""Tests for measurement buffer"""
import pytest
import tempfile
from pathlib import Path
from datetime import datetime, timezone

from ping_monitor.buffer import MeasurementBuffer
from ping_monitor.models import Host, PingResult, MeasurementBatch


class TestMeasurementBuffer:
    """Tests for MeasurementBuffer"""

    @pytest.fixture
    def temp_db_path(self):
        """Create a temporary database path"""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir) / "test_buffer.db"

    @pytest.fixture
    def sample_batch(self):
        """Create a sample measurement batch"""
        measurements = [
            PingResult(
                host="router",
                ip="192.168.1.1",
                timestamp=datetime.now(timezone.utc),
                is_up=True,
                latency_ms=5.0,
                packet_loss=0.0,
                jitter_ms=1.0,
            ),
        ]
        return MeasurementBatch(site="test-site", timestamp=datetime.now(timezone.utc), measurements=measurements)

    @pytest.mark.asyncio
    async def test_initialize_creates_table(self, temp_db_path):
        """Test that initialize creates the database table"""
        buffer = MeasurementBuffer(temp_db_path)
        await buffer.initialize()

        assert temp_db_path.exists()

    @pytest.mark.asyncio
    async def test_add_measurement(self, temp_db_path, sample_batch):
        """Test adding a measurement to buffer"""
        buffer = MeasurementBuffer(temp_db_path)
        await buffer.initialize()

        record_id = await buffer.add(sample_batch)

        assert record_id is not None
        assert record_id > 0

    @pytest.mark.asyncio
    async def test_get_pending_empty(self, temp_db_path):
        """Test getting pending measurements from empty buffer"""
        buffer = MeasurementBuffer(temp_db_path)
        await buffer.initialize()

        pending = await buffer.get_pending()

        assert pending == []

    @pytest.mark.asyncio
    async def test_get_pending_with_data(self, temp_db_path, sample_batch):
        """Test getting pending measurements after adding"""
        buffer = MeasurementBuffer(temp_db_path)
        await buffer.initialize()

        await buffer.add(sample_batch)
        pending = await buffer.get_pending()

        assert len(pending) == 1
        assert pending[0]["site"] == "test-site"
        assert "payload" in pending[0]

    @pytest.mark.asyncio
    async def test_get_pending_respects_limit(self, temp_db_path, sample_batch):
        """Test that get_pending respects the limit parameter"""
        buffer = MeasurementBuffer(temp_db_path)
        await buffer.initialize()

        # Add 5 batches
        for _ in range(5):
            await buffer.add(sample_batch)

        pending = await buffer.get_pending(limit=3)

        assert len(pending) == 3

    @pytest.mark.asyncio
    async def test_mark_posted(self, temp_db_path, sample_batch):
        """Test marking a measurement as posted"""
        buffer = MeasurementBuffer(temp_db_path)
        await buffer.initialize()

        record_id = await buffer.add(sample_batch)
        await buffer.mark_posted(record_id)

        pending = await buffer.get_pending()
        assert len(pending) == 0

    @pytest.mark.asyncio
    async def test_mark_failed(self, temp_db_path, sample_batch):
        """Test marking a measurement as failed"""
        buffer = MeasurementBuffer(temp_db_path)
        await buffer.initialize()

        record_id = await buffer.add(sample_batch)
        await buffer.mark_failed(record_id, "Connection refused")

        pending = await buffer.get_pending()
        assert len(pending) == 1
        assert pending[0]["attempts"] == 1

    @pytest.mark.asyncio
    async def test_mark_failed_increments_attempts(self, temp_db_path, sample_batch):
        """Test that mark_failed increments attempt counter"""
        buffer = MeasurementBuffer(temp_db_path)
        await buffer.initialize()

        record_id = await buffer.add(sample_batch)
        await buffer.mark_failed(record_id, "Error 1")
        await buffer.mark_failed(record_id, "Error 2")
        await buffer.mark_failed(record_id, "Error 3")

        pending = await buffer.get_pending()
        assert pending[0]["attempts"] == 3

    @pytest.mark.asyncio
    async def test_count_pending(self, temp_db_path, sample_batch):
        """Test counting pending measurements"""
        buffer = MeasurementBuffer(temp_db_path)
        await buffer.initialize()

        assert await buffer.count_pending() == 0

        await buffer.add(sample_batch)
        await buffer.add(sample_batch)

        assert await buffer.count_pending() == 2

        pending = await buffer.get_pending(limit=1)
        await buffer.mark_posted(pending[0]["id"])

        assert await buffer.count_pending() == 1

    @pytest.mark.asyncio
    async def test_get_stats(self, temp_db_path, sample_batch):
        """Test getting buffer statistics"""
        buffer = MeasurementBuffer(temp_db_path)
        await buffer.initialize()

        # Add some measurements
        id1 = await buffer.add(sample_batch)
        id2 = await buffer.add(sample_batch)
        await buffer.add(sample_batch)

        # Mark one as posted
        await buffer.mark_posted(id1)

        # Mark one as failed twice
        await buffer.mark_failed(id2, "Error")
        await buffer.mark_failed(id2, "Error again")

        stats = await buffer.get_stats()

        assert stats["total"] == 3
        assert stats["posted"] == 1
        assert stats["pending"] == 2
        assert stats["max_attempts"] == 2

    @pytest.mark.asyncio
    async def test_get_stats_empty_buffer(self, temp_db_path):
        """Test getting stats from empty buffer"""
        buffer = MeasurementBuffer(temp_db_path)
        await buffer.initialize()

        stats = await buffer.get_stats()

        assert stats["total"] == 0
        assert stats["pending"] == 0
        assert stats["posted"] == 0
        assert stats["max_attempts"] == 0

    @pytest.mark.asyncio
    async def test_payload_is_valid_json(self, temp_db_path, sample_batch):
        """Test that stored payload is valid JSON:API format"""
        import json

        buffer = MeasurementBuffer(temp_db_path)
        await buffer.initialize()

        await buffer.add(sample_batch)
        pending = await buffer.get_pending()

        payload = json.loads(pending[0]["payload"])
        assert "data" in payload
        assert "attributes" in payload["data"]
        assert payload["data"]["attributes"]["site"] == "test-site"
