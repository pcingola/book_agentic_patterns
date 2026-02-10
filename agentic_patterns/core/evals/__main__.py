#!/usr/bin/env python3
"""CLI entry point for running agent evaluations.

Usage:
    python -m agentic_patterns.core.evals [OPTIONS]

Options:
    --evals-dir PATH          Directory containing eval_*.py files (default: evals)
    --filter TEXT             Filter by module, file, or dataset name
    --min-assertions FLOAT    Minimum assertion average for pass (default: 1.0)
    --include-input           Show inputs in report
    --include-output          Show outputs in report
    --include-reasons         Show evaluator reasons
    --verbose                 Detailed discovery and execution info
"""

import argparse
import asyncio
import sys
from pathlib import Path

from agentic_patterns.core.evals.discovery import discover_datasets, find_eval_files
from agentic_patterns.core.evals.runner import PrintOptions, run_all_evaluations


async def main() -> int:
    """Main entry point for running evaluations."""
    parser = argparse.ArgumentParser(description="Run agent evaluations")
    parser.add_argument(
        "--evals-dir",
        type=Path,
        default=Path("evals"),
        help="Directory containing eval_*.py files",
    )
    parser.add_argument(
        "--filter", type=str, help="Filter to run only matching evaluations"
    )
    parser.add_argument(
        "--min-assertions",
        type=float,
        default=1.0,
        help="Minimum assertions average for pass",
    )
    parser.add_argument(
        "--include-input",
        action="store_true",
        default=True,
        help="Include input in report",
    )
    parser.add_argument(
        "--include-output",
        action="store_true",
        default=True,
        help="Include output in report",
    )
    parser.add_argument(
        "--include-evaluator-failures",
        action="store_true",
        help="Include evaluator failures",
    )
    parser.add_argument(
        "--include-reasons", action="store_true", help="Include reasons in report"
    )
    parser.add_argument(
        "--verbose", action="store_true", help="Detailed discovery and execution info"
    )

    args = parser.parse_args()

    print_options = PrintOptions(
        include_input=args.include_input,
        include_output=args.include_output,
        include_evaluator_failures=args.include_evaluator_failures,
        include_reasons=args.include_reasons,
    )

    if args.verbose:
        print(f"Scanning directory: {args.evals_dir}")

    eval_files = find_eval_files(args.evals_dir)

    if args.verbose:
        print(f"Found {len(eval_files)} eval files:")
        for f in eval_files:
            print(f"  - {f}")

    datasets = discover_datasets(eval_files, args.filter, args.verbose)

    if args.filter and not args.verbose:
        print(f"Filter applied: {args.filter}")

    success = await run_all_evaluations(
        datasets, print_options, args.min_assertions, args.verbose
    )
    return 0 if success else 1


def main_sync() -> None:
    sys.path.insert(0, str(Path.cwd()))
    sys.exit(asyncio.run(main()))


if __name__ == "__main__":
    main_sync()
