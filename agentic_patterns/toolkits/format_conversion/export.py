"""Export: convert Markdown to PDF/Word/HTML.

PDF: Markdown -> HTML (pypandoc) -> PDF (weasyprint).
DOCX/HTML: Markdown -> target (pypandoc).
"""

from pathlib import Path

import pypandoc
import weasyprint

from agentic_patterns.toolkits.format_conversion.enums import OutputFormat


def markdown_to(
    input_path: Path, output_path: Path, output_format: OutputFormat
) -> Path:
    """Convert a Markdown file to the target format."""
    match output_format:
        case OutputFormat.PDF:
            html = pypandoc.convert_file(str(input_path), "html")
            base_url = str(input_path.parent) + "/"
            weasyprint.HTML(string=html, base_url=base_url).write_pdf(str(output_path))
        case OutputFormat.DOCX:
            pypandoc.convert_file(str(input_path), "docx", outputfile=str(output_path))
        case OutputFormat.HTML:
            pypandoc.convert_file(str(input_path), "html", outputfile=str(output_path))
        case _:
            raise ValueError(f"Unsupported export format: {output_format}")
    return output_path
