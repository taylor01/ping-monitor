"""
Local SQLite buffer for measurements when Rails API is unreachable
"""

import aiosqlite
import json
from pathlib import Path
from typing import List, Optional
from datetime import datetime, timezone
from .models import MeasurementBatch
from .jsonapi import format_measurement_batch


class MeasurementBuffer:
    """
    Async SQLite buffer for storing measurements when API is unavailable
    """

    def __init__(self, db_path: Path):
        """
        Initialize buffer

        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        self._ensure_parent_dir()

    def _ensure_parent_dir(self) -> None:
        """Ensure parent directory exists"""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

    async def initialize(self) -> None:
        """Initialize database schema"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS buffered_measurements (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    created_at TEXT NOT NULL,
                    site TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    posted INTEGER DEFAULT 0,
                    posted_at TEXT,
                    attempts INTEGER DEFAULT 0,
                    last_error TEXT
                )
                """
            )
            await db.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_buffered_posted
                ON buffered_measurements(posted, created_at)
                """
            )
            await db.commit()

    async def add(self, batch: MeasurementBatch) -> int:
        """
        Add a measurement batch to buffer

        Args:
            batch: MeasurementBatch to buffer

        Returns:
            ID of buffered record
        """
        jsonapi_payload = format_measurement_batch(batch)
        payload_json = json.dumps(jsonapi_payload)

        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                """
                INSERT INTO buffered_measurements (created_at, site, payload)
                VALUES (?, ?, ?)
                """,
                (datetime.now(timezone.utc).isoformat(), batch.site, payload_json),
            )
            await db.commit()
            return cursor.lastrowid

    async def get_pending(self, limit: int = 10) -> List[dict]:
        """
        Get pending (unposted) measurements

        Args:
            limit: Maximum number of records to retrieve

        Returns:
            List of buffered measurement dictionaries
        """
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                """
                SELECT id, created_at, site, payload, attempts
                FROM buffered_measurements
                WHERE posted = 0
                ORDER BY created_at ASC
                LIMIT ?
                """,
                (limit,),
            ) as cursor:
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]

    async def mark_posted(self, record_id: int) -> None:
        """
        Mark a buffered measurement as successfully posted

        Args:
            record_id: ID of the buffered record
        """
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
                UPDATE buffered_measurements
                SET posted = 1,
                    posted_at = ?
                WHERE id = ?
                """,
                (datetime.now(timezone.utc).isoformat(), record_id),
            )
            await db.commit()

    async def mark_failed(self, record_id: int, error_message: str) -> None:
        """
        Mark a buffered measurement as failed (increment attempts)

        Args:
            record_id: ID of the buffered record
            error_message: Error message from failed post attempt
        """
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
                UPDATE buffered_measurements
                SET attempts = attempts + 1,
                    last_error = ?
                WHERE id = ?
                """,
                (error_message, record_id),
            )
            await db.commit()

    async def count_pending(self) -> int:
        """
        Count pending (unposted) measurements

        Returns:
            Number of pending measurements
        """
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(
                "SELECT COUNT(*) FROM buffered_measurements WHERE posted = 0"
            ) as cursor:
                row = await cursor.fetchone()
                return row[0] if row else 0

    async def cleanup_old(self, days: int = 7) -> int:
        """
        Delete buffered measurements older than specified days

        Args:
            days: Age threshold in days

        Returns:
            Number of records deleted
        """
        cutoff = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        cutoff = cutoff.replace(day=cutoff.day - days)

        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                """
                DELETE FROM buffered_measurements
                WHERE created_at < ? AND posted = 1
                """,
                (cutoff.isoformat(),),
            )
            await db.commit()
            return cursor.rowcount

    async def get_stats(self) -> dict:
        """
        Get buffer statistics

        Returns:
            Dictionary with buffer stats
        """
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(
                """
                SELECT
                    COUNT(*) as total,
                    SUM(CASE WHEN posted = 0 THEN 1 ELSE 0 END) as pending,
                    SUM(CASE WHEN posted = 1 THEN 1 ELSE 0 END) as posted,
                    MAX(attempts) as max_attempts
                FROM buffered_measurements
                """
            ) as cursor:
                row = await cursor.fetchone()
                if row:
                    return {
                        "total": row[0] or 0,
                        "pending": row[1] or 0,
                        "posted": row[2] or 0,
                        "max_attempts": row[3] or 0,
                    }
                return {"total": 0, "pending": 0, "posted": 0, "max_attempts": 0}
