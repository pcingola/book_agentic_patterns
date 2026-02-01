"""NL2SQL example -- demonstrates natural language queries against the bookstore database."""

import asyncio

from agentic_patterns.core.connectors.sql.config import DBS_YAML_PATH
from agentic_patterns.core.connectors.sql.db_connection_config import DbConnectionConfigs
from agentic_patterns.core.connectors.sql.db_infos import DbInfos
from agentic_patterns.core.agents.nl2sql.agent import run_nl2sql_query


DB_ID = "bookstore"


def setup():
    """Load database configurations and metadata."""
    DbConnectionConfigs.reset()
    DbInfos.reset()
    DbConnectionConfigs.get().load_from_yaml(DBS_YAML_PATH)


async def main():
    setup()

    queries = [
        "What are the top 3 best-selling books?",
        "Which authors have the most books in the store?",
        "Show me all orders that are still pending",
    ]

    for query in queries:
        print(f"\n{'=' * 60}")
        print(f"Question: {query}")
        print("=" * 60)
        result, nodes = await run_nl2sql_query(DB_ID, query, verbose=True)
        if result:
            print(f"\nAnswer: {result.output}")


if __name__ == "__main__":
    asyncio.run(main())
