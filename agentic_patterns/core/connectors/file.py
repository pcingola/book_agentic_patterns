"""File connector for reading, writing, and editing files in the workspace sandbox."""

import fnmatch
from pathlib import Path, PurePosixPath
from typing import Any

from agentic_patterns.core.context.processors import count_lines, detect_encoding, read_line_range
from agentic_patterns.core.context.reader import read_file_as_string
from agentic_patterns.core.tools.permissions import ToolPermission, tool_permission
from agentic_patterns.core.workspace import WorkspaceError, container_to_host_path


def _translate_path(path: str, ctx: Any) -> Path | str:
    """Translate sandbox path to host path, returning error string on failure."""
    try:
        return container_to_host_path(PurePosixPath(path), ctx)
    except WorkspaceError as e:
        return f"[Error] {e}"


class FileConnector:
    """Agent-facing file operations with workspace sandbox isolation.

    All methods are static because there is no instance state yet. When we add
    backend adapters (S3, GCS, etc.) or per-connector config, switch to __init__
    + instance methods.
    """

    @staticmethod
    @tool_permission(ToolPermission.WRITE)
    def append(path: str, content: str, ctx: Any = None) -> str:
        """Append content to the end of a file."""
        host_path = _translate_path(path, ctx)
        if isinstance(host_path, str):
            return host_path

        if not host_path.exists():
            return f"[Error] File not found: {path}"

        try:
            with open(host_path, "a", encoding="utf-8") as f:
                f.write(content)
            return f"Appended {len(content)} bytes to {path}"
        except OSError as e:
            return f"[Error] Failed to append to file: {e}"

    @staticmethod
    @tool_permission(ToolPermission.WRITE)
    def delete(path: str, ctx: Any = None) -> str:
        """Delete a file."""
        host_path = _translate_path(path, ctx)
        if isinstance(host_path, str):
            return host_path

        if not host_path.exists():
            return f"[Error] File not found: {path}"

        try:
            host_path.unlink()
            return f"Deleted {path}"
        except OSError as e:
            return f"[Error] Failed to delete file: {e}"

    @staticmethod
    @tool_permission(ToolPermission.WRITE)
    def edit(path: str, start_line: int, end_line: int, new_content: str, ctx: Any = None) -> str:
        """Replace lines start_line to end_line (1-indexed, inclusive) with new_content."""
        host_path = _translate_path(path, ctx)
        if isinstance(host_path, str):
            return host_path

        if not host_path.exists():
            return f"[Error] File not found: {path}"

        if start_line < 1:
            return "[Error] start_line must be >= 1"
        if end_line < start_line:
            return "[Error] end_line must be >= start_line"

        try:
            encoding = detect_encoding(host_path)
            total_lines = count_lines(host_path, encoding)

            if start_line > total_lines:
                return f"[Error] start_line {start_line} exceeds file length ({total_lines} lines)"

            with open(host_path, "r", encoding=encoding, errors="replace") as f:
                lines = f.read().splitlines()

            start_idx = start_line - 1
            end_idx = min(end_line, len(lines))

            new_lines = new_content.splitlines() if new_content else []
            lines[start_idx:end_idx] = new_lines

            host_path.write_text("\n".join(lines) + "\n" if lines else "")

            lines_removed = end_idx - start_idx
            lines_added = len(new_lines)
            return f"Replaced lines {start_line}-{end_idx} ({lines_removed} lines) with {lines_added} lines in {path}"
        except OSError as e:
            return f"[Error] Failed to edit file: {e}"

    @staticmethod
    @tool_permission(ToolPermission.READ)
    def find(path: str, query: str, ctx: Any = None) -> str:
        """Search file contents for a string, returning matching lines."""
        host_path = _translate_path(path, ctx)
        if isinstance(host_path, str):
            return host_path

        if not host_path.exists():
            return f"[Error] File not found: {path}"

        try:
            encoding = detect_encoding(host_path)
            matches: list[str] = []
            with open(host_path, "r", encoding=encoding, errors="replace") as f:
                for line_num, line in enumerate(f, start=1):
                    if query in line:
                        matches.append(f"{line_num}: {line.rstrip()}")
                        if len(matches) >= 100:
                            break

            if not matches:
                return f"[No matches for '{query}' in {path}]"

            header = f"[{len(matches)} match(es) for '{query}' in {path}]"
            return f"{header}\n" + "\n".join(matches)
        except OSError as e:
            return f"[Error] Failed to search file: {e}"

    @staticmethod
    @tool_permission(ToolPermission.READ)
    def head(path: str, n: int = 10, ctx: Any = None) -> str:
        """Read the first N lines of a file."""
        host_path = _translate_path(path, ctx)
        if isinstance(host_path, str):
            return host_path

        if not host_path.exists():
            return f"[Error] File not found: {path}"

        if n <= 0:
            return "[Error] Line count must be positive"

        try:
            encoding = detect_encoding(host_path)
            total_lines = count_lines(host_path, encoding)

            if total_lines == 0:
                return ""

            lines, _, _ = read_line_range(host_path, encoding, 0, n)
            content = "\n".join(lines)

            if len(lines) < total_lines:
                return f"[Lines 1-{len(lines)} of {total_lines}]\n{content}"
            return content
        except OSError as e:
            return f"[Error] Failed to read file: {e}"

    @staticmethod
    @tool_permission(ToolPermission.READ)
    def list(path: str, pattern: str = "*", ctx: Any = None) -> str:
        """List files matching a glob pattern."""
        host_path = _translate_path(path, ctx)
        if isinstance(host_path, str):
            return host_path

        if not host_path.exists():
            return f"[Error] Directory not found: {path}"

        if not host_path.is_dir():
            return f"[Error] Not a directory: {path}"

        try:
            matches = sorted(
                str(p.relative_to(host_path))
                for p in host_path.rglob("*")
                if p.is_file() and fnmatch.fnmatch(p.name, pattern)
            )

            if not matches:
                return f"[No files matching '{pattern}' in {path}]"

            if len(matches) > 200:
                shown = matches[:200]
                return f"[Showing 200 of {len(matches)} files matching '{pattern}' in {path}]\n" + "\n".join(shown)

            return f"[{len(matches)} file(s) in {path}]\n" + "\n".join(matches)
        except OSError as e:
            return f"[Error] Failed to list directory: {e}"

    @staticmethod
    @tool_permission(ToolPermission.READ)
    def read(path: str, ctx: Any = None) -> str:
        """Read entire file with automatic truncation for large files."""
        host_path = _translate_path(path, ctx)
        if isinstance(host_path, str):
            return host_path

        if not host_path.exists():
            return f"[Error] File not found: {path}"

        return read_file_as_string(host_path)

    @staticmethod
    @tool_permission(ToolPermission.READ)
    def tail(path: str, n: int = 10, ctx: Any = None) -> str:
        """Read the last N lines of a file."""
        host_path = _translate_path(path, ctx)
        if isinstance(host_path, str):
            return host_path

        if not host_path.exists():
            return f"[Error] File not found: {path}"

        if n <= 0:
            return "[Error] Line count must be positive"

        try:
            encoding = detect_encoding(host_path)
            total_lines = count_lines(host_path, encoding)

            if total_lines == 0:
                return ""

            start = max(0, total_lines - n)
            lines, _, _ = read_line_range(host_path, encoding, start, total_lines)
            content = "\n".join(lines)

            if start > 0:
                return f"[Lines {start + 1}-{total_lines} of {total_lines}]\n{content}"
            return content
        except OSError as e:
            return f"[Error] Failed to read file: {e}"

    @staticmethod
    @tool_permission(ToolPermission.WRITE)
    def write(path: str, content: str, ctx: Any = None) -> str:
        """Write or overwrite a file."""
        host_path = _translate_path(path, ctx)
        if isinstance(host_path, str):
            return host_path

        try:
            host_path.parent.mkdir(parents=True, exist_ok=True)
            host_path.write_text(content)
            return f"Wrote {len(content)} bytes to {path}"
        except OSError as e:
            return f"[Error] Failed to write file: {e}"
