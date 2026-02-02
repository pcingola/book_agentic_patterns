"""Index information model."""

from dataclasses import dataclass


@dataclass
class IndexInfo:
    """Database index information."""

    name: str
    columns: list[str]
    is_unique: bool
    is_primary: bool = False
    index_type: str | None = None

    def __str__(self) -> str:
        flags = []
        if self.is_primary:
            flags.append("PK")
        if self.is_unique:
            flags.append("unique")
        flag_str = f" [{', '.join(flags)}]" if flags else ""
        cols = ", ".join(self.columns)
        return f"Index({self.name!r}, [{cols}]{flag_str})"

    @classmethod
    def from_dict(cls, data: dict) -> "IndexInfo":
        return cls(
            name=data["name"],
            columns=data["columns"],
            is_unique=data["is_unique"],
            is_primary=data.get("is_primary", False),
            index_type=data.get("index_type"),
        )

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "columns": self.columns,
            "is_unique": self.is_unique,
            "is_primary": self.is_primary,
            "index_type": self.index_type,
        }
