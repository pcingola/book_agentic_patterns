# Hands-On: Tool Permissions

Tool permissions define explicit authority boundaries that govern what an agent can observe, query, or mutate. Without permissions, an agent with access to both a read-balance function and a transfer-funds function has equal authority to use both. Permissions create the distinction between reading data and modifying it, between internal operations and external connections.

This hands-on explores tool permissions through `example_tool_permissions.ipynb`, demonstrating how to annotate tools with required permissions and enforce those permissions either at agent construction time or at runtime.

## The Permission Model

The example defines three permission levels as an enumeration:

```python
class ToolPermission(str, Enum):
    READ = "read"
    WRITE = "write"
    CONNECT = "connect"
```

READ covers operations that observe state without modifying it. WRITE covers operations that mutate state. CONNECT covers operations that reach external systems like the internet or third-party APIs. A tool can require multiple permissions; sending an email might require both WRITE (recording that a message was sent) and CONNECT (reaching the mail server).

## Annotating Tools with Permissions

Tools are annotated using the `@tool_permission` decorator:

```python
@tool_permission(ToolPermission.READ)
def get_balance(account_id: str) -> float:
    """Get the current balance of an account."""
    return 1500.00

@tool_permission(ToolPermission.WRITE)
def transfer_funds(from_account: str, to_account: str, amount: float) -> bool:
    """Transfer funds between accounts."""
    return True

@tool_permission(ToolPermission.WRITE, ToolPermission.CONNECT)
def send_payment_notification(email: str, amount: float) -> bool:
    """Send payment notification to external email."""
    return True
```

The decorator attaches permission metadata to the function. `get_balance` requires only READ permission. `transfer_funds` requires WRITE because it modifies account state. `send_payment_notification` requires both WRITE and CONNECT because it both records an action and reaches an external email service.

Tools without the decorator default to READ permission, reflecting the principle that observation is the baseline capability and mutation requires explicit authorization.

## Construction-Time Filtering

The first enforcement approach filters tools before creating the agent. The agent only sees tools it has permission to use:

```python
read_only_tools = filter_tools_by_permission(ALL_TOOLS, granted={ToolPermission.READ})
agent = get_agent(tools=read_only_tools)
```

With this configuration, the agent receives only `get_balance` and `get_transactions`. It cannot call `transfer_funds` because that tool is not in its tool set. If asked to transfer money, the agent must respond that it cannot perform that action.

This approach has a clear security benefit: the agent cannot even attempt unauthorized operations because it has no knowledge of the restricted tools. The permission boundary is enforced before the agent begins reasoning.

The downside is that the agent cannot explain why a capability is unavailable. From its perspective, the transfer tool simply does not exist. It might say "I don't have a tool for that" rather than "I'm not authorized to transfer funds."

## Granting Additional Permissions

Expanding the granted permissions expands the available tools:

```python
write_tools = filter_tools_by_permission(
    ALL_TOOLS,
    granted={ToolPermission.READ, ToolPermission.WRITE}
)
```

Now the agent can use `get_balance`, `get_transactions`, and `transfer_funds`. It still cannot use `send_payment_notification` because that tool requires CONNECT permission, which was not granted.

Granting all three permissions gives the agent access to all tools:

```python
full_tools = filter_tools_by_permission(
    ALL_TOOLS,
    granted={ToolPermission.READ, ToolPermission.WRITE, ToolPermission.CONNECT}
)
```

This graduated permission model lets you configure agents for different trust levels. A customer-facing agent might have only READ. An internal operations agent might have READ and WRITE. A fully autonomous agent might have all three.

## Runtime Enforcement

The second approach lets the agent see all tools but enforces permissions when tools are actually called:

```python
enforced_tools = enforce_tools_permissions(ALL_TOOLS, granted={ToolPermission.READ})
agent = get_agent(tools=enforced_tools)
```

The agent now has `transfer_funds` in its tool set and can reason about using it. But when the agent actually calls `transfer_funds`, the wrapper function checks permissions and raises `ToolPermissionError` because WRITE permission was not granted.

The agent receives this error as a tool result and must handle it. Typically, the agent will explain to the user that it attempted the action but was denied permission. This provides more transparency than construction-time filtering: the user learns that the capability exists but is restricted, rather than being told it does not exist.

Runtime enforcement is useful when you want agents to be aware of their limitations. It also enables patterns where an agent might request elevated permissions from a human supervisor before proceeding with a restricted operation.

## Choosing an Approach

Construction-time filtering is simpler and more secure. The agent cannot attempt unauthorized actions because it does not know about them. This is appropriate when you want a clear, hard boundary and when explaining permission limitations is not important.

Runtime enforcement is more flexible. The agent can reason about restricted tools, explain why it cannot use them, and potentially request permission escalation. This is appropriate when transparency matters or when permissions might be granted dynamically during a conversation.

Both approaches use the same underlying permission model. The difference is where the check happens: before the agent is created, or when the tool is invoked.

## Key Takeaways

Tool permissions create explicit authority boundaries between different types of operations. The READ/WRITE/CONNECT model captures the fundamental distinctions between observation, mutation, and external access.

Permissions are attached to tools using decorators and can be combined when a tool requires multiple capabilities.

Construction-time filtering removes unauthorized tools from the agent's view entirely. The agent cannot attempt restricted operations but also cannot explain why they are unavailable.

Runtime enforcement lets the agent see all tools but raises errors for unauthorized calls. The agent can reason about restricted capabilities and explain its limitations to users.

The choice between approaches depends on whether you prioritize strict containment or transparent communication about capability boundaries.
