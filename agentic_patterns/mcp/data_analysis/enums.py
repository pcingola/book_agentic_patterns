"""Enumerations for the data analysis MCP server."""

from enum import Enum
from pathlib import Path


class DisplayFormat(str, Enum):
    """Display formats for dataframes."""

    CSV = "csv"
    MARKDOWN = "markdown"


class FileFormat(str, Enum):
    """File formats supported for data loading and saving."""

    CSV = "csv"
    PICKLE = "pickle"

    @classmethod
    def from_path(cls, path: Path) -> "FileFormat":
        """Get FileFormat from a file path."""
        suffix = path.suffix.lower().lstrip(".")
        if suffix == "csv":
            return cls.CSV
        if suffix in ("pkl", "pickle"):
            return cls.PICKLE
        raise ValueError(f"Unsupported file format: {suffix}")
