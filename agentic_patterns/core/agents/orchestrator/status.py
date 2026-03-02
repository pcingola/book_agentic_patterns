"""Status enum for agent executions."""

from enum import Enum


class AgentStatus(str, Enum):
    AUTH_REQUIRED = "auth_required"
    CANCELLED = "cancelled"
    COMPLETED = "completed"
    FAILED = "failed"
    INPUT_REQUIRED = "input_required"
    RUNNING = "running"
    TIMEOUT = "timeout"
