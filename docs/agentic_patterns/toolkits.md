# Toolkits

Toolkits (`agentic_patterns.toolkits`) contain pure Python business logic with no framework dependency. They sit between connectors (data source access) and tool wrappers (framework integration). Each toolkit provides models and operations that PydanticAI tools and MCP servers delegate to.

## Todo

`agentic_patterns.toolkits.todo` manages hierarchical task lists with workspace persistence.

`TodoState` enum: PENDING, IN_PROGRESS, COMPLETED, FAILED.

`TodoItem` is a Pydantic model representing a task with `description`, `state`, and optional `subtasks`. Items use hierarchical IDs (e.g., "1", "1.1", "1.1.2") for nesting. `TodoList` is a collection of items with `load()`/`save()` for JSON persistence at `/workspace/todo/tasks.json`.

Operations (`todo_add`, `todo_add_many`, `todo_create_list`, `todo_delete`, `todo_show`, `todo_update_status`) work with an in-memory cache keyed by (user_id, session_id), persisting to disk on mutation.

## Data Analysis

`agentic_patterns.toolkits.data_analysis` provides DataFrame operations via an operation registry pattern.

`get_all_operations()` returns a dict mapping operation names to `OperationConfig` objects. Operations are registered across six categories: EDA (describe, info, dtypes, shape, missing values), statistics (correlation, distribution), transforms (filter, sort, group, pivot, merge), classification, regression, and feature importance.

`execute_operation(input_file, output_file, operation_name, parameters)` loads a DataFrame from the workspace, executes the named operation, saves results (CSV/Excel for DataFrames, pickle for models), and returns a formatted string summary.

## Data Visualization

`agentic_patterns.toolkits.data_viz` follows the same registry pattern for matplotlib plots.

`get_all_operations()` returns a dict of `PlotConfig` objects across four categories: basic (line, bar, scatter), distribution (histogram, box, violin), categorical (count, strip, swarm), and matrix (heatmap, pair).

`execute_plot(input_file, output_file, plot_name, parameters)` loads a DataFrame, creates a matplotlib figure using the Agg backend, saves a PNG to the workspace, and returns the workspace path.

## Format Conversion

`agentic_patterns.toolkits.format_conversion` converts between document formats.

`InputFormat` enum: CSV, DOCX, MD, PDF, PPTX, XLSX. `OutputFormat` enum: CSV, DOCX, HTML, MD, PDF.

`convert(input_path, output_format, output_path=None)` dispatches by input extension and output format. Returns a string for text outputs (MD, CSV) or a `Path` for binary outputs (PDF, DOCX, HTML). Non-markdown inputs going to binary formats use a two-stage pipeline: ingest to markdown first, then export via pandoc/weasyprint.
