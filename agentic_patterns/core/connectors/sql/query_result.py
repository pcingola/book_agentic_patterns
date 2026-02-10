"""Query result metadata model."""

import json
from pathlib import Path

from pydantic import BaseModel


QUERY_RESULT_METADATA_EXT = ".query_metadata.json"


class QueryResultMetadata(BaseModel):
    """Metadata for a query result."""

    sql_query: str
    timestamp: str
    row_count: int
    column_count: int
    csv_filename: str
    db_id: str
    natural_language_query: str | None = None

    def __str__(self) -> str:
        query_preview = (
            self.sql_query[:60] + "..." if len(self.sql_query) > 60 else self.sql_query
        )
        return f"QueryResultMetadata(db_id={self.db_id!r}, rows={self.row_count}, query={query_preview!r})"

    @classmethod
    def load(cls, json_path: Path) -> "QueryResultMetadata":
        data = json.loads(json_path.read_text())
        return cls(**data)

    def save(self, json_path: Path) -> None:
        json_path.write_text(json.dumps(self.model_dump(), indent=2))
