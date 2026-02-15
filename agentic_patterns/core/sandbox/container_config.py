"""Container configuration for sandbox sessions."""

from pydantic import BaseModel

from agentic_patterns.core.sandbox.config import SandboxProfile, get_sandbox_profile
from agentic_patterns.core.sandbox.network_mode import NetworkMode


class ContainerConfig(BaseModel):
    """Docker container configuration for a sandbox session."""

    image: str = "python:3.12-slim"
    cpu_limit: float = 1.0
    memory_limit: str = "512m"
    working_dir: str = "/workspace"
    network_mode: NetworkMode = NetworkMode.FULL
    environment: dict[str, str] = {}
    read_only_mounts: dict[str, str] = {}
    user: str = "nobody"

    def __str__(self) -> str:
        return f"ContainerConfig(image={self.image}, network={self.network_mode.value}, cpu={self.cpu_limit}, mem={self.memory_limit})"


def create_container_config(
    network_mode: NetworkMode,
    read_only_mounts: dict[str, str] | None = None,
    profile: SandboxProfile | None = None,
    environment: dict[str, str] | None = None,
) -> ContainerConfig:
    """Create a ContainerConfig from a sandbox profile and network mode."""
    if profile is None:
        profile = get_sandbox_profile("default")
    return ContainerConfig(
        image=profile.image,
        cpu_limit=profile.cpu_limit,
        memory_limit=profile.memory_limit,
        network_mode=network_mode,
        read_only_mounts=read_only_mounts or {},
        environment=environment or {},
    )
