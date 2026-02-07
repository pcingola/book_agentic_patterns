"""Sandbox configuration variables."""

from agentic_patterns.core.config.env import get_variable_env

SANDBOX_DOCKER_IMAGE = get_variable_env("SANDBOX_DOCKER_IMAGE") or "python:3.12-slim"
SANDBOX_CPU_LIMIT = float(get_variable_env("SANDBOX_CPU_LIMIT") or "1.0")
SANDBOX_MEMORY_LIMIT = get_variable_env("SANDBOX_MEMORY_LIMIT") or "512m"
SANDBOX_COMMAND_TIMEOUT = int(get_variable_env("SANDBOX_COMMAND_TIMEOUT") or "30")
SANDBOX_CONTAINER_PREFIX = get_variable_env("SANDBOX_CONTAINER_PREFIX") or "sandbox"
SANDBOX_SESSION_TIMEOUT = int(get_variable_env("SANDBOX_SESSION_TIMEOUT") or "3600")
