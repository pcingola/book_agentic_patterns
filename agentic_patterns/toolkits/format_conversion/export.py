"""Export: convert Markdown to PDF/Word/HTML.

PDF: Markdown -> HTML (mistune) -> PDF (xhtml2pdf).
DOCX: Markdown -> HTML (mistune) -> DOCX (htmldocx + python-docx).
HTML: Markdown -> HTML (mistune).
"""

from pathlib import Path

import mistune
from docx import Document
from htmldocx import HtmlToDocx
from xhtml2pdf import pisa

from agentic_patterns.toolkits.format_conversion.enums import OutputFormat


def _md_to_html(input_path: Path) -> str:
    md = input_path.read_text(encoding="utf-8")
    return mistune.html(md)


def markdown_to(
    input_path: Path, output_path: Path, output_format: OutputFormat
) -> Path:
    """Convert a Markdown file to the target format."""
    match output_format:
        case OutputFormat.PDF:
            html = _md_to_html(input_path)
            with open(output_path, "wb") as f:
                result = pisa.CreatePDF(html, dest=f, path=str(input_path.parent))
                if result.err:
                    raise RuntimeError(f"PDF conversion failed with {result.err} errors")
        case OutputFormat.DOCX:
            html = _md_to_html(input_path)
            doc = Document()
            HtmlToDocx().add_html_to_document(html, doc)
            doc.save(str(output_path))
        case OutputFormat.HTML:
            html = _md_to_html(input_path)
            output_path.write_text(html, encoding="utf-8")
        case _:
            raise ValueError(f"Unsupported export format: {output_format}")
    return output_path
