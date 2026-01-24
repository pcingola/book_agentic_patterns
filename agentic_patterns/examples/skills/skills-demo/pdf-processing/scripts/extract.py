"""PDF text extraction script."""

import sys
from pathlib import Path


def extract_text(pdf_path: Path) -> dict:
    """Extract text from PDF file."""
    return {"pages": [], "tables": []}


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python extract.py <file.pdf>")
        sys.exit(1)
    result = extract_text(Path(sys.argv[1]))
    print(result)
