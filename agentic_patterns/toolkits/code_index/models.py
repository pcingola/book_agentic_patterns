"""Data models for code indexing and search."""

from dataclasses import dataclass, field
from pathlib import Path

from pydantic import BaseModel


class IndexListener:
    """Hooks called during indexing. Override to customise behaviour."""

    async def on_start(self, total_files: int) -> None:
        pass

    async def on_file_start(self, file_path: Path, current: int, total: int) -> None:
        pass

    async def on_file_done(
        self, file_path: Path, n_chunks: int, current: int, total: int
    ) -> None:
        pass

    async def on_done(self, stats: "IndexStats") -> None:
        pass


class PrintIndexListener(IndexListener):
    """Prints indexing progress to stdout."""

    async def on_start(self, total_files: int) -> None:
        print(f"[index] {total_files} files to index")

    async def on_file_done(
        self, file_path: Path, n_chunks: int, current: int, total: int
    ) -> None:
        print(f"[index] [{current}/{total}] {file_path.name} ({n_chunks} chunks)")

    async def on_done(self, stats: "IndexStats") -> None:
        print(f"[index] done: {stats}")


@dataclass
class IndexStats:
    files_indexed: int = 0
    chunks_created: int = 0
    errors: list[str] = field(default_factory=list)

    def __str__(self) -> str:
        msg = f"Indexed {self.files_indexed} files, {self.chunks_created} chunks"
        if self.errors:
            msg += f", {len(self.errors)} errors"
        return msg


class CodeSearchResult(BaseModel):
    """A code search hit combining results from code, description, and breadcrumb indexes."""

    doc_id: str
    code: str
    description: str
    breadcrumb: str
    symbol_name: str
    symbol_type: str
    file_path: str
    start_line: int
    end_line: int
    score: float

    def __str__(self) -> str:
        return (
            f"[{self.score:.3f}] {self.symbol_type} `{self.symbol_name}` "
            f"in {self.file_path}:{self.start_line}\n"
            f"  {self.description}\n"
            f"  {self.breadcrumb}"
        )
