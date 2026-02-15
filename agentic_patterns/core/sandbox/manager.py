"""Sandbox manager for Docker-based code execution with network isolation."""

import logging
import uuid
from collections.abc import Iterator
from contextlib import contextmanager

import docker
from docker.errors import DockerException, NotFound
from docker.models.containers import Container

from agentic_patterns.core.config.config import WORKSPACE_DIR
from agentic_patterns.core.sandbox.config import (
    DOCKER_HOST,
    SANDBOX_COMMAND_TIMEOUT,
    SANDBOX_CONTAINER_PREFIX,
    SandboxProfile,
)
from agentic_patterns.core.sandbox.container_config import (
    ContainerConfig,
    create_container_config,
)
from agentic_patterns.core.sandbox.network_mode import NetworkMode, get_network_mode
from agentic_patterns.core.sandbox.session import SandboxSession

logger = logging.getLogger(__name__)


class SandboxManager:
    """Manages Docker containers for sandboxed code execution.

    Integrates with PrivateData to enforce network isolation: sessions containing
    private data run in containers with no network access (network_mode="none").
    """

    def __init__(
        self,
        read_only_mounts: dict[str, str] | None = None,
        rw_mounts: dict[str, str] | None = None,
        profile: SandboxProfile | None = None,
        environment: dict[str, str] | None = None,
    ) -> None:
        self._client: docker.DockerClient | None = None
        self._read_only_mounts: dict[str, str] = read_only_mounts or {}
        self._rw_mounts: dict[str, str] = rw_mounts or {}
        self._profile: SandboxProfile | None = profile
        self._environment: dict[str, str] = environment or {}
        self._sessions: dict[tuple[str, str], SandboxSession] = {}

    @property
    def client(self) -> docker.DockerClient:
        if self._client is None:
            self._client = (
                docker.DockerClient(base_url=DOCKER_HOST)
                if DOCKER_HOST
                else docker.from_env()
            )
        return self._client

    def close_session(self, user_id: str, session_id: str) -> None:
        """Stop and remove the container for a session."""
        key = (user_id, session_id)
        session = self._sessions.get(key)
        if session is None:
            return
        self._remove_container(session.container_id)
        del self._sessions[key]
        logger.info("Closed session %s:%s", user_id, session_id)

    @contextmanager
    def ephemeral_session(
        self, user_id: str, session_id: str
    ) -> Iterator[SandboxSession]:
        """Create a container, yield the session, destroy the container on exit."""
        session = self._new_session(user_id, session_id, ephemeral=True)
        try:
            yield session
        finally:
            self._remove_container(session.container_id)

    def execute_command(
        self,
        user_id: str,
        session_id: str,
        command: str | list[str],
        timeout: int | None = None,
        *,
        persistent: bool = False,
    ) -> tuple[int, str]:
        """Execute a command in a sandbox container. Returns (exit_code, output).

        command can be a shell string (wrapped in bash -c) or a raw command list.
        persistent=False (default): create container, run, destroy.
        persistent=True: reuse cached session across calls.
        """
        if persistent:
            session = self.get_or_create_session(user_id, session_id)
            return self._run_command(session, command, timeout)
        with self.ephemeral_session(user_id, session_id) as session:
            return self._run_command(session, command, timeout)

    def get_or_create_session(self, user_id: str, session_id: str) -> SandboxSession:
        """Get existing session or create a new one. Checks network mode on every call."""
        key = (user_id, session_id)
        session = self._sessions.get(key)

        if session is None:
            session = self._new_session(user_id, session_id)
            self._sessions[key] = session
        else:
            self._ensure_network_mode(session)

        return session

    def _create_container(
        self, session: SandboxSession, config: ContainerConfig
    ) -> Container:
        """Create and start a Docker container for the session."""
        session.data_dir.mkdir(parents=True, exist_ok=True)

        volumes = {str(session.data_dir): {"bind": config.working_dir, "mode": "rw"}}
        for host_path, container_path in config.read_only_mounts.items():
            volumes[host_path] = {"bind": container_path, "mode": "ro"}
        for host_path, container_path in self._rw_mounts.items():
            volumes[host_path] = {"bind": container_path, "mode": "rw"}

        container = self.client.containers.run(
            image=config.image,
            name=session.container_name,
            detach=True,
            tty=True,
            network_mode=config.network_mode.value,
            working_dir=config.working_dir,
            user=config.user,
            nano_cpus=int(config.cpu_limit * 1e9),
            mem_limit=config.memory_limit,
            environment=config.environment,
            volumes=volumes,
        )

        session.container_id = container.id
        session.config = config
        session.network_mode = config.network_mode
        logger.info(
            "Created container %s (network=%s) for %s:%s",
            session.container_name,
            config.network_mode.value,
            session.user_id,
            session.session_id,
        )
        return container

    def _create_config(self, network_mode: NetworkMode) -> ContainerConfig:
        """Create a ContainerConfig using the manager's profile and environment."""
        return create_container_config(
            network_mode, self._read_only_mounts, self._profile, self._environment
        )

    def _ensure_network_mode(self, session: SandboxSession) -> None:
        """Check if session's network mode matches PrivateData state; recreate if not."""
        required = get_network_mode(session.user_id, session.session_id)
        if session.network_mode == required:
            return
        if required == NetworkMode.NONE:
            logger.info(
                "Private data detected for %s:%s, recreating container with network=none",
                session.user_id,
                session.session_id,
            )
            self._recreate_container(session)

    def _new_session(
        self, user_id: str, session_id: str, *, ephemeral: bool = False
    ) -> SandboxSession:
        """Create a brand new session with container."""
        network_mode = get_network_mode(user_id, session_id)
        config = self._create_config(network_mode)
        data_dir = WORKSPACE_DIR / user_id / session_id

        suffix = f"-{uuid.uuid4().hex[:8]}" if ephemeral else ""
        session = SandboxSession(
            user_id=user_id,
            session_id=session_id,
            container_name=f"{SANDBOX_CONTAINER_PREFIX}-{user_id}-{session_id}{suffix}",
            network_mode=network_mode,
            config=config,
            data_dir=data_dir,
        )

        self._create_container(session, config)
        return session

    def _recreate_container(self, session: SandboxSession) -> None:
        """Stop old container and create a new one with updated network mode."""
        self._remove_container(session.container_id)
        network_mode = get_network_mode(session.user_id, session.session_id)
        config = self._create_config(network_mode)
        self._create_container(session, config)

    def _remove_container(self, container_id: str) -> None:
        """Stop and remove a container, ignoring if already gone."""
        try:
            container = self.client.containers.get(container_id)
            container.stop(timeout=5)
            container.remove(force=True)
        except NotFound:
            pass
        except DockerException as e:
            logger.warning("Error removing container %s: %s", container_id, e)

    def _run_command(
        self,
        session: SandboxSession,
        command: str | list[str],
        timeout: int | None = None,
    ) -> tuple[int, str]:
        """Execute a command in the session's container. Returns (exit_code, output).

        command can be a shell string (wrapped in bash -c) or a raw command list.
        """
        session.touch()
        timeout = timeout or SANDBOX_COMMAND_TIMEOUT
        cmd = command if isinstance(command, list) else ["bash", "-c", command]

        try:
            container = self.client.containers.get(session.container_id)
            result = container.exec_run(
                cmd=cmd,
                workdir=session.config.working_dir,
                demux=True,
            )
            stdout = (
                result.output[0].decode("utf-8", errors="replace")
                if result.output[0]
                else ""
            )
            stderr = (
                result.output[1].decode("utf-8", errors="replace")
                if result.output[1]
                else ""
            )
            return result.exit_code, stdout + stderr
        except NotFound:
            logger.error(
                "Container %s not found for session %s:%s",
                session.container_id,
                session.user_id,
                session.session_id,
            )
            raise
        except DockerException as e:
            logger.error(
                "Docker error executing command in %s:%s: %s",
                session.user_id,
                session.session_id,
                e,
            )
            raise
