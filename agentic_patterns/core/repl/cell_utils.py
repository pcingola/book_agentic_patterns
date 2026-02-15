"""Utilities for cell execution: namespace filtering, function extraction, expression capture."""

import ast
import builtins
import pickle
import shutil
import types
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from agentic_patterns.core.repl.cell_output import CellOutput
from agentic_patterns.core.repl.enums import CellState
from agentic_patterns.core.repl.openpyxl_handler import filter_openpyxl_from_namespace

import logging

logger = logging.getLogger(__name__)


class SubprocessResult(BaseModel):
    """Result of cell execution in a subprocess."""

    state: CellState = CellState.COMPLETED
    outputs: list[CellOutput] = Field(default_factory=list)
    namespace: dict[str, Any] = Field(default_factory=dict)


def cleanup_temp_workbooks(user_id: str, session_id: str) -> None:
    """Clean up temporary workbook files."""
    from agentic_patterns.core.repl.sandbox import get_repl_data_dir

    temp_dir = get_repl_data_dir(user_id, session_id) / ".temp"
    if temp_dir.exists():
        try:
            shutil.rmtree(temp_dir)
            logger.info("Cleaned up temporary workbooks in %s", temp_dir)
        except Exception as e:
            logger.exception(
                "Failed to clean up temporary workbooks in %s: %s", temp_dir, e
            )


def execute_and_capture_last_expression(code: str, namespace: dict[str, Any]) -> Any:
    """Execute code and capture the value of the last expression if present."""
    try:
        parsed_ast = ast.parse(code)
        if parsed_ast.body and isinstance(parsed_ast.body[-1], ast.Expr):
            last_expr = ast.Expression(parsed_ast.body[-1].value)
            code_to_exec = ast.Module(body=parsed_ast.body[:-1], type_ignores=[])
            exec(compile(code_to_exec, "<string>", "exec"), namespace)
            return eval(compile(last_expr, "<string>", "eval"), namespace)
        else:
            exec(code, namespace)
            return None
    except SyntaxError:
        exec(code, namespace)
        return None


def extract_function_definitions(code: str) -> list[str]:
    """Extract function definitions from code as executable strings."""
    function_defs = []
    try:
        tree = ast.parse(code)
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                lines = code.split("\n")
                start_line = node.lineno - 1
                end_line = (
                    node.end_lineno if hasattr(node, "end_lineno") else start_line + 1
                )
                func_lines = lines[start_line:end_line]
                func_def = "\n".join(func_lines)
                function_defs.append(func_def)
    except SyntaxError:
        pass
    return function_defs


def filter_picklable_namespace(
    namespace: dict[str, Any],
    user_id: str | None = None,
    session_id: str | None = None,
    base_dir: Path | None = None,
) -> tuple[dict[str, Any], list[str]]:
    """Filter a namespace to only include picklable objects.

    Special handling for openpyxl Workbook objects: saves them to temp files
    and stores WorkbookReference objects instead.
    """
    builtin_functions = _get_builtin_function_names()

    temp_dir = get_temp_workbooks_dir(user_id, session_id, base_dir)
    openpyxl_items, openpyxl_keys, messages = filter_openpyxl_from_namespace(
        namespace, temp_dir
    )

    result = dict(openpyxl_items)

    for key, value in namespace.items():
        if key in openpyxl_keys:
            continue
        if (
            key in builtin_functions
            or key == "__builtins__"
            or isinstance(value, types.ModuleType)
        ):
            continue
        if is_picklable(value):
            result[key] = value
        else:
            hint = _get_unpicklable_hint(key, value)
            if hint:
                messages.append(hint)

    return result, messages


def get_temp_workbooks_dir(
    user_id: str | None = None,
    session_id: str | None = None,
    base_dir: Path | None = None,
) -> Path:
    """Get directory for temporary workbook storage.

    When called from the executor (inside sandbox), base_dir is the repl_dir
    passed via CLI argument. Otherwise, computes from DATA_DIR on the host.
    """
    if base_dir is not None:
        temp_dir = base_dir / ".temp" / "workbooks"
    else:
        from agentic_patterns.core.repl.sandbox import get_repl_data_dir

        if user_id is not None and session_id is not None:
            temp_dir = get_repl_data_dir(user_id, session_id) / ".temp" / "workbooks"
        else:
            from agentic_patterns.core.user_session import get_session_id, get_user_id

            temp_dir = (
                get_repl_data_dir(get_user_id(), get_session_id())
                / ".temp"
                / "workbooks"
            )

    temp_dir.mkdir(parents=True, exist_ok=True)
    return temp_dir


def is_picklable(obj: Any) -> bool:
    """Check if an object can be pickled AND unpickled."""
    try:
        data = pickle.dumps(obj)
        pickle.loads(data)
        return True
    except Exception:
        return False


def _get_builtin_function_names() -> set[str]:
    return set(
        filter(
            lambda x: isinstance(getattr(builtins, x, None), types.BuiltinFunctionType),
            dir(builtins),
        )
    )


def _get_unpicklable_hint(key: str, value: Any) -> str | None:
    """Get a helpful hint message for common unpicklable object types."""
    obj_type = type(value)
    type_name = obj_type.__name__
    module = getattr(obj_type, "__module__", "")

    if type_name == "function" and getattr(value, "__name__", "") == "<lambda>":
        return f"Note: '{key}' (lambda) not persisted - use 'def {key}(...)' instead"

    type_hints = {
        "TextIOWrapper": ("file handle", "reopen file in next cell"),
        "BufferedReader": ("file handle", "reopen file in next cell"),
        "BufferedWriter": ("file handle", "reopen file in next cell"),
        "FileIO": ("file handle", "reopen file in next cell"),
        "generator": (type_name, "recreate or convert to list"),
        "list_iterator": (type_name, "recreate or convert to list"),
        "dict_keyiterator": (type_name, "recreate or convert to list"),
        "range_iterator": (type_name, "recreate or convert to list"),
        "Thread": (type_name, "not persisted across cells"),
        "Process": (type_name, "not persisted across cells"),
        "Lock": (type_name, "not persisted across cells"),
        "RLock": (type_name, "not persisted across cells"),
        "Semaphore": (type_name, "not persisted across cells"),
    }

    if type_name in type_hints:
        label, hint = type_hints[type_name]
        return f"Note: '{key}' ({label}) not persisted - {hint}"

    if "connection" in type_name.lower() or "cursor" in type_name.lower():
        return f"Note: '{key}' ({type_name}) not persisted - reconnect in next cell"

    if type_name == "socket" or module == "socket":
        return (
            f"Note: '{key}' (socket) not persisted - recreate connection in next cell"
        )

    return None
