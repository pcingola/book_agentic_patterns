"""CodeRepoConnector: scan, read, and search a code repository."""

import fnmatch
import re
from pathlib import Path

from agentic_patterns.core.connectors.base import Connector

# Directories always excluded from scanning
_DEFAULT_EXCLUDES = {
    ".git",
    "__pycache__",
    "node_modules",
    ".venv",
    "venv",
    ".tox",
    ".mypy_cache",
    ".ruff_cache",
    ".pytest_cache",
    "dist",
    "build",
    ".eggs",
    "*.egg-info",
}

# Common source file extensions
_SOURCE_EXTENSIONS = {
    ".py",
    ".js",
    ".jsx",
    ".ts",
    ".tsx",
    ".java",
    ".go",
    ".rs",
    ".c",
    ".cpp",
    ".h",
    ".hpp",
    ".cs",
    ".rb",
    ".php",
    ".swift",
    ".kt",
    ".scala",
    ".sh",
    ".bash",
    ".zsh",
    ".sql",
    ".md",
    ".txt",
    ".yaml",
    ".yml",
    ".toml",
    ".json",
    ".xml",
    ".html",
    ".css",
}


class CodeRepoConnector(Connector):
    """Pure data access for code repositories."""

    def fetch_window(self, path: Path, start_line: int, radius: int = 10) -> str:
        """Return lines around a location for context expansion."""
        if not path.is_file():
            return f"File not found: {path}"
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        begin = max(0, start_line - 1 - radius)
        end = min(len(lines), start_line - 1 + radius + 1)
        numbered = [f"{i + 1:4d} | {lines[i]}" for i in range(begin, end)]
        return f"# {path} (lines {begin + 1}-{end})\n" + "\n".join(numbered)

    def lexical_search(self, root: Path, pattern: str, max_results: int = 20) -> str:
        """Regex/literal search across source files in a repository."""
        try:
            regex = re.compile(pattern)
        except re.error:
            regex = re.compile(re.escape(pattern))

        results: list[str] = []
        for file_path in self._iter_source_files(root):
            try:
                text = file_path.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            for line_num, line in enumerate(text.splitlines(), 1):
                if regex.search(line):
                    rel = file_path.relative_to(root)
                    results.append(f"{rel}:{line_num}: {line.rstrip()}")
                    if len(results) >= max_results:
                        return "\n".join(results)
        return "\n".join(results) if results else "No matches found."

    def read_file(self, path: Path) -> tuple[str, str]:
        """Read a file and return (content, language_hint). Language hint is the extension without dot."""
        content = path.read_text(encoding="utf-8", errors="replace")
        language = path.suffix.lstrip(".").lower() if path.suffix else "text"
        return content, language

    def scan(
        self,
        root: Path,
        include_patterns: list[str] | None = None,
        exclude_patterns: list[str] | None = None,
    ) -> list[Path]:
        """Walk directory tree, return file paths matching patterns."""
        files: list[Path] = []
        for file_path in self._iter_source_files(root, exclude_patterns):
            if include_patterns:
                rel = str(file_path.relative_to(root))
                if not any(fnmatch.fnmatch(rel, p) for p in include_patterns):
                    continue
            files.append(file_path)
        return sorted(files)

    def _iter_source_files(
        self, root: Path, extra_excludes: list[str] | None = None
    ) -> list[Path]:
        """Iterate source files, respecting excludes."""
        excludes = set(_DEFAULT_EXCLUDES)
        if extra_excludes:
            excludes.update(extra_excludes)

        result: list[Path] = []
        for item in root.rglob("*"):
            if not item.is_file():
                continue
            # Check if any parent directory matches an exclude pattern
            parts = item.relative_to(root).parts
            if any(
                any(fnmatch.fnmatch(part, exc) for exc in excludes)
                for part in parts[:-1]
            ):
                continue
            # Check file name against excludes
            if any(fnmatch.fnmatch(item.name, exc) for exc in excludes):
                continue
            if item.suffix.lower() in _SOURCE_EXTENSIONS:
                result.append(item)
        return result
