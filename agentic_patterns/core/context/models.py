"""Data models for context management."""

from dataclasses import dataclass
from enum import Enum


class FileType(str, Enum):
    ARCHIVE = "archive"
    AUDIO = "audio"
    BINARY = "binary"
    CODE = "code"
    CSV = "csv"
    DOCX = "docx"
    IMAGE = "image"
    JSON = "json"
    MARKDOWN = "markdown"
    PDF = "pdf"
    PPTX = "pptx"
    SPREADSHEET = "xlsx"
    TEXT = "text"
    XML = "xml"
    YAML = "yaml"


@dataclass
class TruncationInfo:
    lines_shown: str | None = None
    columns_shown: str | None = None
    rows_shown: str | None = None
    cells_truncated: int = 0
    tokens_shown: int | None = None
    total_tokens: int | None = None
    total_output_limit_reached: bool = False


@dataclass
class FileMetadata:
    size_bytes: int
    modified_time: str | None = None
    mime_type: str | None = None
    encoding: str | None = None


@dataclass
class BinaryContent:
    data: bytes
    mime_type: str


@dataclass
class FileExtractionResult:
    content: str | BinaryContent | None
    success: bool
    error_message: str | None = None
    was_extracted: bool = False
    file_type: FileType | None = None
    truncation_info: TruncationInfo | None = None
    metadata: FileMetadata | None = None
