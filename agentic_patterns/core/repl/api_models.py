"""Pydantic models for the Notebook API."""

from typing import Any

from pydantic import BaseModel, Field

from agentic_patterns.core.repl.cell import Cell
from agentic_patterns.core.repl.cell_output import CellOutput
from agentic_patterns.core.repl.enums import CellState, OutputType
from agentic_patterns.core.repl.image import Image, ImageReference
from agentic_patterns.core.repl.notebook import Notebook


class ResourceLink(BaseModel):
    """Model for resource links."""

    uri: str
    mime_type: str
    description: str | None = None


class CellInfo(BaseModel):
    """Model for cell information."""

    cell_number: int | None = None
    cell_id: str
    code: str
    state: CellState
    execution_time: float | None = None
    outputs: list[CellOutput] = Field(default_factory=list)
    resources: list[ResourceLink] = Field(default_factory=list)

    @classmethod
    def from_cell(cls, cell: Cell, include_outputs: bool = True) -> "CellInfo":
        resources = []
        processed_outputs = []

        if include_outputs and cell.outputs:
            for i, output in enumerate(cell.outputs):
                processed_output = CellOutput(output_type=output.output_type, content=output.content)
                if output.output_type == OutputType.IMAGE and isinstance(output.content, Image):
                    image = output.content
                    resource_uri = f"notebook://cell/{cell.cell_number}/image/{i}"
                    resources.append(ResourceLink(uri=resource_uri, mime_type=f"image/{image.format}", description=f"Image output {i + 1} from cell {cell.cell_number}"))
                    processed_output.content = ImageReference.from_image(image, resource_uri)
                processed_outputs.append(processed_output)

        return cls(
            cell_id=cell.id,
            code=cell.code,
            state=cell.state,
            cell_number=cell.cell_number,
            execution_time=cell.execution_time,
            outputs=processed_outputs if include_outputs else [],
            resources=resources,
        )


class NotebookInfo(BaseModel):
    """Model for notebook information."""

    user_id: str
    session_id: str
    cell_count: int

    @classmethod
    def from_notebook(cls, notebook: Notebook) -> "NotebookInfo":
        return cls(user_id=notebook.user_id, session_id=notebook.session_id, cell_count=len(notebook.cells))


class OperationResult(BaseModel):
    """Model for operation results."""

    success: bool
    message: str
    data: dict[str, Any] | None = None
