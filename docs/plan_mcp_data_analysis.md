# Plan: Data Analysis MCP Server

## Context

The project has three MCP servers (template, todo, file_ops, sql) and needs a fourth: `data_analysis`. This server provides DataFrame-based EDA, statistical tests, data transformations, ML classification/regression, and feature importance analysis. The reference implementation at `~/aixplore/mcp-data-analysis/` has ~53 tools using a registry-based architecture with dynamic tool generation. We port this to the project's MCP patterns (workspace isolation, tool permissions, context result truncation, error classification, logging).

## Directory Structure

```
agentic_patterns/mcp/data_analysis/
    server.py                  # MCP server entry point
    tools.py                   # Tool registration + dynamic generation
    config.py                  # Constants (display rows, save format)
    enums.py                   # FileFormat, DisplayFormat
    models.py                  # OperationConfig dataclass
    executor.py                # execute_operation(): load -> run -> save -> format
    io.py                      # load_df, save_df with workspace isolation
    display.py                 # df2str
    ml_helpers.py              # train_and_fit_classifier/regressor, detect_model_type
    ops_eda.py                 # 17 EDA operations
    ops_stats.py               # 7 statistical test operations
    ops_transform.py           # 10 transformation operations
    ops_classification.py      # 6 classification operations
    ops_regression.py          # 8 regression operations
    ops_feature_importance.py  # 4 feature importance ops + helper functions
```

## Files

### 1. `config.py`
Simple constants: `DEFAULT_DISPLAY_ROWS = 10`, `DEFAULT_SAVE_FORMAT = "pickle"`.

### 2. `enums.py`
`FileFormat(str, Enum)` with CSV/PICKLE and `from_path()` classmethod. `DisplayFormat(str, Enum)` with CSV/MARKDOWN.

### 3. `models.py`
`OperationConfig` dataclass (name, category, func, parameters, returns_df, view_only, description). Ported from reference `base.py`.

### 4. `display.py`
`df2str()` function converting DataFrame to CSV string with optional row limit.

### 5. `io.py`
`load_df(workspace_path)` and `save_df(df, workspace_path)` using `workspace_to_host_path()` for isolation. `list_dataframe_files()` using `list_workspace_files()` with CSV/pickle patterns.

### 6. `ml_helpers.py`
Ported from reference `base.py`:
- `train_and_fit_classifier()` -- trains sklearn classifier, returns dict with accuracy/report/confusion_matrix
- `train_and_fit_regressor()` -- trains sklearn regressor, returns dict with mse/rmse/mae/r2
- `detect_model_type()` -- auto-detect classification vs regression
- Raises `ValueError` (not `AixToolError`) for non-numeric features -- the executor will convert to `ToolRetryError`.

### 7. `ops_eda.py` through `ops_feature_importance.py`
Port the six registry dicts from the reference. Each file defines a module-level dict mapping operation names to `OperationConfig` instances. The lambda functions are nearly identical; only the import paths change. `ops_feature_importance.py` also contains the helper functions (`encode_non_numeric_features`, `linear_feature_importance`, `random_forest_feature_importance`, `gradient_boosting_feature_importance`, `permutation_feature_importance`) since these are substantial and specific to this module.

### 8. `executor.py`
Core execution function:
```python
async def execute_operation(input_file, output_file, operation_name, parameters, ctx) -> str
```
Flow: load DataFrame via `io.load_df()` -> look up operation in combined registry -> call `op.func(df, **params)` -> if result is DataFrame and not view_only, save via `io.save_df()` (auto-generate output path if empty) -> if result is dict with "model" key, pickle model to output path -> format result to string -> return.

Error handling: `FileNotFoundError`, `KeyError`, `ValueError`, `TypeError`, `IndexError` -> `ToolRetryError`. Everything else -> `ToolFatalError`.

Result formatting: DataFrame -> shape + columns + preview via `df2str()`. Dict/list -> `json.dumps()`. String -> as-is. Model dict -> formatted metrics text.

### 9. `tools.py`
`register_tools(mcp)`:
1. Register `list_dataframes` manually with `@tool_permission(READ)`.
2. `get_all_operations()` combines all six registry dicts.
3. `generate_tool_function()` uses `exec()` to create async tool functions with typed parameters matching `OperationConfig.parameters`. Each generated function: logs via `ctx.info()`, builds param dict, calls `execute_operation()`.
4. Registration loop: for each operation, generate function, apply `@context_result()` and `@tool_permission(READ if view_only else WRITE)`, register via `mcp.tool()`.

### 10. `server.py`
Standard pattern:
```python
mcp = create_mcp_server("data_analysis", instructions="...")
register_tools(mcp)
```

### 11. `pyproject.toml` updates
Add: `scikit-learn>=1.6.0`, `scipy>=1.15.0`, `statsmodels>=0.14.0`.

## Key Adaptations from Reference

| Concern | Reference | This implementation |
|---------|-----------|-------------------|
| Path isolation | `aixtools` container_to_host_path | `workspace_to_host_path` |
| Errors | `AixToolError` | `ToolRetryError` / `ToolFatalError` |
| Truncation | Custom `check_returned_result_smart` | `@context_result()` decorator |
| Auth | `aixtools.mcp.create_mcp_server` | `core.mcp.create_mcp_server` (AuthSessionMiddleware) |
| Logging | `DfOperationLogger` to JSON file | `ctx.info()` per tool call |
| Permissions | None | `@tool_permission(READ/WRITE)` on every tool |
| Result classes | OperationResult/DataFrameResult/ModelResult | Plain string formatting |

The reference's `DfOperation` class, `DfOperationLogger`, `OperationResultSummary`, result classes, and `model_description.py` are replaced by a simpler `execute_operation()` function that formats results directly to string. The `@context_result()` decorator handles truncation. No separate result serialization layer needed.

## Verification

1. Run `fastmcp run agentic_patterns/mcp/data_analysis/server.py:mcp --transport http` to verify the server starts and all 53 tools register.
2. Run `uv pip install -e .` to install new dependencies.
3. Import check: `python -c "from agentic_patterns.mcp.data_analysis.server import mcp"`.
