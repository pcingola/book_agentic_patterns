"""Document loaders that return markdown text."""

from pathlib import Path

from agentic_patterns.core.doc_ingestion.models import DocumentProvenance


def load_document(
    file: Path, provenance: DocumentProvenance, pipeline: str = "standard"
) -> str:
    """Parse any document format (PDF, DOCX, PPTX, HTML, images) and return markdown text.

    pipeline="standard" uses docling's text extraction pipeline.
    pipeline="vlm" uses docling's vision-model pipeline for complex layouts.
    """
    from docling.document_converter import DocumentConverter, PdfFormatOption
    from docling.datamodel.base_models import InputFormat

    if pipeline == "vlm":
        from docling.pipeline.vlm_pipeline import VlmPipeline
        from docling.datamodel.pipeline_options import VlmPipelineOptions

        format_options = {
            InputFormat.PDF: PdfFormatOption(
                pipeline_cls=VlmPipeline, pipeline_options=VlmPipelineOptions()
            )
        }
        converter = DocumentConverter(format_options=format_options)
    else:
        converter = DocumentConverter()

    result = converter.convert(str(file))
    return result.document.export_to_markdown()


def load_markdown(file: Path, provenance: DocumentProvenance) -> str:
    """Read an already-converted markdown file directly."""
    return file.read_text(encoding="utf-8")
