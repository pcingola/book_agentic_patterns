"""Schema SQL formatter."""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from agentic_patterns.core.connectors.sql.column_info import ColumnInfo
    from agentic_patterns.core.connectors.sql.foreign_key_info import ForeignKeyInfo
    from agentic_patterns.core.connectors.sql.index_info import IndexInfo
    from agentic_patterns.core.connectors.sql.table_info import TableInfo


class SchemaFormatter:
    """Formats schema objects as SQL statements and comments."""

    @staticmethod
    def format_column(col: "ColumnInfo") -> str:
        parts = [col.name, col.data_type]
        if col.is_primary_key:
            parts.append("PRIMARY KEY")
        elif not col.is_nullable:
            parts.append("NOT NULL")
        if col.is_unique and not col.is_primary_key:
            parts.append("UNIQUE")
        if col.column_default:
            parts.append(f"DEFAULT {col.column_default}")

        comments = []
        if col.description:
            comments.append(col.description)
        if col.is_enum and col.enum_values:
            enum_str = ", ".join(f"'{v}'" for v in col.enum_values)
            comments.append(f"Valid values: [{enum_str}]")

        line = " ".join(parts)
        if comments:
            line += f" -- {' | '.join(comments)}"
        return line

    @staticmethod
    def format_foreign_key(fk: "ForeignKeyInfo") -> str:
        cols = ", ".join(fk.columns)
        ref_cols = ", ".join(fk.referenced_columns)
        parts = [f"FK: ({cols}) -> {fk.referenced_table}({ref_cols})"]
        if fk.on_delete:
            parts.append(f"ON DELETE {fk.on_delete}")
        if fk.on_update:
            parts.append(f"ON UPDATE {fk.on_update}")
        return " ".join(parts)

    @staticmethod
    def format_index(idx: "IndexInfo") -> str:
        cols = ", ".join(idx.columns)
        flags = []
        if idx.is_primary:
            flags.append("PRIMARY KEY")
        if idx.is_unique:
            flags.append("UNIQUE")
        flag_str = f" [{', '.join(flags)}]" if flags else ""
        return f"Index: {idx.name} ({cols}){flag_str}"

    @staticmethod
    def format_table(table: "TableInfo") -> str:
        object_type = "View" if table.is_view else "Table"
        create_stmt = f"CREATE VIEW {table.name} (" if table.is_view else f"CREATE TABLE {table.name} ("

        lines = [f"-- {object_type}: {table.name}"]
        if table.description:
            lines.append(f"-- Description: {table.description}")
        if table.foreign_keys:
            lines.append("-- Foreign Keys:")
            for fk in table.foreign_keys:
                lines.append(f"--   {SchemaFormatter.format_foreign_key(fk)}")
        if table.indexes:
            lines.append("-- Indexes:")
            for idx in table.indexes:
                lines.append(f"--   {SchemaFormatter.format_index(idx)}")

        lines.append(create_stmt)
        col_lines = [f"    {SchemaFormatter.format_column(col)}" for col in table.columns]
        for i in range(len(col_lines) - 1):
            col_lines[i] += ","
        lines.extend(col_lines)
        lines.append(");")

        if table.sample_data_csv:
            lines.append("")
            lines.append(f"Sample '{table.name}' data (CSV):")
            lines.append(table.sample_data_csv.strip())

        lines.append("")
        return "\n".join(lines)

    @staticmethod
    def format_schema(tables: list["TableInfo"], database_name: str, description: str = "") -> str:
        lines = [f"-- Database: {database_name}"]
        if description:
            lines.append("-- Description:")
            for line in description.strip().split("\n"):
                lines.append(f"--   {line}")
        lines.append("")
        for table in tables:
            lines.append(SchemaFormatter.format_table(table))
        return "\n".join(lines)
