"""Matrix plot operations: heatmap, pair_plot."""

import matplotlib.figure
import matplotlib.pyplot as plt
import numpy as np
import seaborn as sns

from agentic_patterns.toolkits.data_viz.config import DEFAULT_FIGSIZE_HEIGHT, DEFAULT_FIGSIZE_WIDTH, DEFAULT_PALETTE, DEFAULT_STYLE
from agentic_patterns.toolkits.data_viz.models import PlotConfig


def _heatmap(df, title=None, xlabel=None, ylabel=None, figsize_width=DEFAULT_FIGSIZE_WIDTH, figsize_height=DEFAULT_FIGSIZE_HEIGHT, style=DEFAULT_STYLE, palette=DEFAULT_PALETTE, columns=None, annot=True, fmt=".2f") -> matplotlib.figure.Figure:
    sns.set_style(style)
    fig, ax = plt.subplots(figsize=(figsize_width, figsize_height))
    if columns:
        cols = [c.strip() for c in columns.split(",")] if isinstance(columns, str) else columns
        corr = df[cols].select_dtypes(include=[np.number]).corr()
    else:
        corr = df.select_dtypes(include=[np.number]).corr()
    sns.heatmap(corr, annot=annot, fmt=fmt, cmap=palette, ax=ax)
    if title:
        ax.set_title(title)
    if xlabel:
        ax.set_xlabel(xlabel)
    if ylabel:
        ax.set_ylabel(ylabel)
    fig.tight_layout()
    return fig


def _pair_plot(df, title=None, figsize_width=DEFAULT_FIGSIZE_WIDTH, figsize_height=DEFAULT_FIGSIZE_HEIGHT, style=DEFAULT_STYLE, palette=DEFAULT_PALETTE, columns=None, hue_column=None) -> matplotlib.figure.Figure:
    sns.set_style(style)
    if columns:
        cols = [c.strip() for c in columns.split(",")] if isinstance(columns, str) else columns
        if hue_column and hue_column not in cols:
            cols.append(hue_column)
        data = df[cols]
    else:
        data = df
    g = sns.pairplot(data, hue=hue_column, palette=palette, height=figsize_height / 3)
    if title:
        g.figure.suptitle(title, y=1.02)
    return g.figure


MATRIX_OPERATIONS: dict[str, PlotConfig] = {
    "heatmap": PlotConfig(
        name="heatmap",
        category="matrix",
        func=_heatmap,
        parameters={"title": None, "xlabel": None, "ylabel": None, "figsize_width": DEFAULT_FIGSIZE_WIDTH, "figsize_height": DEFAULT_FIGSIZE_HEIGHT, "style": DEFAULT_STYLE, "palette": DEFAULT_PALETTE, "columns": None, "annot": True, "fmt": ".2f"},
        description="Correlation heatmap of numeric columns. Use 'columns' (comma-separated) to limit which columns are included.",
    ),
    "pair_plot": PlotConfig(
        name="pair_plot",
        category="matrix",
        func=_pair_plot,
        parameters={"title": None, "figsize_width": DEFAULT_FIGSIZE_WIDTH, "figsize_height": DEFAULT_FIGSIZE_HEIGHT, "style": DEFAULT_STYLE, "palette": DEFAULT_PALETTE, "columns": None, "hue_column": None},
        description="Pair plot (scatter matrix) of numeric columns. Use 'columns' (comma-separated) to limit columns, hue_column for color grouping.",
    ),
}
