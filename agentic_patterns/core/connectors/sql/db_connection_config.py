"""Database connection configuration model."""

from pathlib import Path

import yaml
from pydantic import BaseModel, ConfigDict

from agentic_patterns.core.connectors.sql.database_type import DatabaseType


class DbConnectionConfig(BaseModel):
    """Configuration for a single database connection."""

    model_config = ConfigDict(protected_namespaces=())

    db_id: str
    type: DatabaseType
    host: str = ""
    port: int = 0
    dbname: str = ""
    user: str = ""
    password: str = ""
    schema: str = "main"

    def __str__(self) -> str:
        return f"DbConnectionConfig(db_id={self.db_id!r}, type={self.type.value}, dbname={self.dbname!r})"


class DbConnectionConfigs:
    """Registry for all database connection configurations. Singleton."""

    _instance: "DbConnectionConfigs | None" = None

    def __init__(self) -> None:
        self._configs: dict[str, DbConnectionConfig] = {}

    @classmethod
    def get(cls) -> "DbConnectionConfigs":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def add(self, config: DbConnectionConfig) -> None:
        self._configs[config.db_id] = config

    def get_config(self, db_id: str) -> DbConnectionConfig:
        if db_id not in self._configs:
            raise ValueError(f"Database '{db_id}' not found. Available: {list(self._configs.keys())}")
        return self._configs[db_id]

    def list_db_ids(self) -> list[str]:
        return list(self._configs.keys())

    def load_from_yaml(self, yaml_path: Path) -> None:
        """Load database configurations from a YAML file."""
        if not yaml_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {yaml_path}")
        data = yaml.safe_load(yaml_path.read_text())
        if not data or "databases" not in data:
            raise ValueError("Invalid dbs.yaml format: missing 'databases' key")
        for db_id, db_data in data["databases"].items():
            self._configs[db_id] = DbConnectionConfig(
                db_id=db_id,
                type=DatabaseType(db_data["type"].lower()),
                host=db_data.get("host", ""),
                port=int(db_data.get("port", 0)),
                dbname=db_data.get("dbname", ""),
                user=db_data.get("user", ""),
                password=db_data.get("password", ""),
                schema=db_data.get("schema", "main"),
            )

    def __len__(self) -> int:
        return len(self._configs)

    def __str__(self) -> str:
        return f"DbConnectionConfigs({len(self._configs)} databases: {list(self._configs.keys())})"

    @classmethod
    def reset(cls) -> None:
        cls._instance = None
