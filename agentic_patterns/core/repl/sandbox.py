"""REPL sandbox: pickle-based IPC on top of the generic sandbox.

Writes pickled input (code, namespace, imports, funcdefs) to a temp dir,
runs the executor inside the generic sandbox, reads pickled SubprocessResult back.
"""

import logging
import pickle
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Any

from agentic_patterns.core.repl.cell_output import CellOutput
from agentic_patterns.core.repl.cell_utils import SubprocessResult
from agentic_patterns.core.repl.enums import CellState, OutputType
from agentic_patterns.core.sandbox import BindMount, get_sandbox

logger = logging.getLogger(__name__)


async def execute_in_sandbox(
    code: str,
    namespace: dict[str, Any],
    import_statements: list[str],
    function_definitions: list[str],
    timeout: int,
    user_id: str,
    session_id: str,
    workspace_path: Path,
) -> SubprocessResult:
    """Execute REPL code via the generic sandbox with pickle IPC."""
    from agentic_patterns.core.compliance.private_data import session_has_private_data
    from agentic_patterns.core.sandbox import SandboxBubblewrap

    sandbox = get_sandbox()
    is_bwrap = isinstance(sandbox, SandboxBubblewrap)

    temp_dir = Path(tempfile.mkdtemp(prefix="repl_"))
    try:
        # The executor needs to know the workspace path.
        # Under bwrap it's mounted at /workspace; otherwise it's the real host path.
        executor_workspace = "/workspace" if is_bwrap else str(workspace_path)

        input_data = {
            "code": code,
            "namespace": namespace,
            "import_statements": import_statements,
            "function_definitions": function_definitions,
            "user_id": user_id,
            "session_id": session_id,
            "workspace_path": executor_workspace,
        }
        (temp_dir / "input.pkl").write_bytes(pickle.dumps(input_data))

        command = [sys.executable, "-m", "agentic_patterns.core.repl.executor", str(temp_dir)]

        bind_mounts = [
            BindMount(workspace_path, "/workspace"),
            BindMount(temp_dir, str(temp_dir)),
        ]

        isolate_network = session_has_private_data(user_id, session_id)

        result = await sandbox.run(
            command,
            timeout=timeout,
            bind_mounts=bind_mounts,
            isolate_network=isolate_network,
            cwd=executor_workspace,
        )

        if result.timed_out:
            return SubprocessResult(
                state=CellState.TIMEOUT,
                outputs=[CellOutput(output_type=OutputType.ERROR, content=f"Cell execution timed out after {timeout} seconds")],
            )

        output_path = temp_dir / "output.pkl"
        if output_path.exists():
            return pickle.loads(output_path.read_bytes())

        error_msg = result.stderr.decode(errors="replace") if result.stderr else "Executor produced no output"
        return SubprocessResult(
            state=CellState.ERROR,
            outputs=[CellOutput(output_type=OutputType.ERROR, content=error_msg)],
        )
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)
