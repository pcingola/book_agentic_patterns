#!/bin/bash -eu
set -o pipefail

# Source config to set up environment
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/config.sh"

cd "${PROJECT_DIR}"

# Run ruff linter
ruff check src/ tests/

# Run ruff formatter check
ruff format --check src/ tests/
