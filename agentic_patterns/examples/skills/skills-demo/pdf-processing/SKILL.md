---
name: pdf-processing
description: Extract text and tables from PDF files.
compatibility: Requires PyMuPDF library.
---

# PDF Processing

## When to use this skill

Use this skill when the task involves reading, extracting, or transforming content from PDF documents.

## How to use

For standard extraction, run the bundled script:

```
python scripts/extract.py <file.pdf>
```

The script reads the PDF and outputs structured content with page numbers and detected tables.

## Output

Return extracted text with page numbers and any detected tables in a structured format.

## Notes

If you encounter scanned PDFs or complex layouts, OCR processing may be required.
