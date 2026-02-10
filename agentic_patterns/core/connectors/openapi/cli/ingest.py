"""CLI entry point for API spec ingestion and annotation."""

import argparse
import asyncio
import sys

from agentic_patterns.core.connectors.openapi.annotation.annotator import (
    ApiSpecAnnotator,
)
from agentic_patterns.core.connectors.openapi.api_connection_config import (
    ApiConnectionConfigs,
)
from agentic_patterns.core.connectors.openapi.config import APIS_YAML_PATH


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Ingest and annotate OpenAPI specification"
    )
    parser.add_argument("api_id", type=str, help="API ID from apis.yaml")
    parser.add_argument(
        "-v", "--verbose", action="store_true", help="Enable verbose progress output"
    )
    parser.add_argument(
        "-d",
        "--debug",
        action="store_true",
        help="Enable debug output (includes agent steps)",
    )
    return parser.parse_args()


async def main() -> None:
    args = parse_args()

    try:
        # Load configuration
        configs = ApiConnectionConfigs.get()
        configs.load_from_yaml(APIS_YAML_PATH)

        # Get API config
        config = configs.get_config(args.api_id)
        print(f"Ingesting API: {args.api_id}")
        print(f"Spec source: {config.spec_source}")
        if config.base_url:
            print(f"Base URL: {config.base_url}")

        # Run annotation pipeline
        # Note: base_url from config overrides the spec's servers section, allowing
        # environment-specific URLs (dev/staging/prod) or local testing overrides
        annotator = ApiSpecAnnotator(api_id=args.api_id)
        api_info = await annotator.annotate(
            spec_source=config.spec_source,
            base_url=config.base_url,
            verbose=args.verbose or args.debug,
            debug=args.debug,
        )

        # Display summary
        print("\nAPI ingestion complete!")
        print(f"API: {api_info.title} v{api_info.version}")
        print(f"Endpoints: {len(api_info.endpoints)}")
        print(f"Description: {api_info.description}")
        categories = api_info.get_endpoints_by_category()
        print("\nCategories:")
        for category, endpoints in sorted(categories.items()):
            print(f"  {category}: {len(endpoints)} endpoints")

    except Exception as e:
        if args.debug:
            raise
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)


def main_sync() -> None:
    asyncio.run(main())


if __name__ == "__main__":
    main_sync()
