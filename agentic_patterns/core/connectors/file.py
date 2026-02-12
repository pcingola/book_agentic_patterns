"""File connector for reading, writing, and editing files in the workspace sandbox."""

import fnmatch
from pathlib import Path, PurePosixPath

from pydantic_ai import ModelRetry

from agentic_patterns.core.connectors.base import Connector
from agentic_patterns.core.context.decorators import context_result
from agentic_patterns.core.context.processors import (
    count_lines,
    detect_encoding,
    read_line_range,
)
from agentic_patterns.core.context.reader import read_file_as_string
from agentic_patterns.core.tools.permissions import ToolPermission, tool_permission
from agentic_patterns.core.workspace import WorkspaceError, workspace_to_host_path


class FileConnector(Connector):
    """File operations with workspace sandbox isolation."""

    def _translate_path(self, path: str) -> Path:
        """Translate sandbox path to host path. Raises WorkspaceError on invalid paths."""
        return workspace_to_host_path(PurePosixPath(path))

    @tool_permission(ToolPermission.WRITE)
    def append(self, path: str, content: str) -> str:
        """Append content to the end of a file."""
        try:
            host_path = self._translate_path(path)
            if not host_path.exists():
                raise FileNotFoundError(f"File not found: {path}")
            with open(host_path, "a", encoding="utf-8") as f:
                f.write(content)
            return f"Appended {len(content)} bytes to {path}"
        except (FileNotFoundError, ValueError, WorkspaceError) as e:
            raise ModelRetry(str(e)) from e

    @tool_permission(ToolPermission.WRITE)
    def delete(self, path: str) -> str:
        """Delete a file."""
        try:
            host_path = self._translate_path(path)
            if not host_path.exists():
                raise FileNotFoundError(f"File not found: {path}")
            host_path.unlink()
            return f"Deleted {path}"
        except (FileNotFoundError, ValueError, WorkspaceError) as e:
            raise ModelRetry(str(e)) from e

    @tool_permission(ToolPermission.WRITE)
    def edit(self, path: str, start_line: int, end_line: int, new_content: str) -> str:
        """Replace lines start_line to end_line (1-indexed, inclusive) with new_content."""
        try:
            host_path = self._translate_path(path)
            if not host_path.exists():
                raise FileNotFoundError(f"File not found: {path}")
            if start_line < 1:
                raise ValueError("start_line must be >= 1")
            if end_line < start_line:
                raise ValueError("end_line must be >= start_line")

            encoding = detect_encoding(host_path)
            total_lines = count_lines(host_path, encoding)
            if start_line > total_lines:
                raise ValueError(
                    f"start_line {start_line} exceeds file length ({total_lines} lines)"
                )

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
        except (FileNotFoundError, ValueError, WorkspaceError) as e:
            raise ModelRetry(str(e)) from e

    @tool_permission(ToolPermission.READ)
    @context_result()
    def find(self, path: str, query: str) -> str:
        """Search file contents for a string, returning matching lines."""
        try:
            host_path = self._translate_path(path)
            if not host_path.exists():
                raise FileNotFoundError(f"File not found: {path}")

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
        except (FileNotFoundError, ValueError, WorkspaceError) as e:
            raise ModelRetry(str(e)) from e

    @tool_permission(ToolPermission.READ)
    def head(self, path: str, n: int = 10) -> str:
        """Read the first N lines of a file."""
        try:
            host_path = self._translate_path(path)
            if not host_path.exists():
                raise FileNotFoundError(f"File not found: {path}")
            if n <= 0:
                raise ValueError("Line count must be positive")

            encoding = detect_encoding(host_path)
            total_lines = count_lines(host_path, encoding)
            if total_lines == 0:
                return ""

            lines, _, _ = read_line_range(host_path, encoding, 0, n)
            content = "\n".join(lines)
            if len(lines) < total_lines:
                return f"[Lines 1-{len(lines)} of {total_lines}]\n{content}"
            return content
        except (FileNotFoundError, ValueError, WorkspaceError) as e:
            raise ModelRetry(str(e)) from e

    @tool_permission(ToolPermission.READ)
    @context_result()
    def list(self, path: str, pattern: str = "*") -> str:
        """List files matching a glob pattern."""
        try:
            host_path = self._translate_path(path)
            if not host_path.exists():
                raise FileNotFoundError(f"Directory not found: {path}")
            if not host_path.is_dir():
                raise NotADirectoryError(f"Not a directory: {path}")

            matches = sorted(
                str(p.relative_to(host_path))
                for p in host_path.rglob("*")
                if p.is_file() and fnmatch.fnmatch(p.name, pattern)
            )

            if not matches:
                return f"[No files matching '{pattern}' in {path}]"

            if len(matches) > 200:
                shown = matches[:200]
                return (
                    f"[Showing 200 of {len(matches)} files matching '{pattern}' in {path}]\n"
                    + "\n".join(shown)
                )

            return f"[{len(matches)} file(s) in {path}]\n" + "\n".join(matches)
        except (FileNotFoundError, NotADirectoryError, ValueError, WorkspaceError) as e:
            raise ModelRetry(str(e)) from e

    @tool_permission(ToolPermission.READ)
    @context_result()
    def read(self, path: str) -> str:
        """Read entire file with automatic truncation for large files."""
        try:
            host_path = self._translate_path(path)
            if not host_path.exists():
                raise FileNotFoundError(f"File not found: {path}")
            return read_file_as_string(host_path)
        except (FileNotFoundError, ValueError, WorkspaceError) as e:
            raise ModelRetry(str(e)) from e

    @tool_permission(ToolPermission.READ)
    def tail(self, path: str, n: int = 10) -> str:
        """Read the last N lines of a file."""
        try:
            host_path = self._translate_path(path)
            if not host_path.exists():
                raise FileNotFoundError(f"File not found: {path}")
            if n <= 0:
                raise ValueError("Line count must be positive")

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
        except (FileNotFoundError, ValueError, WorkspaceError) as e:
            raise ModelRetry(str(e)) from e

    @tool_permission(ToolPermission.WRITE)
    def write(self, path: str, content: str) -> str:
        """Write or overwrite a file."""
        try:
            host_path = self._translate_path(path)
            host_path.parent.mkdir(parents=True, exist_ok=True)
            host_path.write_text(content)
            return f"Wrote {len(content)} bytes to {path}"
        except (FileNotFoundError, ValueError, WorkspaceError) as e:
            raise ModelRetry(str(e)) from e
