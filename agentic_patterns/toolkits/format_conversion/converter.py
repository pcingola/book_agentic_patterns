"""Dispatch: route conversion by input extension and output format."""

from pathlib import Path

from agentic_patterns.toolkits.format_conversion.enums import InputFormat, OutputFormat
from agentic_patterns.toolkits.format_conversion.export import markdown_to
from agentic_patterns.toolkits.format_conversion.ingest import (
    docx_to_markdown,
    pdf_to_markdown,
    pptx_to_markdown,
    xlsx_to_csv,
    xlsx_to_markdown,
)

_EXT_TO_INPUT = {f".{f.value}": f for f in InputFormat}

_TEXT_OUTPUTS = {OutputFormat.MD, OutputFormat.CSV}


def convert(
    input_path: Path, output_format: OutputFormat, output_path: Path | None = None
) -> str | Path:
    """Convert a document, dispatching by input extension and output format.

    Returns str for text outputs (MD, CSV), Path for binary outputs (PDF, DOCX, HTML).
    """
    ext = input_path.suffix.lower()
    input_fmt = _EXT_TO_INPUT.get(ext)
    if not input_fmt:
        raise ValueError(f"Unsupported input format: {ext}")

    # Text-to-text ingest conversions
    if output_format == OutputFormat.MD:
        match input_fmt:
            case InputFormat.PDF:
                return pdf_to_markdown(input_path)
            case InputFormat.DOCX:
                return docx_to_markdown(input_path)
            case InputFormat.PPTX:
                return pptx_to_markdown(input_path)
            case InputFormat.XLSX:
                return xlsx_to_markdown(input_path)
            case InputFormat.MD:
                return input_path.read_text()
            case InputFormat.CSV:
                return input_path.read_text()
            case _:
                raise ValueError(f"Cannot convert {input_fmt.value} to Markdown")

    if output_format == OutputFormat.CSV:
        if input_fmt == InputFormat.XLSX:
            return xlsx_to_csv(input_path)
        if input_fmt == InputFormat.CSV:
            return input_path.read_text()
        raise ValueError(f"Cannot convert {input_fmt.value} to CSV")

    # Binary export via pandoc (requires Markdown input)
    if output_path is None:
        output_path = input_path.with_suffix(f".{output_format.value}")

    if input_fmt == InputFormat.MD:
        return markdown_to(input_path, output_path, output_format)

    # For non-MD inputs, ingest to MD first, then export
    md_content = convert(input_path, OutputFormat.MD)
    tmp_md = input_path.with_suffix(".tmp.md")
    try:
        tmp_md.write_text(str(md_content))
        return markdown_to(tmp_md, output_path, output_format)
    finally:
        tmp_md.unlink(missing_ok=True)
