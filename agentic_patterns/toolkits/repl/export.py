"""Export a REPL notebook as a Jupyter .ipynb file."""

import json
from pathlib import Path, PurePosixPath

from agentic_patterns.core.config.config import SANDBOX_PREFIX
from agentic_patterns.core.repl.notebook import Notebook
from agentic_patterns.core.workspace import workspace_to_host_path


def export_notebook_as_ipynb(nb: Notebook, name_or_path: str) -> str:
    """Validate, resolve paths, and write the notebook as .ipynb.

    Accepts either a bare name (e.g. "analysis") which is placed under
    /workspace/, or an absolute sandbox path (e.g. "/workspace/sub/nb.ipynb").
    Returns the sandbox path string for use in response messages.
    """
    if not nb.cells:
        raise ValueError("No cells in the notebook. Execute some cells first.")

    if not name_or_path.endswith(".ipynb"):
        name_or_path = f"{name_or_path}.ipynb"

    sandbox_path = PurePosixPath(name_or_path)
    if not sandbox_path.is_absolute():
        sandbox_path = PurePosixPath(SANDBOX_PREFIX) / sandbox_path

    host_path = workspace_to_host_path(sandbox_path)
    _save_ipynb(nb, host_path)
    return str(sandbox_path)


def _save_ipynb(nb: Notebook, path: Path) -> None:
    """Write the notebook in Jupyter .ipynb format."""
    path.parent.mkdir(parents=True, exist_ok=True)
    ipynb = {
        "metadata": {
            "kernelspec": {
                "display_name": "Python 3",
                "language": "python",
                "name": "python3",
            },
            "language_info": {
                "codemirror_mode": {"name": "ipython", "version": 3},
                "file_extension": ".py",
                "mimetype": "text/x-python",
                "name": "python",
                "nbconvert_exporter": "python",
                "pygments_lexer": "ipython3",
                "version": "3.10.0",
            },
            "mcp_repl": {
                "user_id": nb.user_id,
                "session_id": nb.session_id,
                "created_at": nb.created_at.isoformat(),
                "updated_at": nb.updated_at.isoformat(),
            },
        },
        "nbformat": 4,
        "nbformat_minor": 5,
        "cells": [cell.to_ipynb() for cell in nb.cells],
    }
    with open(path, "w") as f:
        json.dump(ipynb, f, indent=2)
