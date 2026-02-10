"""MCP Sandbox server tools -- thin wrapper delegating to core/sandbox/."""

import asyncio

from docker.errors import DockerException, NotFound
from fastmcp import Context, FastMCP

from agentic_patterns.core.context.decorators import context_result
from agentic_patterns.core.mcp import ToolFatalError
from agentic_patterns.core.sandbox.config import SANDBOX_COMMAND_TIMEOUT
from agentic_patterns.core.sandbox.manager import SandboxManager
from agentic_patterns.core.tools.permissions import ToolPermission, tool_permission
from agentic_patterns.core.user_session import get_session_id, get_user_id

_manager = SandboxManager()


def register_tools(mcp: FastMCP) -> None:
    """Register all sandbox tools on the given MCP server instance."""

    @mcp.tool()
    @tool_permission(ToolPermission.WRITE)
    @context_result()
    async def execute(
        command: str, timeout: int = SANDBOX_COMMAND_TIMEOUT, ctx: Context = None
    ) -> str:
        """Execute a shell command in the Docker sandbox. Returns exit code and output.

        Args:
            command: Shell command to execute.
            timeout: Execution timeout in seconds.
        """
        try:
            exit_code, output = await asyncio.to_thread(
                _manager.execute_command,
                get_user_id(),
                get_session_id(),
                command,
                timeout,
            )
        except NotFound as e:
            raise ToolFatalError(str(e)) from e
        except DockerException as e:
            raise ToolFatalError(str(e)) from e
        await ctx.info(f"execute: exit_code={exit_code}")
        header = f"Exit code: {exit_code}\n"
        return header + output
