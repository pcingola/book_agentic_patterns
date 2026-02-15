"""Generic sandbox for running commands in isolated environments.

Uses bubblewrap (bwrap) for filesystem, network, and PID namespace isolation.
Raises RuntimeError if bwrap is not available -- no silent fallback to
unsandboxed execution.

Usage:
    sandbox = get_sandbox()
    result = await sandbox.run(
        command=["python3", "-m", "my_module", "/tmp/workdir"],
        bind_mounts=[BindMount(Path("/data/workspace"), "/workspace")],
        timeout=30,
        isolate_network=True,
    )
"""

import asyncio
import logging
import shutil
import sys
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class BindMount:
    """A filesystem bind mount for the sandbox."""

    source: Path
    target: str
    readonly: bool = False


@dataclass
class SandboxResult:
    """Result of a sandboxed command execution."""

    exit_code: int
    stdout: bytes = field(default=b"")
    stderr: bytes = field(default=b"")
    timed_out: bool = False


class Sandbox(ABC):
    """Abstract base for sandboxed command execution."""

    @abstractmethod
    async def run(
        self,
        command: list[str],
        *,
        timeout: int,
        bind_mounts: list[BindMount] | None = None,
        isolate_network: bool = False,
        isolate_pid: bool = True,
        cwd: str | None = None,
        env: dict[str, str] | None = None,
    ) -> SandboxResult:
        """Run a command in the sandbox.

        Args:
            command: Command and arguments to execute
            timeout: Maximum execution time in seconds
            bind_mounts: Filesystem mounts (source on host -> target in sandbox)
            isolate_network: Block all network access
            isolate_pid: Isolate PID namespace
            cwd: Working directory inside the sandbox
            env: Environment variables (None = inherit)
        """


class SandboxBubblewrap(Sandbox):
    """Linux sandbox using bubblewrap (bwrap). Requires bwrap on PATH."""

    async def run(
        self,
        command: list[str],
        *,
        timeout: int,
        bind_mounts: list[BindMount] | None = None,
        isolate_network: bool = False,
        isolate_pid: bool = True,
        cwd: str | None = None,
        env: dict[str, str] | None = None,
    ) -> SandboxResult:
        cmd = self._build_command(
            command, bind_mounts or [], isolate_network, isolate_pid, cwd
        )
        logger.debug("bwrap command: %s", " ".join(cmd))

        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=env,
        )

        try:
            stdout, stderr = await asyncio.wait_for(
                process.communicate(), timeout=timeout
            )
            return SandboxResult(
                exit_code=process.returncode or 0, stdout=stdout, stderr=stderr
            )
        except asyncio.TimeoutError:
            process.kill()
            await process.wait()
            return SandboxResult(exit_code=-1, timed_out=True)

    def _build_command(
        self,
        command: list[str],
        bind_mounts: list[BindMount],
        isolate_network: bool,
        isolate_pid: bool,
        cwd: str | None,
    ) -> list[str]:
        cmd = [
            "bwrap",
            "--ro-bind",
            "/usr",
            "/usr",
            "--ro-bind",
            "/lib",
            "/lib",
            "--ro-bind",
            "/lib64",
            "/lib64",
            "--ro-bind",
            "/bin",
            "/bin",
            "--ro-bind",
            "/sbin",
            "/sbin",
            "--proc",
            "/proc",
            "--dev",
            "/dev",
            "--tmpfs",
            "/tmp",
        ]

        if not isolate_network:
            cmd.extend(["--ro-bind", "/etc/resolv.conf", "/etc/resolv.conf"])

        # Bind Python prefix so the child can import installed packages
        python_prefix = Path(sys.prefix)
        if python_prefix != Path("/usr"):
            cmd.extend(["--ro-bind", str(python_prefix), str(python_prefix)])

        for mount in bind_mounts:
            flag = "--ro-bind" if mount.readonly else "--bind"
            cmd.extend([flag, str(mount.source), mount.target])

        if isolate_pid:
            cmd.append("--unshare-pid")
        if isolate_network:
            cmd.append("--unshare-net")
        if cwd:
            cmd.extend(["--chdir", cwd])

        cmd.append("--")
        cmd.extend(command)
        return cmd


def get_sandbox() -> SandboxBubblewrap:
    """Factory: returns SandboxBubblewrap if bwrap is on PATH.

    Raises RuntimeError when bwrap is not available, rather than silently
    falling back to unsandboxed execution.
    """
    if shutil.which("bwrap"):
        return SandboxBubblewrap()
    raise RuntimeError(
        "No sandbox available: bubblewrap (bwrap) not found on PATH. "
        "Install bwrap or use Docker for sandboxed execution."
    )
