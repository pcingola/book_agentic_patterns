"""Distribution plot operations: histogram, box, violin, kde."""

import matplotlib.figure
import matplotlib.pyplot as plt
import seaborn as sns

from agentic_patterns.toolkits.data_viz.config import DEFAULT_FIGSIZE_HEIGHT, DEFAULT_FIGSIZE_WIDTH, DEFAULT_PALETTE, DEFAULT_STYLE
from agentic_patterns.toolkits.data_viz.models import PlotConfig


def _histogram(df, column, title=None, xlabel=None, ylabel=None, figsize_width=DEFAULT_FIGSIZE_WIDTH, figsize_height=DEFAULT_FIGSIZE_HEIGHT, style=DEFAULT_STYLE, palette=DEFAULT_PALETTE, bins=30, kde_overlay=True) -> matplotlib.figure.Figure:
    sns.set_style(style)
    fig, ax = plt.subplots(figsize=(figsize_width, figsize_height))
    sns.histplot(data=df, x=column, bins=bins, kde=kde_overlay, palette=palette, ax=ax)
    if title:
        ax.set_title(title)
    if xlabel:
        ax.set_xlabel(xlabel)
    if ylabel:
        ax.set_ylabel(ylabel)
    fig.tight_layout()
    return fig


def _box_plot(df, columns, title=None, xlabel=None, ylabel=None, figsize_width=DEFAULT_FIGSIZE_WIDTH, figsize_height=DEFAULT_FIGSIZE_HEIGHT, style=DEFAULT_STYLE, palette=DEFAULT_PALETTE, by=None, orient="v") -> matplotlib.figure.Figure:
    sns.set_style(style)
    fig, ax = plt.subplots(figsize=(figsize_width, figsize_height))
    cols = [c.strip() for c in columns.split(",")] if isinstance(columns, str) else columns
    if by:
        sns.boxplot(data=df, x=by, y=cols[0], palette=palette, orient=orient, ax=ax)
    elif len(cols) == 1:
        sns.boxplot(data=df, y=cols[0], palette=palette, orient=orient, ax=ax)
    else:
        sns.boxplot(data=df[cols], palette=palette, orient=orient, ax=ax)
    if title:
        ax.set_title(title)
    if xlabel:
        ax.set_xlabel(xlabel)
    if ylabel:
        ax.set_ylabel(ylabel)
    fig.tight_layout()
    return fig


def _violin_plot(df, columns, title=None, xlabel=None, ylabel=None, figsize_width=DEFAULT_FIGSIZE_WIDTH, figsize_height=DEFAULT_FIGSIZE_HEIGHT, style=DEFAULT_STYLE, palette=DEFAULT_PALETTE, by=None, orient="v") -> matplotlib.figure.Figure:
    sns.set_style(style)
    fig, ax = plt.subplots(figsize=(figsize_width, figsize_height))
    cols = [c.strip() for c in columns.split(",")] if isinstance(columns, str) else columns
    if by:
        sns.violinplot(data=df, x=by, y=cols[0], palette=palette, orient=orient, ax=ax)
    elif len(cols) == 1:
        sns.violinplot(data=df, y=cols[0], palette=palette, orient=orient, ax=ax)
    else:
        sns.violinplot(data=df[cols], palette=palette, orient=orient, ax=ax)
    if title:
        ax.set_title(title)
    if xlabel:
        ax.set_xlabel(xlabel)
    if ylabel:
        ax.set_ylabel(ylabel)
    fig.tight_layout()
    return fig


def _kde_plot(df, columns, title=None, xlabel=None, ylabel=None, figsize_width=DEFAULT_FIGSIZE_WIDTH, figsize_height=DEFAULT_FIGSIZE_HEIGHT, style=DEFAULT_STYLE, palette=DEFAULT_PALETTE, fill=True) -> matplotlib.figure.Figure:
    sns.set_style(style)
    fig, ax = plt.subplots(figsize=(figsize_width, figsize_height))
    cols = [c.strip() for c in columns.split(",")] if isinstance(columns, str) else columns
    colors = sns.color_palette(palette, len(cols))
    for i, col in enumerate(cols):
        sns.kdeplot(data=df, x=col, fill=fill, color=colors[i], label=col, ax=ax)
    if len(cols) > 1:
        ax.legend()
    if title:
        ax.set_title(title)
    if xlabel:
        ax.set_xlabel(xlabel)
    if ylabel:
        ax.set_ylabel(ylabel)
    fig.tight_layout()
    return fig


DISTRIBUTION_OPERATIONS: dict[str, PlotConfig] = {
    "histogram": PlotConfig(
        name="histogram",
        category="distribution",
        func=_histogram,
        parameters={"column": str, "title": None, "xlabel": None, "ylabel": None, "figsize_width": DEFAULT_FIGSIZE_WIDTH, "figsize_height": DEFAULT_FIGSIZE_HEIGHT, "style": DEFAULT_STYLE, "palette": DEFAULT_PALETTE, "bins": 30, "kde_overlay": True},
        description="Histogram with optional KDE overlay. Set kde_overlay=False to disable the density curve.",
    ),
    "box_plot": PlotConfig(
        name="box_plot",
        category="distribution",
        func=_box_plot,
        parameters={"columns": str, "title": None, "xlabel": None, "ylabel": None, "figsize_width": DEFAULT_FIGSIZE_WIDTH, "figsize_height": DEFAULT_FIGSIZE_HEIGHT, "style": DEFAULT_STYLE, "palette": DEFAULT_PALETTE, "by": None, "orient": "v"},
        description="Box plot. columns is a comma-separated list. Use 'by' to group by a categorical column.",
    ),
    "violin_plot": PlotConfig(
        name="violin_plot",
        category="distribution",
        func=_violin_plot,
        parameters={"columns": str, "title": None, "xlabel": None, "ylabel": None, "figsize_width": DEFAULT_FIGSIZE_WIDTH, "figsize_height": DEFAULT_FIGSIZE_HEIGHT, "style": DEFAULT_STYLE, "palette": DEFAULT_PALETTE, "by": None, "orient": "v"},
        description="Violin plot. columns is a comma-separated list. Use 'by' to group by a categorical column.",
    ),
    "kde_plot": PlotConfig(
        name="kde_plot",
        category="distribution",
        func=_kde_plot,
        parameters={"columns": str, "title": None, "xlabel": None, "ylabel": None, "figsize_width": DEFAULT_FIGSIZE_WIDTH, "figsize_height": DEFAULT_FIGSIZE_HEIGHT, "style": DEFAULT_STYLE, "palette": DEFAULT_PALETTE, "fill": True},
        description="Kernel density estimate plot. columns is a comma-separated list. Set fill=False for line-only.",
    ),
}
