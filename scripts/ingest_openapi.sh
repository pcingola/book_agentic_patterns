#!/bin/bash -eu
set -o pipefail

source "$(dirname "${BASH_SOURCE[0]}")/config.sh"

python -m agentic_patterns.core.connectors.openapi.cli.ingest "$@"
