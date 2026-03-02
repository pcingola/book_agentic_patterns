## Security

A2A security defines how agents authenticate, authorize, isolate, and audit cross-agent interactions while preserving composability and asynchronous execution.

### Authentication and Agent Identity

At the protocol level, A2A assumes strong, explicit agent identity rather than implicit trust between peers. Each agent is identified by a stable agent ID and presents verifiable credentials with every request. The protocol deliberately avoids mandating a single authentication mechanism, but its security model presumes cryptographically verifiable identity, typically implemented using OAuth2-style bearer tokens or mutual TLS.

Authentication is performed before any task lifecycle logic is evaluated. A crucial requirement is that the cryptographic identity asserted by the credential is bound to the declared agent ID, preventing confused-deputy and identity-spoofing attacks.

```python
def authenticate_request(http_request):
    token = extract_bearer_token(http_request.headers)
    claims = verify_token_signature(token)

    assert claims.issuer in TRUSTED_ISSUERS
    assert claims.audience == "a2a"

    agent_id = claims.subject
    return AuthContext(
        agent_id=agent_id,
        scopes=claims.scopes,
        expires_at=claims.exp
    )
```

In the core library, this pattern is implemented by `AuthSessionMiddleware` (`core/a2a/middleware.py`), a Starlette middleware that extracts the Bearer token from the `Authorization` header and calls `set_user_session_from_token()` to propagate the authenticated identity into contextvars. Token creation and validation use HS256 JWT via `core/auth.py`, with secrets read from environment variables.

An important design constraint is that task payloads are treated as untrusted data until authentication has completed. Identity verification is therefore orthogonal to task semantics.

### Authorization and Capability Scoping

Authorization in A2A is capability-oriented rather than role-oriented. Instead of assigning broad roles to agents, the protocol evaluates whether a specific agent is permitted to perform a specific protocol operation on a specific resource. This allows fine-grained control over actions such as task creation, inspection, streaming, or cancellation.

Authorization is evaluated at several layers simultaneously: the operation being requested, the relationship between the agent and the task (for example, creator versus observer), and the scope of resources exposed by that task. These checks are intentionally redundant, ensuring that partial privilege does not accidentally grant full access.

```python
def authorize(auth_ctx, operation, task=None):
    if operation not in auth_ctx.scopes:
        raise Forbidden("scope missing")

    if task is not None:
        if operation in WRITE_OPS and task.owner != auth_ctx.agent_id:
            raise Forbidden("not task owner")

    return True
```

A key property of the protocol is that authorization is never assumed to be static. Even for long-running tasks, permissions are re-evaluated on every request, including status polling and streaming updates.

### Task Isolation and Trust Boundaries

In A2A, a task is not merely a unit of work; it is a security boundary. Task state, intermediate artifacts, and final outputs are all scoped to a task ID and an explicit access policy. This prevents unrelated agents from inferring information about concurrent or historical tasks.

Isolation is enforced whenever task state is loaded. Visibility is determined by explicit allow-lists rather than implicit trust derived from network location or execution context.

```python
def load_task(task_id, auth_ctx):
    task = storage.get(task_id)

    if auth_ctx.agent_id not in task.allowed_readers:
        raise Forbidden("task not visible")

    return task
```

This model discourages shared mutable global state across agents. Any shared context must be materialized as task-scoped artifacts with clearly defined read and write permissions.

### Streaming, Polling, and Push Security

Asynchronous interaction modes introduce additional attack surfaces, particularly around replay, hijacking, and information leakage. A2A addresses these risks by binding every asynchronous interaction to authenticated agent identity.

For streaming and polling, authorization is enforced on each request, and continuation tokens or cursors are non-guessable and cryptographically bound to the requesting agent. A stolen cursor cannot be reused by a different agent.

```python
def stream_updates(task_id, cursor, auth_ctx):
    assert cursor.agent_id == auth_ctx.agent_id
    authorize(auth_ctx, "tasks.stream", task_id)

    return event_stream(task_id, cursor)
```

Push notifications require even stricter controls. Endpoints must be explicitly registered and verified, delivery credentials are scoped to a single task or subscription, and revocation immediately invalidates any pending deliveries. This ensures that long-lived subscriptions do not become permanent exfiltration channels.

### Secure Delegation and Agent-to-Agent Calls

Delegation is a core feature of A2A and one of its most sensitive security mechanisms. The protocol does not permit implicit privilege propagation. Instead, delegation is implemented using explicit, narrowly scoped credentials issued by the delegating agent.

When one agent delegates execution to another, the delegated agent receives only the minimal capabilities required to perform the delegated work, and only for a limited time. Even if the delegated agent has broader native permissions, those permissions are not applied to the delegated task.

```python
def create_delegation_token(parent_ctx, allowed_ops, ttl):
    return sign_token({
        "delegator": parent_ctx.agent_id,
        "scopes": allowed_ops,
        "exp": now() + ttl
    })
```

This design prevents privilege amplification across agent networks and ensures that delegation chains remain auditable and bounded.

In the core library, bearer tokens are propagated through `A2AClientConfig.bearer_token`. When configured, `A2AClientExtended` injects the token as an `Authorization: Bearer` header on every request to the remote agent, keeping credential management in configuration rather than scattered across delegation logic.

### Auditability and Non-Repudiation

A2A is designed for environments where accountability matters. Every security-relevant action is expected to generate an audit record, including authentication failures, authorization denials, task lifecycle events, and delegation operations.

Audit records must include the agent identity, the affected task, the operation performed, and a timestamp. Because tasks may span minutes or days, audit logs must be durable and resistant to tampering.

```python
audit_log.write({
    "agent": auth_ctx.agent_id,
    "operation": operation,
    "task_id": task_id,
    "timestamp": now()
})
```

This auditability enables forensic analysis, compliance verification, and operational debugging in multi-agent deployments.

### Interaction with MCP Security

When A2A is composed with Model Context Protocol, the security boundary remains explicit. A2A governs agent identity, task lifecycle, and delegation, while MCP governs tool invocation and context access. Credentials are not implicitly shared across protocols, preventing cross-protocol privilege leakage while preserving composability.
