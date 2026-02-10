"""SQLite-based data persistence layer for Chainlit using SQLAlchemy."""

import asyncio
from logging import getLogger
from pathlib import Path

from chainlit.data.sql_alchemy import SQLAlchemyDataLayer
from sqlalchemy import inspect, text
from sqlalchemy.ext.asyncio import create_async_engine

from agentic_patterns.core.config.config import (
    CHAINLIT_DATA_LAYER_DB,
    CHAINLIT_SCHEMA_FILE,
)
from agentic_patterns.core.ui.chainlit.storage import FilesystemStorageClient

logger = getLogger(__name__)


async def init_db(connection_string: str):
    """Initialize database tables if they don't exist."""
    engine = create_async_engine(connection_string)
    async with engine.begin() as conn:

        def check_tables(connection):
            inspector = inspect(connection)
            return inspector.get_table_names()

        tables = await conn.run_sync(check_tables)
        if not tables:
            logger.info(f"Creating database tables from {CHAINLIT_SCHEMA_FILE}...")
            sql_content = CHAINLIT_SCHEMA_FILE.read_text()
            for statement in sql_content.split(";"):
                statement = statement.strip()
                if statement:
                    # Convert PostgreSQL types to SQLite
                    statement_sqlite = (
                        statement.replace("UUID", "TEXT")
                        .replace("JSONB", "TEXT")
                        .replace("TEXT[]", "TEXT")
                    )
                    await conn.execute(text(statement_sqlite))
            logger.info("Database tables created")
        else:
            logger.info(f"Database tables already exist: {tables}")
    await engine.dispose()


def get_sqlite_data_layer(
    db_path: Path = CHAINLIT_DATA_LAYER_DB,
) -> SQLAlchemyDataLayer:
    """Create and return a SQLAlchemy data layer configured for SQLite."""
    logger.info(f"Setting up SQLite data layer for Chainlit: {db_path}")
    connection_string = f"sqlite+aiosqlite:///{db_path}"
    db_path.parent.mkdir(parents=True, exist_ok=True)
    logger.info(f"Initializing SQLite data layer at {db_path}")
    asyncio.run(init_db(connection_string))
    return SQLAlchemyDataLayer(
        conninfo=connection_string, storage_provider=FilesystemStorageClient()
    )
