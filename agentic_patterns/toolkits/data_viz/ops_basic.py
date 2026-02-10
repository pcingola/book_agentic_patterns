"""Basic plot operations: line, bar, scatter, area."""

import matplotlib.figure
import matplotlib.pyplot as plt
import seaborn as sns

from agentic_patterns.toolkits.data_viz.config import (
    DEFAULT_FIGSIZE_HEIGHT,
    DEFAULT_FIGSIZE_WIDTH,
    DEFAULT_PALETTE,
    DEFAULT_STYLE,
)
from agentic_patterns.toolkits.data_viz.models import PlotConfig


def _line_plot(
    df,
    x_column,
    y_columns,
    title=None,
    xlabel=None,
    ylabel=None,
    figsize_width=DEFAULT_FIGSIZE_WIDTH,
    figsize_height=DEFAULT_FIGSIZE_HEIGHT,
    style=DEFAULT_STYLE,
    palette=DEFAULT_PALETTE,
    marker=None,
    linewidth=1.5,
) -> matplotlib.figure.Figure:
    sns.set_style(style)
    fig, ax = plt.subplots(figsize=(figsize_width, figsize_height))
    cols = (
        [c.strip() for c in y_columns.split(",")]
        if isinstance(y_columns, str)
        else y_columns
    )
    colors = sns.color_palette(palette, len(cols))
    for i, col in enumerate(cols):
        ax.plot(
            df[x_column],
            df[col],
            label=col,
            color=colors[i],
            marker=marker,
            linewidth=linewidth,
        )
    if len(cols) > 1:
        ax.legend()
    if title:
        ax.set_title(title)
    ax.set_xlabel(xlabel or x_column)
    ax.set_ylabel(ylabel or (cols[0] if len(cols) == 1 else ""))
    fig.tight_layout()
    return fig


def _bar_plot(
    df,
    x_column,
    y_column,
    title=None,
    xlabel=None,
    ylabel=None,
    figsize_width=DEFAULT_FIGSIZE_WIDTH,
    figsize_height=DEFAULT_FIGSIZE_HEIGHT,
    style=DEFAULT_STYLE,
    palette=DEFAULT_PALETTE,
    horizontal=False,
    top_n=None,
) -> matplotlib.figure.Figure:
    sns.set_style(style)
    fig, ax = plt.subplots(figsize=(figsize_width, figsize_height))
    data = df.nlargest(top_n, y_column) if top_n else df
    if horizontal:
        sns.barplot(data=data, y=x_column, x=y_column, palette=palette, ax=ax)
    else:
        sns.barplot(data=data, x=x_column, y=y_column, palette=palette, ax=ax)
    if title:
        ax.set_title(title)
    if xlabel:
        ax.set_xlabel(xlabel)
    if ylabel:
        ax.set_ylabel(ylabel)
    ax.tick_params(axis="x", rotation=45)
    fig.tight_layout()
    return fig


def _scatter_plot(
    df,
    x_column,
    y_column,
    title=None,
    xlabel=None,
    ylabel=None,
    figsize_width=DEFAULT_FIGSIZE_WIDTH,
    figsize_height=DEFAULT_FIGSIZE_HEIGHT,
    style=DEFAULT_STYLE,
    palette=DEFAULT_PALETTE,
    hue_column=None,
    size_column=None,
    alpha=0.7,
) -> matplotlib.figure.Figure:
    sns.set_style(style)
    fig, ax = plt.subplots(figsize=(figsize_width, figsize_height))
    sns.scatterplot(
        data=df,
        x=x_column,
        y=y_column,
        hue=hue_column,
        size=size_column,
        palette=palette,
        alpha=alpha,
        ax=ax,
    )
    if title:
        ax.set_title(title)
    ax.set_xlabel(xlabel or x_column)
    ax.set_ylabel(ylabel or y_column)
    fig.tight_layout()
    return fig


def _area_plot(
    df,
    x_column,
    y_columns,
    title=None,
    xlabel=None,
    ylabel=None,
    figsize_width=DEFAULT_FIGSIZE_WIDTH,
    figsize_height=DEFAULT_FIGSIZE_HEIGHT,
    style=DEFAULT_STYLE,
    palette=DEFAULT_PALETTE,
    alpha=0.5,
    stacked=True,
) -> matplotlib.figure.Figure:
    sns.set_style(style)
    fig, ax = plt.subplots(figsize=(figsize_width, figsize_height))
    cols = (
        [c.strip() for c in y_columns.split(",")]
        if isinstance(y_columns, str)
        else y_columns
    )
    colors = sns.color_palette(palette, len(cols))
    if stacked:
        ax.stackplot(
            df[x_column],
            *[df[c] for c in cols],
            labels=cols,
            colors=colors,
            alpha=alpha,
        )
    else:
        for i, col in enumerate(cols):
            ax.fill_between(
                df[x_column], df[col], label=col, color=colors[i], alpha=alpha
            )
    ax.legend()
    if title:
        ax.set_title(title)
    ax.set_xlabel(xlabel or x_column)
    ax.set_ylabel(ylabel or "")
    fig.tight_layout()
    return fig


BASIC_OPERATIONS: dict[str, PlotConfig] = {
    "line_plot": PlotConfig(
        name="line_plot",
        category="basic",
        func=_line_plot,
        parameters={
            "x_column": str,
            "y_columns": str,
            "title": None,
            "xlabel": None,
            "ylabel": None,
            "figsize_width": DEFAULT_FIGSIZE_WIDTH,
            "figsize_height": DEFAULT_FIGSIZE_HEIGHT,
            "style": DEFAULT_STYLE,
            "palette": DEFAULT_PALETTE,
            "marker": None,
            "linewidth": 1.5,
        },
        description="Line plot. y_columns is a comma-separated list of column names.",
    ),
    "bar_plot": PlotConfig(
        name="bar_plot",
        category="basic",
        func=_bar_plot,
        parameters={
            "x_column": str,
            "y_column": str,
            "title": None,
            "xlabel": None,
            "ylabel": None,
            "figsize_width": DEFAULT_FIGSIZE_WIDTH,
            "figsize_height": DEFAULT_FIGSIZE_HEIGHT,
            "style": DEFAULT_STYLE,
            "palette": DEFAULT_PALETTE,
            "horizontal": False,
            "top_n": None,
        },
        description="Bar plot. Set horizontal=True for horizontal bars, top_n to show only top N values.",
    ),
    "scatter_plot": PlotConfig(
        name="scatter_plot",
        category="basic",
        func=_scatter_plot,
        parameters={
            "x_column": str,
            "y_column": str,
            "title": None,
            "xlabel": None,
            "ylabel": None,
            "figsize_width": DEFAULT_FIGSIZE_WIDTH,
            "figsize_height": DEFAULT_FIGSIZE_HEIGHT,
            "style": DEFAULT_STYLE,
            "palette": DEFAULT_PALETTE,
            "hue_column": None,
            "size_column": None,
            "alpha": 0.7,
        },
        description="Scatter plot with optional color (hue_column) and size (size_column) encoding.",
    ),
    "area_plot": PlotConfig(
        name="area_plot",
        category="basic",
        func=_area_plot,
        parameters={
            "x_column": str,
            "y_columns": str,
            "title": None,
            "xlabel": None,
            "ylabel": None,
            "figsize_width": DEFAULT_FIGSIZE_WIDTH,
            "figsize_height": DEFAULT_FIGSIZE_HEIGHT,
            "style": DEFAULT_STYLE,
            "palette": DEFAULT_PALETTE,
            "alpha": 0.5,
            "stacked": True,
        },
        description="Area plot. y_columns is a comma-separated list of column names. Set stacked=False for overlapping areas.",
    ),
}
