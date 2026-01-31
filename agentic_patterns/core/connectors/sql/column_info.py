"""Column information model."""

from __future__ import annotations

from typing import TYPE_CHECKING

from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from agentic_patterns.core.connectors.sql.table_info import TableInfo


class ColumnInfo(BaseModel):
    """Database column information."""

    model_config = {"arbitrary_types_allowed": True}

    name: str
    data_type: str
    is_nullable: bool
    description: str = ""
    column_default: str | None = None
    is_primary_key: bool = False
    is_unique: bool = False
    is_enum: bool | None = None
    enum_values: list[str] | None = None
    table: "TableInfo | None" = Field(default=None, exclude=True, repr=False)

    def __str__(self) -> str:
        flags = []
        if self.is_primary_key:
            flags.append("PK")
        if self.is_unique:
            flags.append("unique")
        if not self.is_nullable:
            flags.append("NOT NULL")
        if self.is_enum:
            flags.append(f"enum({len(self.enum_values)} values)")
        flag_str = f" [{', '.join(flags)}]" if flags else ""
        return f"ColumnInfo({self.name!r}, {self.data_type}{flag_str})"

    def schema_sql(self) -> str:
        """Generate SQL fragment for this column."""
        from agentic_patterns.core.connectors.sql.schema_formatter import SchemaFormatter
        return SchemaFormatter.format_column(self)

    @classmethod
    def from_dict(cls, data: dict, table: "TableInfo | None" = None) -> "ColumnInfo":
        col = cls(
            name=data["name"],
            data_type=data["data_type"],
            is_nullable=data["is_nullable"],
            description=data.get("description", ""),
            column_default=data.get("column_default"),
            is_primary_key=data.get("is_primary_key", False),
            is_unique=data.get("is_unique", False),
            is_enum=data.get("is_enum"),
            enum_values=data.get("enum_values"),
        )
        col.table = table
        return col

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "data_type": self.data_type,
            "is_nullable": self.is_nullable,
            "description": self.description,
            "column_default": self.column_default,
            "is_primary_key": self.is_primary_key,
            "is_unique": self.is_unique,
            "is_enum": self.is_enum,
            "enum_values": self.enum_values,
        }
