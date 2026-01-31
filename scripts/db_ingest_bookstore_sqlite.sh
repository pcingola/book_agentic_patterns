#!/bin/bash -eu
set -o pipefail
source "$(dirname "$0")/config.sh"

SQL_DIR="${PROJECT_DIR}/tests/data/sql"
SQLITE_DB="${PROJECT_DIR}/data/db/bookstore.db"

mkdir -p "$(dirname "$SQLITE_DB")"
rm -f "$SQLITE_DB"

sqlite3 "$SQLITE_DB" < "${SQL_DIR}/bookstore_schema_sqlite.sql"
sqlite3 "$SQLITE_DB" < "${SQL_DIR}/bookstore_data.sql"
