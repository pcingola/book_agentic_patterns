"""CLI to convert a REPL notebook (cells.json) into a Jupyter notebook (.ipynb)."""

import argparse
import sys
from pathlib import Path

from agentic_patterns.toolkits.repl.export import convert_cells_to_ipynb


def main() -> None:
    parser = argparse.ArgumentParser(description="Convert a REPL cells.json to a Jupyter notebook (.ipynb)")
    parser.add_argument("input", type=Path, help="Path to cells.json")
    parser.add_argument("output", type=Path, nargs="?", default=None, help="Output .ipynb path (default: same name as input with .ipynb extension)")
    args = parser.parse_args()

    if not args.input.exists():
        print(f"Error: {args.input} not found", file=sys.stderr)
        sys.exit(1)

    output: Path = args.output or args.input.with_suffix(".ipynb")

    try:
        convert_cells_to_ipynb(args.input, output)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
