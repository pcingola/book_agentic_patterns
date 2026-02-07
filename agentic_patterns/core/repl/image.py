import base64
import io
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
from PIL import Image as PILImage
from pydantic import BaseModel, Field


class ImageBase(BaseModel, ABC):
    """Base class for image-related models with shared metadata."""

    format: str = "png"
    width: int | None = None
    height: int | None = None
    source: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    def _get_dimensions_str(self) -> str:
        if self.width and self.height:
            return f" {self.width}x{self.height}"
        return ""

    def _get_source_str(self) -> str:
        return f" from {self.source}" if self.source else ""

    @abstractmethod
    def __str__(self) -> str:
        pass

    @abstractmethod
    def serialize(self) -> dict:
        pass


class Image(ImageBase):
    """Model for image data in cell outputs."""

    data: bytes

    def __str__(self) -> str:
        dimensions = self._get_dimensions_str()
        source_info = self._get_source_str()
        return f"Image[{self.format}{dimensions}{source_info}]"

    def get_data_base64(self) -> str:
        return base64.b64encode(self.data).decode()

    def save_to_file(self, path: str | Path, format: str | None = None) -> None:
        if isinstance(path, str):
            path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        if format and format.lower() != self.format.lower():
            img = PILImage.open(io.BytesIO(self.data))
            img.save(path, format=format.upper())
        else:
            with open(path, "wb") as f:
                f.write(self.data)

    def serialize(self) -> dict:
        return {
            "data": self.get_data_base64(),
            "format": self.format,
            "width": self.width,
            "height": self.height,
            "source": self.source,
            "metadata": self.metadata,
        }

    @classmethod
    def unserialize(cls, data: dict) -> "Image":
        binary_data = base64.b64decode(data["data"])
        return cls(
            data=binary_data,
            format=data["format"],
            width=data.get("width"),
            height=data.get("height"),
            source=data.get("source"),
            metadata=data.get("metadata", {}),
        )

    def show(self) -> None:
        img = PILImage.open(io.BytesIO(self.data))
        plt.figure(figsize=(10, 6))
        plt.imshow(img)
        plt.axis("off")
        plt.show()

    @classmethod
    def from_matplotlib_figure(cls, fig: plt.Figure) -> "Image":
        fig_width, fig_height = fig.get_size_inches()
        fig_dpi = fig.dpi
        img_data = io.BytesIO()
        fig.savefig(img_data, format="png")
        img_data.seek(0)
        binary_data = img_data.read()
        return cls(
            data=binary_data,
            format="png",
            width=int(fig_width * fig_dpi),
            height=int(fig_height * fig_dpi),
            source="matplotlib",
            metadata={"dpi": int(fig_dpi)},
        )


class ImageReference(ImageBase):
    """Model for image reference with resource URI instead of binary data."""

    resource_uri: str

    def __str__(self) -> str:
        dimensions = self._get_dimensions_str()
        source_info = self._get_source_str()
        return f"ImageRef[{self.format}{dimensions}{source_info}] -> {self.resource_uri}"

    @classmethod
    def from_image(cls, image: Image, resource_uri: str) -> "ImageReference":
        return cls(
            resource_uri=resource_uri,
            format=image.format,
            width=image.width,
            height=image.height,
            source=image.source,
            metadata=image.metadata,
        )

    def serialize(self) -> dict:
        return {
            "resource_uri": self.resource_uri,
            "format": self.format,
            "width": self.width,
            "height": self.height,
            "source": self.source,
            "metadata": self.metadata,
        }

    @classmethod
    def unserialize(cls, data: dict) -> "ImageReference":
        return cls(
            resource_uri=data["resource_uri"],
            format=data["format"],
            width=data.get("width"),
            height=data.get("height"),
            source=data.get("source"),
            metadata=data.get("metadata", {}),
        )
