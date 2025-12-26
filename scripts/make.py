#!/usr/bin/env python3
import re
import sys
from pathlib import Path


def resolve_includes(file_path: Path, visited: set[Path]) -> str:
    """Recursively resolve markdown includes, detecting circular references."""
    file_path = file_path.resolve()

    if file_path in visited:
        print(f"Error: Circular reference detected: {file_path}", file=sys.stderr)
        sys.exit(1)

    if not file_path.exists():
        print(f"Error: File not found: {file_path}", file=sys.stderr)
        sys.exit(1)

    visited.add(file_path)
    content = file_path.read_text()

    # Match markdown links: [text](file.md)
    pattern = r'\[([^\]]+)\]\(([^\)]+\.md)\)'

    def replace_include(match: re.Match) -> str:
        link_text = match.group(1)
        link_path = match.group(2)

        # Skip URLs
        if link_path.startswith(('http://', 'https://')):
            return match.group(0)

        # Skip absolute paths
        if link_path.startswith('/'):
            return match.group(0)

        # Skip paths going up (cross-references)
        if '..' in link_path:
            return match.group(0)

        # Skip anchors
        if link_path.startswith('#'):
            return match.group(0)

        # This is an include - resolve it
        target_path = (file_path.parent / link_path).resolve()
        return resolve_includes(target_path, visited.copy())

    result = re.sub(pattern, replace_include, content)
    visited.remove(file_path)

    return result


def main() -> None:
    if len(sys.argv) != 2:
        print("Usage: scripts/make.py main_file.md", file=sys.stderr)
        sys.exit(1)

    input_file = Path(sys.argv[1])

    if not input_file.exists():
        print(f"Error: File not found: {input_file}", file=sys.stderr)
        sys.exit(1)

    result = resolve_includes(input_file, set())
    print(result, end='')


if __name__ == "__main__":
    main()
