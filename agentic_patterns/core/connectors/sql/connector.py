"""SqlConnector: unified connector for SQL database operations."""

import hashlib
import json
from datetime import datetime
from pathlib import PurePosixPath

import pandas as pd

from agentic_patterns.core.compliance.private_data import DataSensitivity, PrivateData
from agentic_patterns.core.connectors.base import Connector
from agentic_patterns.core.connectors.sql.config import PREVIEW_COLUMNS, PREVIEW_ROWS
from agentic_patterns.core.connectors.sql.db_connection_config import DbConnectionConfigs
from agentic_patterns.core.connectors.sql.db_infos import DbInfos
from agentic_patterns.core.connectors.sql.query_result import QUERY_RESULT_METADATA_EXT, QueryResultMetadata
from agentic_patterns.core.connectors.sql.query_validation import validate_query
from agentic_patterns.core.context.decorators import context_result
from agentic_patterns.core.workspace import workspace_to_host_path, write_to_workspace


class SqlConnector(Connector):
    """SQL database operations."""

    async def execute_sql(self, db_id: str, query: str, output_file: str | None = None, nl_query: str | None = None) -> str:
        """Execute SQL query and return results."""
        validate_query(query)

        db_infos = DbInfos.get()
        db_ops = db_infos.get_operations(db_id)
        df = await db_ops.execute_select_query(query)

        # Tag session when reading from sensitive sources
        db_config = DbConnectionConfigs.get().get_config(db_id)
        if db_config.sensitivity != DataSensitivity.PUBLIC:
            pd = PrivateData()
            pd.add_private_dataset(f"sql:{db_id}", db_config.sensitivity)

        if len(df) == 1 and len(df.columns) == 1:
            return f"Result: {df.iloc[0, 0]}"

        if not output_file:
            query_hash = hashlib.md5(query.encode()).hexdigest()[:8]
            output_file = f"/workspace/results/sql_{query_hash}.csv"

        csv_content = df.to_csv(index=False)
        write_to_workspace(output_file, csv_content)
        host_path = workspace_to_host_path(PurePosixPath(output_file))

        metadata = QueryResultMetadata(
            sql_query=query, timestamp=datetime.now().isoformat(),
            row_count=len(df), column_count=len(df.columns),
            csv_filename=host_path.name, db_id=db_id,
            natural_language_query=nl_query,
        )
        metadata.save(host_path.with_suffix(QUERY_RESULT_METADATA_EXT))

        return _truncate_df_to_csv(df, max_rows=PREVIEW_ROWS, max_columns=PREVIEW_COLUMNS, file_path=output_file)

    @context_result("sql_query")
    async def get_row_by_id(self, db_id: str, table_name: str, row_id: str, fetch_related: bool = False) -> str:
        """Fetch a row by ID, optionally with related data from referenced tables."""
        db_infos = DbInfos.get()
        db_info = db_infos.get_db_info(db_id)
        table = db_info.get_table(table_name)
        if table is None:
            return json.dumps({"error": f"Table '{table_name}' not found in database schema"})

        db_ops = db_infos.get_operations(db_id)
        base_data = await db_ops.fetch_row_by_id(table, row_id)
        if base_data is None:
            pk_column = table.get_primary_key_column()
            return json.dumps({"error": f"No row found with {pk_column}={row_id}"})

        if not fetch_related:
            return json.dumps(base_data, indent=2, default=str)

        related = {}
        for fk in table.foreign_keys:
            if len(fk.columns) > 1:
                continue
            fk_value = base_data.get(fk.columns[0])
            if fk_value is None:
                continue
            ref_table = db_info.get_table(fk.referenced_table)
            if ref_table is None:
                continue
            row = await db_ops.fetch_related_row(ref_table, fk.referenced_columns[0], fk_value)
            if row:
                related[fk.referenced_table] = row
        return json.dumps({"data": base_data, "related": related}, indent=2, default=str)

    async def list_databases(self) -> str:
        """List all available databases."""
        db_infos = DbInfos.get()
        databases = []
        for db_id in db_infos.list_db_ids():
            db_info = db_infos.get_db_info(db_id)
            databases.append({"name": db_id, "description": db_info.description, "table_count": len(db_info.tables)})
        return json.dumps(databases, indent=2)

    async def list_tables(self, db_id: str) -> str:
        """List all tables in a database with descriptions."""
        db_infos = DbInfos.get()
        db_info = db_infos.get_db_info(db_id)
        lines = []
        for table_name in db_info.get_table_names():
            table = db_info.get_table(table_name)
            desc = table.description if table.description else "No description"
            lines.append(f"{table_name}: {desc}")
        return "\n".join(lines)

    async def show_schema(self, db_id: str) -> str:
        """Show full database schema."""
        db_infos = DbInfos.get()
        db_info = db_infos.get_db_info(db_id)
        output = [f"Database: {db_id}"]
        if db_info.description:
            output.append(f"\n{db_info.description}")
        output.append("\n\nSchema:\n")
        output.append(db_info.schema_sql())
        if db_info.example_queries:
            output.append("\n\nExample Queries:\n")
            for i, q in enumerate(db_info.example_queries, 1):
                output.append(f"\n{i}. {q}")
        return "".join(output)

    async def show_table_details(self, db_id: str, table_name: str) -> str:
        """Show detailed information about a specific table."""
        db_infos = DbInfos.get()
        db_info = db_infos.get_db_info(db_id)
        table = db_info.get_table(table_name)
        if table is None:
            raise ValueError(f"Table '{table_name}' not found in database '{db_id}'")
        return table.schema_sql()


def _truncate_df_to_csv(df: pd.DataFrame, max_rows: int = 10, max_columns: int = 200, file_path: str | None = None) -> str:
    """Truncate DataFrame to a CSV preview string."""
    preview_df = df.head(max_rows)
    if len(df.columns) > max_columns:
        preview_df = preview_df.iloc[:, :max_columns]
    csv_str = preview_df.to_csv(index=False)
    parts = []
    if file_path:
        parts.append(f"File: {file_path}")
    parts.append(f"Rows: {len(df)} (showing {len(preview_df)}), Columns: {len(df.columns)}")
    parts.append(csv_str)
    return "\n".join(parts)
