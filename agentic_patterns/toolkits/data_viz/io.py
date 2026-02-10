"""I/O utilities for data visualization: DataFrame loading, figure saving, file listing."""

from pathlib import PurePosixPath

import matplotlib.figure
import matplotlib.pyplot as plt
import pandas as pd

from agentic_patterns.core.workspace import list_workspace_files, workspace_to_host_path
from agentic_patterns.toolkits.data_viz.config import DEFAULT_DPI, DEFAULT_FORMAT
from agentic_patterns.toolkits.data_viz.enums import ImageFormat


def list_plot_files() -> list[str]:
    """List image files (PNG, SVG) in the workspace."""
    png_files = list_workspace_files("*.png")
    svg_files = list_workspace_files("*.svg")
    return sorted(set(png_files + svg_files))


def load_df(workspace_path: str) -> pd.DataFrame:
    """Load a DataFrame from a CSV file in the workspace."""
    host_path = workspace_to_host_path(PurePosixPath(workspace_path))
    if not host_path.exists():
        raise FileNotFoundError(f"File not found: {workspace_path}")
    return pd.read_csv(host_path)


def save_figure(
    fig: matplotlib.figure.Figure, workspace_path: str, dpi: int = DEFAULT_DPI
) -> str:
    """Save a matplotlib Figure to the workspace and close it. Returns the workspace path."""
    host_path = workspace_to_host_path(PurePosixPath(workspace_path))
    host_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        image_format = ImageFormat.from_path(host_path)
    except ValueError:
        image_format = ImageFormat(DEFAULT_FORMAT)
        host_path = host_path.with_suffix(f".{DEFAULT_FORMAT}")

    fig.savefig(host_path, format=image_format.value, dpi=dpi, bbox_inches="tight")
    plt.close(fig)
    return str(PurePosixPath(workspace_path))
