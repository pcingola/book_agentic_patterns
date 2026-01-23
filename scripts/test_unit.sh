#!/bin/bash -eu
set -o pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/config.sh"

cd "${PROJECT_DIR}"

if [ $# -eq 0 ]; then
    python -m unittest discover -s tests/unit -p "test_*.py"
else
    python -m unittest "$@"
fi
