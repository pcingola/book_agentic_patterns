"""Abstract database operations interface."""

from abc import ABC, abstractmethod

import pandas as pd

from agentic_patterns.core.connectors.sql.connection import DbConnection
from agentic_patterns.core.connectors.sql.table_info import TableInfo


class DbOperations(ABC):
    """Abstract interface for database operations."""

    def __init__(self, connection: DbConnection) -> None:
        self.connection = connection

    @abstractmethod
    async def execute_select_query(self, query: str) -> pd.DataFrame:
        """Execute a SELECT query and return results as DataFrame."""

    @abstractmethod
    async def fetch_row_by_id(self, table: TableInfo, row_id: str) -> dict | None:
        """Fetch a single row by primary key."""

    @abstractmethod
    async def fetch_related_row(self, table: TableInfo, column_name: str, value: str) -> dict | None:
        """Fetch a related row from another table."""
