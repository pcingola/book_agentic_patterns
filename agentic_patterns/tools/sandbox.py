"""PydanticAI agent tools for Docker sandbox -- wraps core/sandbox/."""

import asyncio

from agentic_patterns.core.context.decorators import context_result
from agentic_patterns.core.sandbox.config import SANDBOX_COMMAND_TIMEOUT
from agentic_patterns.core.sandbox.manager import SandboxManager
from agentic_patterns.core.tools.permissions import ToolPermission, tool_permission
from agentic_patterns.core.user_session import get_session_id, get_user_id


def get_all_tools() -> list:
    """Get all sandbox tools for use with PydanticAI agents."""

    manager = SandboxManager()

    @tool_permission(ToolPermission.WRITE)
    @context_result()
    async def sandbox_execute(
        command: str, timeout: int = SANDBOX_COMMAND_TIMEOUT
    ) -> str:
        """Execute a shell command in the Docker sandbox. Returns exit code and output."""
        exit_code, output = await asyncio.to_thread(
            manager.execute_command, get_user_id(), get_session_id(), command, timeout
        )
        header = f"Exit code: {exit_code}\n"
        return header + output

    return [sandbox_execute]
