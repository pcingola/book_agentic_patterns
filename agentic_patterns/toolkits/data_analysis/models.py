"""Data models for data analysis operations."""

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any


@dataclass
class OperationConfig:
    """Configuration for a data analysis operation."""

    name: str
    category: str
    func: Callable
    parameters: dict[str, Any]
    returns_df: bool = True
    view_only: bool = False
    description: str = ""
