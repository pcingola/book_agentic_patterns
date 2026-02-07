"""Cell model: represents a single executable cell in a notebook."""

import asyncio
import logging
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from agentic_patterns.core.repl.cell_output import CellOutput
from agentic_patterns.core.repl.cell_utils import SubprocessResult
from agentic_patterns.core.repl.config import DEFAULT_CELL_TIMEOUT
from agentic_patterns.core.repl.enums import CellState, OutputType
from agentic_patterns.core.repl.image import Image

logger = logging.getLogger(__name__)


class Cell(BaseModel):
    """Model representing a notebook cell."""

    cell_number: int | None = None
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    code: str
    state: CellState = CellState.IDLE
    outputs: list[CellOutput] = Field(default_factory=list)
    execution_count: int | None = None
    created_at: datetime = Field(default_factory=datetime.now)
    executed_at: datetime | None = None
    execution_time: float | None = None

    async def execute(
        self,
        namespace: dict[str, Any],
        timeout: int = DEFAULT_CELL_TIMEOUT,
        import_statements: list[str] | None = None,
        function_definitions: list[str] | None = None,
        user_id: str | None = None,
        session_id: str | None = None,
    ) -> None:
        """Execute the cell code in the given namespace with timeout."""
        logger.debug("Starting async execution of cell %s", self.id)
        self.state = CellState.RUNNING
        self.executed_at = datetime.now()
        self.outputs = []

        if user_id is None or session_id is None:
            try:
                from agentic_patterns.core.user_session import get_session_id, get_user_id
                user_id = user_id or get_user_id()
                session_id = session_id or get_session_id()
            except Exception:
                user_id = user_id or "test_user"
                session_id = session_id or "test_session"
                logger.warning("Session context unavailable, falling back to defaults for cell %s", self.id)

        start_time = datetime.now()

        await asyncio.to_thread(
            self._execute_sync,
            namespace,
            timeout,
            import_statements or [],
            function_definitions or [],
            user_id,
            session_id,
        )

        self.execution_time = (datetime.now() - start_time).total_seconds()
        logger.debug("Cell %s execution completed in %.2f seconds", self.id, self.execution_time)

    def _execute_sync(
        self,
        namespace: dict[str, Any],
        timeout: int,
        import_statements: list[str],
        function_definitions: list[str],
        user_id: str,
        session_id: str,
    ) -> None:
        """Execute the cell synchronously via sandbox."""
        import types

        from agentic_patterns.core.config.config import WORKSPACE_DIR
        from agentic_patterns.core.repl.sandbox import execute_in_sandbox

        workspace_path: Path = WORKSPACE_DIR / user_id / session_id
        workspace_path.mkdir(parents=True, exist_ok=True)

        clean_namespace = {k: v for k, v in namespace.items() if not isinstance(v, types.ModuleType)}

        loop = asyncio.new_event_loop()
        try:
            result: SubprocessResult = loop.run_until_complete(
                execute_in_sandbox(
                    code=self.code,
                    namespace=clean_namespace,
                    import_statements=import_statements,
                    function_definitions=function_definitions,
                    timeout=timeout,
                    user_id=user_id,
                    session_id=session_id,
                    workspace_path=workspace_path,
                )
            )
        finally:
            loop.close()

        self.state = result.state
        self.outputs = result.outputs
        namespace.update(result.namespace)

    def save_outputs(self, output_dir: Path) -> list[Path]:
        """Save the cell's image outputs to the specified directory."""
        saved_resources = []
        output_dir.mkdir(parents=True, exist_ok=True)
        for i, output in enumerate(self.outputs):
            if output.output_type == OutputType.IMAGE and isinstance(output.content, Image):
                filename = f"cell_{self.id}_output_{i}.{output.content.format}"
                file_path = output_dir / filename
                output.content.save_to_file(file_path)
                saved_resources.append(file_path)
        return saved_resources

    def serialize(self) -> dict:
        result = {
            "id": self.id,
            "code": self.code,
            "state": self.state.value,
            "execution_count": self.execution_count,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "executed_at": self.executed_at.isoformat() if self.executed_at else None,
            "execution_time": self.execution_time,
            "number": self.cell_number,
        }
        if self.outputs:
            result["outputs"] = [output.serialize() for output in self.outputs]
        return result

    def to_ipynb(self) -> dict:
        """Convert the cell to Jupyter notebook cell format."""
        ipynb_cell = {
            "cell_type": "code",
            "execution_count": self.execution_count,
            "id": self.id,
            "metadata": {
                "mcp_repl": {
                    "cell_number": self.cell_number,
                    "state": self.state.value,
                    "created_at": self.created_at.isoformat() if self.created_at else None,
                    "executed_at": self.executed_at.isoformat() if self.executed_at else None,
                    "execution_time": self.execution_time,
                }
            },
            "source": self.code.split("\n"),
            "outputs": [],
        }
        for output in self.outputs:
            ipynb_output = output.to_ipynb()
            if ipynb_output:
                ipynb_cell["outputs"].append(ipynb_output)
        return ipynb_cell

    @classmethod
    def unserialize(cls, data: dict) -> "Cell":
        cell = cls(
            id=data["id"],
            code=data["code"],
            state=CellState(data["state"]),
            execution_count=data["execution_count"],
            created_at=datetime.fromisoformat(data["created_at"]) if data.get("created_at") else None,
            executed_at=datetime.fromisoformat(data["executed_at"]) if data.get("executed_at") else None,
            execution_time=data.get("execution_time"),
            cell_number=data.get("number"),
        )
        if "outputs" in data and data["outputs"]:
            cell.outputs = [CellOutput.unserialize(output_data) for output_data in data["outputs"]]
        return cell

    def __repr__(self) -> str:
        return f"Cell(id={self.id}, number={self.cell_number}, state={self.state.name}, execution_count={self.execution_count})"

    def __str__(self) -> str:
        exec_time = f"{self.execution_time:.2f}s" if self.execution_time is not None else "N/A"
        result = [f"Cell[{self.cell_number or '-'}] {self.state.name}, {exec_time}"]

        prefix = "  | "
        result.append("Code:")
        for line in self.code.split("\n"):
            result.append(f"{prefix}{line}")

        if self.outputs:
            for i, output in enumerate(self.outputs):
                show_cell_number = f" {i + 1} / {len(self.outputs)}" if len(self.outputs) > 1 else ""
                if output.output_type == OutputType.IMAGE and isinstance(output.content, Image):
                    result.append(f"Output{show_cell_number}, type: {output.output_type.name}:")
                    result.append(f"{prefix}{str(output.content)}")
                else:
                    result.append(f"Output{show_cell_number}:")
                    content_lines = str(output.content).rstrip().split("\n")
                    for line in content_lines:
                        result.append(f"{prefix}{line}")
        else:
            result.append("\n--- No Outputs ---")

        return "\n".join(result)
