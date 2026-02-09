"""Enumerations for data visualization."""

from enum import Enum
from pathlib import Path


class ImageFormat(str, Enum):
    """Supported image output formats."""

    PNG = "png"
    SVG = "svg"

    @classmethod
    def from_path(cls, path: Path) -> "ImageFormat":
        """Get ImageFormat from a file path."""
        suffix = path.suffix.lower().lstrip(".")
        match suffix:
            case "png":
                return cls.PNG
            case "svg":
                return cls.SVG
            case _:
                raise ValueError(f"Unsupported image format: {suffix}")
