"""REPL sandbox: pickle-based IPC on top of the generic sandbox.

Writes pickled input (code, namespace, imports, funcdefs) to the workspace
.repl directory, runs the executor inside the generic sandbox, reads pickled
SubprocessResult back. Pkl files persist per cell for debugging.

Sandbox selection order:
1. bwrap (Linux production)
2. Docker (via SandboxManager, when Docker is available)
3. Plain subprocess (fallback, no isolation)
"""

import logging
import pickle
import shutil
import sys
from pathlib import Path
from typing import Any

from agentic_patterns.core.repl.cell_output import CellOutput
from agentic_patterns.core.repl.cell_utils import SubprocessResult
from agentic_patterns.core.repl.enums import CellState, OutputType
from agentic_patterns.core.process_sandbox import BindMount, get_sandbox

logger = logging.getLogger(__name__)

REPL_DIR_NAME = ".repl"


def _is_docker_available() -> bool:
    """Check if Docker daemon is reachable."""
    try:
        import docker

        client = docker.from_env()
        client.ping()
        return True
    except Exception:
        return False


def get_repl_dir(workspace_path: Path) -> Path:
    """Get the .repl directory inside the workspace."""
    return workspace_path / REPL_DIR_NAME


def delete_cell_pkl_files(workspace_path: Path, cell_id: str) -> None:
    """Remove the input/output pkl files for a given cell."""
    repl_dir = get_repl_dir(workspace_path)
    for suffix in ("input", "output"):
        pkl_file = repl_dir / f"{cell_id}_{suffix}.pkl"
        pkl_file.unlink(missing_ok=True)


def delete_repl_dir(workspace_path: Path) -> None:
    """Remove the entire .repl directory."""
    repl_dir = get_repl_dir(workspace_path)
    if repl_dir.exists():
        shutil.rmtree(repl_dir, ignore_errors=True)


async def execute_in_sandbox(
    code: str,
    namespace: dict[str, Any],
    import_statements: list[str],
    function_definitions: list[str],
    timeout: int,
    user_id: str,
    session_id: str,
    workspace_path: Path,
    cell_id: str,
) -> SubprocessResult:
    """Execute REPL code via the generic sandbox with pickle IPC."""
    from agentic_patterns.core.process_sandbox import SandboxBubblewrap

    sandbox = get_sandbox()
    is_bwrap = isinstance(sandbox, SandboxBubblewrap)

    repl_dir = get_repl_dir(workspace_path)
    repl_dir.mkdir(parents=True, exist_ok=True)

    executor_workspace = "/workspace" if is_bwrap else str(workspace_path)
    executor_repl_dir = f"/workspace/{REPL_DIR_NAME}" if is_bwrap else str(repl_dir)

    input_data = {
        "code": code,
        "namespace": namespace,
        "import_statements": import_statements,
        "function_definitions": function_definitions,
        "user_id": user_id,
        "session_id": session_id,
        "workspace_path": executor_workspace,
    }
    (repl_dir / f"{cell_id}_input.pkl").write_bytes(pickle.dumps(input_data))

    if is_bwrap:
        return await _execute_bwrap(
            sandbox,
            workspace_path,
            executor_workspace,
            executor_repl_dir,
            cell_id,
            timeout,
            user_id,
            session_id,
            repl_dir,
        )

    if _is_docker_available():
        return await _execute_docker(
            workspace_path, cell_id, timeout, user_id, session_id, repl_dir
        )

    logger.warning(
        "No bwrap or Docker available -- running REPL executor without isolation"
    )
    return await _execute_subprocess(
        sandbox,
        executor_workspace,
        executor_repl_dir,
        cell_id,
        timeout,
        user_id,
        session_id,
        repl_dir,
    )


async def _execute_bwrap(
    sandbox: Any,
    workspace_path: Path,
    executor_workspace: str,
    executor_repl_dir: str,
    cell_id: str,
    timeout: int,
    user_id: str,
    session_id: str,
    repl_dir: Path,
) -> SubprocessResult:
    """Execute via bubblewrap sandbox."""
    from agentic_patterns.core.compliance.private_data import session_has_private_data

    command = [
        sys.executable,
        "-m",
        "agentic_patterns.core.repl.executor",
        executor_repl_dir,
        cell_id,
    ]

    bind_mounts = [BindMount(workspace_path, "/workspace")]
    isolate_network = session_has_private_data(user_id, session_id)

    result = await sandbox.run(
        command,
        timeout=timeout,
        bind_mounts=bind_mounts,
        isolate_network=isolate_network,
        cwd=executor_workspace,
    )

    return _process_sandbox_result(result, repl_dir, cell_id, timeout)


async def _execute_docker(
    workspace_path: Path,
    cell_id: str,
    timeout: int,
    user_id: str,
    session_id: str,
    repl_dir: Path,
) -> SubprocessResult:
    """Execute via Docker container using SandboxManager."""
    import asyncio

    from agentic_patterns.core.sandbox.config import get_sandbox_profile
    from agentic_patterns.core.sandbox.manager import SandboxManager

    project_dir = Path(__file__).resolve().parents[3]
    read_only_mounts = {str(project_dir): "/app"}

    manager = SandboxManager(
        read_only_mounts=read_only_mounts,
        profile=get_sandbox_profile("repl"),
        environment={"PYTHONPATH": "/app"},
    )

    command = [
        "python",
        "-m",
        "agentic_patterns.core.repl.executor",
        f"/workspace/{REPL_DIR_NAME}",
        cell_id,
    ]

    try:
        exit_code, output = await asyncio.to_thread(
            manager.execute_command,
            user_id,
            session_id,
            command,
            timeout,
            persistent=True,
        )
    except Exception as e:
        logger.error("Docker execution failed: %s", e)
        return SubprocessResult(
            state=CellState.ERROR,
            outputs=[
                CellOutput(
                    output_type=OutputType.ERROR,
                    content=f"Docker execution failed: {e}",
                )
            ],
        )

    output_path = repl_dir / f"{cell_id}_output.pkl"
    if output_path.exists():
        return pickle.loads(output_path.read_bytes())

    return SubprocessResult(
        state=CellState.ERROR,
        outputs=[
            CellOutput(
                output_type=OutputType.ERROR,
                content=output or "Executor produced no output",
            )
        ],
    )


async def _execute_subprocess(
    sandbox: Any,
    executor_workspace: str,
    executor_repl_dir: str,
    cell_id: str,
    timeout: int,
    user_id: str,
    session_id: str,
    repl_dir: Path,
) -> SubprocessResult:
    """Execute via plain subprocess (no isolation fallback)."""
    command = [
        sys.executable,
        "-m",
        "agentic_patterns.core.repl.executor",
        executor_repl_dir,
        cell_id,
    ]

    result = await sandbox.run(command, timeout=timeout, cwd=executor_workspace)
    return _process_sandbox_result(result, repl_dir, cell_id, timeout)


def _process_sandbox_result(
    result: Any, repl_dir: Path, cell_id: str, timeout: int
) -> SubprocessResult:
    """Convert a SandboxResult into a SubprocessResult by reading the output pkl."""
    if result.timed_out:
        return SubprocessResult(
            state=CellState.TIMEOUT,
            outputs=[
                CellOutput(
                    output_type=OutputType.ERROR,
                    content=f"Cell execution timed out after {timeout} seconds",
                )
            ],
        )

    output_path = repl_dir / f"{cell_id}_output.pkl"
    if output_path.exists():
        return pickle.loads(output_path.read_bytes())

    error_msg = (
        result.stderr.decode(errors="replace")
        if result.stderr
        else "Executor produced no output"
    )
    return SubprocessResult(
        state=CellState.ERROR,
        outputs=[CellOutput(output_type=OutputType.ERROR, content=error_msg)],
    )
