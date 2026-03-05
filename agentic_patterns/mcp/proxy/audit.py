"""Audit trail for the MCP proxy. Append-only JSON Lines file."""

import json
from dataclasses import asdict, dataclass
from pathlib import Path


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
    """Append-only audit log backed by a JSON Lines file."""

    def __init__(self, path: Path) -> None:
        self._path = path
        path.parent.mkdir(parents=True, exist_ok=True)

    def __str__(self) -> str:
        return f"AuditLogger(path={self._path})"

    def log(self, entry: AuditEntry) -> None:
        with open(self._path, "a") as f:
            f.write(json.dumps(asdict(entry)) + "\n")

    def read(self, limit: int = 100) -> list[AuditEntry]:
        """Read the most recent entries."""
        if not self._path.exists():
            return []
        with open(self._path) as f:
            lines = f.readlines()
        entries = [AuditEntry(**json.loads(line)) for line in lines[-limit:]]
        entries.reverse()
        return entries
