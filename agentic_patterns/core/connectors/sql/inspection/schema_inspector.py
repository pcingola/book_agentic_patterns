"""Abstract database schema inspector."""

from abc import ABC, abstractmethod

from agentic_patterns.core.connectors.sql.column_info import ColumnInfo
from agentic_patterns.core.connectors.sql.foreign_key_info import ForeignKeyInfo
from agentic_patterns.core.connectors.sql.index_info import IndexInfo


class DbSchemaInspector(ABC):
    """Base class for database schema inspectors."""

    def __init__(self, connection, schema: str = "public") -> None:
        self.conn = connection
        self.schema = schema

    @abstractmethod
    def get_columns(
        self, table_name: str, column_descriptions: dict[str, str] | None = None
    ) -> list[ColumnInfo]:
        pass

    @abstractmethod
    def get_foreign_keys(self, table_name: str) -> list[ForeignKeyInfo]:
        pass

    @abstractmethod
    def get_indexes(self, table_name: str) -> list[IndexInfo]:
        pass

    @abstractmethod
    def get_primary_keys(self, table_name: str) -> set[str]:
        pass

    @abstractmethod
    def get_tables(self) -> list[str]:
        pass

    @abstractmethod
    def get_unique_constraints(self, table_name: str) -> set[str]:
        pass

    @abstractmethod
    def is_view_map(self) -> dict[str, bool]:
        pass
