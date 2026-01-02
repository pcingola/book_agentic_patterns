#!/bin/bash -eu
set -o pipefail

# Source config to set up environment
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/config.sh"

cd "${PROJECT_DIR}"

# Run specific test if argument provided, otherwise run all tests
if [ $# -eq 0 ]; then
    python -m unittest discover -s tests -p "test_*.py"
else
    python -m unittest "$@"
fi
