"""Container configuration for sandbox sessions."""

from pydantic import BaseModel

from agentic_patterns.core.sandbox.config import (
    SANDBOX_CPU_LIMIT,
    SANDBOX_DOCKER_IMAGE,
    SANDBOX_MEMORY_LIMIT,
)
from agentic_patterns.core.sandbox.network_mode import NetworkMode


class ContainerConfig(BaseModel):
    """Docker container configuration for a sandbox session."""
    image: str = SANDBOX_DOCKER_IMAGE
    cpu_limit: float = SANDBOX_CPU_LIMIT
    memory_limit: str = SANDBOX_MEMORY_LIMIT
    working_dir: str = "/workspace"
    network_mode: NetworkMode = NetworkMode.FULL
    environment: dict[str, str] = {}
    user: str = "nobody"

    def __str__(self) -> str:
        return f"ContainerConfig(image={self.image}, network={self.network_mode.value}, cpu={self.cpu_limit}, mem={self.memory_limit})"


def create_default_config(network_mode: NetworkMode) -> ContainerConfig:
    """Create a ContainerConfig with the given network mode and default settings."""
    return ContainerConfig(network_mode=network_mode)
