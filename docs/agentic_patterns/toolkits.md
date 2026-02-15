# Toolkits

Toolkits (`agentic_patterns.toolkits`) contain pure Python business logic with no framework dependency. They sit between connectors (data source access) and tool wrappers (framework integration). Each toolkit provides models and operations that PydanticAI tools and MCP servers delegate to.

## Todo

`agentic_patterns.toolkits.todo` manages hierarchical task lists with workspace persistence.

`TodoState` enum: PENDING, IN_PROGRESS, COMPLETED, FAILED.

`TodoItem` is a Pydantic model representing a task with `description`, `state`, and optional `subtasks`. Items use hierarchical IDs (e.g., "1", "1.1", "1.1.2") for nesting. `TodoList` is a collection of items with `load()`/`save()` for JSON persistence at `/workspace/todo/tasks.json`.

Operations (`todo_add`, `todo_add_many`, `todo_create_list`, `todo_delete`, `todo_show`, `todo_update_status`) work with an in-memory cache keyed by (user_id, session_id), persisting to disk on mutation.

## Data Analysis

`agentic_patterns.toolkits.data_analysis` provides DataFrame operations via an operation registry pattern.

`get_all_operations()` returns a dict mapping operation names to `OperationConfig` objects. 53 operations across six categories:

| Category | Count | Examples |
|---|---|---|
| EDA | 17 | head, tail, shape, describe, info, dtypes, columns, unique, nunique, value_counts, correlation, missing_values, groupby_mean, groupby_count, groupby_sum, pivot_table, crosstab |
| Transform | 11 | min_max_scale, standard_scale, select_columns, drop_columns, rename_columns, one_hot_encode, log_transform, sort_values, sample, filter_rows |
| Statistics | 7 | t_test_one_sample, t_test_two_sample, chi_square_test, normality_test, correlation_test, anova_one_way, mann_whitney_u_test |
| Classification | 6 | logistic_regression, random_forest, decision_tree, gradient_boosting, knn, svm |
| Regression | 8 | linear, ridge, lasso, random_forest, decision_tree, gradient_boosting, knn, svr |
| Feature importance | 4 | gradient_boosting, linear, permutation, random_forest |

`execute_operation(input_file, output_file, operation_name, parameters)` loads a DataFrame from the workspace, executes the named operation, saves results (CSV for DataFrames, pickle for models), and returns a formatted string summary. Supporting utilities: `load_df()` and `save_df()` handle workspace I/O, `list_dataframe_files()` discovers available files.

## Data Visualization

`agentic_patterns.toolkits.data_viz` follows the same registry pattern for matplotlib plots.

`get_all_operations()` returns a dict of `PlotConfig` objects. 12 plots across four categories:

| Category | Plots |
|---|---|
| Basic | line_plot, bar_plot, scatter_plot, area_plot |
| Distribution | histogram, box_plot, violin_plot, kde_plot |
| Categorical | count_plot, pie_chart |
| Matrix | heatmap, pair_plot |

`execute_plot(input_file, output_file, plot_name, parameters)` loads a DataFrame, creates a matplotlib figure using the Agg backend, saves a PNG to the workspace, and returns the workspace path. Configuration defaults: DPI=150, figure size 10x6, seaborn "muted" palette.

## Format Conversion

`agentic_patterns.toolkits.format_conversion` converts between document formats.

`InputFormat` enum: CSV, DOCX, MD, PDF, PPTX, XLSX. `OutputFormat` enum: CSV, DOCX, HTML, MD, PDF.

`convert(input_path, output_format, output_path=None)` dispatches by input extension and output format. Returns a string for text outputs (MD, CSV) or a `Path` for binary outputs (PDF, DOCX, HTML). Non-markdown inputs going to binary formats use a two-stage pipeline: ingest to markdown first, then export via mistune/xhtml2pdf/htmldocx.
