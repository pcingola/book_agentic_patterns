"""Database type enum."""

from enum import Enum


class DatabaseType(str, Enum):
    """Supported database types."""

    POSTGRES = "postgres"
    SQLITE = "sqlite"
