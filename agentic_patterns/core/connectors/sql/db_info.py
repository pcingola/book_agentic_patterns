"""Database information model."""

import json
from dataclasses import dataclass, field
from pathlib import Path

from agentic_patterns.core.connectors.sql.table_info import TableInfo


@dataclass
class DbInfo:
    """Database information including all tables and description."""

    db_id: str
    description: str = ""
    tables: list[TableInfo] = field(default_factory=list)
    example_queries: list[dict[str, str]] = field(default_factory=list)
    cache_file_path: Path | None = field(default=None, repr=False, compare=False)

    def __str__(self) -> str:
        desc_preview = (
            self.description[:50] + "..."
            if len(self.description) > 50
            else self.description
        )
        return f"DbInfo(db_id={self.db_id!r}, tables={len(self.tables)}, description={desc_preview!r})"

    def __iter__(self):
        return iter(self.tables)

    def __len__(self) -> int:
        return len(self.tables)

    def add_table(self, table: TableInfo) -> None:
        table.db = self
        self.tables.append(table)

    def get_table(self, name: str) -> TableInfo | None:
        for table in self.tables:
            if table.name == name:
                return table
        return None

    def get_table_names(self) -> list[str]:
        return sorted([table.name for table in self.tables])

    def schema_sql(self) -> str:
        from agentic_patterns.core.connectors.sql.schema_formatter import (
            SchemaFormatter,
        )

        return SchemaFormatter.format_schema(self.tables, self.db_id, self.description)

    @classmethod
    def from_dict(cls, data: dict, cache_file_path: Path | None = None) -> "DbInfo":
        db_info = cls(
            db_id=data["db_id"],
            description=data["description"],
            tables=[],
            example_queries=data.get("example_queries", []),
            cache_file_path=cache_file_path,
        )
        db_info.tables = [TableInfo.from_dict(t, db=db_info) for t in data["tables"]]
        return db_info

    @classmethod
    def load(cls, db_id: str | None = None, input_path: Path | None = None) -> "DbInfo":
        """Load database info from JSON file."""
        if input_path is None:
            if db_id is None:
                raise ValueError("Either db_id or input_path must be provided")
            from agentic_patterns.core.connectors.sql.config import (
                DATABASE_CACHE_DIR,
                DB_INFO_EXT,
            )

            input_path = DATABASE_CACHE_DIR / db_id / f"{db_id}{DB_INFO_EXT}"
        data = json.loads(input_path.read_text())
        return cls.from_dict(data, cache_file_path=input_path)

    def save(self, output_path: Path | None = None) -> Path:
        """Save database info to JSON file."""
        if output_path is None:
            if self.cache_file_path is not None:
                output_path = self.cache_file_path
            else:
                from agentic_patterns.core.connectors.sql.config import (
                    DATABASE_CACHE_DIR,
                    DB_INFO_EXT,
                )

                output_dir = DATABASE_CACHE_DIR / self.db_id
                output_dir.mkdir(parents=True, exist_ok=True)
                output_path = output_dir / f"{self.db_id}{DB_INFO_EXT}"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(self.to_dict(), indent=2))
        self.cache_file_path = output_path
        return output_path

    def to_dict(self) -> dict:
        return {
            "db_id": self.db_id,
            "description": self.description,
            "tables": [table.to_dict() for table in self.tables],
            "example_queries": self.example_queries,
        }
