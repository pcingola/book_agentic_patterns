"""Status enum for agent executions."""

from enum import Enum


class AgentStatus(str, Enum):
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    INPUT_REQUIRED = "input_required"
    CANCELLED = "cancelled"
    TIMEOUT = "timeout"
