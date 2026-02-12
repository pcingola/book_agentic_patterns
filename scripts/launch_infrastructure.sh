#!/bin/bash -eu
set -o pipefail

source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/config.sh"

PIDS=()
cleanup() {
    for pid in "${PIDS[@]}"; do
        kill "$pid" 2>/dev/null || true
    done
    wait 2>/dev/null || true
}
trap cleanup EXIT

start_mcp() {
    local module="$1" port="$2"
    fastmcp run "agentic_patterns/mcp/${module}/server.py:mcp" --transport http --port "$port" &
    PIDS+=($!)
}

start_a2a() {
    local module="$1" port="$2"
    uvicorn "agentic_patterns.a2a.${module}.server:app" --port "$port" &
    PIDS+=($!)
}

# MCP servers (start these first -- A2A servers depend on them)
start_mcp file_ops 8100
start_mcp sandbox 8101
start_mcp todo 8102
start_mcp format_conversion 8103
start_mcp data_analysis 8010
start_mcp data_viz 8104
start_mcp sql 8011
start_mcp repl 8105
start_mcp vocabulary 8106

sleep 2

# A2A servers
start_a2a nl2sql 8200
start_a2a data_analysis 8201
start_a2a vocabulary 8202

wait
