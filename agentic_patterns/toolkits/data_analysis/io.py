"""DataFrame I/O with workspace isolation."""

from pathlib import PurePosixPath

import pandas as pd

from agentic_patterns.core.workspace import list_workspace_files, workspace_to_host_path
from agentic_patterns.toolkits.data_analysis.config import DEFAULT_SAVE_FORMAT
from agentic_patterns.toolkits.data_analysis.enums import FileFormat


def load_df(workspace_path: str) -> pd.DataFrame:
    """Load a DataFrame from a workspace path (CSV or pickle)."""
    host_path = workspace_to_host_path(PurePosixPath(workspace_path))
    if not host_path.exists():
        raise FileNotFoundError(f"File not found: {workspace_path}")
    file_format = FileFormat.from_path(host_path)
    if file_format == FileFormat.CSV:
        return pd.read_csv(host_path)
    if file_format == FileFormat.PICKLE:
        return pd.read_pickle(host_path)
    raise ValueError(f"Unsupported file format: {file_format}")


def save_df(
    df: pd.DataFrame, workspace_path: str, file_format: FileFormat | None = None
) -> None:
    """Save a DataFrame to a workspace path."""
    host_path = workspace_to_host_path(PurePosixPath(workspace_path))
    host_path.parent.mkdir(parents=True, exist_ok=True)

    if file_format is None:
        if host_path.suffix:
            try:
                file_format = FileFormat.from_path(host_path)
            except ValueError:
                file_format = FileFormat(DEFAULT_SAVE_FORMAT)
                host_path = host_path.with_suffix(".pkl")
        else:
            file_format = FileFormat(DEFAULT_SAVE_FORMAT)
            host_path = host_path.with_suffix(".pkl")

    if file_format == FileFormat.CSV:
        df.to_csv(host_path)
    elif file_format == FileFormat.PICKLE:
        df.to_pickle(host_path)
    else:
        raise ValueError(f"Unsupported file format: {file_format}")


def list_dataframe_files() -> list[str]:
    """List CSV and pickle files in the workspace."""
    csv_files = list_workspace_files("*.csv")
    pkl_files = list_workspace_files("*.pkl") + list_workspace_files("*.pickle")
    return sorted(set(csv_files + pkl_files))
