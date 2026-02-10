"""CLI entry point for schema annotation."""

import argparse
import asyncio
import logging
import sys

from agentic_patterns.core.connectors.sql.annotation.annotator import DbSchemaAnnotator


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Annotate database schema with AI-generated descriptions"
    )
    parser.add_argument("db_id", type=str, help="Database ID from dbs.yaml")
    parser.add_argument(
        "-d", "--debug", action="store_true", help="Enable debug logging"
    )
    return parser.parse_args()


async def main() -> None:
    args = parse_args()
    level = logging.DEBUG if args.debug else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    try:
        annotator = DbSchemaAnnotator(db_id=args.db_id)
        db_info = await annotator.annotate(verbose=args.debug)
        logging.info(f"Schema:\n{db_info.schema_sql()}")
    except Exception as e:
        logging.error(f"Schema annotation failed: {e}")
        sys.exit(1)


def main_sync() -> None:
    asyncio.run(main())


if __name__ == "__main__":
    main_sync()
