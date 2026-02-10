"""Factory functions for creating database-specific components."""

from agentic_patterns.core.connectors.sql.connection import DbConnection
from agentic_patterns.core.connectors.sql.database_type import DatabaseType
from agentic_patterns.core.connectors.sql.db_connection_config import (
    DbConnectionConfigs,
)
from agentic_patterns.core.connectors.sql.inspection.schema_inspector import (
    DbSchemaInspector,
)


def create_connection(db_id: str) -> DbConnection:
    """Create a database connection for specified database."""
    config = DbConnectionConfigs.get().get_config(db_id)
    match config.type:
        case DatabaseType.SQLITE:
            from agentic_patterns.core.connectors.sql.sqlite.connection import (
                DbConnectionSqlite,
            )

            return DbConnectionSqlite(config=config)
        case DatabaseType.POSTGRES:
            raise NotImplementedError("Postgres support not yet implemented")
        case _:
            raise ValueError(f"Unsupported database type: {config.type}")


def create_schema_inspector(db_id: str, connection: DbConnection) -> DbSchemaInspector:
    """Create a schema inspector for specified database."""
    config = DbConnectionConfigs.get().get_config(db_id)
    match config.type:
        case DatabaseType.SQLITE:
            from agentic_patterns.core.connectors.sql.inspection.sqlite.schema_inspector import (
                DbSchemaInspectorSqlite,
            )

            return DbSchemaInspectorSqlite(
                connection=connection.connect(), schema=config.db_schema
            )
        case DatabaseType.POSTGRES:
            raise NotImplementedError("Postgres support not yet implemented")
        case _:
            raise ValueError(f"Unsupported database type: {config.type}")


def create_db_operations(
    db_id: str, connection: DbConnection | None = None
) -> "DbOperations":
    """Create database operations instance based on database type."""
    config = DbConnectionConfigs.get().get_config(db_id)
    if connection is None:
        connection = create_connection(db_id)
    match config.type:
        case DatabaseType.SQLITE:
            from agentic_patterns.core.connectors.sql.sqlite.operations import (
                DbOperationsSqlite,
            )

            return DbOperationsSqlite(connection)
        case DatabaseType.POSTGRES:
            raise NotImplementedError("Postgres support not yet implemented")
        case _:
            raise ValueError(f"Unsupported database type: {config.type}")
