"""Table information model."""

from __future__ import annotations

from typing import TYPE_CHECKING

from pydantic import BaseModel, Field

from agentic_patterns.core.connectors.sql.column_info import ColumnInfo
from agentic_patterns.core.connectors.sql.foreign_key_info import ForeignKeyInfo
from agentic_patterns.core.connectors.sql.index_info import IndexInfo

if TYPE_CHECKING:
    from agentic_patterns.core.connectors.sql.db_info import DbInfo


class TableInfo(BaseModel):
    """Database table information."""

    model_config = {"arbitrary_types_allowed": True}

    name: str
    columns: list[ColumnInfo] = Field(default_factory=list)
    foreign_keys: list[ForeignKeyInfo] = Field(default_factory=list)
    indexes: list[IndexInfo] = Field(default_factory=list)
    is_view: bool = False
    description: str = ""
    sample_data_csv: str = ""
    db: "DbInfo | None" = Field(default=None, exclude=True, repr=False)

    def __str__(self) -> str:
        pk = self.get_primary_key_column()
        pk_str = f", pk={pk!r}" if pk else ""
        return f"TableInfo({self.name!r}, {len(self.columns)} columns{pk_str})"

    def __iter__(self):
        return iter(self.columns)

    def __len__(self) -> int:
        return len(self.columns)

    def add_column(self, column: ColumnInfo) -> None:
        column.table = self
        self.columns.append(column)

    def get_column(self, name: str) -> ColumnInfo | None:
        for col in self.columns:
            if col.name == name:
                return col
        return None

    def get_column_names(self) -> list[str]:
        return sorted([col.name for col in self.columns])

    def get_primary_key_column(self) -> str | None:
        for col in self.columns:
            if col.is_primary_key:
                return col.name
        return None

    def schema_sql(self) -> str:
        from agentic_patterns.core.connectors.sql.schema_formatter import SchemaFormatter
        return SchemaFormatter.format_table(self)

    @classmethod
    def from_dict(cls, data: dict, db: "DbInfo | None" = None) -> "TableInfo":
        table = cls(
            name=data["name"],
            is_view=data.get("is_view", False),
            description=data.get("description", ""),
            sample_data_csv=data.get("sample_data_csv", ""),
            columns=[],
            foreign_keys=[ForeignKeyInfo.from_dict(fk) for fk in data.get("foreign_keys", [])],
            indexes=[IndexInfo.from_dict(idx) for idx in data.get("indexes", [])],
        )
        table.db = db
        table.columns = [ColumnInfo.from_dict(col, table=table) for col in data["columns"]]
        return table

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "is_view": self.is_view,
            "description": self.description,
            "sample_data_csv": self.sample_data_csv,
            "columns": [col.to_dict() for col in self.columns],
            "foreign_keys": [fk.to_dict() for fk in self.foreign_keys],
            "indexes": [idx.to_dict() for idx in self.indexes],
        }
