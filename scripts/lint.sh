#!/bin/bash -eu
set -o pipefail

# Source config to set up environment
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/config.sh"

cd "${PROJECT_DIR}"

if [[ "${1:-}" == "--fix" ]]; then
    ruff check --fix agentic_patterns/ tests/
    ruff format agentic_patterns/ tests/
else
    ruff check agentic_patterns/ tests/
    ruff format --check agentic_patterns/ tests/
fi
