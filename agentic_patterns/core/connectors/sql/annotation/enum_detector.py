"""Enum detection for database columns."""

import logging

from pydantic import BaseModel

from agentic_patterns.core.agents.agents import get_agent, run_agent
from agentic_patterns.core.connectors.sql.config import MAX_ENUM_VALUES
from agentic_patterns.core.connectors.sql.db_info import DbInfo
from agentic_patterns.core.connectors.sql.db_infos import DbInfos
from agentic_patterns.core.prompt import get_prompt


logger = logging.getLogger(__name__)

SKIP_TYPES = {
    "INTEGER",
    "INT",
    "REAL",
    "FLOAT",
    "DOUBLE",
    "NUMERIC",
    "DECIMAL",
    "BOOLEAN",
    "BOOL",
    "DATE",
    "DATETIME",
    "TIMESTAMP",
    "TIME",
    "BLOB",
}


class EnumDetectionResult(BaseModel):
    is_enum: bool
    reasoning: str


def _should_analyze(col) -> bool:
    """Quick screening: skip columns unlikely to be enums."""
    if col.is_primary_key:
        return False
    base_type = col.data_type.split("(")[0].upper()
    return base_type not in SKIP_TYPES


async def detect_enums(db_info: DbInfo, verbose: bool = False) -> None:
    """Run two-phase enum detection on all columns."""
    db_ops = DbInfos.get().get_operations(db_info.db_id)

    for table in db_info.tables:
        for col in table.columns:
            if not _should_analyze(col):
                col.is_enum = False
                col.enum_values = []
                continue

            try:
                df = await db_ops.execute_select_query(
                    f'SELECT "{col.name}", COUNT(*) as cnt FROM "{table.name}" GROUP BY "{col.name}" ORDER BY cnt DESC LIMIT {MAX_ENUM_VALUES + 1}'
                )
            except Exception:
                col.is_enum = False
                col.enum_values = []
                continue

            distinct_count = len(df)
            if distinct_count > MAX_ENUM_VALUES:
                col.is_enum = False
                col.enum_values = []
                continue

            row_count_df = await db_ops.execute_select_query(
                f'SELECT COUNT(*) FROM "{table.name}"'
            )
            row_count = int(row_count_df.iloc[0, 0])

            distinct_str = "\n".join(
                f"  {row[col.name]}: {row['cnt']}" for _, row in df.iterrows()
            )

            prompt = get_prompt(
                "sql/enum_detection/enum_detection",
                db_description=db_info.description,
                table_schema=table.schema_sql(),
                column_name=col.name,
                column_data_type=col.data_type,
                column_description=col.description,
                row_count=str(row_count),
                distinct_count=str(distinct_count),
                distinct_by_count=distinct_str,
            )

            agent = get_agent(
                system_prompt="You are a database analyst.",
                output_type=EnumDetectionResult,
            )
            result, _ = await run_agent(agent, prompt, verbose=verbose)
            if result and result.output:
                col.is_enum = result.output.is_enum
                col.enum_values = (
                    sorted(
                        [
                            str(row[col.name])
                            for _, row in df.iterrows()
                            if row[col.name] is not None
                        ]
                    )
                    if col.is_enum
                    else []
                )
            else:
                col.is_enum = False
                col.enum_values = []
