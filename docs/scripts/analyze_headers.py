#!/usr/bin/env python3
"""Analyze top-level headers in a markdown file, skipping code blocks."""

import re
import sys
from pathlib import Path


def analyze_headers(filepath: Path, header_prefix: str = "# ") -> None:
    lines = filepath.read_text().splitlines()

    in_code_block = False
    headers: list[tuple[int, str]] = []

    for i, line in enumerate(lines, 1):
        if line.rstrip().startswith("```"):
            in_code_block = not in_code_block
            continue
        if not in_code_block and line.startswith(header_prefix) and not line.startswith(header_prefix + "#"):
            headers.append((i, line.rstrip()[:120]))

    print(f"File: {filepath}")
    print(f"Total lines: {len(lines)}")
    print(f"Headers matching '{header_prefix}': {len(headers)}")
    print()

    prev_line = 0
    for line_num, text in headers:
        section_size = line_num - prev_line if prev_line else line_num
        print(f"  Line {line_num:5d} ({section_size:5d} lines): {text}")
        prev_line = line_num

    remaining = len(lines) - prev_line
    print(f"  {'':5s}        ({remaining:5d} lines): [after last header]")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} <markdown_file> [header_prefix]")
        sys.exit(1)

    filepath = Path(sys.argv[1])
    header_prefix = sys.argv[2] if len(sys.argv) > 2 else "# "
    analyze_headers(filepath, header_prefix)
