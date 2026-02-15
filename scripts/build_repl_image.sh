#!/bin/bash -eu
set -o pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

docker build \
    -t agentic-patterns-repl:latest \
    -f "${PROJECT_DIR}/docker/repl/Dockerfile" \
    "${PROJECT_DIR}/docker/repl"
