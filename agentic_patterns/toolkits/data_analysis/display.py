"""DataFrame display formatting."""

import pandas as pd

from agentic_patterns.toolkits.data_analysis.config import DEFAULT_DISPLAY_ROWS


def df2str(df: pd.DataFrame, max_rows: int | None = DEFAULT_DISPLAY_ROWS) -> str:
    """Convert a DataFrame to a CSV string with optional row limit."""
    if df is None or df.empty:
        return "Empty DataFrame"
    if max_rows is not None:
        df = df.head(max_rows)
    return df.to_csv(index=True)
