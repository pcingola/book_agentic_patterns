"""Data models for the data visualization MCP server."""

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any


@dataclass
class PlotConfig:
    """Configuration for a visualization operation."""

    name: str
    category: str
    func: Callable
    parameters: dict[str, Any]
    description: str = ""
