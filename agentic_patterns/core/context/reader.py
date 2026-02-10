"""Main interface for context engineering file processing with file type detection."""

import mimetypes
from collections.abc import Callable
from pathlib import Path

import tiktoken

from agentic_patterns.core.context.config import (
    EXTRACTABLE_DOCUMENT_TYPES,
    ContextConfig,
    load_context_config,
)
from agentic_patterns.core.context.models import (
    FileExtractionResult,
    FileType,
    TruncationInfo,
)
from agentic_patterns.core.context.processors.csv_processor import process_csv
from agentic_patterns.core.context.processors.document import process_document
from agentic_patterns.core.context.processors.image import process_image
from agentic_patterns.core.context.processors.json_processor import process_json
from agentic_patterns.core.context.processors.spreadsheet import process_spreadsheet
from agentic_patterns.core.context.processors.text import process_code, process_text
from agentic_patterns.core.context.processors.xml_processor import process_xml
from agentic_patterns.core.context.processors.yaml_processor import process_yaml


CODE_EXTENSIONS = {
    ".py",
    ".js",
    ".jsx",
    ".ts",
    ".tsx",
    ".java",
    ".cpp",
    ".c",
    ".h",
    ".hpp",
    ".cs",
    ".rb",
    ".go",
    ".rs",
    ".php",
    ".swift",
    ".kt",
    ".scala",
    ".r",
    ".m",
    ".mm",
    ".sh",
    ".bash",
    ".zsh",
    ".fish",
    ".ps1",
    ".sql",
    ".html",
    ".css",
    ".scss",
    ".sass",
    ".less",
    ".vue",
    ".svelte",
}

MARKDOWN_EXTENSIONS = {".md", ".markdown", ".mdown", ".mkd", ".rmd"}
TEXT_EXTENSIONS = {".txt", ".log", ".cfg", ".conf", ".ini", ".properties", ".env"}
DOCUMENT_EXTENSIONS = {".pdf", ".docx", ".doc", ".pptx"}
SPREADSHEET_EXTENSIONS = {".xlsx", ".xls", ".ods"}
JSON_EXTENSIONS = {".json", ".jsonl", ".ipynb"}
YAML_EXTENSIONS = {".yaml", ".yml"}
XML_EXTENSIONS = {".xml", ".xsd", ".xsl", ".xslt", ".svg"}
TABULAR_EXTENSIONS = {".csv", ".tsv"}
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp", ".tiff", ".tif"}
AUDIO_EXTENSIONS = {".mp3", ".wav", ".ogg", ".flac", ".m4a", ".aac", ".wma", ".opus"}
ARCHIVE_EXTENSIONS = {".zip", ".tar", ".gz", ".bz2", ".xz", ".7z", ".rar"}


def _detect_file_type(file_path: Path) -> FileType:
    """Detect file type from extension and MIME type."""
    suffix = file_path.suffix.lower()

    if suffix in CODE_EXTENSIONS:
        return FileType.CODE
    if suffix in MARKDOWN_EXTENSIONS:
        return FileType.MARKDOWN
    if suffix in TEXT_EXTENSIONS:
        return FileType.TEXT
    if suffix in DOCUMENT_EXTENSIONS:
        if suffix == ".pdf":
            return FileType.PDF
        if suffix == ".pptx":
            return FileType.PPTX
        return FileType.DOCX
    if suffix in SPREADSHEET_EXTENSIONS:
        return FileType.SPREADSHEET
    if suffix in JSON_EXTENSIONS:
        return FileType.JSON
    if suffix in YAML_EXTENSIONS:
        return FileType.YAML
    if suffix in XML_EXTENSIONS:
        return FileType.XML
    if suffix in TABULAR_EXTENSIONS:
        return FileType.CSV
    if suffix in IMAGE_EXTENSIONS:
        return FileType.IMAGE
    if suffix in AUDIO_EXTENSIONS:
        return FileType.AUDIO
    if suffix in ARCHIVE_EXTENSIONS:
        return FileType.ARCHIVE

    mime_type, _ = mimetypes.guess_type(file_path)
    if mime_type:
        if mime_type.startswith("text/"):
            return FileType.TEXT
        if mime_type.startswith("image/"):
            return FileType.IMAGE
        if mime_type.startswith("audio/"):
            return FileType.AUDIO
        if mime_type in {"application/json"}:
            return FileType.JSON
        if mime_type in {"application/xml", "text/xml"}:
            return FileType.XML
        if mime_type in {"text/csv"}:
            return FileType.CSV
        if mime_type in EXTRACTABLE_DOCUMENT_TYPES:
            if "pdf" in mime_type:
                return FileType.PDF
            if "word" in mime_type:
                return FileType.DOCX
            if "spreadsheet" in mime_type or "excel" in mime_type:
                return FileType.SPREADSHEET

    return FileType.BINARY


def _get_default_tokenizer() -> Callable[[str], int]:
    """Get default tokenizer (tiktoken cl100k_base with fallback)."""
    try:
        encoding = tiktoken.get_encoding("cl100k_base")
        return lambda text: len(encoding.encode(text))
    except Exception:
        return lambda text: len(text) // 4


def _apply_token_limit(
    result: FileExtractionResult, tokenizer: Callable[[str], int], max_tokens: int
) -> FileExtractionResult:
    """Apply token-based truncation if content exceeds max_tokens."""
    if not isinstance(result.content, str) or not result.success:
        return result

    token_count = tokenizer(result.content)

    if token_count <= max_tokens:
        if result.truncation_info:
            result.truncation_info.tokens_shown = token_count
            result.truncation_info.total_tokens = token_count
        return result

    encoding = tiktoken.get_encoding("cl100k_base")
    tokens = encoding.encode(result.content)
    truncated_tokens = tokens[:max_tokens]
    truncated_content = encoding.decode(truncated_tokens)

    result.content = truncated_content + "\n\n[... truncated due to token limit ...]"

    if not result.truncation_info:
        result.truncation_info = TruncationInfo()

    result.truncation_info.tokens_shown = max_tokens
    result.truncation_info.total_tokens = token_count
    result.truncation_info.total_output_limit_reached = True

    return result


def read_file(
    file_path: Path | str,
    tokenizer: Callable[[str], int] | None = None,
    config: ContextConfig | None = None,
    **kwargs,
) -> FileExtractionResult:
    """Read and process file based on detected type.

    Args:
        file_path: Path to file to process
        tokenizer: Optional tokenizer function (str -> int). Default: tiktoken cl100k_base
        config: Optional context config. Default: loaded from config.yaml
        **kwargs: Additional processor-specific arguments

    Returns:
        FileExtractionResult with processed content
    """
    if isinstance(file_path, str):
        file_path = Path(file_path)

    if not file_path.exists():
        return FileExtractionResult(
            content=None, success=False, error_message=f"File not found: {file_path}"
        )

    if config is None:
        config = load_context_config()

    if tokenizer is None:
        tokenizer = _get_default_tokenizer()

    file_type = _detect_file_type(file_path)

    match file_type:
        case FileType.CODE:
            result = process_code(
                file_path, config=config, tokenizer=tokenizer, **kwargs
            )
        case FileType.MARKDOWN:
            result = process_text(
                file_path,
                config=config,
                tokenizer=tokenizer,
                file_type=FileType.MARKDOWN,
                **kwargs,
            )
        case FileType.TEXT:
            result = process_text(
                file_path,
                config=config,
                tokenizer=tokenizer,
                file_type=FileType.TEXT,
                **kwargs,
            )
        case FileType.JSON:
            result = process_json(
                file_path, config=config, tokenizer=tokenizer, **kwargs
            )
        case FileType.YAML:
            result = process_yaml(
                file_path, config=config, tokenizer=tokenizer, **kwargs
            )
        case FileType.XML:
            result = process_xml(
                file_path, config=config, tokenizer=tokenizer, **kwargs
            )
        case FileType.CSV:
            result = process_csv(
                file_path, config=config, tokenizer=tokenizer, **kwargs
            )
        case FileType.PDF | FileType.DOCX | FileType.PPTX:
            result = process_document(
                file_path,
                file_type=file_type,
                config=config,
                tokenizer=tokenizer,
                **kwargs,
            )
        case FileType.SPREADSHEET:
            result = process_spreadsheet(
                file_path, config=config, tokenizer=tokenizer, **kwargs
            )
        case FileType.IMAGE:
            result = process_image(file_path, config=config, **kwargs)
        case FileType.AUDIO:
            result = FileExtractionResult(
                content=None,
                success=False,
                error_message="Audio processing not yet implemented",
                file_type=file_type,
            )
        case FileType.ARCHIVE:
            result = FileExtractionResult(
                content=None,
                success=False,
                error_message="Archive processing not yet implemented",
                file_type=file_type,
            )
        case FileType.BINARY:
            result = FileExtractionResult(
                content=None,
                success=False,
                error_message="Binary file metadata processing not yet implemented",
                file_type=file_type,
            )
        case _:
            result = FileExtractionResult(
                content=None,
                success=False,
                error_message=f"Unknown file type: {file_type}",
                file_type=file_type,
            )

    result = _apply_token_limit(result, tokenizer, config.max_tokens_per_file)

    return result


def read_file_as_string(
    file_path: Path | str, config: ContextConfig | None = None, **kwargs
) -> str:
    """Convenience wrapper that returns content string or error message."""
    result = read_file(file_path, config=config, **kwargs)
    if result.success and isinstance(result.content, str):
        return result.content
    return f"[Error reading {file_path}: {result.error_message}]"
