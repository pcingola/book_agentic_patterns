"""Core execution function for data visualization operations."""

from typing import Any

import matplotlib
import matplotlib.pyplot as plt

from agentic_patterns.core.mcp import ToolFatalError, ToolRetryError
from agentic_patterns.mcp.data_viz.io import load_df, save_figure
from agentic_patterns.mcp.data_viz.models import PlotConfig
from agentic_patterns.mcp.data_viz.ops_basic import BASIC_OPERATIONS
from agentic_patterns.mcp.data_viz.ops_categorical import CATEGORICAL_OPERATIONS
from agentic_patterns.mcp.data_viz.ops_distribution import DISTRIBUTION_OPERATIONS
from agentic_patterns.mcp.data_viz.ops_matrix import MATRIX_OPERATIONS

matplotlib.use("Agg")

_ALL_OPERATIONS: dict[str, PlotConfig] | None = None


def get_all_operations() -> dict[str, PlotConfig]:
    """Get combined registry of all plot operations."""
    global _ALL_OPERATIONS
    if _ALL_OPERATIONS is None:
        _ALL_OPERATIONS = {}
        _ALL_OPERATIONS.update(BASIC_OPERATIONS)
        _ALL_OPERATIONS.update(DISTRIBUTION_OPERATIONS)
        _ALL_OPERATIONS.update(CATEGORICAL_OPERATIONS)
        _ALL_OPERATIONS.update(MATRIX_OPERATIONS)
    return _ALL_OPERATIONS


async def execute_plot(input_file: str, output_file: str | None, plot_name: str, parameters: dict[str, Any]) -> str:
    """Execute a plot operation: load CSV, create figure, save image, return path."""
    operations = get_all_operations()
    if plot_name not in operations:
        raise ToolRetryError(f"Unknown plot: {plot_name}. Available: {list(operations.keys())}")

    op = operations[plot_name]

    try:
        df = load_df(input_file)
        fig = op.func(df, **parameters)

        if output_file is None:
            base = input_file.rsplit(".", 1)[0]
            output_file = f"{base}_{plot_name}.png"

        workspace_path = save_figure(fig, output_file)
        return f"Plot saved to: {workspace_path}"

    except (FileNotFoundError, KeyError, ValueError, TypeError, IndexError) as e:
        plt.close("all")
        raise ToolRetryError(str(e)) from e
    except (ToolRetryError, ToolFatalError):
        plt.close("all")
        raise
    except Exception as e:
        plt.close("all")
        raise ToolFatalError(f"Plot '{plot_name}' failed unexpectedly: {e}") from e
