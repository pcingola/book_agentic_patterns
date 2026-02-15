"""Standalone executor script that runs inside a sandbox.

Entry point: python -m agentic_patterns.core.repl.executor <repl_dir> <cell_id>

Reads pickled input from <repl_dir>/<cell_id>_input.pkl, executes the code,
and writes pickled SubprocessResult to <repl_dir>/<cell_id>_output.pkl.
"""

import io
import os
import pickle
import sys
import traceback
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

from agentic_patterns.core.repl.cell_output import CellOutput
from agentic_patterns.core.repl.cell_utils import (
    SubprocessResult,
    execute_and_capture_last_expression,
    filter_picklable_namespace,
)
from agentic_patterns.core.repl.enums import CellState, OutputType
from agentic_patterns.core.repl.matplotlib_backend import (
    capture_matplotlib_figures,
    configure_matplotlib,
    reset_matplotlib,
)
from agentic_patterns.core.repl.openpyxl_handler import restore_workbook_references


def main() -> None:
    repl_dir = Path(sys.argv[1])
    cell_id = sys.argv[2]

    input_path = repl_dir / f"{cell_id}_input.pkl"
    output_path = repl_dir / f"{cell_id}_output.pkl"

    input_data = pickle.loads(input_path.read_bytes())

    code = input_data["code"]
    namespace = input_data["namespace"]
    import_statements = input_data["import_statements"]
    function_definitions = input_data["function_definitions"]
    user_id = input_data["user_id"]
    session_id = input_data["session_id"]
    workspace_path = Path(input_data["workspace_path"])

    result = SubprocessResult()
    stdout_buf, stderr_buf = io.StringIO(), io.StringIO()

    if workspace_path.exists():
        os.chdir(str(workspace_path))

    try:
        restore_workbook_references(namespace)
        original_show = configure_matplotlib()

        with redirect_stdout(stdout_buf), redirect_stderr(stderr_buf):
            for import_stmt in import_statements:
                try:
                    exec(import_stmt, namespace)
                except Exception as e:
                    print(f"Failed to execute import statement '{import_stmt}': {e}")

            for func_def in function_definitions or []:
                try:
                    exec(func_def, namespace)
                except Exception as e:
                    print(f"Failed to execute function definition: {e}")

            last_value = execute_and_capture_last_expression(code, namespace)

            if last_value is not None:
                result.outputs.append(
                    CellOutput(output_type=OutputType.TEXT, content=repr(last_value))
                )

            if stdout_text := stdout_buf.getvalue():
                result.outputs.append(
                    CellOutput(output_type=OutputType.TEXT, content=stdout_text)
                )
            if stderr_text := stderr_buf.getvalue():
                result.outputs.append(
                    CellOutput(output_type=OutputType.ERROR, content=stderr_text)
                )

            figure_outputs = capture_matplotlib_figures()
            result.outputs.extend(figure_outputs)
            reset_matplotlib(original_show)

    except Exception as e:
        result.state = CellState.ERROR
        error_msg = f"{type(e).__name__}: {str(e)}\n{traceback.format_exc()}"
        result.outputs.append(
            CellOutput(output_type=OutputType.ERROR, content=error_msg)
        )

    result.namespace, namespace_messages = filter_picklable_namespace(
        namespace, user_id, session_id, workspace_path
    )
    if namespace_messages:
        result.outputs.append(
            CellOutput(
                output_type=OutputType.TEXT, content="\n".join(namespace_messages)
            )
        )

    output_path.write_bytes(pickle.dumps(result))


if __name__ == "__main__":
    main()
