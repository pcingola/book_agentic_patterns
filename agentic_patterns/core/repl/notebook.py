"""Notebook model: collection of cells with shared namespace and persistence."""

import ast
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from agentic_patterns.core.repl.cell import Cell
from agentic_patterns.core.repl.cell_utils import (
    cleanup_temp_workbooks,
    extract_function_definitions,
)
from agentic_patterns.core.repl.sandbox import (
    delete_cell_pkl_files,
    delete_repl_dir,
    get_repl_data_dir,
)
from agentic_patterns.core.repl.config import (
    DEFAULT_CELL_TIMEOUT,
    MAX_CELLS,
)
from agentic_patterns.core.repl.enums import CellState

logger = logging.getLogger(__name__)


class Notebook(BaseModel):
    """Model representing a Jupyter-like notebook."""

    user_id: str
    session_id: str
    cells: list[Cell] = Field(default_factory=list)
    execution_count: int = 0
    namespace: dict[str, Any] = Field(default_factory=dict)
    import_statements: list[str] = Field(default_factory=list)
    function_definitions: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

    @staticmethod
    def _get_session_notebook_dir(user_id: str, session_id: str) -> Path:
        """Get the path to the REPL data directory for a user/session."""
        return get_repl_data_dir(user_id, session_id)

    @classmethod
    def _get_notebook_path(cls, user_id: str, session_id: str) -> Path:
        return cls._get_session_notebook_dir(user_id, session_id) / "cells.json"

    async def add_cell(
        self,
        code: str,
        execute: bool = True,
        number: int | None = None,
        timeout: int = DEFAULT_CELL_TIMEOUT,
    ) -> Cell:
        """Add a new cell to the notebook and optionally execute it."""
        logger.debug("Adding new cell to notebook %s", self.session_id)
        if len(self.cells) >= MAX_CELLS:
            raise ValueError(f"Maximum number of cells ({MAX_CELLS}) reached")

        cell = Cell(code=code)

        if number is None or number >= len(self.cells):
            cell.cell_number = len(self.cells)
            self.cells.append(cell)
        else:
            number = max(number, 0)
            self.cells.insert(number, cell)
            self._renumber_cells()

        if execute:
            await self.execute_cell(cell.id, timeout=timeout)

        self.save()
        return cell

    def clear(self) -> None:
        """Clear all cells and reset the namespace."""
        self.cells = []
        self.namespace = {}
        self.execution_count = 0
        cleanup_temp_workbooks(self.user_id, self.session_id)
        delete_repl_dir(self.user_id, self.session_id)
        self.save()

    def delete_cell(self, cell_id_or_number: str | int) -> None:
        """Delete a cell by ID or number (0-based)."""
        if isinstance(cell_id_or_number, int):
            if cell_id_or_number < 0 or cell_id_or_number >= len(self.cells):
                raise ValueError(
                    f"Cell number {cell_id_or_number} out of range (0-{len(self.cells) - 1})"
                )
            cell_id = self.cells[cell_id_or_number].id
            del self.cells[cell_id_or_number]
        else:
            cell_id = None
            for i, cell in enumerate(self.cells):
                if cell.id == cell_id_or_number:
                    cell_id = cell.id
                    del self.cells[i]
                    break
            else:
                raise ValueError(f"Cell with ID {cell_id_or_number} not found")
        if cell_id:
            delete_cell_pkl_files(self.user_id, self.session_id, cell_id)
        self._renumber_cells()
        self.save()

    async def execute_cell(
        self, cell_id_or_number: str | int, timeout: int = DEFAULT_CELL_TIMEOUT
    ) -> Cell:
        """Execute a cell by ID or number (0-based)."""
        logger.debug(
            "Executing cell %s in notebook %s", cell_id_or_number, self.session_id
        )
        cell = self[cell_id_or_number]

        self.execution_count += 1
        if cell.execution_count is None:
            cell.execution_count = self.execution_count

        await cell.execute(
            self.namespace,
            timeout,
            self.import_statements,
            self.function_definitions,
            self.user_id,
            self.session_id,
        )

        if cell.state == CellState.COMPLETED:
            try:
                tree = ast.parse(cell.code)
                for node in ast.walk(tree):
                    if isinstance(node, ast.Import):
                        for name in node.names:
                            import_stmt = f"import {name.name}"
                            if name.asname:
                                import_stmt += f" as {name.asname}"
                            if import_stmt not in self.import_statements:
                                self.import_statements.append(import_stmt)
                    elif isinstance(node, ast.ImportFrom) and node.module:
                        names_str = ", ".join(
                            name.name + (f" as {name.asname}" if name.asname else "")
                            for name in node.names
                        )
                        import_stmt = f"from {node.module} import {names_str}"
                        if import_stmt not in self.import_statements:
                            self.import_statements.append(import_stmt)
            except SyntaxError:
                pass

            new_function_defs = extract_function_definitions(cell.code)
            for func_def in new_function_defs:
                if func_def not in self.function_definitions:
                    self.function_definitions.append(func_def)

        self.save()
        return cell

    @property
    def id(self) -> str:
        return f"{self.user_id}:{self.session_id}"

    @classmethod
    def load(cls, user_id: str, session_id: str) -> "Notebook":
        """Load a notebook from disk, or create a new one if it doesn't exist."""
        notebook_path = cls._get_notebook_path(user_id, session_id)

        if not notebook_path.exists():
            logger.debug("Creating new notebook at %s", notebook_path)
            notebook = cls(user_id=user_id, session_id=session_id)
            notebook.save()
            return notebook

        logger.debug("Loading notebook from %s", notebook_path)
        with open(notebook_path) as f:
            data = json.load(f)

        notebook = cls(
            user_id=data["user_id"],
            session_id=data["session_id"],
            execution_count=data["execution_count"],
            created_at=datetime.fromisoformat(data["created_at"]),
            updated_at=datetime.fromisoformat(data["updated_at"]),
        )
        for i, cell_data in enumerate(data["cells"]):
            cell = Cell.unserialize(cell_data)
            cell.cell_number = i
            notebook.cells.append(cell)

        return notebook

    def save(self) -> None:
        """Save the notebook to disk."""
        notebook_path = Notebook._get_notebook_path(self.user_id, self.session_id)
        notebook_path.parent.mkdir(parents=True, exist_ok=True)
        self.updated_at = datetime.now()

        data = {
            "user_id": self.user_id,
            "session_id": self.session_id,
            "execution_count": self.execution_count,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "cells": [cell.serialize() for cell in self.cells],
        }

        with open(notebook_path, "w") as f:
            json.dump(data, f, indent=2)

    def __getitem__(self, key: int | str) -> Cell:
        if isinstance(key, int):
            if key < 0 or key >= len(self.cells):
                raise IndexError(
                    f"Cell number {key} out of range (0-{len(self.cells) - 1})"
                )
            return self.cells[key]
        else:
            for cell in self.cells:
                if cell.id == key:
                    return cell
            raise ValueError(f"Cell with ID {key} not found")

    def _renumber_cells(self) -> None:
        for i, cell in enumerate(self.cells):
            cell.cell_number = i

    def __repr__(self) -> str:
        return f"Notebook(user_id={self.user_id}, session_id={self.session_id}, cells={len(self.cells)})"

    def __str__(self) -> str:
        created = self.created_at.strftime("%Y-%m-%d %H:%M:%S")
        updated = self.updated_at.strftime("%Y-%m-%d %H:%M:%S")

        result = [
            f"Notebook: {self.user_id}, {self.session_id}",
            f"  Number of cells: {len(self.cells)}",
            f"  Cells executions: {self.execution_count}",
            f"  Created: {created}",
            f"  Last updated: {updated}",
            "",
        ]

        if not self.cells:
            result.append("No cells")
        else:
            result.extend([f"{cell}\n" for cell in self.cells])

        return "\n".join(result)
