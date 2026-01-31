"""Schema annotation pipeline -- AI-powered schema enrichment."""

import logging

from agentic_patterns.core.agents.agents import get_agent, run_agent
from agentic_patterns.core.connectors.sql.annotation.enum_detector import detect_enums
from agentic_patterns.core.connectors.sql.annotation.example_queries import generate_example_queries
from agentic_patterns.core.connectors.sql.config import DATABASE_CACHE_DIR, MAX_SAMPLE_ROWS
from agentic_patterns.core.connectors.sql.db_info import DbInfo
from agentic_patterns.core.connectors.sql.inspection.schema_extractor import DbSchemaExtractor
from agentic_patterns.core.prompt import get_prompt


logger = logging.getLogger(__name__)


class DbSchemaAnnotator:
    """Orchestrates AI-powered schema annotation: descriptions, enums, sample data, example queries."""

    def __init__(self, db_id: str) -> None:
        self.db_id = db_id

    async def annotate(self, verbose: bool = False) -> DbInfo:
        """Run the full annotation pipeline."""
        with DbSchemaExtractor(self.db_id) as extractor:
            db_info = extractor.db_info(cache=False)

        await self._annotate_db_description(db_info, verbose)
        await self._annotate_table_descriptions(db_info, verbose)
        await self._annotate_column_descriptions(db_info, verbose)
        await self._collect_sample_data(db_info)
        await detect_enums(db_info, verbose=verbose)
        await generate_example_queries(db_info, verbose=verbose)

        db_info.save()
        logger.info(f"Annotation complete for {self.db_id}")
        return db_info

    async def _annotate_db_description(self, db_info: DbInfo, verbose: bool) -> None:
        schema = db_info.schema_sql()
        prompt = get_prompt("sql/schema_annotation/schema_db_description", schema=schema)
        agent = get_agent(system_prompt="You are a database analyst.")
        result, _ = await run_agent(agent, prompt, verbose=verbose)
        if result:
            db_info.description = result.output

    async def _annotate_table_descriptions(self, db_info: DbInfo, verbose: bool) -> None:
        for table in db_info.tables:
            table_schema = table.schema_sql()
            prompt = get_prompt("sql/schema_annotation/schema_table_description", db_description=db_info.description, table_schema=table_schema)
            agent = get_agent(system_prompt="You are a database analyst.")
            result, _ = await run_agent(agent, prompt, verbose=verbose)
            if result:
                table.description = result.output

    async def _annotate_column_descriptions(self, db_info: DbInfo, verbose: bool) -> None:
        for table in db_info.tables:
            table_schema = table.schema_sql()
            prompt = get_prompt("sql/schema_annotation/schema_columns_description", db_description=db_info.description, table_schema=table_schema)
            agent = get_agent(system_prompt="You are a database analyst.")
            result, _ = await run_agent(agent, prompt, verbose=verbose)
            if result:
                for line in result.output.strip().split("\n"):
                    if ":" in line:
                        col_name, desc = line.split(":", 1)
                        col = table.get_column(col_name.strip())
                        if col:
                            col.description = desc.strip()

    async def _collect_sample_data(self, db_info: DbInfo) -> None:
        """Collect sample data for each table."""
        from agentic_patterns.core.connectors.sql.db_infos import DbInfos
        db_ops = DbInfos.get().get_operations(self.db_id)
        for table in db_info.tables:
            try:
                df = await db_ops.execute_select_query(f'SELECT * FROM "{table.name}" LIMIT {MAX_SAMPLE_ROWS}')
                table.sample_data_csv = df.to_csv(index=False)
            except Exception as e:
                logger.warning(f"Failed to collect sample data for {table.name}: {e}")
