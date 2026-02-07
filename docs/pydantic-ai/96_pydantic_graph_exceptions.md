# `pydantic_graph.exceptions`

### GraphSetupError

Bases: `TypeError`

Error caused by an incorrectly configured graph.

Source code in `pydantic_graph/pydantic_graph/exceptions.py`

```python
class GraphSetupError(TypeError):
    """Error caused by an incorrectly configured graph."""

    message: str
    """Description of the mistake."""

    def __init__(self, message: str):
        self.message = message
        super().__init__(message)
```

#### message

```python
message: str = message
```

Description of the mistake.

### GraphBuildingError

Bases: `ValueError`

An error raised during graph-building.

Source code in `pydantic_graph/pydantic_graph/exceptions.py`

```python
class GraphBuildingError(ValueError):
    """An error raised during graph-building."""

    message: str
    """The error message."""

    def __init__(self, message: str):
        self.message = message
        super().__init__(message)
```

#### message

```python
message: str = message
```

The error message.

### GraphValidationError

Bases: `ValueError`

An error raised during graph validation.

Source code in `pydantic_graph/pydantic_graph/exceptions.py`

```python
class GraphValidationError(ValueError):
    """An error raised during graph validation."""

    message: str
    """The error message."""

    def __init__(self, message: str):
        self.message = message
        super().__init__(message)
```

#### message

```python
message: str = message
```

The error message.

### GraphRuntimeError

Bases: `RuntimeError`

Error caused by an issue during graph execution.

Source code in `pydantic_graph/pydantic_graph/exceptions.py`

```python
class GraphRuntimeError(RuntimeError):
    """Error caused by an issue during graph execution."""

    message: str
    """The error message."""

    def __init__(self, message: str):
        self.message = message
        super().__init__(message)
```

#### message

```python
message: str = message
```

The error message.

### GraphNodeStatusError

Bases: `GraphRuntimeError`

Error caused by trying to run a node that already has status `'running'`, `'success'`, or `'error'`.

Source code in `pydantic_graph/pydantic_graph/exceptions.py`

```python
class GraphNodeStatusError(GraphRuntimeError):
    """Error caused by trying to run a node that already has status `'running'`, `'success'`, or `'error'`."""

    def __init__(self, actual_status: 'SnapshotStatus'):
        self.actual_status = actual_status
        super().__init__(f"Incorrect snapshot status {actual_status!r}, must be 'created' or 'pending'.")

    @classmethod
    def check(cls, status: 'SnapshotStatus') -> None:
        """Check if the status is valid."""
        if status not in {'created', 'pending'}:
            raise cls(status)
```

#### check

```python
check(status: SnapshotStatus) -> None
```

Check if the status is valid.

Source code in `pydantic_graph/pydantic_graph/exceptions.py`

```python
@classmethod
def check(cls, status: 'SnapshotStatus') -> None:
    """Check if the status is valid."""
    if status not in {'created', 'pending'}:
        raise cls(status)
```
