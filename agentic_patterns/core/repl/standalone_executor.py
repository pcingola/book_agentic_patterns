"""Standalone executor source written to repl_dir at runtime for Docker execution.

The EXECUTOR_SOURCE string is a self-contained Python script that runs inside the
Docker container with zero agentic_patterns imports. It uses only stdlib plus
container-installed packages (matplotlib, openpyxl, PIL).

IPC protocol: reads plain dict from <cell_id>_input.pkl, writes plain dict to
<cell_id>_output.pkl. The host converts dicts back to pydantic models.
"""

EXECUTOR_SOURCE = '''\
import ast
import base64
import builtins
import io
import os
import pickle
import sys
import traceback
import types
from contextlib import redirect_stderr, redirect_stdout
from datetime import datetime
from pathlib import Path

REPL_DIR = Path("/repl")
_INTERNAL_MARKER = "_executor.py"


def _make_output(output_type, content, timestamp=None):
    return {
        "output_type": output_type,
        "content": content,
        "timestamp": timestamp or datetime.now().isoformat(),
    }


# -- matplotlib ----------------------------------------------------------------

def _configure_matplotlib():
    try:
        import matplotlib.pyplot as plt
        plt.switch_backend("agg")
        original_show = plt.show
        plt.show = lambda *a, **kw: None
        return original_show
    except ImportError:
        return None


def _capture_matplotlib_figures():
    try:
        import matplotlib.pyplot as plt
    except ImportError:
        return []
    outputs = []
    for fig_num in plt.get_fignums():
        fig = plt.figure(fig_num)
        fig_w, fig_h = fig.get_size_inches()
        dpi = fig.dpi
        buf = io.BytesIO()
        fig.savefig(buf, format="png")
        buf.seek(0)
        img_data = {
            "data": base64.b64encode(buf.read()).decode(),
            "format": "png",
            "width": int(fig_w * dpi),
            "height": int(fig_h * dpi),
            "source": "matplotlib",
            "metadata": {"dpi": int(dpi)},
        }
        outputs.append(_make_output("IMAGE", img_data))
    plt.close("all")
    return outputs


def _reset_matplotlib(original_show):
    if original_show is None:
        return
    try:
        import matplotlib.pyplot as plt
        plt.show = original_show
    except ImportError:
        pass


# -- openpyxl ------------------------------------------------------------------

def _is_openpyxl_workbook(obj):
    t = type(obj)
    return (
        t.__name__ == "Workbook"
        and getattr(t, "__module__", "").startswith("openpyxl.")
        and hasattr(obj, "active")
        and hasattr(obj, "save")
    )


def _is_saveable_workbook(obj):
    return (
        _is_openpyxl_workbook(obj)
        and not getattr(obj, "read_only", False)
        and not getattr(obj, "write_only", False)
    )


def _is_wb_ref(obj):
    return isinstance(obj, dict) and obj.get("ref_type") == "WorkbookReference"


def _is_openpyxl_worksheet(obj):
    t = type(obj)
    return (
        t.__name__ == "Worksheet"
        and getattr(t, "__module__", "").startswith("openpyxl.")
        and hasattr(obj, "parent")
        and hasattr(obj, "cell")
    )


def _is_openpyxl_object(obj):
    return getattr(type(obj), "__module__", "").startswith("openpyxl.")


def _load_wb_from_ref(ref):
    import openpyxl
    if isinstance(ref, dict) and "temp_path" in ref:
        return openpyxl.load_workbook(ref["temp_path"])
    raise ValueError(f"Expected dict with temp_path, got {type(ref)}")


def _restore_workbook_references(namespace):
    for key, value in list(namespace.items()):
        if _is_wb_ref(value):
            try:
                namespace[key] = _load_wb_from_ref(value)
            except Exception:
                pass


def _save_workbook(workbook, var_name, temp_dir):
    temp_path = temp_dir / f"{var_name}.xlsx"
    workbook.save(str(temp_path))
    return {"ref_type": "WorkbookReference", "temp_path": str(temp_path), "var_name": var_name}


def _filter_openpyxl(namespace, temp_dir):
    result = {}
    handled = set()
    messages = []
    for key, value in namespace.items():
        if _is_saveable_workbook(value):
            result[key] = _save_workbook(value, key, temp_dir)
            handled.add(key)
        elif _is_openpyxl_workbook(value):
            mode = "read-only" if getattr(value, "read_only", False) else "write-only"
            messages.append("Note: " + mode + " workbook " + repr(key) + " not persisted (cannot be serialized)")
            handled.add(key)
        elif _is_wb_ref(value):
            try:
                wb = _load_wb_from_ref(value)
                result[key] = _save_workbook(wb, key, temp_dir)
            except Exception:
                pass
            handled.add(key)
        elif _is_openpyxl_worksheet(value):
            parent_wb = getattr(value, "parent", None)
            wb_var = None
            if parent_wb is not None:
                for k, v in namespace.items():
                    if v is parent_wb:
                        wb_var = k
                        break
            if wb_var:
                messages.append("Note: worksheet " + repr(key) + " not persisted - re-access via: " + key + " = " + wb_var + ".active")
            else:
                messages.append("Note: worksheet " + repr(key) + " not persisted - re-access via workbook in next cell")
            handled.add(key)
        elif _is_openpyxl_object(value):
            handled.add(key)
    return result, handled, messages


# -- namespace filtering -------------------------------------------------------

def _is_picklable(obj):
    try:
        data = pickle.dumps(obj)
        pickle.loads(data)
        return True
    except Exception:
        return False


def _get_builtin_names():
    return set(
        name for name in dir(builtins)
        if isinstance(getattr(builtins, name, None), types.BuiltinFunctionType)
    )


_UNPICKLABLE_HINTS = {
    "TextIOWrapper": ("file handle", "reopen file in next cell"),
    "BufferedReader": ("file handle", "reopen file in next cell"),
    "BufferedWriter": ("file handle", "reopen file in next cell"),
    "FileIO": ("file handle", "reopen file in next cell"),
    "generator": ("generator", "recreate or convert to list"),
    "list_iterator": ("list_iterator", "recreate or convert to list"),
    "dict_keyiterator": ("dict_keyiterator", "recreate or convert to list"),
    "range_iterator": ("range_iterator", "recreate or convert to list"),
    "Thread": ("Thread", "not persisted across cells"),
    "Process": ("Process", "not persisted across cells"),
    "Lock": ("Lock", "not persisted across cells"),
    "RLock": ("RLock", "not persisted across cells"),
    "Semaphore": ("Semaphore", "not persisted across cells"),
}


def _get_unpicklable_hint(key, value):
    obj_type = type(value)
    type_name = obj_type.__name__
    module = getattr(obj_type, "__module__", "")
    if type_name == "function" and getattr(value, "__name__", "") == "<lambda>":
        return "Note: " + repr(key) + " (lambda) not persisted - use def instead"
    if type_name in _UNPICKLABLE_HINTS:
        label, hint = _UNPICKLABLE_HINTS[type_name]
        return "Note: " + repr(key) + " (" + label + ") not persisted - " + hint
    if "connection" in type_name.lower() or "cursor" in type_name.lower():
        return "Note: " + repr(key) + " (" + type_name + ") not persisted - reconnect in next cell"
    if type_name == "socket" or module == "socket":
        return "Note: " + repr(key) + " (socket) not persisted - recreate connection in next cell"
    return None


def _filter_picklable_namespace(namespace, base_dir):
    builtin_names = _get_builtin_names()
    temp_dir = base_dir / ".temp" / "workbooks"
    temp_dir.mkdir(parents=True, exist_ok=True)
    openpyxl_items, openpyxl_keys, messages = _filter_openpyxl(namespace, temp_dir)
    result = dict(openpyxl_items)
    for key, value in namespace.items():
        if key in openpyxl_keys:
            continue
        if key in builtin_names or key == "__builtins__" or isinstance(value, types.ModuleType):
            continue
        if _is_picklable(value):
            result[key] = value
        else:
            hint = _get_unpicklable_hint(key, value)
            if hint:
                messages.append(hint)
    return result, messages


# -- code execution ------------------------------------------------------------

def _execute_and_capture_last(code, namespace):
    try:
        parsed = ast.parse(code)
        if parsed.body and isinstance(parsed.body[-1], ast.Expr):
            last_expr = ast.Expression(parsed.body[-1].value)
            rest = ast.Module(body=parsed.body[:-1], type_ignores=[])
            exec(compile(rest, "<string>", "exec"), namespace)
            return eval(compile(last_expr, "<string>", "eval"), namespace)
        else:
            exec(code, namespace)
            return None
    except SyntaxError:
        exec(code, namespace)
        return None


def _format_cell_error(exc, code):
    tb = traceback.extract_tb(exc.__traceback__)
    user_frames = [f for f in tb if _INTERNAL_MARKER not in f.filename]
    lines = [type(exc).__name__ + ": " + str(exc)]
    if user_frames:
        lines.append("Traceback (user code):")
        for frame in user_frames:
            lines.append("  File " + repr(frame.filename) + ", line " + str(frame.lineno) + ", in " + frame.name)
            if frame.line:
                lines.append("    " + frame.line)
    lines.append("")
    lines.append("Cell code:")
    for line in code.splitlines():
        lines.append("  " + line)
    return chr(10).join(lines)


def main():
    cell_id = sys.argv[1]
    input_path = REPL_DIR / f"{cell_id}_input.pkl"
    output_path = REPL_DIR / f"{cell_id}_output.pkl"

    input_data = pickle.loads(input_path.read_bytes())

    code = input_data["code"]
    namespace = input_data["namespace"]
    import_statements = input_data["import_statements"]
    function_definitions = input_data["function_definitions"]
    workspace_path = Path(input_data["workspace_path"])

    state = "COMPLETED"
    outputs = []
    stdout_buf, stderr_buf = io.StringIO(), io.StringIO()

    if workspace_path.exists():
        os.chdir(str(workspace_path))

    try:
        _restore_workbook_references(namespace)
        original_show = _configure_matplotlib()

        with redirect_stdout(stdout_buf), redirect_stderr(stderr_buf):
            for stmt in import_statements:
                try:
                    exec(stmt, namespace)
                except Exception as e:
                    print("Failed to execute import statement " + repr(stmt) + ": " + str(e))

            for func_def in function_definitions or []:
                try:
                    exec(func_def, namespace)
                except Exception as e:
                    print("Failed to execute function definition: " + str(e))

            last_value = _execute_and_capture_last(code, namespace)

            if last_value is not None:
                outputs.append(_make_output("TEXT", repr(last_value)))

            if stdout_text := stdout_buf.getvalue():
                outputs.append(_make_output("TEXT", stdout_text))
            if stderr_text := stderr_buf.getvalue():
                outputs.append(_make_output("ERROR", stderr_text))

            outputs.extend(_capture_matplotlib_figures())
            _reset_matplotlib(original_show)

    except Exception as e:
        state = "ERROR"
        outputs.append(_make_output("ERROR", _format_cell_error(e, code)))

    filtered_ns, ns_messages = _filter_picklable_namespace(namespace, REPL_DIR)
    if ns_messages:
        outputs.append(_make_output("TEXT", chr(10).join(ns_messages)))

    result = {"state": state, "outputs": outputs, "namespace": filtered_ns}
    output_path.write_bytes(pickle.dumps(result))


if __name__ == "__main__":
    main()
'''
