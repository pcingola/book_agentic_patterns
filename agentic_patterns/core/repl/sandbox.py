"""REPL sandbox: pickle-based IPC on top of the generic sandbox.

Writes pickled input (code, namespace, imports, funcdefs) to the REPL data
directory, runs the executor inside the generic sandbox, reads pickled
SubprocessResult back. Pkl files persist per cell for debugging.

REPL internal data (pkl files, cells.json, temp workbooks) lives under
DATA_DIR/repl/<user_id>/<session_id>/, separate from the user-visible
workspace, so user code never sees internal files.

Sandbox selection order:
1. bwrap (Linux production)
2. Docker (via SandboxManager, when Docker is available)
3. Raises RuntimeError (no silent fallback to unsandboxed execution)
"""

import logging
import pickle
import shutil
import sys
from pathlib import Path
from typing import Any

from agentic_patterns.core.repl.cell_output import CellOutput
from agentic_patterns.core.repl.cell_utils import SubprocessResult
from agentic_patterns.core.repl.config import REPL_SANDBOX_MOUNT
from agentic_patterns.core.repl.enums import CellState, OutputType
from agentic_patterns.core.process_sandbox import BindMount, get_sandbox

logger = logging.getLogger(__name__)


def _is_docker_available() -> bool:
    """Check if Docker daemon is reachable."""
    try:
        import docker

        client = docker.from_env()
        client.ping()
        return True
    except Exception:
        return False


def get_repl_data_dir(user_id: str, session_id: str) -> Path:
    """Get the REPL data directory for a user/session (host-side)."""
    from agentic_patterns.core.config.config import DATA_DIR

    return DATA_DIR / "repl" / user_id / session_id


def delete_cell_pkl_files(user_id: str, session_id: str, cell_id: str) -> None:
    """Remove the input/output pkl files for a given cell."""
    repl_dir = get_repl_data_dir(user_id, session_id)
    for suffix in ("input", "output"):
        pkl_file = repl_dir / f"{cell_id}_{suffix}.pkl"
        pkl_file.unlink(missing_ok=True)


def delete_repl_dir(user_id: str, session_id: str) -> None:
    """Remove the entire REPL data directory for a user/session."""
    repl_dir = get_repl_data_dir(user_id, session_id)
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
    repl_dir = get_repl_data_dir(user_id, session_id)
    repl_dir.mkdir(parents=True, exist_ok=True)

    input_data = {
        "code": code,
        "namespace": namespace,
        "import_statements": import_statements,
        "function_definitions": function_definitions,
        "user_id": user_id,
        "session_id": session_id,
        "workspace_path": "/workspace",
    }
    (repl_dir / f"{cell_id}_input.pkl").write_bytes(pickle.dumps(input_data))

    # Try bwrap first, then Docker, then fail loudly.
    try:
        sandbox = get_sandbox()  # raises RuntimeError if bwrap not found
    except RuntimeError:
        sandbox = None

    if sandbox is not None:
        return await _execute_bwrap(
            sandbox,
            workspace_path,
            repl_dir,
            "/workspace",
            REPL_SANDBOX_MOUNT,
            cell_id,
            timeout,
            user_id,
            session_id,
        )

    if _is_docker_available():
        return await _execute_docker(
            workspace_path, repl_dir, cell_id, timeout, user_id, session_id
        )

    raise RuntimeError(
        "No sandbox available. Install bubblewrap (bwrap) or Docker to run REPL cells. "
        "Unsandboxed execution is not allowed."
    )


async def _execute_bwrap(
    sandbox: Any,
    workspace_path: Path,
    repl_dir: Path,
    executor_workspace: str,
    executor_repl_dir: str,
    cell_id: str,
    timeout: int,
    user_id: str,
    session_id: str,
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

    bind_mounts = [
        BindMount(workspace_path, "/workspace"),
        BindMount(repl_dir, REPL_SANDBOX_MOUNT),
    ]
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
    repl_dir: Path,
    cell_id: str,
    timeout: int,
    user_id: str,
    session_id: str,
) -> SubprocessResult:
    """Execute via Docker container using SandboxManager."""
    import asyncio

    from agentic_patterns.core.sandbox.config import get_sandbox_profile
    from agentic_patterns.core.sandbox.manager import SandboxManager

    project_dir = Path(__file__).resolve().parents[3]
    read_only_mounts = {str(project_dir): "/app"}

    manager = SandboxManager(
        read_only_mounts=read_only_mounts,
        rw_mounts={str(repl_dir): REPL_SANDBOX_MOUNT},
        profile=get_sandbox_profile("repl"),
        environment={"PYTHONPATH": "/app"},
    )

    command = [
        "python",
        "-m",
        "agentic_patterns.core.repl.executor",
        REPL_SANDBOX_MOUNT,
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
