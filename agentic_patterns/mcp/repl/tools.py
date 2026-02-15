"""MCP REPL server tools -- thin wrapper delegating to core/repl/."""

from pathlib import PurePosixPath

from fastmcp import Context, FastMCP

from agentic_patterns.core.config.config import SANDBOX_PREFIX
from agentic_patterns.core.context.decorators import context_result
from agentic_patterns.core.mcp import ToolFatalError, ToolRetryError
from agentic_patterns.core.repl.config import DEFAULT_CELL_TIMEOUT
from agentic_patterns.core.repl.notebook import Notebook
from agentic_patterns.core.tools.permissions import ToolPermission, tool_permission
from agentic_patterns.core.user_session import get_session_id, get_user_id
from agentic_patterns.core.workspace import workspace_to_host_path


def _load_notebook() -> Notebook:
    """Load notebook for the current user/session."""
    return Notebook.load(get_user_id(), get_session_id())


def register_tools(mcp: FastMCP) -> None:
    """Register all REPL tools on the given MCP server instance."""

    @mcp.tool()
    @tool_permission(ToolPermission.WRITE)
    @context_result(save=False)
    async def clear_notebook(ctx: Context = None) -> str:
        """Clear all cells and reset the notebook namespace."""
        try:
            nb = _load_notebook()
            nb.clear()
        except ValueError as e:
            raise ToolRetryError(str(e)) from e
        await ctx.info("clear_notebook")
        return "Notebook cleared."

    @mcp.tool()
    @tool_permission(ToolPermission.WRITE)
    async def delete_cell(cell_number: int, ctx: Context = None) -> str:
        """Delete a cell by number (0-based).

        Args:
            cell_number: The 0-based cell index to delete.
        """
        try:
            nb = _load_notebook()
            nb.delete_cell(cell_number)
        except (ValueError, IndexError) as e:
            raise ToolRetryError(str(e)) from e
        await ctx.info(f"delete_cell: {cell_number}")
        return f"Cell {cell_number} deleted."

    @mcp.tool()
    @tool_permission(ToolPermission.WRITE)
    @context_result()
    async def execute_cell(
        code: str, timeout: int = DEFAULT_CELL_TIMEOUT, ctx: Context = None
    ) -> str:
        """Add and execute a new Python cell. Returns cell output.

        Args:
            code: Python code to execute.
            timeout: Execution timeout in seconds.
        """
        try:
            nb = _load_notebook()
            cell = await nb.add_cell(code, execute=True, timeout=timeout)
        except ValueError as e:
            raise ToolRetryError(str(e)) from e
        await ctx.info(f"execute_cell: cell_number={cell.cell_number}")
        return str(cell)

    @mcp.tool()
    @tool_permission(ToolPermission.WRITE)
    @context_result()
    async def create_notebook(name: str, ctx: Context = None) -> str:
        """Create a Jupyter notebook (.ipynb) from the current REPL session.

        The notebook is saved to /workspace/<name>.ipynb and can be downloaded
        and opened in VS Code or JupyterLab.

        Args:
            name: Notebook filename (e.g. 'analysis'). Extension .ipynb added automatically.
        """
        nb = _load_notebook()
        if not nb.cells:
            raise ToolRetryError("No cells in the notebook. Execute some cells first.")
        if not name.endswith(".ipynb"):
            name = f"{name}.ipynb"
        sandbox_path = PurePosixPath(SANDBOX_PREFIX) / name
        try:
            host_path = workspace_to_host_path(sandbox_path)
            nb.save_as_ipynb(host_path)
        except OSError as e:
            raise ToolFatalError(str(e)) from e
        await ctx.info(f"create_notebook: {sandbox_path}")
        return f"Notebook created at {sandbox_path}"

    @mcp.tool()
    @tool_permission(ToolPermission.WRITE)
    @context_result()
    async def export_ipynb(path: str, ctx: Context = None) -> str:
        """Export the notebook to a .ipynb file at the given workspace path.

        Args:
            path: Workspace path for the exported file (e.g. /workspace/notebook.ipynb).
        """
        try:
            nb = _load_notebook()
            host_path = workspace_to_host_path(PurePosixPath(path))
            nb.save_as_ipynb(host_path)
        except ValueError as e:
            raise ToolRetryError(str(e)) from e
        except OSError as e:
            raise ToolFatalError(str(e)) from e
        await ctx.info(f"export_ipynb: {path}")
        return f"Notebook exported to {path}"

    @mcp.tool()
    @tool_permission(ToolPermission.WRITE)
    @context_result()
    async def rerun_cell(
        cell_number: int, timeout: int = DEFAULT_CELL_TIMEOUT, ctx: Context = None
    ) -> str:
        """Re-execute an existing cell by number (0-based).

        Args:
            cell_number: The 0-based cell index to re-execute.
            timeout: Execution timeout in seconds.
        """
        try:
            nb = _load_notebook()
            cell = await nb.execute_cell(cell_number, timeout=timeout)
        except (ValueError, IndexError) as e:
            raise ToolRetryError(str(e)) from e
        await ctx.info(f"rerun_cell: cell_number={cell_number}")
        return str(cell)

    @mcp.tool()
    @tool_permission(ToolPermission.READ)
    async def show_cell(cell_number: int, ctx: Context = None) -> str:
        """Show a single cell by number (0-based).

        Args:
            cell_number: The 0-based cell index to show.
        """
        try:
            nb = _load_notebook()
            result = str(nb[cell_number])
        except (ValueError, IndexError) as e:
            raise ToolRetryError(str(e)) from e
        await ctx.info(f"show_cell: {cell_number}")
        return result

    @mcp.tool()
    @tool_permission(ToolPermission.READ)
    @context_result(save=False)
    async def show_notebook(ctx: Context = None) -> str:
        """Show all cells in the notebook."""
        try:
            nb = _load_notebook()
        except (ValueError, IndexError) as e:
            raise ToolRetryError(str(e)) from e
        await ctx.info("show_notebook")
        return str(nb)
