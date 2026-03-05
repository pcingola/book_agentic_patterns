"""Audit trail for the MCP proxy."""

import json
import logging
import sqlite3
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)

CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS audit_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp REAL NOT NULL,
    user_id TEXT NOT NULL,
    tenant TEXT NOT NULL,
    session_id TEXT NOT NULL,
    server TEXT NOT NULL,
    tool TEXT NOT NULL,
    args TEXT NOT NULL,
    status TEXT NOT NULL,
    duration_ms REAL NOT NULL
)
"""


@dataclass
class AuditEntry:
    """A single audit log entry."""

    timestamp: float
    user_id: str
    tenant: str
    session_id: str
    server: str
    tool: str
    args: dict
    status: str
    duration_ms: float

    def __str__(self) -> str:
        return f"AuditEntry(user={self.user_id}, server={self.server}, tool={self.tool}, status={self.status})"


class AuditLogger:
    """Append-only audit log backed by SQLite."""

    def __init__(self, db_path: Path) -> None:
        self._db_path = db_path
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(db_path))
        self._conn.execute(CREATE_TABLE_SQL)
        self._conn.commit()

    def close(self) -> None:
        self._conn.close()

    def log(self, entry: AuditEntry) -> None:
        self._conn.execute(
            "INSERT INTO audit_log (timestamp, user_id, tenant, session_id, server, tool, args, status, duration_ms) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (entry.timestamp, entry.user_id, entry.tenant, entry.session_id, entry.server, entry.tool, json.dumps(entry.args), entry.status, entry.duration_ms),
        )
        self._conn.commit()

    def query(self, user_id: str | None = None, tenant: str | None = None, server: str | None = None, limit: int = 100) -> list[AuditEntry]:
        """Query audit entries with optional filters."""
        clauses = []
        params: list = []
        if user_id:
            clauses.append("user_id = ?")
            params.append(user_id)
        if tenant:
            clauses.append("tenant = ?")
            params.append(tenant)
        if server:
            clauses.append("server = ?")
            params.append(server)
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        rows = self._conn.execute(f"SELECT timestamp, user_id, tenant, session_id, server, tool, args, status, duration_ms FROM audit_log {where} ORDER BY id DESC LIMIT ?", [*params, limit]).fetchall()
        return [AuditEntry(timestamp=r[0], user_id=r[1], tenant=r[2], session_id=r[3], server=r[4], tool=r[5], args=json.loads(r[6]), status=r[7], duration_ms=r[8]) for r in rows]
