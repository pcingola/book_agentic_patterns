"""Abstract database connection."""

from abc import ABC, abstractmethod

from agentic_patterns.core.connectors.sql.db_connection_config import DbConnectionConfig


class DbConnection(ABC):
    """Base class for database connections."""

    def __init__(self, config: DbConnectionConfig) -> None:
        self.config = config
        self._conn = None

    @property
    def database_type(self):
        return self.config.type

    @abstractmethod
    def connect(self):
        """Establish database connection."""

    @abstractmethod
    def close(self) -> None:
        """Close database connection."""

    @abstractmethod
    def cursor(self):
        """Get database cursor."""

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
