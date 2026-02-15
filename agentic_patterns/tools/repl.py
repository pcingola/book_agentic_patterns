"""PydanticAI agent tools for REPL notebook -- wraps core/repl/."""

from pathlib import PurePosixPath

from pydantic_ai import ModelRetry

from agentic_patterns.core.config.config import SANDBOX_PREFIX
from agentic_patterns.core.context.decorators import context_result
from agentic_patterns.core.repl.config import DEFAULT_CELL_TIMEOUT
from agentic_patterns.core.repl.notebook import Notebook
from agentic_patterns.core.tools.permissions import ToolPermission, tool_permission
from agentic_patterns.core.user_session import get_session_id, get_user_id
from agentic_patterns.core.workspace import workspace_to_host_path


def _load_notebook() -> Notebook:
    """Load notebook for the current user/session."""
    return Notebook.load(get_user_id(), get_session_id())


def get_all_tools() -> list:
    """Get all REPL tools for use with PydanticAI agents."""

    @tool_permission(ToolPermission.WRITE)
    @context_result(save=False)
    async def repl_clear_notebook() -> str:
        """Clear all cells and reset the notebook namespace."""
        nb = _load_notebook()
        nb.clear()
        return "Notebook cleared."

    @tool_permission(ToolPermission.WRITE)
    async def repl_delete_cell(cell_number: int) -> str:
        """Delete a cell by number (0-based)."""
        try:
            nb = _load_notebook()
            nb.delete_cell(cell_number)
            return f"Cell {cell_number} deleted."
        except (ValueError, IndexError) as e:
            raise ModelRetry(str(e)) from e

    @tool_permission(ToolPermission.WRITE)
    @context_result()
    async def repl_execute_cell(code: str, timeout: int = DEFAULT_CELL_TIMEOUT) -> str:
        """Add and execute a new Python cell. Returns cell output."""
        try:
            nb = _load_notebook()
            cell = await nb.add_cell(code, execute=True, timeout=timeout)
            return str(cell)
        except ValueError as e:
            raise ModelRetry(str(e)) from e

    @tool_permission(ToolPermission.WRITE)
    @context_result()
    async def repl_create_notebook(name: str) -> str:
        """Create a Jupyter notebook (.ipynb) from the current REPL session.

        The notebook is saved to /workspace/<name>.ipynb and can be downloaded
        and opened in VS Code or JupyterLab.
        """
        nb = _load_notebook()
        if not nb.cells:
            raise ModelRetry("No cells in the notebook. Execute some cells first.")
        if not name.endswith(".ipynb"):
            name = f"{name}.ipynb"
        sandbox_path = PurePosixPath(SANDBOX_PREFIX) / name
        host_path = workspace_to_host_path(sandbox_path)
        nb.save_as_ipynb(host_path)
        return f"Notebook created at {sandbox_path}"

    @tool_permission(ToolPermission.WRITE)
    @context_result()
    async def repl_export_ipynb(path: str) -> str:
        """Export the notebook to a .ipynb file at the given workspace path."""
        try:
            nb = _load_notebook()
            host_path = workspace_to_host_path(PurePosixPath(path))
            nb.save_as_ipynb(host_path)
            return f"Notebook exported to {path}"
        except ValueError as e:
            raise ModelRetry(str(e)) from e

    @tool_permission(ToolPermission.WRITE)
    @context_result()
    async def repl_rerun_cell(
        cell_number: int, timeout: int = DEFAULT_CELL_TIMEOUT
    ) -> str:
        """Re-execute an existing cell by number (0-based)."""
        try:
            nb = _load_notebook()
            cell = await nb.execute_cell(cell_number, timeout=timeout)
            return str(cell)
        except (ValueError, IndexError) as e:
            raise ModelRetry(str(e)) from e

    @tool_permission(ToolPermission.READ)
    async def repl_show_cell(cell_number: int) -> str:
        """Show a single cell by number (0-based)."""
        try:
            nb = _load_notebook()
            return str(nb[cell_number])
        except (ValueError, IndexError) as e:
            raise ModelRetry(str(e)) from e

    @tool_permission(ToolPermission.READ)
    @context_result(save=False)
    async def repl_show_notebook() -> str:
        """Show all cells in the notebook."""
        nb = _load_notebook()
        return str(nb)

    return [
        repl_clear_notebook,
        repl_create_notebook,
        repl_delete_cell,
        repl_execute_cell,
        repl_export_ipynb,
        repl_rerun_cell,
        repl_show_cell,
        repl_show_notebook,
    ]
