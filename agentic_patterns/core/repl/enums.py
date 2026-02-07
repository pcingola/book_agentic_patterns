from enum import Enum


class CellState(str, Enum):
    """Enum representing the state of a cell."""

    IDLE = "IDLE"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    ERROR = "ERROR"
    TIMEOUT = "TIMEOUT"


class OutputType(str, Enum):
    """Enum representing the type of output from a cell."""

    TEXT = "TEXT"
    HTML = "HTML"
    IMAGE = "IMAGE"
    ERROR = "ERROR"
    DATAFRAME = "DATAFRAME"
