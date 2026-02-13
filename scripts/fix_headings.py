#!/usr/bin/env python3
"""One-time script to fix heading levels in chapter section files.

For each section file (referenced from chapter.md), keeps the first ## heading
(the section title) and shifts all subsequent headings down by one level:
  ## -> ###, ### -> ####, #### -> #####

This makes --toc-depth=2 produce a clean TOC with only chapters (#) and sections (##).

Usage:
    scripts/fix_headings.py [--dry-run]
"""
import re
import sys
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent.parent
CHAPTERS_DIR = PROJECT_DIR / "chapters"


def get_section_files() -> list[Path]:
    """Extract section file paths from all chapter.md files."""
    pattern = re.compile(r'\[([^\]]+)\]\((\./[^\)]+\.md)\)')
    files = []
    for chapter_md in sorted(CHAPTERS_DIR.glob("*/chapter.md")):
        for match in pattern.finditer(chapter_md.read_text()):
            section_path = (chapter_md.parent / match.group(2)).resolve()
            if section_path.exists():
                files.append(section_path)
    return files


def fix_headings(content: str) -> str:
    """Keep first ## heading, shift all subsequent headings down by 1 level."""
    lines = content.split('\n')
    result = []
    first_heading_seen = False
    in_code_block = False

    for line in lines:
        stripped = line.lstrip()
        if stripped.startswith('```') or stripped.startswith('~~~'):
            in_code_block = not in_code_block
            result.append(line)
            continue

        if in_code_block:
            result.append(line)
            continue

        m = re.match(r'^(#{1,6})\s+(.*)', line)
        if m:
            if not first_heading_seen:
                first_heading_seen = True
                result.append(line)
            else:
                new_level = min(len(m.group(1)) + 1, 6)
                result.append(f"{'#' * new_level} {m.group(2)}")
        else:
            result.append(line)

    return '\n'.join(result)


def main() -> None:
    dry_run = '--dry-run' in sys.argv

    section_files = get_section_files()
    changed = 0

    for path in section_files:
        original = path.read_text()
        fixed = fix_headings(original)
        if fixed != original:
            changed += 1
            rel = path.relative_to(PROJECT_DIR)
            if dry_run:
                print(f"Would fix: {rel}")
            else:
                path.write_text(fixed)
                print(f"Fixed: {rel}")

    if dry_run:
        print(f"\n{changed} files would be changed (dry run)")
    else:
        print(f"\n{changed} files changed")


if __name__ == "__main__":
    main()
