"""
NC State Management

Handles site contexts, incidents, learned patterns, and persistence to SQLite.
"""

import json
import sqlite3
from datetime import datetime, timedelta, timezone
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from contextlib import contextmanager


@dataclass
class Alert:
    """An alert from the Rails API."""
    id: str
    site: str
    device: str
    alert_type: str  # 'down', 'high_latency', 'packet_loss'
    severity: str
    message: str
    started_at: datetime
    resolved_at: Optional[datetime] = None
    
    @classmethod
    def from_api(cls, data: dict) -> "Alert":
        """Create Alert from API response."""
        return cls(
            id=str(data.get('id')),
            site=data.get('site', ''),
            device=data.get('device', ''),
            alert_type=data.get('alert_type', 'unknown'),
            severity=data.get('severity', 'warning'),
            message=data.get('message', ''),
            started_at=datetime.fromisoformat(data['started_at'].replace('Z', '+00:00')) if data.get('started_at') else datetime.now(timezone.utc),
            resolved_at=datetime.fromisoformat(data['resolved_at'].replace('Z', '+00:00')) if data.get('resolved_at') else None
        )


@dataclass
class LearnedPattern:
    """A pattern NC has learned."""
    id: int
    site: str
    device: Optional[str]
    pattern_type: str  # 'scheduled_downtime', 'cascade_source', 'flaky', 'normal_reboot'
    description: str
    confidence: float
    occurrences: int
    time_pattern: Optional[str]  # e.g., "03:00-03:10" for daily reboot window
    last_seen_at: datetime


@dataclass  
class Incident:
    """An incident being tracked."""
    id: int
    site: str
    started_at: datetime
    resolved_at: Optional[datetime]
    auto_recovered: bool
    nc_summary: Optional[str]
    nc_root_cause_guess: Optional[str]
    devices_affected: List[str]
    human_root_cause: Optional[str]
    human_notes: Optional[str]
    human_reviewed_at: Optional[datetime]
    severity: str
    reported_in_summary: bool


@dataclass
class InferredTopology:
    """Inferred network topology relationship."""
    upstream_device: str
    downstream_devices: List[str]
    confidence: float
    observed_count: int


@dataclass
class SiteContext:
    """Current context for a site - passed to Claude for reasoning."""
    site: str
    concern_level: str  # NORMAL, WATCHING, INVESTIGATING, ESCALATED
    active_alerts: List[Alert]
    watching_since: Optional[datetime]
    
    # Enrichment
    learned_patterns: List[LearnedPattern] = field(default_factory=list)
    inferred_topology: Dict[str, List[str]] = field(default_factory=dict)
    recent_incidents: List[Incident] = field(default_factory=list)
    
    def to_prompt(self) -> str:
        """Format context for Claude prompt."""
        lines = [
            f"Site: {self.site}",
            f"Concern Level: {self.concern_level}",
            f"Active Alerts ({len(self.active_alerts)}):"
        ]
        
        for alert in self.active_alerts:
            lines.append(f"  - {alert.device}: {alert.alert_type} since {alert.started_at.strftime('%H:%M:%S')}")
            
        if self.watching_since:
            elapsed = (datetime.now(timezone.utc) - self.watching_since).total_seconds()
            lines.append(f"Watching since: {self.watching_since.strftime('%H:%M:%S')} ({int(elapsed)}s ago)")
            
        if self.learned_patterns:
            lines.append(f"\nKnown Patterns ({len(self.learned_patterns)}):")
            for pattern in self.learned_patterns:
                lines.append(f"  - {pattern.device or 'site-wide'}: {pattern.description} (confidence: {pattern.confidence:.0%})")
                
        if self.inferred_topology:
            lines.append(f"\nInferred Topology:")
            for upstream, downstream in self.inferred_topology.items():
                lines.append(f"  - {upstream} -> {', '.join(downstream)}")
                
        if self.recent_incidents:
            lines.append(f"\nRecent Incidents ({len(self.recent_incidents)}):")
            for incident in self.recent_incidents[:5]:
                status = "resolved" if incident.resolved_at else "active"
                cause = incident.human_root_cause or incident.nc_root_cause_guess or "unknown"
                lines.append(f"  - {incident.started_at.strftime('%Y-%m-%d %H:%M')}: {cause} ({status})")
                
        return "\n".join(lines)


class StateManager:
    """Manages NC's state with SQLite persistence."""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._init_db()
        
        # In-memory state
        self._site_contexts: Dict[str, SiteContext] = {}
        self._last_poll_time: Optional[datetime] = None
        
    @contextmanager
    def _get_conn(self):
        """Get a database connection."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()
            
    def _init_db(self):
        """Initialize database schema."""
        with self._get_conn() as conn:
            conn.executescript("""
                -- Incidents
                CREATE TABLE IF NOT EXISTS incidents (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    site TEXT NOT NULL,
                    started_at TIMESTAMP NOT NULL,
                    resolved_at TIMESTAMP,
                    auto_recovered BOOLEAN DEFAULT FALSE,
                    nc_summary TEXT,
                    nc_root_cause_guess TEXT,
                    devices_affected TEXT,  -- JSON array
                    human_root_cause TEXT,
                    human_notes TEXT,
                    human_reviewed_at TIMESTAMP,
                    severity TEXT DEFAULT 'normal',
                    reported_in_summary BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                
                -- Learned patterns
                CREATE TABLE IF NOT EXISTS learned_patterns (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    site TEXT NOT NULL,
                    device TEXT,
                    pattern_type TEXT NOT NULL,
                    description TEXT,
                    confidence REAL DEFAULT 0.5,
                    occurrences INTEGER DEFAULT 1,
                    time_pattern TEXT,
                    last_seen_at TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                
                -- Inferred topology
                CREATE TABLE IF NOT EXISTS inferred_topology (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    site TEXT NOT NULL,
                    upstream_device TEXT NOT NULL,
                    downstream_device TEXT NOT NULL,
                    confidence REAL DEFAULT 0.5,
                    observed_count INTEGER DEFAULT 1,
                    last_seen_at TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(site, upstream_device, downstream_device)
                );
                
                -- Investigation steps (audit log)
                CREATE TABLE IF NOT EXISTS investigation_steps (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    incident_id INTEGER REFERENCES incidents(id),
                    site TEXT NOT NULL,
                    step_type TEXT NOT NULL,
                    target TEXT,
                    result TEXT,
                    interpretation TEXT,
                    performed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                
                -- NC metadata
                CREATE TABLE IF NOT EXISTS nc_metadata (
                    key TEXT PRIMARY KEY,
                    value TEXT,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                
                -- Site concern levels
                CREATE TABLE IF NOT EXISTS site_states (
                    site TEXT PRIMARY KEY,
                    concern_level TEXT DEFAULT 'NORMAL',
                    watching_since TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                
                -- Active alerts cache
                CREATE TABLE IF NOT EXISTS active_alerts (
                    id TEXT PRIMARY KEY,
                    site TEXT NOT NULL,
                    device TEXT NOT NULL,
                    alert_type TEXT NOT NULL,
                    severity TEXT,
                    message TEXT,
                    started_at TIMESTAMP NOT NULL,
                    ingested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                
                -- Create indexes
                CREATE INDEX IF NOT EXISTS idx_incidents_site ON incidents(site);
                CREATE INDEX IF NOT EXISTS idx_incidents_started ON incidents(started_at);
                CREATE INDEX IF NOT EXISTS idx_patterns_site ON learned_patterns(site);
                CREATE INDEX IF NOT EXISTS idx_alerts_site ON active_alerts(site);
            """)
            
    # =========================================================================
    # Alert Management
    # =========================================================================
    
    def ingest_alerts(self, alerts: List[Alert], reconcile: bool = True):
        """
        Ingest alerts from the API.

        Args:
            alerts: List of alerts from the API
            reconcile: If True, remove local alerts not in the API's active list.
                      Set to True when fetching the full active alerts list.
        """
        with self._get_conn() as conn:
            # Get current active alert IDs from API response
            api_alert_ids = {alert.id for alert in alerts if not alert.resolved_at}

            # Reconcile: remove local alerts that are no longer active in API
            if reconcile:
                local_alerts = conn.execute("SELECT id FROM active_alerts").fetchall()
                for row in local_alerts:
                    if row['id'] not in api_alert_ids:
                        conn.execute("DELETE FROM active_alerts WHERE id = ?", (row['id'],))

            for alert in alerts:
                if alert.resolved_at:
                    # Alert resolved - remove from active
                    conn.execute("DELETE FROM active_alerts WHERE id = ?", (alert.id,))
                else:
                    # New or ongoing alert
                    conn.execute("""
                        INSERT OR REPLACE INTO active_alerts
                        (id, site, device, alert_type, severity, message, started_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (alert.id, alert.site, alert.device, alert.alert_type,
                          alert.severity, alert.message, alert.started_at.isoformat()))

                    # Ensure site has a state record
                    conn.execute("""
                        INSERT OR IGNORE INTO site_states (site, concern_level)
                        VALUES (?, 'NORMAL')
                    """, (alert.site,))

                    # If site is NORMAL, move to WATCHING
                    conn.execute("""
                        UPDATE site_states
                        SET concern_level = 'WATCHING',
                            watching_since = COALESCE(watching_since, ?),
                            updated_at = CURRENT_TIMESTAMP
                        WHERE site = ? AND concern_level = 'NORMAL'
                    """, (datetime.now(timezone.utc).isoformat(), alert.site))
                    
    def get_active_alerts(self, site: Optional[str] = None) -> List[Alert]:
        """Get active alerts, optionally filtered by site."""
        with self._get_conn() as conn:
            if site:
                rows = conn.execute(
                    "SELECT * FROM active_alerts WHERE site = ? ORDER BY started_at",
                    (site,)
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM active_alerts ORDER BY site, started_at"
                ).fetchall()
                
        return [Alert(
            id=row['id'],
            site=row['site'],
            device=row['device'],
            alert_type=row['alert_type'],
            severity=row['severity'],
            message=row['message'],
            started_at=datetime.fromisoformat(row['started_at'])
        ) for row in rows]
        
    def clear_alert(self, alert_id: str):
        """Remove an alert from active alerts."""
        with self._get_conn() as conn:
            conn.execute("DELETE FROM active_alerts WHERE id = ?", (alert_id,))

    def reconcile_site_states(self):
        """
        Reset concern levels for sites with no active alerts.
        Should be called after ingesting alerts.
        """
        with self._get_conn() as conn:
            # Get sites with elevated concern but no active alerts
            conn.execute("""
                UPDATE site_states
                SET concern_level = 'NORMAL',
                    watching_since = NULL,
                    updated_at = CURRENT_TIMESTAMP
                WHERE concern_level != 'NORMAL'
                  AND site NOT IN (SELECT DISTINCT site FROM active_alerts)
            """)
            
    # =========================================================================
    # Site State Management  
    # =========================================================================
    
    def get_site_context(self, site: str) -> SiteContext:
        """Get full context for a site."""
        with self._get_conn() as conn:
            # Get site state
            state_row = conn.execute(
                "SELECT * FROM site_states WHERE site = ?", (site,)
            ).fetchone()
            
            concern_level = state_row['concern_level'] if state_row else 'NORMAL'
            watching_since = None
            if state_row and state_row['watching_since']:
                watching_since = datetime.fromisoformat(state_row['watching_since'])
                
        active_alerts = self.get_active_alerts(site)
        learned_patterns = self.get_learned_patterns(site)
        inferred_topology = self.get_inferred_topology(site)
        recent_incidents = self.get_recent_incidents(site, days=30)
        
        return SiteContext(
            site=site,
            concern_level=concern_level,
            active_alerts=active_alerts,
            watching_since=watching_since,
            learned_patterns=learned_patterns,
            inferred_topology=inferred_topology,
            recent_incidents=recent_incidents
        )
        
    def set_concern_level(self, site: str, level: str):
        """Update concern level for a site."""
        with self._get_conn() as conn:
            if level == 'WATCHING':
                conn.execute("""
                    INSERT OR REPLACE INTO site_states (site, concern_level, watching_since, updated_at)
                    VALUES (?, ?, ?, CURRENT_TIMESTAMP)
                """, (site, level, datetime.now(timezone.utc).isoformat()))
            elif level == 'NORMAL':
                conn.execute("""
                    INSERT OR REPLACE INTO site_states (site, concern_level, watching_since, updated_at)
                    VALUES (?, ?, NULL, CURRENT_TIMESTAMP)
                """, (site, level))
            else:
                conn.execute("""
                    UPDATE site_states SET concern_level = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE site = ?
                """, (level, site))
                
    def get_watching_sites(self) -> List[str]:
        """Get sites in WATCHING state."""
        with self._get_conn() as conn:
            rows = conn.execute(
                "SELECT site FROM site_states WHERE concern_level = 'WATCHING'"
            ).fetchall()
        return [row['site'] for row in rows]
        
    def get_escalated_sites(self) -> List[str]:
        """Get sites in ESCALATED state."""
        with self._get_conn() as conn:
            rows = conn.execute(
                "SELECT site FROM site_states WHERE concern_level = 'ESCALATED'"
            ).fetchall()
        return [row['site'] for row in rows]
        
    def sites_needing_attention(self) -> List[str]:
        """Get sites in INVESTIGATING state."""
        with self._get_conn() as conn:
            rows = conn.execute(
                "SELECT site FROM site_states WHERE concern_level = 'INVESTIGATING'"
            ).fetchall()
        return [row['site'] for row in rows]
        
    def get_all_site_statuses(self) -> Dict[str, str]:
        """Get concern level for all known sites."""
        with self._get_conn() as conn:
            rows = conn.execute("SELECT site, concern_level FROM site_states").fetchall()
        return {row['site']: row['concern_level'] for row in rows}
        
    # =========================================================================
    # Incident Management
    # =========================================================================
    
    def create_incident(self, site: str, summary: str, nc_root_cause_guess: str,
                       devices_affected: List[str], severity: str = "normal") -> Incident:
        """Create a new incident."""
        with self._get_conn() as conn:
            cursor = conn.execute("""
                INSERT INTO incidents (site, started_at, nc_summary, nc_root_cause_guess, 
                                       devices_affected, severity)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (site, datetime.now(timezone.utc).isoformat(), summary, nc_root_cause_guess,
                  json.dumps(devices_affected), severity))
            incident_id = cursor.lastrowid
            
        return self.get_incident(incident_id)
        
    def get_incident(self, incident_id: int) -> Optional[Incident]:
        """Get incident by ID."""
        with self._get_conn() as conn:
            row = conn.execute(
                "SELECT * FROM incidents WHERE id = ?", (incident_id,)
            ).fetchone()
            
        if not row:
            return None
            
        return self._row_to_incident(row)
        
    def get_active_incident(self, site: str) -> Optional[Incident]:
        """Get the active (unresolved) incident for a site."""
        with self._get_conn() as conn:
            row = conn.execute("""
                SELECT * FROM incidents 
                WHERE site = ? AND resolved_at IS NULL
                ORDER BY started_at DESC LIMIT 1
            """, (site,)).fetchone()
            
        if not row:
            return None
        return self._row_to_incident(row)
        
    def resolve_incident(self, site: str, auto_recovered: bool = False,
                        nc_summary: str = None, human_root_cause: str = None):
        """Resolve the active incident for a site."""
        with self._get_conn() as conn:
            conn.execute("""
                UPDATE incidents 
                SET resolved_at = ?,
                    auto_recovered = ?,
                    nc_summary = COALESCE(?, nc_summary),
                    human_root_cause = COALESCE(?, human_root_cause),
                    human_reviewed_at = CASE WHEN ? IS NOT NULL THEN CURRENT_TIMESTAMP ELSE human_reviewed_at END
                WHERE site = ? AND resolved_at IS NULL
            """, (datetime.now(timezone.utc).isoformat(), auto_recovered, nc_summary,
                  human_root_cause, human_root_cause, site))
                  
    def get_recent_incidents(self, site: str, days: int = 30) -> List[Incident]:
        """Get recent incidents for a site."""
        since = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
        with self._get_conn() as conn:
            rows = conn.execute("""
                SELECT * FROM incidents 
                WHERE site = ? AND started_at > ?
                ORDER BY started_at DESC
            """, (site, since)).fetchall()
            
        return [self._row_to_incident(row) for row in rows]
        
    def get_incidents_since_last_summary(self) -> List[Incident]:
        """Get incidents since last morning summary."""
        with self._get_conn() as conn:
            # Get last summary time
            row = conn.execute(
                "SELECT value FROM nc_metadata WHERE key = 'last_summary_time'"
            ).fetchone()
            
            since = row['value'] if row else (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()
            
            rows = conn.execute("""
                SELECT * FROM incidents 
                WHERE started_at > ?
                ORDER BY site, started_at
            """, (since,)).fetchall()
            
        return [self._row_to_incident(row) for row in rows]
        
    def get_pending_human_review(self) -> List[Incident]:
        """Get incidents pending human review."""
        with self._get_conn() as conn:
            rows = conn.execute("""
                SELECT * FROM incidents 
                WHERE human_reviewed_at IS NULL 
                  AND resolved_at IS NOT NULL
                ORDER BY started_at DESC
            """).fetchall()
            
        return [self._row_to_incident(row) for row in rows]
        
    def _row_to_incident(self, row) -> Incident:
        """Convert database row to Incident."""
        return Incident(
            id=row['id'],
            site=row['site'],
            started_at=datetime.fromisoformat(row['started_at']),
            resolved_at=datetime.fromisoformat(row['resolved_at']) if row['resolved_at'] else None,
            auto_recovered=bool(row['auto_recovered']),
            nc_summary=row['nc_summary'],
            nc_root_cause_guess=row['nc_root_cause_guess'],
            devices_affected=json.loads(row['devices_affected']) if row['devices_affected'] else [],
            human_root_cause=row['human_root_cause'],
            human_notes=row['human_notes'],
            human_reviewed_at=datetime.fromisoformat(row['human_reviewed_at']) if row['human_reviewed_at'] else None,
            severity=row['severity'],
            reported_in_summary=bool(row['reported_in_summary'])
        )
        
    # =========================================================================
    # Learned Patterns
    # =========================================================================
    
    def get_learned_patterns(self, site: str, device: str = None) -> List[LearnedPattern]:
        """Get learned patterns for a site/device."""
        with self._get_conn() as conn:
            if device:
                rows = conn.execute("""
                    SELECT * FROM learned_patterns 
                    WHERE site = ? AND (device = ? OR device IS NULL)
                    ORDER BY confidence DESC
                """, (site, device)).fetchall()
            else:
                rows = conn.execute("""
                    SELECT * FROM learned_patterns WHERE site = ?
                    ORDER BY confidence DESC
                """, (site,)).fetchall()
                
        return [LearnedPattern(
            id=row['id'],
            site=row['site'],
            device=row['device'],
            pattern_type=row['pattern_type'],
            description=row['description'],
            confidence=row['confidence'],
            occurrences=row['occurrences'],
            time_pattern=row['time_pattern'],
            last_seen_at=datetime.fromisoformat(row['last_seen_at']) if row['last_seen_at'] else None
        ) for row in rows]
        
    def record_pattern(self, site: str, device: str, pattern_type: str,
                      description: str, time_pattern: str = None):
        """Record or update a learned pattern."""
        with self._get_conn() as conn:
            # Check if pattern exists
            existing = conn.execute("""
                SELECT id, occurrences, confidence FROM learned_patterns
                WHERE site = ? AND device IS ? AND pattern_type = ?
            """, (site, device, pattern_type)).fetchone()
            
            if existing:
                # Update existing pattern
                new_occurrences = existing['occurrences'] + 1
                new_confidence = min(0.95, existing['confidence'] + 0.1)
                conn.execute("""
                    UPDATE learned_patterns
                    SET occurrences = ?, confidence = ?, last_seen_at = ?, description = ?
                    WHERE id = ?
                """, (new_occurrences, new_confidence, datetime.now(timezone.utc).isoformat(),
                      description, existing['id']))
            else:
                # Create new pattern
                conn.execute("""
                    INSERT INTO learned_patterns 
                    (site, device, pattern_type, description, time_pattern, last_seen_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (site, device, pattern_type, description, time_pattern,
                      datetime.now(timezone.utc).isoformat()))
                      
    # =========================================================================
    # Inferred Topology
    # =========================================================================
    
    def get_inferred_topology(self, site: str) -> Dict[str, List[str]]:
        """Get inferred topology for a site as upstream -> [downstream] dict."""
        with self._get_conn() as conn:
            rows = conn.execute("""
                SELECT upstream_device, downstream_device FROM inferred_topology
                WHERE site = ? AND confidence > 0.5
                ORDER BY upstream_device
            """, (site,)).fetchall()
            
        topology = {}
        for row in rows:
            upstream = row['upstream_device']
            if upstream not in topology:
                topology[upstream] = []
            topology[upstream].append(row['downstream_device'])
            
        return topology
        
    def record_topology_inference(self, site: str, upstream: str, downstream: List[str]):
        """Record inferred topology relationship."""
        with self._get_conn() as conn:
            for device in downstream:
                conn.execute("""
                    INSERT INTO inferred_topology (site, upstream_device, downstream_device, last_seen_at)
                    VALUES (?, ?, ?, ?)
                    ON CONFLICT(site, upstream_device, downstream_device) DO UPDATE SET
                        observed_count = observed_count + 1,
                        confidence = MIN(0.95, confidence + 0.15),
                        last_seen_at = excluded.last_seen_at
                """, (site, upstream, device, datetime.now(timezone.utc).isoformat()))
                
    # =========================================================================
    # Investigation Log
    # =========================================================================
    
    def log_investigation_step(self, site: str, step_type: str, target: str,
                               result: str, interpretation: str, incident_id: int = None):
        """Log an investigation step."""
        with self._get_conn() as conn:
            conn.execute("""
                INSERT INTO investigation_steps 
                (incident_id, site, step_type, target, result, interpretation)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (incident_id, site, step_type, target, result, interpretation))
            
    # =========================================================================
    # Metadata
    # =========================================================================
    
    def get_last_poll_time(self) -> Optional[datetime]:
        """Get the last time we polled for alerts."""
        with self._get_conn() as conn:
            row = conn.execute(
                "SELECT value FROM nc_metadata WHERE key = 'last_poll_time'"
            ).fetchone()
            
        if row and row['value']:
            return datetime.fromisoformat(row['value'])
        return None
        
    def update_last_poll_time(self):
        """Update last poll time to now."""
        with self._get_conn() as conn:
            conn.execute("""
                INSERT OR REPLACE INTO nc_metadata (key, value, updated_at)
                VALUES ('last_poll_time', ?, CURRENT_TIMESTAMP)
            """, (datetime.now(timezone.utc).isoformat(),))
            
    def mark_summary_done(self):
        """Mark that morning summary was done."""
        with self._get_conn() as conn:
            conn.execute("""
                INSERT OR REPLACE INTO nc_metadata (key, value, updated_at)
                VALUES ('last_summary_time', ?, CURRENT_TIMESTAMP)
            """, (datetime.now(timezone.utc).isoformat(),))
