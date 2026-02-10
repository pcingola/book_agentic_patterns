"""Database catalog agent -- selects the appropriate database for a query."""

from pydantic import BaseModel
from pydantic_ai import Agent

from agentic_patterns.core.agents import get_agent
from agentic_patterns.core.config.config import PROMPTS_DIR
from agentic_patterns.core.connectors.sql.db_infos import DbInfos
from agentic_patterns.core.prompt import load_prompt


class DatabaseSelection(BaseModel):
    database: str
    reasoning: str


def create_agent() -> Agent:
    """Create a database catalog agent that selects the appropriate database."""
    system_prompt = (
        PROMPTS_DIR / "sql" / "db_catalog" / "db_catalog_system_prompt.md"
    ).read_text(encoding="utf-8")
    databases_info = _build_databases_info()
    instructions = load_prompt(
        PROMPTS_DIR / "sql" / "db_catalog" / "db_catalog_instructions.md",
        databases_info=databases_info,
    )
    return get_agent(
        system_prompt=system_prompt,
        instructions=instructions,
        output_type=DatabaseSelection,
    )


def _build_databases_info() -> str:
    """Build a summary of all available databases for the catalog prompt."""
    db_infos = DbInfos.get()
    lines = []
    for db_id in db_infos.list_db_ids():
        db_info = db_infos.get_db_info(db_id)
        lines.append(f"### {db_id}")
        lines.append(f"Description: {db_info.description}")
        table_names = db_info.get_table_names()
        lines.append(f"Tables: {', '.join(table_names)}")
        for t_name in table_names:
            table = db_info.get_table(t_name)
            if table and table.description:
                lines.append(f"  - {t_name}: {table.description}")
        lines.append("")
    return "\n".join(lines)
