"""Transform operations registry."""

import numpy as np
import pandas as pd
from sklearn.preprocessing import MinMaxScaler, StandardScaler

from agentic_patterns.toolkits.data_analysis.models import OperationConfig

TRANSFORM_OPERATIONS = {
    "min_max_scale": OperationConfig(
        name="min_max_scale",
        category="transform",
        func=lambda df, columns=None: df.copy().assign(**{col: MinMaxScaler().fit_transform(df[[col]]).flatten() for col in (columns if columns else df.select_dtypes(include=["number"]).columns)}),
        parameters={"columns": None},
        returns_df=True,
        view_only=False,
        description="Apply Min-Max scaling to selected columns (default: all numeric columns)",
    ),
    "standard_scale": OperationConfig(
        name="standard_scale",
        category="transform",
        func=lambda df, columns=None: df.copy().assign(**{col: StandardScaler().fit_transform(df[[col]]).flatten() for col in (columns if columns else df.select_dtypes(include=["number"]).columns)}),
        parameters={"columns": None},
        returns_df=True,
        view_only=False,
        description="Apply Standard scaling (z-score normalization) to selected columns (default: all numeric columns)",
    ),
    "select_columns": OperationConfig(
        name="select_columns",
        category="transform",
        func=lambda df, columns: df[columns],
        parameters={"columns": []},
        returns_df=True,
        view_only=False,
        description="Select only specified columns from dataframe",
    ),
    "drop_columns": OperationConfig(
        name="drop_columns",
        category="transform",
        func=lambda df, columns: df.drop(columns=columns),
        parameters={"columns": []},
        returns_df=True,
        view_only=False,
        description="Drop specified columns from dataframe",
    ),
    "rename_columns": OperationConfig(
        name="rename_columns",
        category="transform",
        func=lambda df, column_mapping: df.rename(columns=column_mapping),
        parameters={"column_mapping": {}},
        returns_df=True,
        view_only=False,
        description="Rename columns using a mapping dictionary",
    ),
    "one_hot_encode": OperationConfig(
        name="one_hot_encode",
        category="transform",
        func=lambda df, columns=None, drop_first=False: pd.get_dummies(df, columns=columns if columns else df.select_dtypes(include=["object", "category"]).columns.tolist(), drop_first=drop_first),
        parameters={"columns": None, "drop_first": False},
        returns_df=True,
        view_only=False,
        description="Convert categorical variables to dummy/indicator variables",
    ),
    "log_transform": OperationConfig(
        name="log_transform",
        category="transform",
        func=lambda df, columns=None: df.assign(**{col: np.log(df[col]) for col in (columns if columns else df.select_dtypes(include=["number"]).columns.tolist()) if df[col].dtype in ["int64", "float64"] and (df[col] > 0).all()}),
        parameters={"columns": None},
        returns_df=True,
        view_only=False,
        description="Apply logarithmic transformation to numeric columns (only positive values)",
    ),
    "sort_values": OperationConfig(
        name="sort_values",
        category="transform",
        func=lambda df, by, ascending=True: df.sort_values(by=by, ascending=ascending),
        parameters={"by": str, "ascending": True},
        returns_df=True,
        view_only=False,
        description="Sort dataframe by specified column(s)",
    ),
    "sample": OperationConfig(
        name="sample",
        category="transform",
        func=lambda df, n=None, frac=None, random_state=None: df.sample(n=n, frac=frac, random_state=random_state),
        parameters={"n": None, "frac": None, "random_state": None},
        returns_df=True,
        view_only=False,
        description="Random sample of rows from dataframe",
    ),
    "filter_rows": OperationConfig(
        name="filter_rows",
        category="transform",
        func=lambda df, condition: df.query(condition),
        parameters={"condition": str},
        returns_df=True,
        view_only=False,
        description="Filter rows using pandas query syntax (e.g., 'column > 5')",
    ),
}
