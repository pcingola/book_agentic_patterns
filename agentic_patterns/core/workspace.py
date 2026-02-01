"""Workspace management for agent file operations with user/session isolation.

Provides sandbox path translation between agent-visible paths (/workspace/...) and
host filesystem paths. Each user/session gets an isolated directory.

User/session identity comes from contextvars (see user_session.py).
When not set, defaults are used for development/testing.
"""

import asyncio
from pathlib import Path, PurePosixPath

from agentic_patterns.core.config.config import SANDBOX_PREFIX, WORKSPACE_DIR
from agentic_patterns.core.user_session import get_session_id, get_user_id


class WorkspaceError(Exception):
    """Raised for user-correctable workspace errors (invalid paths, missing files, etc.)."""
    pass


def _get_host_root() -> Path:
    """Get the host root directory for the current user/session."""
    return WORKSPACE_DIR / get_user_id() / get_session_id()


def workspace_to_host_path(sandbox_path: PurePosixPath) -> Path:
    """Convert a sandbox path (/workspace/...) to a host filesystem path."""
    path_str = str(sandbox_path)
    if not path_str.startswith(SANDBOX_PREFIX):
        raise WorkspaceError(f"Invalid sandbox path: must start with {SANDBOX_PREFIX}")

    relative = sandbox_path.relative_to(SANDBOX_PREFIX)
    host_root = _get_host_root()
    host_path = host_root / relative

    try:
        host_path.resolve().relative_to(host_root.resolve())
    except ValueError:
        raise WorkspaceError("Path traversal not allowed")

    return host_path


def host_to_workspace_path(host_path: Path) -> PurePosixPath:
    """Convert a host filesystem path to a sandbox path (/workspace/...)."""
    try:
        relative = host_path.resolve().relative_to(WORKSPACE_DIR.resolve())
        parts = relative.parts
        if len(parts) < 2:
            raise WorkspaceError(f"Invalid workspace path structure: {host_path}")
        # Skip user_id and session_id parts
        actual_relative = Path(*parts[2:]) if len(parts) > 2 else Path(".")
        result = f"{SANDBOX_PREFIX}/{actual_relative.as_posix()}"
        return PurePosixPath(result.rstrip("/."))
    except ValueError:
        raise WorkspaceError(f"Path {host_path} is outside workspace")


def list_workspace_files(pattern: str) -> list[str]:
    """List files in workspace matching pattern, returns sandbox paths."""
    host_root = _get_host_root()
    if not host_root.exists():
        return []
    return [str(host_to_workspace_path(p)) for p in host_root.rglob(pattern) if p.is_file()]


def read_from_workspace(sandbox_path: str) -> str:
    """Read text content from workspace."""
    host_path = workspace_to_host_path(PurePosixPath(sandbox_path))
    if not host_path.exists():
        raise WorkspaceError(f"File not found: {sandbox_path}")
    return host_path.read_text()


async def read_from_workspace_async(sandbox_path: str) -> str:
    """Async read text content from workspace."""
    return await asyncio.to_thread(read_from_workspace, sandbox_path)


def write_to_workspace(sandbox_path: str, content: str | bytes) -> str:
    """Write content to workspace, returns sandbox path."""
    host_path = workspace_to_host_path(PurePosixPath(sandbox_path))
    host_path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(content, bytes):
        host_path.write_bytes(content)
    else:
        host_path.write_text(content)
    return sandbox_path


async def write_to_workspace_async(sandbox_path: str, content: str | bytes) -> str:
    """Async write content to workspace, returns sandbox path."""
    return await asyncio.to_thread(write_to_workspace, sandbox_path, content)


def store_result(content: str | bytes, content_type: str) -> str:
    """Store content in workspace and return sandbox path."""
    from uuid import uuid4

    extensions = {"json": ".json", "csv": ".csv", "txt": ".txt", "md": ".md", "xml": ".xml", "yaml": ".yaml"}
    ext = extensions.get(content_type.lower(), ".txt")
    filename = f"result_{uuid4().hex[:8]}{ext}"
    path = f"/workspace/results/{filename}"
    write_to_workspace(path, content)
    return path


async def store_result_async(content: str | bytes, content_type: str) -> str:
    """Async store content in workspace and return sandbox path."""
    return await asyncio.to_thread(store_result, content, content_type)
