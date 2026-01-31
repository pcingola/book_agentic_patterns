"""SQLite schema inspection."""

from agentic_patterns.core.connectors.sql.column_info import ColumnInfo
from agentic_patterns.core.connectors.sql.foreign_key_info import ForeignKeyInfo
from agentic_patterns.core.connectors.sql.index_info import IndexInfo
from agentic_patterns.core.connectors.sql.inspection.schema_inspector import DbSchemaInspector


class DbSchemaInspectorSqlite(DbSchemaInspector):
    """Inspects SQLite database schema."""

    def get_columns(self, table_name: str, column_descriptions: dict[str, str] | None = None) -> list[ColumnInfo]:
        pks = self.get_primary_keys(table_name)
        uniques = self.get_unique_constraints(table_name)
        cur = self.conn.cursor()
        cur.execute(f"PRAGMA table_info({table_name})")
        columns = []
        for row in cur.fetchall():
            col_id, col_name, data_type, not_null, col_default, is_pk = row
            columns.append(ColumnInfo(
                name=col_name,
                data_type=data_type.upper() if data_type else "TEXT",
                is_nullable=not not_null,
                column_default=col_default,
                is_primary_key=col_name in pks,
                is_unique=col_name in uniques,
                description=column_descriptions.get(col_name, "") if column_descriptions else "",
            ))
        cur.close()
        return columns

    def get_foreign_keys(self, table_name: str) -> list[ForeignKeyInfo]:
        cur = self.conn.cursor()
        cur.execute(f"PRAGMA foreign_key_list({table_name})")
        fk_map: dict[int, ForeignKeyInfo] = {}
        for row in cur.fetchall():
            fk_id, seq, ref_table, col_name, ref_col, on_update, on_delete, match = row
            if fk_id not in fk_map:
                fk_map[fk_id] = ForeignKeyInfo(
                    name=None, columns=[], referenced_table=ref_table, referenced_columns=[],
                    on_delete=on_delete if on_delete != "NO ACTION" else None,
                    on_update=on_update if on_update != "NO ACTION" else None,
                )
            fk_map[fk_id].columns.append(col_name)
            fk_map[fk_id].referenced_columns.append(ref_col)
        cur.close()
        return list(fk_map.values())

    def get_indexes(self, table_name: str) -> list[IndexInfo]:
        cur = self.conn.cursor()
        cur.execute(f"PRAGMA index_list({table_name})")
        indexes = []
        for row in cur.fetchall():
            seq, index_name, is_unique, origin, is_partial = row
            cur_info = self.conn.cursor()
            cur_info.execute(f"PRAGMA index_info({index_name})")
            columns = [info_row[2] for info_row in cur_info.fetchall()]
            cur_info.close()
            if columns:
                indexes.append(IndexInfo(
                    name=index_name, columns=columns, is_unique=bool(is_unique),
                    is_primary=origin == "pk", index_type=None,
                ))
        cur.close()
        return indexes

    def get_primary_keys(self, table_name: str) -> set[str]:
        cur = self.conn.cursor()
        cur.execute(f"PRAGMA table_info({table_name})")
        result = {row[1] for row in cur.fetchall() if row[5]}
        cur.close()
        return result

    def get_tables(self) -> list[str]:
        cur = self.conn.cursor()
        cur.execute("""
            SELECT name FROM sqlite_master
            WHERE type IN ('table', 'view') AND name NOT LIKE 'sqlite_%'
            ORDER BY name
        """)
        result = [row[0] for row in cur.fetchall()]
        cur.close()
        return result

    def get_unique_constraints(self, table_name: str) -> set[str]:
        unique_cols = set()
        cur = self.conn.cursor()
        cur.execute(f"PRAGMA index_list({table_name})")
        for row in cur.fetchall():
            index_name, is_unique = row[1], row[2]
            if is_unique:
                cur.execute(f"PRAGMA index_info({index_name})")
                for info_row in cur.fetchall():
                    unique_cols.add(info_row[2])
        cur.close()
        return unique_cols

    def is_view_map(self) -> dict[str, bool]:
        cur = self.conn.cursor()
        cur.execute("""
            SELECT name, type FROM sqlite_master
            WHERE type IN ('table', 'view') AND name NOT LIKE 'sqlite_%'
            ORDER BY name
        """)
        result = {row[0]: row[1] == "view" for row in cur.fetchall()}
        cur.close()
        return result
