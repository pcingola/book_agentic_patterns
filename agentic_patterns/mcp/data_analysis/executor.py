"""Core execution function for data analysis operations."""

import json
import pickle
from pathlib import PurePosixPath
from typing import Any

import pandas as pd

from agentic_patterns.core.mcp import ToolFatalError, ToolRetryError
from agentic_patterns.core.workspace import workspace_to_host_path
from agentic_patterns.mcp.data_analysis.display import df2str
from agentic_patterns.mcp.data_analysis.io import load_df, save_df
from agentic_patterns.mcp.data_analysis.models import OperationConfig
from agentic_patterns.mcp.data_analysis.ops_classification import CLASSIFICATION_OPERATIONS
from agentic_patterns.mcp.data_analysis.ops_eda import EDA_OPERATIONS
from agentic_patterns.mcp.data_analysis.ops_feature_importance import FEATURE_IMPORTANCE_OPERATIONS
from agentic_patterns.mcp.data_analysis.ops_regression import REGRESSION_OPERATIONS
from agentic_patterns.mcp.data_analysis.ops_stats import STATS_OPERATIONS
from agentic_patterns.mcp.data_analysis.ops_transform import TRANSFORM_OPERATIONS

_ALL_OPERATIONS: dict[str, OperationConfig] | None = None


def get_all_operations() -> dict[str, OperationConfig]:
    """Get combined registry of all operations."""
    global _ALL_OPERATIONS
    if _ALL_OPERATIONS is None:
        _ALL_OPERATIONS = {}
        _ALL_OPERATIONS.update(EDA_OPERATIONS)
        _ALL_OPERATIONS.update(STATS_OPERATIONS)
        _ALL_OPERATIONS.update(TRANSFORM_OPERATIONS)
        _ALL_OPERATIONS.update(CLASSIFICATION_OPERATIONS)
        _ALL_OPERATIONS.update(REGRESSION_OPERATIONS)
        _ALL_OPERATIONS.update(FEATURE_IMPORTANCE_OPERATIONS)
    return _ALL_OPERATIONS


def _format_result(result: Any, op: OperationConfig, output_file: str | None) -> str:
    """Format operation result to string for tool return."""
    if isinstance(result, pd.DataFrame):
        shape = f"Shape: {result.shape[0]} rows x {result.shape[1]} columns"
        cols = f"Columns: {', '.join(result.columns.tolist())}"
        preview = df2str(result)
        parts = [shape, cols]
        if output_file:
            parts.append(f"Saved to: {output_file}")
        parts.append(f"\nPreview:\n{preview}")
        return "\n".join(parts)

    if isinstance(result, dict):
        if "model" in result:
            # ML model result -- format metrics
            lines = []
            for k, v in result.items():
                if k == "model":
                    lines.append(f"Model: {type(v).__name__}")
                elif k == "confusion_matrix":
                    lines.append(f"Confusion Matrix:\n{json.dumps(v, indent=2)}")
                else:
                    lines.append(f"{k}: {v}")
            if output_file:
                lines.append(f"Model saved to: {output_file}")
            return "\n".join(lines)
        return json.dumps(result, indent=2, default=str)

    if isinstance(result, list):
        return json.dumps(result, indent=2, default=str)

    return str(result)


async def execute_operation(input_file: str, output_file: str | None, operation_name: str, parameters: dict[str, Any]) -> str:
    """Execute a data analysis operation.

    Loads the DataFrame, runs the operation, saves results if applicable, and returns a formatted string.
    """
    operations = get_all_operations()
    if operation_name not in operations:
        raise ToolRetryError(f"Unknown operation: {operation_name}. Available: {list(operations.keys())}")

    op = operations[operation_name]

    try:
        df = load_df(input_file)
        result = op.func(df, **parameters)

        # Save result if operation produces output
        if not op.view_only:
            if isinstance(result, pd.DataFrame) and output_file:
                save_df(result, output_file)
            elif isinstance(result, dict) and "model" in result and output_file:
                host_path = workspace_to_host_path(PurePosixPath(output_file))
                host_path.parent.mkdir(parents=True, exist_ok=True)
                with open(host_path, "wb") as f:
                    pickle.dump(result, f)

        return _format_result(result, op, output_file)

    except (FileNotFoundError, KeyError, ValueError, TypeError, IndexError) as e:
        raise ToolRetryError(str(e)) from e
    except (ToolRetryError, ToolFatalError):
        raise
    except Exception as e:
        raise ToolFatalError(f"Operation '{operation_name}' failed unexpectedly: {e}") from e
