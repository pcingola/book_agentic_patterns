#!/bin/bash -eu
set -o pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/config.sh"

cd "${PROJECT_DIR}"

if [ $# -eq 0 ]; then
    python -m unittest -v tests.notebooks.test_notebooks
else
    NOTEBOOK_FILTER="$1" python -m unittest -v tests.notebooks.test_notebooks.TestNotebooks.test_standalone_notebooks
fi
