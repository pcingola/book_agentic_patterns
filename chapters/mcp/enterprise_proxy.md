## Enterprise MCP Proxy

### The Problem

In a production environment, agents connect directly to individual MCP servers. Each server handles its own authentication, each agent manages its own connections, and there is no centralized place to observe, control, or meter what is happening across the system. This works for small deployments but breaks down at enterprise scale, where security, compliance, and cost control are non-negotiable.

The issues compound. A new MCP server requires updating every agent's configuration. Authorization rules are scattered across servers. There is no single audit trail. Rate limiting, if it exists at all, is per-server rather than per-user. Cost attribution is impossible because no component has a global view of usage.

### Proxy Architecture

The MCP proxy sits between agents and backend MCP servers as a single entry point. It is itself an MCP server -- agents connect to it using the same protocol they would use to connect to any MCP server. The proxy discovers tools from all registered backends, namespaces them (e.g., `sql.run_query`, `file_ops.read_file`), and exposes the aggregated tool list to clients.

```
                    +------------------+
                    |    MCP Proxy     |
Agent A  ---------> |  auth | authz   | --------> sql server
Agent B  ---------> |  rate | audit   | --------> file_ops server
Agent C  ---------> |  circuit | acct  | --------> data_analysis server
                    +------------------+
```

Because the proxy speaks MCP on both sides, it is transparent to agents. An agent does not know or care whether it is talking to the proxy or directly to a backend. This preserves all MCP semantics -- lifecycle, capability negotiation, error classification -- while adding enterprise cross-cutting concerns at a single point.

### Cross-Cutting Concerns

The proxy addresses ten concerns, each implemented as an independent component that can be enabled or configured separately.

**Authentication and identity propagation.** The proxy validates JWT tokens at entry. Once validated, the user identity (user ID, tenant, session, role) is extracted from claims and propagated to backend servers. Individual servers do not need to implement auth; they trust the proxy.

**Authorization.** A policy engine evaluates whether the caller's role is allowed to invoke the requested tool. Policies are defined in configuration using glob patterns (e.g., `sql.*` to allow all SQL tools, `sql.execute_write` to deny a specific one). Deny rules take precedence over allow rules.

**Server registry and discovery.** Backend servers are registered in configuration. On startup, the proxy connects to each, discovers its tools via `list_tools`, and builds the aggregated tool list. Servers can be added or removed at runtime. Health checks track which backends are available.

**Network isolation.** The proxy extends the dual-instance pattern from `MCPServerPrivateData` to the proxy layer. When a session contains private data, the proxy routes to isolated backend instances (configured via `url_isolated`). The one-way ratchet -- once private, always private for that session -- is enforced centrally.

**Observability.** Every tool invocation is logged with structured fields: user, tenant, server, tool, duration, and status. Metrics (call count, error rate, latency) are collected per tool, per server, per user, and per tenant. OpenTelemetry integration enables distributed tracing across proxy and backends.

**Rate limiting.** Token-bucket rate limiters enforce per-user and per-server call rates. When a limit is exceeded, the proxy returns a `ToolRetryError` with a retry hint, allowing the agent to back off gracefully rather than failing hard.

**Circuit breaking.** Each backend has a circuit breaker that tracks consecutive failures. After a threshold, the circuit opens and the proxy immediately returns a `ToolFatalError` for that backend, preventing cascading failures. After a recovery timeout, the circuit enters a half-open state to probe whether the backend has recovered.

**Audit trail.** An append-only audit log records every tool invocation with full context: timestamp, user, tenant, session, server, tool, arguments (redacted as needed), status, and duration. The log is queryable for compliance review and forensic investigation.

**Multi-tenancy.** Tenant identity is extracted from JWT claims (`org_id`). Each tenant gets isolated quotas, rate limits, audit entries, and optionally distinct sets of allowed backends. Tenants cannot observe or affect each other.

**Accounting and cost attribution.** Usage is tracked per user, tenant, session, and server. Budget alerts fire when configurable thresholds are crossed (warning at N calls, hard limit at M). This enables chargeback models, capacity planning, and cost-aware agent design.

### Configuration

The proxy is configured in `config.yaml` under the `mcp_proxy` key:

```yaml
mcp_proxy:
  port: 8200
  health_check_interval: 30

  backends:
    - name: sql
      url: http://localhost:8101/mcp
      url_isolated: http://localhost:8102/mcp
    - name: file_ops
      url: http://localhost:8103/mcp
    - name: data_analysis
      url: http://localhost:8104/mcp

  policies:
    - role: analyst
      allow: ["sql.*", "data_analysis.*"]
      deny: ["sql.execute_write"]
    - role: admin
      allow: ["*"]

  rate_limits:
    default:
      requests_per_minute: 60
    per_server:
      sql:
        requests_per_minute: 30

  circuit_breaker:
    failure_threshold: 5
    recovery_timeout: 30

  accounting:
    budget_alerts:
      - tenant: "*"
        warn_at: 1000
        hard_limit: 5000
```

### Trade-Offs

The proxy adds a network hop and connection overhead to every tool call. For latency-sensitive workloads, this cost may be significant. The proxy is also a single point of failure -- though this is mitigated by running multiple proxy instances behind a load balancer, since the proxy itself is stateless (audit and metrics can be backed by shared stores).

The proxy introduces operational complexity: another service to deploy, monitor, and configure. This is justified when the alternative -- implementing auth, audit, rate limiting, and cost tracking in every agent and every MCP server independently -- is more complex and less reliable.

### Implementation

The proxy lives in `agentic_patterns/mcp/proxy/` with each concern in its own module:

- `config.py` -- Pydantic models for proxy configuration
- `registry.py` -- Server discovery and health tracking
- `proxy_server.py` -- Main proxy server that wires all concerns together
- `authorization.py` -- Policy-based access control
- `rate_limiter.py` -- Token-bucket rate limiting
- `circuit_breaker.py` -- Per-server circuit breakers
- `observability.py` -- Structured logging and metrics collection
- `audit.py` -- Append-only audit log (SQLite-backed)
- `accounting.py` -- Usage tracking and budget alerts
- `server.py` -- Entry point for running the proxy
