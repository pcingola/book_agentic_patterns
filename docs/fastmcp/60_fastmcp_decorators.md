# `fastmcp.decorators`

Shared decorator utilities for FastMCP.

## Functions

### `resolve_task_config` <sup><a href="https://github.com/jlowin/fastmcp/blob/main/src/fastmcp/decorators.py#L17"><Icon icon="github" /></a></sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
resolve_task_config(task: bool | TaskConfig | None) -> bool | TaskConfig
```

Resolve task config, defaulting None to False.

### `get_fastmcp_meta` <sup><a href="https://github.com/jlowin/fastmcp/blob/main/src/fastmcp/decorators.py#L29"><Icon icon="github" /></a></sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
get_fastmcp_meta(fn: Any) -> Any | None
```

Extract FastMCP metadata from a function, handling bound methods and wrappers.

## Classes

### `HasFastMCPMeta` <sup><a href="https://github.com/jlowin/fastmcp/blob/main/src/fastmcp/decorators.py#L23"><Icon icon="github" /></a></sup>

Protocol for callables decorated with FastMCP metadata.
