#!/bin/bash -eu
set -o pipefail

source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/config.sh"

free_port() {
    local pid
    pid=$(lsof -ti :"$1" 2>/dev/null) || return 0
    kill "$pid" 2>/dev/null || true
}

PIDS=()
cleanup() {
    for pid in "${PIDS[@]}"; do
        kill "$pid" 2>/dev/null || true
    done
    wait 2>/dev/null || true
}
trap cleanup EXIT

check_pids() {
    for pid in "${PIDS[@]}"; do
        if ! kill -0 "$pid" 2>/dev/null; then
            return 1
        fi
    done
}

start_mcp() {
    local module="$1" port="$2"
    free_port "$port"
    fastmcp run "agentic_patterns/mcp/${module}/server.py:mcp" --transport http --port "$port" \
        > >(sed -u "s/^/[mcp:${module}] /") 2>&1 &
    PIDS+=($!)
}

start_a2a() {
    local module="$1" port="$2"
    free_port "$port"
    uvicorn "agentic_patterns.a2a.${module}.server:app" --port "$port" \
        > >(sed -u "s/^/[a2a:${module}] /") 2>&1 &
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
start_mcp openapi 8107

MCP_PORTS=(8100 8101 8102 8103 8010 8104 8011 8105 8106 8107)
MAX_WAIT=30
for port in "${MCP_PORTS[@]}"; do
    elapsed=0
    while ! curl -s -o /dev/null "http://localhost:${port}/mcp" 2>/dev/null; do
        sleep 1
        elapsed=$((elapsed + 1))
        if [ "$elapsed" -ge "$MAX_WAIT" ]; then
            echo "MCP server on port $port did not become ready in ${MAX_WAIT}s" >&2
            exit 1
        fi
    done
done

check_pids || { echo "An MCP server failed to start" >&2; exit 1; }

# A2A servers
start_a2a nl2sql 8200
start_a2a data_analysis 8201
start_a2a vocabulary 8202
start_a2a openapi 8203

# Wait for any process to exit -- if one dies, kill the rest.
while true; do
    check_pids || exit 1
    sleep 1
done
