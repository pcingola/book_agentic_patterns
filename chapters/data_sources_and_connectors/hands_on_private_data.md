## Hands-On: Private Data Guardrails

This hands-on walks through `example_private_data.ipynb`, where a banking agent demonstrates how session-level tagging prevents data exfiltration through external connectivity tools. The agent has three tools: one that reads public market data, one that reads confidential account information, and one that sends emails to external addresses. A multi-turn conversation shows that the email tool works before sensitive data enters the session and stops working after.

## Tools with Different Sensitivity Profiles

The three tools illustrate the spectrum of data sensitivity and connectivity. `get_exchange_rates` returns publicly available market data and carries only a READ permission. `get_balance` also carries READ, but internally it tags the session as containing confidential data via the `PrivateData` class. `send_notification` carries both WRITE and CONNECT permissions, meaning it reaches an external system.

```python
@tool_permission(ToolPermission.READ)
def get_exchange_rates(base_currency: str) -> dict:
    """Get current exchange rates for a base currency."""
    rates = {"EUR": {"USD": 1.08, "GBP": 0.86, "JPY": 162.5}}
    return rates.get(base_currency, {"error": f"Unknown currency: {base_currency}"})


@tool_permission(ToolPermission.READ)
def get_balance(account_id: str) -> dict:
    """Get account balance."""
    pd = PrivateData()
    pd.add_private_dataset(f"account:{account_id}", DataSensitivity.CONFIDENTIAL)
    return {"account_id": account_id, "balance": 15420.50, "currency": "EUR"}


@tool_permission(ToolPermission.WRITE, ToolPermission.CONNECT)
def send_notification(email: str, subject: str, body: str) -> str:
    """Send a notification email to an external address."""
    return f"Email sent to {email}: {subject}"
```

The critical line is `pd.add_private_dataset(...)` inside `get_balance`. This is the tagging call described in the chapter's private data section. The tool itself is a normal READ tool -- it does not send data anywhere. But by tagging the session, it changes what other tools can do for the rest of the conversation. In a real system, this tagging would happen inside a connector (SQL connector, file connector) rather than in the tool function directly. The example places it in the tool to keep the demonstration self-contained.

## Turn 1: Public Data and External Connectivity

The first prompt asks the agent to fetch exchange rates and email a summary. Both operations succeed because no sensitive data has entered the session yet. The `@tool_permission` decorator on `send_notification` checks the session's private data state and finds it clean, so the CONNECT permission is granted.

```python
prompt_1 = "Get the EUR exchange rates and email a summary to trader@bank.com with subject 'Daily EUR rates'"
run_1, nodes_1 = await run_agent(agent, prompt_1, verbose=True)
```

After this turn, inspecting the `PrivateData` object confirms the session is still untagged:

```python
pd = PrivateData()
print(f"Has private data: {pd.has_private_data}")  # False
```

## Turn 2: Confidential Data Triggers the Guardrail

The second prompt asks the agent to check an account balance and email it to the client. The agent calls `get_balance`, which returns the account data and tags the session as `CONFIDENTIAL`. When the agent then tries to call `send_notification`, the `@tool_permission` decorator detects that the session contains private data and raises `ToolPermissionError` before the function body executes.

```python
prompt_2 = "Now check the balance for account ACC-7291 and email it to client@example.com with subject 'Your balance'"

try:
    run_2, nodes_2 = await run_agent(agent, prompt_2, message_history=message_history, verbose=True)
except ToolPermissionError as e:
    print(f"\nGuardrail activated: {e}")
```

The error is not a suggestion the agent can work around. It is a hard block at the infrastructure layer. The agent cannot rephrase its request, call a different tool, or be instructed by the user to bypass it. The `ToolPermissionError` fires before any code inside `send_notification` runs, so no data reaches the external endpoint.

After this turn, the session state reflects the tagging:

```python
pd = PrivateData()
pd.has_private_data   # True
pd.sensitivity        # DataSensitivity.CONFIDENTIAL
pd.get_private_datasets()  # ["account:ACC-7291"]
```

## Turn 3: The Ratchet Persists

The third prompt goes back to a purely public request: fetch USD exchange rates and email them. This is effectively the same operation that succeeded in Turn 1, but now it fails. The session was tagged as private in Turn 2, and that tag never clears within the session.

```python
prompt_3 = "Get the USD exchange rates and email them to trader@bank.com with subject 'USD update'"

try:
    run_3, nodes_3 = await run_agent(agent, prompt_3, message_history=message_history, verbose=True)
except ToolPermissionError as e:
    print(f"\nGuardrail activated: {e}")
```

This demonstrates the ratchet principle. Even though the exchange rates themselves are public, the agent's context window still contains the account balance from Turn 2 as a tool result. If the CONNECT tool were allowed, the agent could include that balance in the email body -- not because it intends to leak data, but because it optimizes for helpfulness and the balance is available context. The ratchet prevents this by removing the exfiltration vector entirely.

## Where Tagging Belongs in Practice

The example places the `add_private_dataset()` call directly inside the `get_balance` tool function. In a production system, this responsibility belongs to the connector layer. A SQL connector that queries a database marked as confidential in the catalog would tag the session automatically when returning results. A file connector reading from a protected directory would do the same. The tagging happens as a side effect of data retrieval, independent of the agent's reasoning or the user's instructions. This is precisely what makes the mechanism reliable: it operates below the prompt level, where advisory instructions cannot be circumvented.

## Key Takeaways

Session-level tagging with `PrivateData` provides a hard enforcement mechanism that blocks CONNECT tools once sensitive data enters the session. The `@tool_permission` decorator checks the private data state on every CONNECT tool invocation, raising `ToolPermissionError` before the function body runs. Sensitivity only escalates within a session and never degrades, following the ratchet principle. The compliance state is stored outside the agent's workspace so the agent cannot tamper with it. In production, connectors tag sessions automatically based on data source classification, removing any reliance on the agent or user to maintain the guardrail.
