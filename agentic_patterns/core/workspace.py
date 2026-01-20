"""Workspace management for agent file operations with user/session isolation.

Provides sandbox path translation between agent-visible paths (/workspace/...) and
host filesystem paths. Each user/session gets an isolated directory.

Server frameworks (FastAPI, FastMCP) provide request context. When ctx=None,
defaults are used for development/testing.
"""

import asyncio
from pathlib import Path, PurePosixPath
from typing import Any

from agentic_patterns.core.config.config import DEFAULT_SESSION_ID, DEFAULT_USER_ID, SANDBOX_PREFIX, WORKSPACE_DIR


class WorkspaceError(Exception):
    """Raised for user-correctable workspace errors (invalid paths, missing files, etc.)."""
    pass


def get_session_id_from_request(ctx: Any = None) -> str:
    """Extract session_id from request context or return default."""
    if ctx is None:
        return DEFAULT_SESSION_ID
    if hasattr(ctx, "session_id"):
        return ctx.session_id
    if isinstance(ctx, dict):
        return ctx.get("session_id", DEFAULT_SESSION_ID)
    return DEFAULT_SESSION_ID


def get_user_id_from_request(ctx: Any = None) -> str:
    """Extract user_id from request context or return default."""
    if ctx is None:
        return DEFAULT_USER_ID
    if hasattr(ctx, "user_id"):
        return ctx.user_id
    if isinstance(ctx, dict):
        return ctx.get("user_id", DEFAULT_USER_ID)
    return DEFAULT_USER_ID


def _get_host_root(ctx: Any) -> Path:
    """Get the host root directory for the current user/session. Does not create directories."""
    user_id = get_user_id_from_request(ctx)
    session_id = get_session_id_from_request(ctx)
    return WORKSPACE_DIR / user_id / session_id


def container_to_host_path(sandbox_path: PurePosixPath, ctx: Any = None) -> Path:
    """Convert a sandbox path (/workspace/...) to a host filesystem path."""
    path_str = str(sandbox_path)
    if not path_str.startswith(SANDBOX_PREFIX):
        raise WorkspaceError(f"Invalid sandbox path: must start with {SANDBOX_PREFIX}")

    relative = sandbox_path.relative_to(SANDBOX_PREFIX)
    host_root = _get_host_root(ctx)
    host_path = host_root / relative

    try:
        host_path.resolve().relative_to(host_root.resolve())
    except ValueError:
        raise WorkspaceError("Path traversal not allowed")

    return host_path


def host_to_container_path(host_path: Path) -> str:
    """Convert a host filesystem path to a sandbox path (/workspace/...)."""
    try:
        relative = host_path.resolve().relative_to(WORKSPACE_DIR.resolve())
        parts = relative.parts
        if len(parts) < 2:
            raise WorkspaceError(f"Invalid workspace path structure: {host_path}")
        # Skip user_id and session_id parts
        actual_relative = Path(*parts[2:]) if len(parts) > 2 else Path(".")
        result = f"{SANDBOX_PREFIX}/{actual_relative.as_posix()}"
        return result.rstrip("/.")
    except ValueError:
        raise WorkspaceError(f"Path {host_path} is outside workspace")


def list_workspace_files(pattern: str, ctx: Any = None) -> list[str]:
    """List files in workspace matching pattern, returns sandbox paths."""
    host_root = _get_host_root(ctx)
    if not host_root.exists():
        return []
    return [host_to_container_path(p) for p in host_root.rglob(pattern) if p.is_file()]


def read_from_workspace(sandbox_path: str, ctx: Any = None) -> str:
    """Read text content from workspace."""
    host_path = container_to_host_path(PurePosixPath(sandbox_path), ctx)
    if not host_path.exists():
        raise WorkspaceError(f"File not found: {sandbox_path}")
    return host_path.read_text()


async def read_from_workspace_async(sandbox_path: str, ctx: Any = None) -> str:
    """Async read text content from workspace."""
    return await asyncio.to_thread(read_from_workspace, sandbox_path, ctx)


def write_to_workspace(sandbox_path: str, content: str | bytes, ctx: Any = None) -> str:
    """Write content to workspace, returns sandbox path."""
    host_path = container_to_host_path(PurePosixPath(sandbox_path), ctx)
    host_path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(content, bytes):
        host_path.write_bytes(content)
    else:
        host_path.write_text(content)
    return sandbox_path


async def write_to_workspace_async(sandbox_path: str, content: str | bytes, ctx: Any = None) -> str:
    """Async write content to workspace, returns sandbox path."""
    return await asyncio.to_thread(write_to_workspace, sandbox_path, content, ctx)


def store_result(content: str | bytes, content_type: str, ctx: Any = None) -> str:
    """Store content in workspace and return sandbox path.

    Args:
        content: Content to store (string or bytes)
        content_type: Type hint for file extension (e.g., "json", "csv", "txt")
        ctx: Request context for user/session isolation

    Returns:
        Sandbox path where content was stored (e.g., /workspace/results/result_abc123.json)
    """
    from uuid import uuid4

    extensions = {"json": ".json", "csv": ".csv", "txt": ".txt", "md": ".md", "xml": ".xml", "yaml": ".yaml"}
    ext = extensions.get(content_type.lower(), ".txt")
    filename = f"result_{uuid4().hex[:8]}{ext}"
    path = f"/workspace/results/{filename}"
    write_to_workspace(path, content, ctx)
    return path


async def store_result_async(content: str | bytes, content_type: str, ctx: Any = None) -> str:
    """Async store content in workspace and return sandbox path."""
    return await asyncio.to_thread(store_result, content, content_type, ctx)
