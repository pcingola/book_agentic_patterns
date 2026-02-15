#!/bin/bash -eu
set -o pipefail

source "$(dirname "${BASH_SOURCE[0]}")/config.sh"

DOCS_DIR="${PROJECT_DIR}/docs"
INDEX="${DOCS_DIR}/agentic_patterns.md"

cp "${INDEX}" "${PROJECT_DIR}/llms.txt"

{
    cat "${INDEX}"
    grep -oE '\(agentic_patterns/[^)]+\)' "${INDEX}" | tr -d '()' | while read -r relpath; do
        printf '\n---\n\n'
        cat "${DOCS_DIR}/${relpath}"
    done
} > "${PROJECT_DIR}/llms-full.txt"
