"""Categorical plot operations: count, pie."""

import matplotlib.figure
import matplotlib.pyplot as plt
import seaborn as sns

from agentic_patterns.toolkits.data_viz.config import DEFAULT_FIGSIZE_HEIGHT, DEFAULT_FIGSIZE_WIDTH, DEFAULT_PALETTE, DEFAULT_STYLE
from agentic_patterns.toolkits.data_viz.models import PlotConfig


def _count_plot(df, column, title=None, xlabel=None, ylabel=None, figsize_width=DEFAULT_FIGSIZE_WIDTH, figsize_height=DEFAULT_FIGSIZE_HEIGHT, style=DEFAULT_STYLE, palette=DEFAULT_PALETTE, hue_column=None, orient="v") -> matplotlib.figure.Figure:
    sns.set_style(style)
    fig, ax = plt.subplots(figsize=(figsize_width, figsize_height))
    if orient == "h":
        sns.countplot(data=df, y=column, hue=hue_column, palette=palette, ax=ax)
    else:
        sns.countplot(data=df, x=column, hue=hue_column, palette=palette, ax=ax)
    if title:
        ax.set_title(title)
    if xlabel:
        ax.set_xlabel(xlabel)
    if ylabel:
        ax.set_ylabel(ylabel)
    ax.tick_params(axis="x", rotation=45)
    fig.tight_layout()
    return fig


def _pie_chart(df, column, title=None, figsize_width=DEFAULT_FIGSIZE_WIDTH, figsize_height=DEFAULT_FIGSIZE_HEIGHT, style=DEFAULT_STYLE, palette=DEFAULT_PALETTE, top_n=None, autopct="%1.1f%%") -> matplotlib.figure.Figure:
    sns.set_style(style)
    fig, ax = plt.subplots(figsize=(figsize_width, figsize_height))
    counts = df[column].value_counts()
    if top_n:
        top = counts.head(top_n)
        other = counts.iloc[top_n:].sum()
        if other > 0:
            top["Other"] = other
        counts = top
    colors = sns.color_palette(palette, len(counts))
    ax.pie(counts.values, labels=counts.index, autopct=autopct, colors=colors)
    if title:
        ax.set_title(title)
    fig.tight_layout()
    return fig


CATEGORICAL_OPERATIONS: dict[str, PlotConfig] = {
    "count_plot": PlotConfig(
        name="count_plot",
        category="categorical",
        func=_count_plot,
        parameters={"column": str, "title": None, "xlabel": None, "ylabel": None, "figsize_width": DEFAULT_FIGSIZE_WIDTH, "figsize_height": DEFAULT_FIGSIZE_HEIGHT, "style": DEFAULT_STYLE, "palette": DEFAULT_PALETTE, "hue_column": None, "orient": "v"},
        description="Count plot showing frequency of each category. Use hue_column for grouped counts, orient='h' for horizontal.",
    ),
    "pie_chart": PlotConfig(
        name="pie_chart",
        category="categorical",
        func=_pie_chart,
        parameters={"column": str, "title": None, "figsize_width": DEFAULT_FIGSIZE_WIDTH, "figsize_height": DEFAULT_FIGSIZE_HEIGHT, "style": DEFAULT_STYLE, "palette": DEFAULT_PALETTE, "top_n": None, "autopct": "%1.1f%%"},
        description="Pie chart of value counts. Use top_n to limit categories (rest grouped as 'Other').",
    ),
}
