## Enterprise MCP Proxy

### The Problem

In a production environment, agents connect directly to individual MCP servers. Each server handles its own authentication, each agent manages its own connections, and there is no centralized place to observe, control, or meter what is happening across the system. This works for small deployments but breaks down at enterprise scale, where security, compliance, and cost control are non-negotiable.

The issues compound. A new MCP server requires updating every agent's configuration. Authorization rules are scattered across servers. There is no single audit trail. Rate limiting, if it exists at all, is per-server rather than per-user. Cost attribution is impossible because no component has a global view of usage.

### Proxy Architecture

The MCP proxy sits between agents and backend MCP servers as a single entry point. It is itself a FastMCP server that uses `FastMCP.as_proxy()` and `mount()` to compose backends, preserving their full MCP surface -- tools with schemas, prompts, and resources. Agents connect to the proxy using the same protocol they would use to connect to any MCP server. Tools are namespaced automatically (e.g., `sql_run_query`, `file_ops_read_file`).

```
                    +------------------+
                    |    MCP Proxy     |
Agent A  ---------> |  auth | authz   | --------> sql server
Agent B  ---------> |  rate | audit   | --------> file_ops server
Agent C  ---------> |  circuit | acct  | --------> data_analysis server
                    +------------------+
```

Because the proxy speaks MCP on both sides, it is transparent to agents. An agent does not know or care whether it is talking to the proxy or directly to a backend. FastMCP's composition handles session management, feature forwarding (sampling, elicitation, logging, progress), and schema preservation automatically.

Enterprise cross-cutting concerns are implemented as FastMCP middleware, not as manual checks inside tool handlers. This is important: middleware applies uniformly to all operations (tools, prompts, resources), is composable, and follows the standard pipeline pattern where each middleware can inspect, modify, or reject requests before passing them to the next layer.

### Cross-Cutting Concerns

The proxy addresses ten concerns.

**Authentication and identity propagation.** The `AuthSessionMiddleware` (reused from `core/mcp/`) validates JWT tokens at entry and sets the user session context. Backend servers trust the proxy's identity propagation.

**Authorization.** The `AuthorizationMiddleware` evaluates whether the caller's role is allowed to invoke the requested tool. Policies are defined in configuration using glob patterns (e.g., `sql_*` to allow all SQL tools, `sql_execute_write` to deny a specific one). Deny rules take precedence over allow rules. If no policies are configured, all access is denied by default -- this is the secure posture.

**Server composition.** Backend servers are mounted using `FastMCP.as_proxy()` + `mount()`. This is a live (dynamic) connection: changes to a backend's tools are reflected immediately without restarting the proxy. Each backend is mounted with a prefix for automatic namespacing. Unlike manual tool aggregation, this preserves the full MCP surface including input schemas, prompts, and resources.

**Network isolation.** Network isolation for private data is handled at the backend level using `MCPServerPrivateData` (dual-instance routing with the one-way ratchet). The proxy does not duplicate this concern -- it delegates to backends that already enforce isolation. This keeps the proxy focused on cross-cutting concerns that span all backends.

**Observability.** FastMCP provides built-in `LoggingMiddleware` and `TimingMiddleware` that emit structured logs for every operation. The proxy's `AuditMiddleware` extends this with persistent, queryable records.

**Rate limiting.** FastMCP's built-in `RateLimitingMiddleware` enforces call rates with configurable requests-per-second and burst capacity. When a limit is exceeded, the request is rejected with an error, allowing the agent to back off gracefully.

**Circuit breaking.** The `CircuitBreakerMiddleware` tracks consecutive failures per backend. After a configurable threshold, the circuit opens and requests are rejected immediately, preventing cascading failures. After a recovery timeout, the circuit enters a half-open state to probe whether the backend has recovered.

**Audit trail.** The `AuditMiddleware` records every tool invocation to an append-only JSON Lines file with full context: timestamp, user, tenant, session, tool, arguments, status, and duration. In production this would be replaced by a proper audit service or message queue; the JSON Lines format keeps the implementation simple while remaining easy to ingest into any log aggregation system.

**Multi-tenancy.** Tenant identity is extracted from JWT claims (`org_id`). Each tenant gets isolated audit entries and budget tracking. Tenants cannot observe or affect each other.

**Accounting and cost attribution.** The `AccountingMiddleware` tracks usage per user, tenant, session, and tool. Budget alerts fire when configurable thresholds are crossed (warning at N calls, hard limit at M). This enables chargeback models, capacity planning, and cost-aware agent design.

### Configuration

The proxy is configured in `config.yaml` under the `mcp_proxy` key:

```yaml
mcp_proxy:
  port: 8200

  backends:
    - name: sql
      url: http://localhost:8101/mcp
    - name: file_ops
      url: http://localhost:8103/mcp
    - name: data_analysis
      url: http://localhost:8104/mcp

  policies:
    - role: analyst
      allow: ["sql_*", "data_analysis_*"]
      deny: ["sql_execute_write"]
    - role: admin
      allow: ["*"]

  rate_limit:
    requests_per_second: 1.0
    burst_capacity: 20

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
- `proxy_server.py` -- Builds the FastMCP server: mounts backends via `as_proxy()`, wires middleware stack, registers introspection tools (`proxy_audit_read`, `proxy_accounting_usage`)
- `middleware.py` -- FastMCP middleware: `AuthorizationMiddleware`, `CircuitBreakerMiddleware`, `AuditMiddleware`, `AccountingMiddleware`
- `authorization.py` -- Policy evaluation engine (glob-based allow/deny rules)
- `circuit_breaker.py` -- Per-server circuit breaker state machine
- `audit.py` -- Append-only audit log (JSON Lines file)
- `accounting.py` -- Usage tracking and budget alerts
- `server.py` -- Entry point for creating and running the proxy
