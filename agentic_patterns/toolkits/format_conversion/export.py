"""Export: convert Markdown to PDF/Word/HTML via pypandoc."""

from pathlib import Path

import pypandoc

from agentic_patterns.toolkits.format_conversion.enums import OutputFormat

_PANDOC_FORMAT_MAP = {
    OutputFormat.PDF: "pdf",
    OutputFormat.DOCX: "docx",
    OutputFormat.HTML: "html",
}


def markdown_to(
    input_path: Path, output_path: Path, output_format: OutputFormat
) -> Path:
    """Convert a Markdown file to the target format using pypandoc."""
    fmt = _PANDOC_FORMAT_MAP.get(output_format)
    if not fmt:
        raise ValueError(f"Unsupported export format: {output_format}")
    extra_args = ["--pdf-engine=typst"] if output_format == OutputFormat.PDF else []
    pypandoc.convert_file(
        str(input_path), fmt, outputfile=str(output_path), extra_args=extra_args
    )
    return output_path
