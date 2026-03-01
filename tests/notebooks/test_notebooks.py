"""Smoke tests that execute Jupyter notebooks end-to-end."""

import os
import unittest
from pathlib import Path

import nbformat
from nbconvert.preprocessors import ExecutePreprocessor

EXAMPLES_DIR = Path(__file__).resolve().parents[2] / "agentic_patterns" / "examples"

REQUIRES_SERVER = {
    "a2a/example_a2a_client.ipynb",
    "a2a/example_a2a_client_v2.ipynb",
    "mcp/example_agent_mcp_client_http.ipynb",
    "mcp/example_agent_mcp_client_stdio.ipynb",
    "mcp/example_mcp_features.ipynb",
    "mcp/example_mcp_stdio.ipynb",
    "execution_infrastructure/example_mcp_isolation.ipynb",
    "the_complete_agent/example_agent_infrastructure.ipynb",
    "evals/example_doctors.ipynb",
}


class TestNotebooks(unittest.TestCase):
    def test_standalone_notebooks(self) -> None:
        notebook_filter = os.environ.get("NOTEBOOK_FILTER")

        if notebook_filter:
            path = EXAMPLES_DIR / notebook_filter
            self.assertTrue(path.exists(), f"Notebook not found: {path}")
            notebooks = [path]
        else:
            notebooks = sorted(EXAMPLES_DIR.rglob("*.ipynb"))
            self.assertTrue(notebooks, f"No notebooks found in {EXAMPLES_DIR}")

        for path in notebooks:
            rel = str(path.relative_to(EXAMPLES_DIR))
            if rel in REQUIRES_SERVER:
                continue

            with self.subTest(notebook=rel):
                nb = nbformat.read(path, as_version=4)
                ep = ExecutePreprocessor(timeout=600, kernel_name="python3")
                ep.preprocess(nb, {"metadata": {"path": str(path.parent)}})
