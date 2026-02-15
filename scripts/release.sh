#!/bin/bash -eu
set -o pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/config.sh"

cd "${PROJECT_DIR}"

# Parse arguments
BUMP_VERSION=""
while [[ $# -gt 0 ]]; do
    case "$1" in
        --bump) BUMP_VERSION="$2"; shift 2 ;;
        *) echo "Usage: release.sh [--bump <version>]"; exit 1 ;;
    esac
done

# 1. Lint
"${SCRIPT_DIR}/lint.sh"

# 2. Unit tests
"${SCRIPT_DIR}/test_unit.sh"

# 3. Integration tests
"${SCRIPT_DIR}/test_integration.sh"

# 4. Generate llms.txt and llms-full.txt
"${SCRIPT_DIR}/llms_txt.sh"

# 5. Bump version (if requested)
if [[ -n "${BUMP_VERSION}" ]]; then
    sed -i '' "s/^version = .*/version = \"${BUMP_VERSION}\"/" pyproject.toml
fi

# 6. Clean notebooks
"${SCRIPT_DIR}/clean_notebooks.sh"
