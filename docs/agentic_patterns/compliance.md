# Compliance & Private Data

When a connector retrieves sensitive data, the session is tagged to prevent exfiltration through external connectivity tools. This operates at the infrastructure layer, below the prompt level, where it cannot be circumvented by the agent or user.

## DataSensitivity

```python
from agentic_patterns.core.compliance.private_data import DataSensitivity

# Ordered from least to most restrictive
DataSensitivity.PUBLIC
DataSensitivity.INTERNAL
DataSensitivity.CONFIDENTIAL
DataSensitivity.SECRET
```

## PrivateData

`PrivateData` manages the compliance flag for a session. The state is persisted as a `.private_data` JSON file in `PRIVATE_DATA_DIR` -- outside the agent's workspace so the agent cannot tamper with it.

```python
from agentic_patterns.core.compliance.private_data import PrivateData, DataSensitivity

pd = PrivateData()
pd.add_private_dataset("patient_records", DataSensitivity.CONFIDENTIAL)
pd.has_private_data   # True
pd.sensitivity        # DataSensitivity.CONFIDENTIAL
pd.get_private_datasets()  # ["patient_records"]
```

`add_private_dataset(dataset_name, sensitivity)` registers a dataset and persists immediately. Sensitivity only escalates within a session (ratchet principle): if the session starts with INTERNAL and later loads CONFIDENTIAL, it becomes CONFIDENTIAL permanently. The flag cannot be cleared by the agent -- only an external action (admin, session reset) can downgrade it.

## Enforcement

The `@tool_permission` decorator checks private data state on every CONNECT tool invocation. When the session is tagged, any tool carrying `CONNECT` permission raises `ToolPermissionError` before its function body executes.

```python
from agentic_patterns.core.tools.permissions import tool_permission, ToolPermission

@tool_permission(ToolPermission.WRITE, ToolPermission.CONNECT)
def send_notification(email: str, subject: str, body: str) -> str:
    """Send email to external address."""
    return f"Email sent to {email}"

# If the session has private data, calling send_notification raises ToolPermissionError
```

This is a hard block. The agent cannot rephrase its request or be instructed to bypass it. The error fires before any code inside the tool runs.

## Where Tagging Happens

Connectors tag sessions automatically when retrieving sensitive data. The SQL connector checks the database's sensitivity level in its configuration. The OpenAPI connector checks the API's sensitivity level. The tagging is a side effect of data retrieval, independent of agent reasoning or user instructions.

```python
# Inside a connector:
if db_config.sensitivity != DataSensitivity.PUBLIC:
    pd = PrivateData()
    pd.add_private_dataset(f"sql:{db_id}", db_config.sensitivity)
```

At the sandbox level, sessions containing private data get `network_mode="none"` (Docker removes all network interfaces), preventing data exfiltration even through code execution.
