#!/usr/bin/env python3
import re
from pathlib import Path


def renumber_references(file_path: Path, offset: int) -> None:
    """Renumber all reference-style markdown links by adding an offset."""
    content = file_path.read_text()

    # Find all reference definitions like [1]: url
    # and all reference uses like [text][1]

    # First, collect all reference numbers used
    ref_nums = set()
    for match in re.finditer(r'\[(\d+)\]:', content):
        ref_nums.add(int(match.group(1)))

    if not ref_nums or offset == 0:
        print(f"Skipping {file_path.name}: no references or offset=0")
        return

    # Sort in descending order to avoid conflicts when replacing
    ref_nums_sorted = sorted(ref_nums, reverse=True)

    for old_num in ref_nums_sorted:
        new_num = old_num + offset

        # Replace reference definitions: [1]: url -> [11]: url
        content = re.sub(
            rf'^\[{old_num}\]:',
            f'[{new_num}]:',
            content,
            flags=re.MULTILINE
        )

        # Replace reference uses: [text][1] -> [text][11]
        content = re.sub(
            rf'\]\[{old_num}\]',
            f'][{new_num}]',
            content
        )

    file_path.write_text(content)
    print(f"Updated {file_path.name}: added offset {offset} to {len(ref_nums)} references")


def main() -> None:
    chapters_dir = Path(__file__).parent.parent / "chapters" / "01_foundations"

    # Files and their offsets
    files_to_fix = [
        ("stochasticity.md", 0),    # Keep [1]-[10]
        ("modularity.md", 10),       # [1]-[15] -> [11]-[25]
        ("best_practices.md", 25),   # [1]-[7] -> [26]-[32]
    ]

    for filename, offset in files_to_fix:
        file_path = chapters_dir / filename
        if file_path.exists():
            renumber_references(file_path, offset)
        else:
            print(f"Warning: {filename} not found")


if __name__ == "__main__":
    main()
