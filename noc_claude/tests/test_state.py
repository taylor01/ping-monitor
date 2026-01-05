"""Tests for state management and alert reconciliation."""

import pytest
import tempfile
import os
from datetime import datetime, timezone

from nc.state import StateManager, Alert


@pytest.fixture
def state_manager():
    """Create a StateManager with a temporary database."""
    fd, db_path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    manager = StateManager(db_path)
    yield manager
    # Cleanup
    os.unlink(db_path)


def make_alert(id: str, site: str = "home", device: str = "router",
               alert_type: str = "down", resolved: bool = False) -> Alert:
    """Helper to create test alerts."""
    return Alert(
        id=id,
        site=site,
        device=device,
        alert_type=alert_type,
        severity="warning",
        message=f"{device} is {alert_type}",
        started_at=datetime.now(timezone.utc),
        resolved_at=datetime.now(timezone.utc) if resolved else None
    )


class TestAlertIngestion:
    """Test alert ingestion and caching."""

    def test_ingest_new_alert(self, state_manager):
        """New alerts are cached in active_alerts."""
        alerts = [make_alert("1", site="home", device="router")]
        state_manager.ingest_alerts(alerts, reconcile=False)

        active = state_manager.get_active_alerts()
        assert len(active) == 1
        assert active[0].id == "1"
        assert active[0].device == "router"

    def test_ingest_resolved_alert_removes_from_cache(self, state_manager):
        """Resolved alerts are removed from active_alerts."""
        # First ingest an active alert
        alerts = [make_alert("1")]
        state_manager.ingest_alerts(alerts, reconcile=False)
        assert len(state_manager.get_active_alerts()) == 1

        # Now ingest same alert as resolved
        alerts = [make_alert("1", resolved=True)]
        state_manager.ingest_alerts(alerts, reconcile=False)
        assert len(state_manager.get_active_alerts()) == 0

    def test_ingest_multiple_alerts(self, state_manager):
        """Multiple alerts from different sites are cached."""
        alerts = [
            make_alert("1", site="home", device="router"),
            make_alert("2", site="home", device="switch"),
            make_alert("3", site="cabin", device="ap"),
        ]
        state_manager.ingest_alerts(alerts, reconcile=False)

        active = state_manager.get_active_alerts()
        assert len(active) == 3

        home_alerts = state_manager.get_active_alerts(site="home")
        assert len(home_alerts) == 2

        cabin_alerts = state_manager.get_active_alerts(site="cabin")
        assert len(cabin_alerts) == 1


class TestAlertReconciliation:
    """Test reconciliation of local state with API state."""

    def test_reconcile_removes_stale_alerts(self, state_manager):
        """Alerts not in API response are removed when reconcile=True."""
        # Ingest 3 alerts
        initial_alerts = [
            make_alert("1", device="router"),
            make_alert("2", device="switch"),
            make_alert("3", device="ap"),
        ]
        state_manager.ingest_alerts(initial_alerts, reconcile=False)
        assert len(state_manager.get_active_alerts()) == 3

        # API now only returns 1 active alert (2 and 3 resolved externally)
        current_alerts = [make_alert("1", device="router")]
        state_manager.ingest_alerts(current_alerts, reconcile=True)

        # Only alert 1 should remain
        active = state_manager.get_active_alerts()
        assert len(active) == 1
        assert active[0].id == "1"

    def test_reconcile_removes_all_alerts_when_empty(self, state_manager):
        """All alerts removed when API returns empty list."""
        # Ingest some alerts
        alerts = [make_alert("1"), make_alert("2")]
        state_manager.ingest_alerts(alerts, reconcile=False)
        assert len(state_manager.get_active_alerts()) == 2

        # API returns empty list - all resolved
        state_manager.ingest_alerts([], reconcile=True)
        assert len(state_manager.get_active_alerts()) == 0

    def test_reconcile_false_preserves_stale_alerts(self, state_manager):
        """Stale alerts preserved when reconcile=False."""
        # Ingest 2 alerts
        alerts = [make_alert("1"), make_alert("2")]
        state_manager.ingest_alerts(alerts, reconcile=False)

        # Ingest only 1 alert without reconciliation
        alerts = [make_alert("1")]
        state_manager.ingest_alerts(alerts, reconcile=False)

        # Both alerts should still exist
        assert len(state_manager.get_active_alerts()) == 2

    def test_reconcile_adds_new_and_removes_stale(self, state_manager):
        """Reconciliation handles add and remove simultaneously."""
        # Start with alerts 1 and 2
        alerts = [make_alert("1"), make_alert("2")]
        state_manager.ingest_alerts(alerts, reconcile=False)

        # API now has alerts 2 and 3 (1 resolved, 3 new)
        alerts = [make_alert("2"), make_alert("3")]
        state_manager.ingest_alerts(alerts, reconcile=True)

        active = state_manager.get_active_alerts()
        assert len(active) == 2
        ids = {a.id for a in active}
        assert ids == {"2", "3"}


class TestSiteStateReconciliation:
    """Test site concern level reconciliation."""

    def test_site_moves_to_watching_on_alert(self, state_manager):
        """Site concern level changes to WATCHING when alert ingested."""
        alerts = [make_alert("1", site="home")]
        state_manager.ingest_alerts(alerts, reconcile=False)

        statuses = state_manager.get_all_site_statuses()
        assert statuses.get("home") == "WATCHING"

    def test_reconcile_resets_sites_with_no_alerts(self, state_manager):
        """Sites with no active alerts are reset to NORMAL."""
        # Create alert and escalate site
        alerts = [make_alert("1", site="home")]
        state_manager.ingest_alerts(alerts, reconcile=False)
        state_manager.set_concern_level("home", "ESCALATED")

        # Verify escalated
        assert state_manager.get_all_site_statuses()["home"] == "ESCALATED"

        # All alerts resolved
        state_manager.ingest_alerts([], reconcile=True)
        state_manager.reconcile_site_states()

        # Site should be NORMAL now
        statuses = state_manager.get_all_site_statuses()
        assert statuses.get("home") == "NORMAL"

    def test_reconcile_preserves_sites_with_alerts(self, state_manager):
        """Sites with active alerts keep their concern level."""
        # Create alerts for two sites
        alerts = [
            make_alert("1", site="home"),
            make_alert("2", site="cabin"),
        ]
        state_manager.ingest_alerts(alerts, reconcile=False)
        state_manager.set_concern_level("home", "INVESTIGATING")
        state_manager.set_concern_level("cabin", "ESCALATED")

        # Remove cabin alert but keep home alert
        alerts = [make_alert("1", site="home")]
        state_manager.ingest_alerts(alerts, reconcile=True)
        state_manager.reconcile_site_states()

        statuses = state_manager.get_all_site_statuses()
        # Home still has alerts - keep level
        assert statuses["home"] == "INVESTIGATING"
        # Cabin has no alerts - reset to NORMAL
        assert statuses["cabin"] == "NORMAL"

    def test_reconcile_resets_watching_since(self, state_manager):
        """watching_since is cleared when site returns to NORMAL."""
        # Create alert
        alerts = [make_alert("1", site="home")]
        state_manager.ingest_alerts(alerts, reconcile=False)

        # Verify watching_since is set
        context = state_manager.get_site_context("home")
        assert context.watching_since is not None

        # Remove all alerts and reconcile
        state_manager.ingest_alerts([], reconcile=True)
        state_manager.reconcile_site_states()

        # watching_since should be None
        context = state_manager.get_site_context("home")
        assert context.watching_since is None


class TestClearAlert:
    """Test individual alert clearing."""

    def test_clear_alert_removes_single(self, state_manager):
        """clear_alert removes just the specified alert."""
        alerts = [make_alert("1"), make_alert("2")]
        state_manager.ingest_alerts(alerts, reconcile=False)

        state_manager.clear_alert("1")

        active = state_manager.get_active_alerts()
        assert len(active) == 1
        assert active[0].id == "2"
