#!/bin/bash -eu
set -o pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUTPUT_DIR="$PROJECT_DIR/output"
GENERATE_PDF=false

if [ "${1:-}" = "pdf" ]; then
    GENERATE_PDF=true
fi

# Delete old output and create a new one
rm -rf "$OUTPUT_DIR"
mkdir -p "$OUTPUT_DIR"

# Start with title page
if [ -f "$PROJECT_DIR/title_page.md" ]; then
    cat "$PROJECT_DIR/title_page.md" > "$OUTPUT_DIR/book.md"
fi

# Get chapter names from chapters.md
CHAPTERS=$(sed -n 's|.*](chapters/\([^/]*\)/chapter\.md).*|\1|p' "$PROJECT_DIR/chapters.md")

# For each chapter, process it and append to the book
for chapter_name in $CHAPTERS; do
    chapter_dir="$PROJECT_DIR/chapters/$chapter_name"
    chapter_file="$chapter_dir/chapter.md"
    output_file="$OUTPUT_DIR/${chapter_name}.md"

    if [ -f "$chapter_file" ]; then
        echo "Processing chapter '$chapter_name'"
        "$PROJECT_DIR/scripts/make.py" "$chapter_file" > "$output_file"
        cat "$output_file" >> "$OUTPUT_DIR/book.md"
        echo "" >> "$OUTPUT_DIR/book.md"

        # Add page breaks between chapters
        echo '\newpage' >> "$OUTPUT_DIR/book.md"
        echo '\ ' >> "$OUTPUT_DIR/book.md"
        echo '\newpage' >> "$OUTPUT_DIR/book.md"
        echo "" >> "$OUTPUT_DIR/book.md"

        # # Generate PDF for the chapter if requested
        # if [ "$GENERATE_PDF" = true ]; then
        #     echo "Generating PDF for chapter '$chapter_name'"
        #     pandoc "$output_file" -o "$OUTPUT_DIR/${chapter_name}.pdf" --pdf-engine=xelatex -V geometry:margin=1in
        # fi
    fi
done

# Generate PDF for the entire book if requested
if [ "$GENERATE_PDF" = true ]; then
    echo "Generating PDF for the entire book"
    pandoc "$OUTPUT_DIR/book.md" \
        -o "$OUTPUT_DIR/book.pdf" \
        --pdf-engine=xelatex \
        --toc \
        --toc-depth=2 \
        -V geometry:margin=1in \
        -V toc-own-page=true
fi
