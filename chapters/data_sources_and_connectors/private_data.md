## Private Data

When an agent connects to an external data source, the data it retrieves may be public, internal, confidential, or secret. A SQL query against a patient database, a file download from a regulated share, or an API call returning financial records can all introduce sensitive content into the session. That content ends up in two places: in the workspace as files (a CSV export, a downloaded document), and in the LLM's context window as tool results. Both are exfiltration vectors. A workspace file can be uploaded by a subsequent tool call. A tool result sitting in context can be passed as an argument to the next tool the agent decides to call -- the agent reads the balance from one tool's output and writes it into the body of a notification email. No file needs to exist on disk for the leak to happen; the data flows directly through the context window from one tool call to the next.

The fundamental problem is not that agents are malicious. It is that agents are *eager*. They optimize for task completion and will use any available tool to get there. If a tool exists that sends data to an external endpoint, the agent will eventually use it when it seems like the right next step. Prompt-level instructions ("do not share confidential data") are insufficient because they are advisory, not enforceable: the model can misinterpret them, ignore them under pressure from a persuasive user prompt, or simply not recognize that a particular tool call constitutes data leakage.

Reliable data protection therefore requires a mechanism that operates below the prompt level, at the infrastructure layer where tools are registered, filtered, and executed. The approach described here is deliberately simple: tag the session as "private" whenever sensitive data enters it -- whether that data lands in the workspace or only passes through the context window -- and use that tag to enforce guardrails that block unsafe operations regardless of what the agent or the user requests.

### Sensitivity levels

Not all private data carries the same risk. A document marked "internal" may be shared freely within the company but not externally. A patient record marked "confidential" may only be accessed by authorized personnel. An API key marked "secret" should never appear in logs, tool outputs, or any persistent artifact.

These distinctions are captured by a small enumeration of sensitivity levels, ordered from least to most restrictive: `PUBLIC`, `INTERNAL`, `CONFIDENTIAL`, and `SECRET`. When multiple datasets with different sensitivity levels coexist in the same session, the session's overall sensitivity is the highest level among them. Sensitivity never degrades within a session; once a secret dataset has been loaded, the session remains at `SECRET` level even if that specific dataset is no longer actively referenced. This ratchet behavior is intentional. Residual information from sensitive data may persist in the agent's context, in workspace files, or in tool call history, and downgrading sensitivity would create a false sense of safety.

```python
class DataSensitivity(str, Enum):
    PUBLIC = "public"
    INTERNAL = "internal"
    CONFIDENTIAL = "confidential"
    SECRET = "secret"
```

### Tagging the workspace

The implementation stores the private-data state as a JSON file (`.private_data`) in a dedicated directory (`PRIVATE_DATA_DIR`) that mirrors the workspace directory structure per user and session but is located outside the agent's workspace. If the file does not exist, the session contains no private data and all tools operate normally.

This separation is important. The agent has read/write access to its own workspace through the file connector and workspace tools. If the compliance flag lived inside the workspace, the agent could delete or modify it -- either through direct manipulation (an agent tricked into running a cleanup operation) or through a prompt injection attack that instructs the agent to remove the `.private_data` file before exfiltrating data. Storing the flag outside the workspace means the agent has no tool that can reach it. The compliance state is managed exclusively by server-side code (connectors, the `PrivateData` class) that runs in the host process, not by the agent itself.

In production systems, file-based persistence would be replaced by a database or a Redis cache. A relational database provides transactional guarantees and audit logging. A Redis cache provides low-latency reads that scale well when multiple services need to check the compliance state of a session on every tool invocation. The file-based approach used here is sufficient for development and single-process deployments, but any system handling real sensitive data at scale should use a centralized store that supports concurrent access, replication, and access control.

```python
pd = PrivateData(user_id="alice", session_id="analysis-42")

# A connector retrieves patient records from a database
pd.add_private_dataset("patient_records", DataSensitivity.CONFIDENTIAL)

# Later, the agent loads financial projections
pd.add_private_dataset("financials_q4", DataSensitivity.SECRET)

# The session is now at SECRET level
pd.sensitivity          # DataSensitivity.SECRET
pd.has_private_data     # True
pd.get_private_datasets()  # ["patient_records", "financials_q4"]
```

All mutations persist immediately. The `PrivateData` class writes to disk on every state change so that the tag survives process restarts and is visible to other components (MCP servers, sandbox controllers, monitoring systems) that may need to check it independently of the agent process.

The tagging is typically performed by connectors themselves. When a SQL connector executes a query against a database that is known to contain sensitive data, or when a file connector reads from a protected directory, the connector calls `add_private_dataset()` as a side effect. This means the tagging happens automatically, without relying on the agent or the user to remember to set it.

### Enforcing guardrails

The tag alone does not prevent anything. It is a signal that downstream enforcement layers consume. The two primary enforcement points are tool filtering and connectivity control.

Tool filtering uses the permission system introduced in the tools chapter. Every tool is annotated with permission requirements (`READ`, `WRITE`, `CONNECT`). The `@tool_permission` decorator automatically checks the session's private data state on every invocation of a CONNECT tool. When the session is tagged as private, any tool that carries the `CONNECT` permission raises `ToolPermissionError` before its function body executes. No additional wiring is required -- the decorator handles it.

```python
@tool_permission(ToolPermission.WRITE, ToolPermission.CONNECT)
def send_payment_notification(email: str, amount: float) -> bool:
    """Send payment notification to external email."""
    return True

# If the session has private data, calling this tool raises ToolPermissionError
```

This is a hard enforcement. The agent cannot circumvent it by rephrasing its request or by being instructed by the user to "ignore security rules."

Connectivity control operates at a lower level, typically in the execution sandbox or container that hosts the agent's code execution environment. When the session is private, the sandbox can be switched to a network configuration that blocks all outbound connections, or routes them through a proxy that only allows whitelisted destinations (internal company servers, trusted services with zero-data-retention agreements). The sandbox implementation uses Docker's `network_mode="none"` to remove all network interfaces when `PrivateData` is present, and automatically recreates containers mid-conversation when private data appears. The full mechanism is described in the "Network Isolation with PrivateData" section of the execution infrastructure chapter.

### The ratchet principle

A critical design decision is that the private flag, once set, cannot be cleared by the agent. Only an explicit external action (an administrator, a session reset, or a policy engine) can downgrade a session's sensitivity. This prevents a class of attacks where the agent is manipulated into calling a hypothetical `clear_private_data()` tool before proceeding to exfiltrate data.

Similarly, the sensitivity level only escalates. If a session starts with `INTERNAL` data and later loads `CONFIDENTIAL` data, it becomes `CONFIDENTIAL` and stays there. The implementation achieves this by taking the maximum sensitivity across all registered datasets:

```python
def add_private_dataset(self, dataset_name, sensitivity=DataSensitivity.CONFIDENTIAL):
    if dataset_name not in self._private_datasets:
        self._private_datasets.append(dataset_name)
        self._has_private_data = True
        self._sensitivity = max(self._sensitivity, sensitivity.value, key=_sensitivity_order)
        self.save()
```

### Where tagging happens in practice

In a typical deployment, tagging is wired into the connector layer rather than the agent logic. Consider a SQL connector that executes queries on behalf of an agent. The connector knows which databases contain sensitive data (this is part of the database catalog configuration), and it tags the session automatically when results are returned:

```python
async def execute_sql(db_id: str, query: str, ctx: RunContext) -> str:
    # ... validate query, execute, format results ...

    if db_config.sensitivity != DataSensitivity.PUBLIC:
        pd = PrivateData()
        pd.add_private_dataset(f"sql:{db_id}", db_config.sensitivity)

    return formatted_result
```

The same pattern applies to file connectors reading from protected directories, API connectors calling internal services with sensitive response data, and any other connector that knows the sensitivity of its source. The key insight is that the connector is the right place to make this determination, because it is the component that actually touches the data source and knows its classification.

### What this does not solve

Session-level tagging is a coarse-grained mechanism. It does not track which specific fields or rows within a dataset are sensitive. It does not redact sensitive values from the agent's context window. It does not prevent the agent from reasoning about sensitive data internally or including sensitive details in its natural language responses to the user (who presumably has access, since they initiated the query).

These limitations are acceptable because the goal is not to build a complete data loss prevention system. The goal is to prevent the most common and most damaging failure mode: an agent using an available tool to send private data to an external system. Session tagging addresses this by removing the tools that could cause the leak, which is a simple, auditable, and hard-to-bypass mechanism that complements rather than replaces more granular data governance controls.
