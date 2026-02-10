"""Prompt generation for NL2SQL agent."""

from agentic_patterns.core.config.config import PROMPTS_DIR
from agentic_patterns.core.connectors.sql.db_connection_config import (
    DbConnectionConfigs,
)
from agentic_patterns.core.connectors.sql.db_info import DbInfo
from agentic_patterns.core.prompt import get_prompt


def get_example_queries_md(db_info: DbInfo) -> str:
    """Format example queries as markdown."""
    if not db_info.example_queries:
        return ""
    result = ""
    for i, q in enumerate(db_info.example_queries):
        descr = q.get("description", "")
        sql = q.get("query", "")
        result += f"### Example {i + 1}\n{descr}\n\n```sql\n{sql}\n```\n\n"
    return result


def get_instructions(db_info: DbInfo) -> str:
    """Get instructions for the agent including schema and examples."""
    schema = db_info.schema_sql()
    example_queries_md = get_example_queries_md(db_info)
    base = get_prompt(
        "sql/nl2sql/nl2sql_instructions",
        schema=schema,
        example_queries_md=example_queries_md,
    )

    config = DbConnectionConfigs.get().get_config(db_info.db_id)
    db_type = config.type.value
    specific = _load_specific_instructions(db_info.db_id, db_type)
    if specific:
        return f"{base}\n\n## Additional Instructions\n\n{specific}"
    return base


def get_system_prompt() -> str:
    """Get the system prompt for the NL2SQL agent."""
    prompt_path = PROMPTS_DIR / "sql" / "nl2sql" / "nl2sql_system_prompt.md"
    return prompt_path.read_text(encoding="utf-8")


def _load_specific_instructions(db_id: str, db_type: str) -> str | None:
    """Load database-specific or database-type-specific instructions if they exist."""
    prompts_dir = PROMPTS_DIR / "sql" / "nl2sql"

    db_specific = prompts_dir / "db_specific" / f"{db_id}_instructions.md"
    if db_specific.exists():
        return db_specific.read_text()

    db_type_prompt = prompts_dir / "db_type" / f"{db_type}_instructions.md"
    if db_type_prompt.exists():
        return db_type_prompt.read_text()

    return None
