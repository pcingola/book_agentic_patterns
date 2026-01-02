#!/bin/bash -eu
set -o pipefail

# Get project directory (parent of scripts directory)
export PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# Load .env file if it exists
if [ -f "${PROJECT_DIR}/.env" ]; then
    set -a
    source "${PROJECT_DIR}/.env"
    set +a
else
    echo "Error: .env file not found at ${PROJECT_DIR}/.env"
    exit 1
fi

# Check for virtual environment
if [ ! -d "${PROJECT_DIR}/.venv" ]; then
    echo "Error: Virtual environment not found at ${PROJECT_DIR}/.venv"
    echo "Run 'uv venv' in the project directory to create it"
    exit 1
fi

# Activate virtual environment
source "${PROJECT_DIR}/.venv/bin/activate"

# Set PYTHONPATH to include agentic_patterns directory
export PYTHONPATH="${PROJECT_DIR}/agentic_patterns:${PYTHONPATH:-}"
