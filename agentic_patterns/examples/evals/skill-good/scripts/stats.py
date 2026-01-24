#!/usr/bin/env python3
"""Counts lines, words, and characters in a text file."""

import sys
from pathlib import Path


def count_stats(file_path: Path) -> tuple[int, int, int]:
    """Return (lines, words, characters) for the given file."""
    content = file_path.read_text()
    lines = len(content.splitlines())
    words = len(content.split())
    characters = len(content)
    return lines, words, characters


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: stats.py <file>", file=sys.stderr)
        sys.exit(1)

    file_path = Path(sys.argv[1])
    try:
        lines, words, characters = count_stats(file_path)
    except FileNotFoundError:
        print(f"Error: File not found: {file_path}", file=sys.stderr)
        sys.exit(1)
    except OSError as e:
        print(f"Error reading file: {e}", file=sys.stderr)
        sys.exit(1)

    print(f"Lines: {lines}")
    print(f"Words: {words}")
    print(f"Characters: {characters}")


if __name__ == "__main__":
    main()
