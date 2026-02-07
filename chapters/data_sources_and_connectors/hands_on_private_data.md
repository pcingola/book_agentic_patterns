## Hands-On: Private Data Guardrails

This hands-on walks through the private data tagging system and its integration with tool permissions. The goal is to see how sensitive data entering a session automatically blocks outbound connectivity, preventing data leakage without relying on prompt-level instructions.

### Marking a session manually

The simplest way to tag a session is to call `mark_session_private()`. This sets the private-data flag for the current user/session pair and persists it to disk:

```python
from agentic_patterns.core.compliance.private_data import (
    PrivateData, mark_session_private, session_has_private_data,
)

mark_session_private()
session_has_private_data()  # True
```

The flag is idempotent -- calling it again has no effect.

### Adding datasets with sensitivity levels

In practice, sessions become private because a connector loads sensitive data. Each dataset is registered with a sensitivity level. The session's overall sensitivity is the maximum across all datasets:

```python
from agentic_patterns.core.compliance.private_data import DataSensitivity, PrivateData

pd = PrivateData()
pd.add_private_dataset("internal_docs", DataSensitivity.INTERNAL)
pd.sensitivity  # DataSensitivity.INTERNAL

pd.add_private_dataset("patient_records", DataSensitivity.CONFIDENTIAL)
pd.sensitivity  # DataSensitivity.CONFIDENTIAL -- escalated

pd.add_private_dataset("public_catalog", DataSensitivity.PUBLIC)
pd.sensitivity  # DataSensitivity.CONFIDENTIAL -- never downgrades
```

This ratchet behavior is intentional. Once sensitive data has entered the workspace, it may persist in the agent's context, in files, or in tool call history. Downgrading would create a false sense of safety.

### Configuring sensitivity in data sources

Database connections declare their sensitivity in `dbs.yaml`:

```yaml
databases:
  bookstore:
    type: sqlite
    dbname: bookstore.db

  patients:
    type: sqlite
    dbname: patients.db
    sensitivity: confidential
```

Databases without a `sensitivity` field default to `public`. The same pattern applies to API connections in `apis.yaml`:

```yaml
apis:
  weather:
    spec_source: https://api.weather.com/openapi.json
    base_url: https://api.weather.com

  internal_hr:
    spec_source: https://hr.internal/openapi.json
    base_url: https://hr.internal
    sensitivity: internal
```

### Automatic session tagging

When the SQL connector executes a query against a database configured with non-public sensitivity, it automatically tags the session:

```python
# Inside SqlConnector.execute_sql, after executing the query:
db_config = DbConnectionConfigs.get().get_config(db_id)
if db_config.sensitivity != DataSensitivity.PUBLIC:
    pd = PrivateData()
    pd.add_private_dataset(f"sql:{db_id}", db_config.sensitivity)
```

The OpenAPI connector does the same after calling an endpoint. The agent and the user do not need to remember to tag anything -- the connector handles it as a side effect of data retrieval.

### Blocking CONNECT tools after tagging

The private data state feeds into the permission system through `resolve_permissions`. This function checks whether the current session has private data and, if so, removes `CONNECT` from the granted permission set:

```python
from agentic_patterns.core.compliance.private_data import resolve_permissions
from agentic_patterns.core.tools import ToolPermission, enforce_tools_permissions

base = {ToolPermission.READ, ToolPermission.WRITE, ToolPermission.CONNECT}
tools = enforce_tools_permissions(all_tools, granted=lambda: resolve_permissions(base))
```

Passing a callable (rather than a static set) to `enforce_tools_permissions` ensures that permissions are evaluated on every tool invocation. Before any sensitive data arrives, `resolve_permissions` returns the full set and CONNECT tools work normally. The moment a connector tags the session, the next invocation detects the flag, drops CONNECT, and raises `ToolPermissionError` for any tool requiring outbound connectivity.

The agent receives this error as a tool result. It cannot circumvent it by rephrasing the request or by being instructed to "ignore security." The tools are blocked at the infrastructure layer, below the prompt.
