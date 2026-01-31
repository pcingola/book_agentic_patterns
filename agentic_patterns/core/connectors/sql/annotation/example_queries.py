"""Example query generation for database schema annotation."""

import json
import logging

from agentic_patterns.core.agents.agents import get_agent, run_agent
from agentic_patterns.core.connectors.sql.config import MAX_QUERY_GENERATION_RETRIES, NUMBER_OF_EXAMPLE_QUERIES
from agentic_patterns.core.connectors.sql.db_info import DbInfo
from agentic_patterns.core.connectors.sql.db_infos import DbInfos
from agentic_patterns.core.prompt import get_prompt


logger = logging.getLogger(__name__)


async def generate_example_queries(db_info: DbInfo, verbose: bool = False) -> None:
    """Generate and validate example SQL queries for the database."""
    db_ops = DbInfos.get().get_operations(db_info.db_id)
    schema = db_info.schema_sql()
    queries = []

    for idx in range(1, NUMBER_OF_EXAMPLE_QUERIES + 1):
        retry_note = ""
        for attempt in range(MAX_QUERY_GENERATION_RETRIES):
            prompt = get_prompt(
                "sql/schema_annotation/example_query_generation",
                db_description=db_info.description,
                schema=schema,
                idx=str(idx),
                total=str(NUMBER_OF_EXAMPLE_QUERIES),
                retry_note=retry_note,
            )
            agent = get_agent(system_prompt="You are a SQL expert.")
            result, _ = await run_agent(agent, prompt, verbose=verbose)
            if not result:
                break

            try:
                query_dict = json.loads(result.output)
                sql = query_dict["query"]
                await db_ops.execute_select_query(sql)
                queries.append(query_dict)
                break
            except Exception as e:
                retry_note = f"\n\nPrevious attempt failed with error: {e}. Please fix the query."
                logger.warning(f"Example query {idx} attempt {attempt + 1} failed: {e}")

    db_info.example_queries = queries
