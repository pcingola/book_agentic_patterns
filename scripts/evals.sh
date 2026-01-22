#!/bin/bash -eu
set -o pipefail

source "$(dirname "$0")/config.sh"
cd "$PROJECT_DIR"

python -m agentic_patterns.core.evals "$@"
