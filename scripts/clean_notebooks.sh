#!/bin/bash -eu
set -o pipefail

source "$(dirname "${BASH_SOURCE[0]}")/config.sh"

python "${PROJECT_DIR}/scripts/clean_notebooks.py" "${PROJECT_DIR}"
