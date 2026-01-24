#!/bin/bash -eu
set -o pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUTPUT_DIR="$PROJECT_DIR/output"
GENERATE_PDF=false

if [ "${1:-}" = "pdf" ]; then
    GENERATE_PDF=true
fi

rm -rf "$OUTPUT_DIR"
mkdir -p "$OUTPUT_DIR"

if [ -f "$PROJECT_DIR/title_page.md" ]; then
    cat "$PROJECT_DIR/title_page.md" > "$OUTPUT_DIR/book.md"
fi

CHAPTERS="foundations core_patterns tools orchestration rag context_memory mcp a2a skills connectors execution_infrastructure"

for chapter_name in $CHAPTERS; do
    chapter_dir="$PROJECT_DIR/chapters/$chapter_name"
    chapter_file="$chapter_dir/chapter.md"
    output_file="$OUTPUT_DIR/${chapter_name}.md"

    if [ -f "$chapter_file" ]; then
        echo "Processing chapter '$chapter_name'"
        "$PROJECT_DIR/scripts/make.py" "$chapter_file" > "$output_file"
        cat "$output_file" >> "$OUTPUT_DIR/book.md"
        echo "" >> "$OUTPUT_DIR/book.md"
        echo '\newpage' >> "$OUTPUT_DIR/book.md"
        echo "" >> "$OUTPUT_DIR/book.md"

        if [ "$GENERATE_PDF" = true ]; then
            echo "Generating PDF for chapter '$chapter_name'"
            pandoc "$output_file" -o "$OUTPUT_DIR/${chapter_name}.pdf" --pdf-engine=xelatex -V geometry:margin=1in
        fi
    fi
done

if [ "$GENERATE_PDF" = true ]; then
    echo "Generating PDF for the entire book"
    pandoc "$OUTPUT_DIR/book.md" -o "$OUTPUT_DIR/book.pdf" --pdf-engine=xelatex --toc --toc-depth=2 -V geometry:margin=1in
fi
