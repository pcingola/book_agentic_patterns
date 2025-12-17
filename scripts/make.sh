#!/bin/bash -eu
set -o pipefail

cd "$(dirname "$0")/.."

OUTPUT_DIR="output"
BOOK_TITLE="Agentic Patterns"

mkdir -p "$OUTPUT_DIR"

# Collect all chapter READMEs in order
CHAPTERS=$(find . -maxdepth 1 -type d -name "chapter_*" | sort | while read -r dir; do
    echo "$dir/README.md"
done)

if [ -z "$CHAPTERS" ]; then
    echo "Error: No chapters found" >&2
    exit 1
fi

# Generate PDF
if command -v pandoc &> /dev/null; then
    pandoc $CHAPTERS \
        -o "$OUTPUT_DIR/book.pdf" \
        --pdf-engine=xelatex \
        --toc \
        --toc-depth=2 \
        --metadata title="$BOOK_TITLE" \
        --resource-path=.:images 2>/dev/null || {
            echo "Warning: PDF generation failed (LaTeX may not be installed)" >&2
        }

    # Generate HTML
    pandoc $CHAPTERS \
        -o "$OUTPUT_DIR/book.html" \
        --standalone \
        --toc \
        --toc-depth=2 \
        --metadata title="$BOOK_TITLE" \
        --resource-path=.:images \
        --css=style.css 2>/dev/null

    echo "Generated: $OUTPUT_DIR/book.pdf and $OUTPUT_DIR/book.html"
else
    echo "Error: pandoc not installed. Install with: brew install pandoc" >&2
    exit 1
fi
