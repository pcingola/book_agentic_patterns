"""SQL connector configuration."""

import os

from agentic_patterns.core.config.config import DATA_DIR, MAIN_PROJECT_DIR


DBS_YAML_PATH = MAIN_PROJECT_DIR / os.getenv("DBS_YAML", "dbs.yaml")
DATABASE_CACHE_DIR = DATA_DIR / "database"
DB_INFO_EXT = ".db_info.json"

MAX_SAMPLE_ROWS = int(os.getenv("MAX_SAMPLE_ROWS", "10"))
MAX_ENUM_VALUES = int(os.getenv("MAX_ENUM_VALUES", "50"))
MAX_QUERY_GENERATION_RETRIES = int(os.getenv("MAX_QUERY_GENERATION_RETRIES", "3"))
NUMBER_OF_EXAMPLE_QUERIES = int(os.getenv("NUMBER_OF_EXAMPLE_QUERIES", "5"))
PREVIEW_ROWS = int(os.getenv("PREVIEW_ROWS", "10"))
PREVIEW_COLUMNS = int(os.getenv("PREVIEW_COLUMNS", "200"))
MAX_CSV_VIEW_ROWS = int(os.getenv("MAX_CSV_VIEW_ROWS", "1000"))
