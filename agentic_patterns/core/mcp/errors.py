"""MCP error classification: retryable vs fatal tool errors."""

from fastmcp.exceptions import ToolError


FATAL_PREFIX = "[FATAL] "


class ToolRetryError(ToolError):
    """Retryable: the LLM picked bad arguments, let it try again."""

    pass


class ToolFatalError(ToolError):
    """Fatal: infrastructure failure, abort the agent run."""

    def __init__(self, message: str):
        super().__init__(f"{FATAL_PREFIX}{message}")
