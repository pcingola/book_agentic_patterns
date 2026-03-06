## Analysis tools

All analysis tools operate on **CSV or pickle files** in the workspace. Every tool takes an `input_file` path and references columns **by name** as string parameters. Multi-column parameters use comma-separated strings (e.g. `columns="revenue,profit"`). Modifying operations accept an optional `output_file`; if omitted, one is generated automatically.

Exploratory data analysis: list_dataframes, head, tail, shape, dtypes, columns, describe, info, missing_values, unique, nunique, value_counts, correlation, groupby (mean/count/sum), pivot_table, crosstab, filter_rows, sort_values, sample.

Statistics: t_test (one-sample, two-sample), chi_square, normality, correlation_test, anova, mann_whitney.

Transformations: min_max_scale, standard_scale, select_columns, drop_columns, rename_columns, one_hot_encode, log_transform.

ML: classification (logistic regression, decision trees, random forest, SVM, KNN, gradient boosting), regression, feature importance.
