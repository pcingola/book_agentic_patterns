"""Format conversion enums."""

from enum import Enum


class InputFormat(str, Enum):
    CSV = "csv"
    DOCX = "docx"
    MD = "md"
    PDF = "pdf"
    PPTX = "pptx"
    XLSX = "xlsx"


class OutputFormat(str, Enum):
    CSV = "csv"
    DOCX = "docx"
    HTML = "html"
    MD = "md"
    PDF = "pdf"
