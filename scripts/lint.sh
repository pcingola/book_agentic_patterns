#!/bin/bash -eu
set -o pipefail

# Source config to set up environment
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/config.sh"

cd "${PROJECT_DIR}"

EXCLUDE="--exclude *.ipynb"

if [[ "${1:-}" == "--fix" ]]; then
    ruff check --fix ${EXCLUDE} agentic_patterns/ tests/
    ruff format ${EXCLUDE} agentic_patterns/ tests/
else
    ruff check ${EXCLUDE} agentic_patterns/ tests/
    ruff format --check ${EXCLUDE} agentic_patterns/ tests/
fi
