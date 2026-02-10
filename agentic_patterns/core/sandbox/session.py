"""Sandbox session tracking."""

from datetime import datetime, timezone
from pathlib import Path

from pydantic import BaseModel, Field

from agentic_patterns.core.sandbox.container_config import ContainerConfig
from agentic_patterns.core.sandbox.network_mode import NetworkMode


class Session(BaseModel):
    """Represents an active sandbox session tied to a Docker container."""

    user_id: str
    session_id: str
    container_id: str = ""
    container_name: str = ""
    network_mode: NetworkMode = NetworkMode.FULL
    config: ContainerConfig = Field(default_factory=ContainerConfig)
    data_dir: Path = Path(".")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    last_active_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    def touch(self) -> None:
        """Update last activity timestamp."""
        self.last_active_at = datetime.now(timezone.utc)

    def __str__(self) -> str:
        return f"Session({self.user_id}:{self.session_id}, container={self.container_name}, network={self.network_mode.value})"
