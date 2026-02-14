"""Remove execution outputs from Jupyter notebooks, skipping already-clean ones."""

import json
import sys
from pathlib import Path

SKIP_DIRS = {".venv", ".ipynb_checkpoints", "node_modules", "__pycache__"}


def has_outputs(nb: dict) -> bool:
    for cell in nb.get("cells", []):
        if cell.get("outputs"):
            return True
        if cell.get("execution_count") is not None:
            return True
    return False


def clean_notebook(path: Path) -> bool:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not has_outputs(data):
        return False
    for cell in data.get("cells", []):
        cell["outputs"] = []
        cell["execution_count"] = None
    path.write_text(json.dumps(data, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    return True


def main(root: Path) -> None:
    cleaned = 0
    for path in sorted(root.rglob("*.ipynb")):
        if SKIP_DIRS & set(path.parts):
            continue
        if clean_notebook(path):
            print(path.relative_to(root))
            cleaned += 1
    if cleaned:
        print(f"\nCleaned {cleaned} notebook(s)")


if __name__ == "__main__":
    main(Path(sys.argv[1]))
