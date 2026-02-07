"""Private data management for agent sessions.

Tracks whether a session's workspace contains private/confidential data.
The state is persisted as a JSON file (`.private_data`) inside a separate
directory (PRIVATE_DATA_DIR) outside the agent's workspace, so the agent
cannot tamper with the compliance flag. When the flag is set, downstream
guardrails can block tools that would leak data outside trusted boundaries
(external APIs, MCP servers with outbound connectivity, etc.).

All modifications save to disk immediately.
"""

import json
import logging
from enum import Enum
from pathlib import Path

from agentic_patterns.core.config.config import PRIVATE_DATA_DIR
from agentic_patterns.core.user_session import get_session_id, get_user_id

logger = logging.getLogger(__name__)

PRIVATE_DATA_FILENAME = ".private_data"


class DataSensitivity(str, Enum):
    """Data sensitivity levels, from least to most restrictive."""
    PUBLIC = "public"
    INTERNAL = "internal"
    CONFIDENTIAL = "confidential"
    SECRET = "secret"


class PrivateData:
    """Manages the private-data flag and dataset registry for a session.

    The information is stored in a JSON file named `.private_data` within a
    dedicated directory outside the agent's workspace. If the file does not
    exist, there is no private data.

    All mutations persist immediately.
    """

    def __init__(self, user_id: str | None = None, session_id: str | None = None):
        self._user_id = user_id or get_user_id()
        self._session_id = session_id or get_session_id()
        self._has_private_data: bool = False
        self._private_datasets: list[str] = []
        self._sensitivity: str = DataSensitivity.CONFIDENTIAL.value
        self.load()

    def add_private_dataset(self, dataset_name: str, sensitivity: DataSensitivity = DataSensitivity.CONFIDENTIAL) -> None:
        """Register a dataset as private. Idempotent."""
        if dataset_name not in self._private_datasets:
            self._private_datasets.append(dataset_name)
            self._has_private_data = True
            self._sensitivity = max(self._sensitivity, sensitivity.value, key=_sensitivity_order)
            self.save()

    def get_private_datasets(self) -> list[str]:
        """Return a copy of the private dataset names."""
        return list(self._private_datasets)

    def has_private_dataset(self, dataset_name: str) -> bool:
        return dataset_name in self._private_datasets

    @property
    def has_private_data(self) -> bool:
        return self._has_private_data

    @has_private_data.setter
    def has_private_data(self, value: bool) -> None:
        self._has_private_data = value
        if not value:
            self._private_datasets = []
            self._sensitivity = DataSensitivity.CONFIDENTIAL.value
        self.save()

    @property
    def sensitivity(self) -> DataSensitivity:
        return DataSensitivity(self._sensitivity)

    def _get_path(self) -> Path:
        return PRIVATE_DATA_DIR / self._user_id / self._session_id / PRIVATE_DATA_FILENAME

    def load(self) -> None:
        path = self._get_path()
        if not path.exists():
            self._has_private_data = False
            self._private_datasets = []
            self._sensitivity = DataSensitivity.CONFIDENTIAL.value
            return
        data = json.loads(path.read_text(encoding="utf-8"))
        self._has_private_data = data.get("has_private_data", False)
        self._private_datasets = data.get("private_datasets", [])
        self._sensitivity = data.get("sensitivity", DataSensitivity.CONFIDENTIAL.value)

    def save(self) -> None:
        path = self._get_path()
        if not self._has_private_data:
            path.unlink(missing_ok=True)
            return
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "has_private_data": self._has_private_data,
            "private_datasets": self._private_datasets,
            "sensitivity": self._sensitivity,
        }
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def __repr__(self) -> str:
        return f"PrivateData(has_private_data={self._has_private_data}, sensitivity={self._sensitivity}, datasets={self._private_datasets})"

    def __str__(self) -> str:
        return self.__repr__()


def mark_session_private(user_id: str | None = None, session_id: str | None = None) -> PrivateData:
    """Mark the current session's workspace as containing private data. Idempotent."""
    pd = PrivateData(user_id, session_id)
    if not pd.has_private_data:
        pd.has_private_data = True
        logger.info("Marked session workspace as private")
    return pd


def session_has_private_data(user_id: str | None = None, session_id: str | None = None) -> bool:
    """Check whether the current session contains private data."""
    return PrivateData(user_id, session_id).has_private_data


_SENSITIVITY_ORDER = [s.value for s in DataSensitivity]


def _sensitivity_order(value: str) -> int:
    try:
        return _SENSITIVITY_ORDER.index(value)
    except ValueError:
        return 0
