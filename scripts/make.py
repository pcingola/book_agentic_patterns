#!/usr/bin/env python3
import re
import sys
from pathlib import Path


def resolve_includes(file_path: Path, visited: set[Path], source_file: Path | None = None, source_line: int | None = None) -> str:
    """Recursively resolve markdown includes, detecting circular references."""
    file_path = file_path.resolve()

    if file_path in visited:
        location = f"{source_file}:{source_line}: " if source_file and source_line else ""
        print(f"{location}Error: Circular reference detected: {file_path}", file=sys.stderr)
        sys.exit(1)

    if not file_path.exists():
        location = f"{source_file}:{source_line}: " if source_file and source_line else ""
        print(f"{location}Warning: File not found: {file_path}", file=sys.stderr)
        return ""

    visited.add(file_path)
    content = file_path.read_text()
    lines = content.split('\n')

    # Match markdown links: [text](file.md)
    pattern = r'\[([^\]]+)\]\(([^\)]+\.md)\)'

    result_lines = []
    for line_num, line in enumerate(lines, start=1):
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
            return resolve_includes(target_path, visited.copy(), file_path, line_num)

        line = re.sub(pattern, replace_include, line)
        result_lines.append(line)

    result = '\n'.join(result_lines)

    # Resolve image paths to absolute paths
    img_pattern = r'!\[([^\]]*)\]\(([^)]+)\)'
    result_lines = []

    for line_num, line in enumerate(result.split('\n'), start=1):
        def replace_image(match: re.Match) -> str:
            alt_text = match.group(1)
            img_path = match.group(2)

            # Skip URLs
            if img_path.startswith(('http://', 'https://')):
                return match.group(0)

            # Skip absolute paths
            if img_path.startswith('/'):
                return match.group(0)

            # Convert relative image path to absolute
            abs_img_path = (file_path.parent / img_path).resolve()
            if abs_img_path.exists():
                return f'![{alt_text}]({abs_img_path})'
            else:
                print(f"{file_path}:{line_num}: Warning: Image not found: {abs_img_path}", file=sys.stderr)
                return match.group(0)

        line = re.sub(img_pattern, replace_image, line)
        result_lines.append(line)

    result = '\n'.join(result_lines)
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
