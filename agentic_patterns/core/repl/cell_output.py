from datetime import datetime

import matplotlib.pyplot as plt
from pydantic import BaseModel, Field

from agentic_patterns.core.repl.enums import OutputType
from agentic_patterns.core.repl.image import Image, ImageReference


class CellOutput(BaseModel):
    """Model for cell execution output."""

    output_type: OutputType
    content: str | Image | ImageReference
    timestamp: datetime | None = Field(default_factory=datetime.now)

    def __str__(self) -> str:
        time_str = self.timestamp.strftime("%H:%M:%S")
        if self.output_type == OutputType.IMAGE:
            if isinstance(self.content, Image | ImageReference):
                content_preview = str(self.content)
            else:
                content_preview = "[Base64 encoded image]"
        elif isinstance(self.content, str):
            content_preview = self.content.replace("\n", " ").strip()
            if len(content_preview) > 60:
                content_preview = content_preview[:57] + "..."
        else:
            content_preview = str(self.content)
        return f"{self.output_type.name} [{time_str}]: {content_preview}"

    def __repr__(self) -> str:
        return f"CellOutput(type={self.output_type.name}, timestamp={self.timestamp.isoformat()})"

    def serialize(self) -> dict:
        result = {
            "output_type": self.output_type.value,
            "timestamp": self.timestamp.isoformat(),
        }
        if self.output_type == OutputType.IMAGE and isinstance(self.content, Image | ImageReference):
            if isinstance(self.content, Image):
                result["content_type"] = "image"
            else:
                result["content_type"] = "image_reference"
            result["content"] = self.content.serialize()
        else:
            result["content_type"] = "text"
            result["content"] = self.content
        return result

    @classmethod
    def unserialize(cls, data: dict) -> "CellOutput":
        if data.get("content_type") == "image":
            content = Image.unserialize(data["content"])
        elif data.get("content_type") == "image_reference":
            content = ImageReference.unserialize(data["content"])
        else:
            content = data["content"]
        return cls(
            output_type=OutputType(data["output_type"]),
            content=content,
            timestamp=datetime.fromisoformat(data["timestamp"]),
        )

    @classmethod
    def from_image(cls, image: Image) -> "CellOutput":
        return cls(output_type=OutputType.IMAGE, content=image)

    @classmethod
    def from_matplotlib_figure(cls, fig: plt.Figure) -> "CellOutput":
        image = Image.from_matplotlib_figure(fig)
        return cls.from_image(image)

    def show(self) -> None:
        if self.output_type == OutputType.IMAGE and isinstance(self.content, Image):
            self.content.show()
        elif self.output_type == OutputType.IMAGE and isinstance(self.content, ImageReference):
            print(f"Image Reference: {self.content}")
            print("Use get_cell_image tool to fetch the actual image data")
        else:
            print(self.content)

    def to_ipynb(self) -> dict | None:
        """Convert the cell output to Jupyter notebook output format."""
        match self.output_type:
            case OutputType.TEXT:
                return {"output_type": "stream", "name": "stdout", "text": str(self.content).split("\n")}
            case OutputType.ERROR:
                return {"output_type": "error", "ename": "Error", "evalue": str(self.content), "traceback": str(self.content).split("\n")}
            case OutputType.HTML:
                return {"output_type": "display_data", "data": {"text/html": self.content}, "metadata": {}}
            case OutputType.IMAGE if isinstance(self.content, Image):
                mime_type = f"image/{self.content.format}"
                return {"output_type": "display_data", "data": {mime_type: self.content.get_data_base64()}, "metadata": {mime_type: {"width": self.content.width, "height": self.content.height}}}
            case OutputType.IMAGE if isinstance(self.content, ImageReference):
                return {"output_type": "display_data", "data": {"text/plain": f"Image Reference: {self.content.resource_uri}"}, "metadata": {}}
            case OutputType.DATAFRAME:
                return {"output_type": "display_data", "data": {"text/html": self.content}, "metadata": {}}
            case _:
                return None
