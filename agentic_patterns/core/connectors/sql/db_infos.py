"""Database metadata and operations registry."""

from __future__ import annotations

from typing import TYPE_CHECKING

from agentic_patterns.core.connectors.sql.config import DATABASE_CACHE_DIR, DB_INFO_EXT
from agentic_patterns.core.connectors.sql.connection import DbConnection
from agentic_patterns.core.connectors.sql.db_connection_config import DbConnectionConfigs
from agentic_patterns.core.connectors.sql.db_info import DbInfo
from agentic_patterns.core.connectors.sql.factories import create_connection

if TYPE_CHECKING:
    from agentic_patterns.core.connectors.sql.db_operations import DbOperations


class DbInfos:
    """Registry for all database connections and metadata. Singleton."""

    _instance: "DbInfos | None" = None

    def __init__(self) -> None:
        self._db_info: dict[str, DbInfo] = {}
        self._connections: dict[str, DbConnection] = {}
        self._operations: dict[str, DbOperations] = {}
        self._initialized = False

    @classmethod
    def get(cls) -> "DbInfos":
        if cls._instance is None:
            cls._instance = cls()
            cls._instance._initialize()
        return cls._instance

    def _initialize(self) -> None:
        if self._initialized:
            return
        db_configs = DbConnectionConfigs.get()
        for db_id in db_configs.list_db_ids():
            db_info_path = DATABASE_CACHE_DIR / db_id / f"{db_id}{DB_INFO_EXT}"
            if db_info_path.exists():
                self._db_info[db_id] = DbInfo.load(db_id, db_info_path)
        self._initialized = True

    def add(self, db_info: DbInfo) -> None:
        self._db_info[db_info.db_id] = db_info

    def close_all(self) -> None:
        for conn in self._connections.values():
            conn.close()
        self._connections.clear()
        self._operations.clear()

    def get_connection(self, db_id: str) -> DbConnection:
        if db_id not in self._db_info:
            raise ValueError(f"Database '{db_id}' not found. Available: {list(self._db_info.keys())}")
        if db_id not in self._connections:
            self._connections[db_id] = create_connection(db_id)
        return self._connections[db_id]

    def get_db_info(self, db_id: str) -> DbInfo:
        if db_id not in self._db_info:
            raise ValueError(f"Database '{db_id}' not found. Available: {list(self._db_info.keys())}")
        return self._db_info[db_id]

    def get_operations(self, db_id: str) -> "DbOperations":
        if db_id not in self._db_info:
            raise ValueError(f"Database '{db_id}' not found. Available: {list(self._db_info.keys())}")
        if db_id not in self._operations:
            from agentic_patterns.core.connectors.sql.factories import create_db_operations
            conn = self.get_connection(db_id)
            self._operations[db_id] = create_db_operations(db_id, conn)
        return self._operations[db_id]

    def list_db_ids(self) -> list[str]:
        return sorted(list(self._db_info.keys()))

    def __len__(self) -> int:
        return len(self._db_info)

    def __str__(self) -> str:
        return f"DbInfos({len(self._db_info)} databases: {self.list_db_ids()})"

    @classmethod
    def reset(cls) -> None:
        if cls._instance is not None:
            cls._instance.close_all()
        cls._instance = None
