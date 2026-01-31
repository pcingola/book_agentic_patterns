"""Foreign key information model."""

from pydantic import BaseModel


class ForeignKeyInfo(BaseModel):
    """Database foreign key constraint information."""

    name: str | None = None
    columns: list[str]
    referenced_table: str
    referenced_columns: list[str]
    on_delete: str | None = None
    on_update: str | None = None

    def __str__(self) -> str:
        cols = ", ".join(self.columns)
        ref_cols = ", ".join(self.referenced_columns)
        return f"FK([{cols}] -> {self.referenced_table}[{ref_cols}])"

    @classmethod
    def from_dict(cls, data: dict) -> "ForeignKeyInfo":
        return cls(
            name=data.get("name"),
            columns=data["columns"],
            referenced_table=data["referenced_table"],
            referenced_columns=data["referenced_columns"],
            on_delete=data.get("on_delete"),
            on_update=data.get("on_update"),
        )

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "columns": self.columns,
            "referenced_table": self.referenced_table,
            "referenced_columns": self.referenced_columns,
            "on_delete": self.on_delete,
            "on_update": self.on_update,
        }
