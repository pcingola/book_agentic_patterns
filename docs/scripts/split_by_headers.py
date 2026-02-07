#!/usr/bin/env python3
"""Split a markdown file into separate files by top-level headers, skipping code blocks.

Creates an output directory next to the source file (e.g. docs/a2a_specification/)
with numbered files like 01_section_name.md.

Use --dry-run to preview without writing files.
"""

import re
import sys
from pathlib import Path


def slugify(text: str) -> str:
    """Convert header text to a filename-safe slug."""
    text = re.sub(r"^#+\s*", "", text)
    text = text.lower().strip()
    text = re.sub(r"[^a-z0-9]+", "_", text)
    text = text.strip("_")
    return text[:60]


def split_file(filepath: Path, header_prefix: str = "# ", dry_run: bool = False) -> None:
    lines = filepath.read_text().splitlines(keepends=True)
    out_dir = filepath.parent / filepath.stem

    in_code_block = False
    sections: list[tuple[str, int]] = []  # (header_text, start_line_index)

    for i, line in enumerate(lines):
        stripped = line.rstrip()
        if stripped.startswith("```"):
            in_code_block = not in_code_block
            continue
        if not in_code_block and line.startswith(header_prefix) and not line.startswith(header_prefix + "#"):
            sections.append((stripped, i))

    if not sections:
        print("No headers found. Nothing to split.")
        return

    # Build file contents: preamble (before first header) + each section
    file_parts: list[tuple[str, str]] = []  # (filename, content)

    # Preamble (content before first header)
    first_header_idx = sections[0][1]
    if first_header_idx > 0:
        preamble = "".join(lines[:first_header_idx]).strip()
        if preamble:
            file_parts.append(("00_preamble.md", preamble + "\n"))

    for idx, (header_text, start) in enumerate(sections):
        end = sections[idx + 1][1] if idx + 1 < len(sections) else len(lines)
        content = "".join(lines[start:end]).rstrip() + "\n"
        slug = slugify(header_text)
        filename = f"{idx + 1:02d}_{slug}.md"
        file_parts.append((filename, content))

    print(f"Source: {filepath} ({len(lines)} lines)")
    print(f"Output: {out_dir}/")
    print(f"Sections: {len(file_parts)}")
    print()

    for filename, content in file_parts:
        line_count = content.count("\n")
        print(f"  {filename:<60s} ({line_count:5d} lines)")

    if dry_run:
        print("\n[dry-run] No files written.")
        return

    out_dir.mkdir(parents=True, exist_ok=True)
    for filename, content in file_parts:
        (out_dir / filename).write_text(content)

    print(f"\nDone. {len(file_parts)} files written to {out_dir}/")


if __name__ == "__main__":
    if len(sys.argv) < 2 or "--help" in sys.argv:
        print(f"Usage: {sys.argv[0]} <markdown_file> [header_prefix] [--dry-run]")
        print(f"  header_prefix defaults to '# '")
        print(f"  --dry-run  preview without writing files")
        sys.exit(0)

    filepath = Path(sys.argv[1])
    dry_run = "--dry-run" in sys.argv
    args = [a for a in sys.argv[2:] if a != "--dry-run"]
    header_prefix = args[0] if args else "# "
    split_file(filepath, header_prefix, dry_run=dry_run)
