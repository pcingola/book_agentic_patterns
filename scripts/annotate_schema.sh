#!/bin/bash -eu
set -o pipefail
source "$(dirname "$0")/config.sh"

python -m agentic_patterns.core.connectors.sql.cli.annotate_schema "$@"
