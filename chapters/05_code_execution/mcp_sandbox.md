## MCP Sandbox Overview

MCP Sandbox is an implementation of CodeAct. Itprovides secure, isolated execution environments for running arbitrary code through Docker containers. The system manages concurrent multi-tenant sessions, each with dedicated containers and filesystems, while ensuring resource isolation, failure recovery, and operational observability.

## Core Architecture

### Multi-Tenant Session Model

The architecture implements strict session isolation where each user session operates in a dedicated container with its own filesystem. Sessions are identified by a composite key (`user_id:session_id`), enabling multiple concurrent sessions per user while maintaining complete isolation.

**Key Design Decisions**:
- Composite session keys provide natural multi-tenancy without complex access control
- One-to-one mapping between sessions and containers simplifies lifecycle management
- Session state machines (CREATING → RUNNING → STOPPED/ERROR) enable predictable state transitions
- Activity tracking with configurable timeouts enables automatic resource reclamation

**Trade-offs**:
- Each session requires a full container (higher resource usage vs. simpler isolation)
- Container startup latency on first request (mitigated by lazy creation pattern)
- Resource overhead acceptable for strong isolation guarantees

### Data Isolation Through Filesystem Namespacing

Each session's data resides in a host directory mounted into the container at a fixed path. This design provides filesystem isolation while enabling data persistence across container lifecycles.

**Directory Hierarchy**:
```
{base_data_dir}/
  `-- {user_id}/
      `-- {session_id}/
          `-- [session data]
```

**Benefits**:
- Physical isolation at filesystem level prevents cross-session access
- Data persists when containers are recreated after failures
- Path translation layer (`to_host_path`/`to_container_path`) abstracts storage details
- Supports both bind mounts (local development) and named volumes (production)

**Path Translation Pattern**:
- Container paths are fixed (`/workspace`) for consistency
- Host paths computed from session context (`user_id`, `session_id`)
- Translation happens at the boundary between application and container layers
- Volume subpaths enable multi-tenancy on shared storage

### Lifecycle Management with Health Monitoring

Containers follow a managed lifecycle with verification at each stage and continuous health monitoring to detect failures.

**Startup Verification**:
- Containers must achieve sustained "running" state (multiple consecutive checks)
- Prevents race conditions where containers briefly appear running before crashing
- Startup failures captured with diagnostic logs for debugging
- Fast-fail approach: Reject containers that cannot reach stable state

**Continuous Health Monitoring**:
- Background thread periodically checks all tracked containers
- Detects external failures: manual stops, crashes, OOM kills, removals
- Handler pattern enables reactive responses to failures
- Polling interval trades detection latency vs. system load

**Automatic Cleanup**:
- Age-based cleanup removes old containers automatically
- Prevents resource accumulation from abandoned sessions
- Force cleanup on startup handles unclean shutdowns
- Port resources released synchronously with container removal

### Multi-Level Failure Detection

The system implements defense-in-depth for failure detection, combining proactive monitoring with reactive validation.

**Detection Layers**:

1. **Proactive Layer** (Health Monitoring):
   - Periodic background polling of all containers
   - Detects failures even when system is idle
   - Marks affected sessions for automatic recovery

2. **Reactive Layer** (Pre-Use Validation):
   - Status check before every operation
   - Catches failures between monitoring intervals
   - Ensures container validity immediately before use

3. **Recovery Layer** (Automatic Recreation):
   - Sessions marked ERROR automatically recreated on next use
   - Transparent to clients (idempotent operations)
   - Data preserved through persistent storage

**Failure Flow**:
```
External Failure
    ↓
Health Monitor Detection
    ↓
Session Marked ERROR
    ↓
Client Next Request
    ↓
Pre-Use Validation
    ↓
Container Recreated
    ↓
Operation Proceeds
```

This layered approach provides maximum detection latency of one monitoring interval while ensuring operations never proceed on failed containers.

### Concurrency Model

The system uses multi-threaded background processing with careful synchronization to handle concurrent operations safely.

**Thread Categories**:
- **Lifecycle Threads**: Container cleanup, session expiration
- **Monitoring Threads**: Health checks, service status monitoring
- **Execution Threads**: Command execution with timeout enforcement

**Synchronization Strategy**:
- Fine-grained locks protect shared data structures
- Copy-before-iterate pattern prevents modification-during-iteration
- All background threads are daemon threads (clean shutdown)
- Lock-free reads where possible through immutable snapshots

**Command Execution Isolation**:
- Each command execution runs in isolated process
- Timeout enforcement through process termination
- Inter-process communication via queues (not shared memory)
- Graceful degradation: SIGTERM → SIGKILL escalation

**Race Condition Prevention**:
- Sustained state checks (multiple consecutive reads) for critical transitions
- Activity updates before status checks (establishes happens-before relationships)
- Atomic state transitions through lock-protected modifications
- No assumptions about operation ordering across threads

### Service Management Architecture

Long-running processes (web servers, databases) require different lifecycle management than one-off commands. The service subsystem addresses this with background process management and health monitoring.

**Background Execution Pattern**:
- Services started via `nohup` with output redirection
- PID captured and tracked for lifecycle operations
- Process monitoring through PID checks, not container status
- Exit code captured for post-mortem analysis

**Monitoring Strategy**:
- Per-session service monitor with dedicated thread
- Periodic process existence checks via PID
- Port detection through `lsof` (dynamic port discovery)
- Status updates don't affect session activity (read-only monitoring)

**Service State Machine**:
```
STARTING → RUNNING → STOPPED (graceful)
                   → FAILED (error exit)
                   → STOPPING → STOPPED (manual stop)
```

**Lifecycle Operations**:
- **Start**: Generate script, execute with nohup, capture PID
- **Monitor**: Check PID, update ports, detect failures
- **Stop**: Graceful SIGTERM, wait, force SIGKILL if needed, fallback to pattern kill
- **Logs**: Tail stdout/stderr files, queryable by clients

**Design Rationale**:
- Services don't allocate specific ports (container has pre-allocated pool)
- System detects actual ports post-startup (flexible port binding)
- Services cleared on container failure (stale state eliminated)
- No automatic restart (client controls service lifecycle)

### Resource Management

**Port Allocation**:
- Fixed pool of ports allocated per container at creation
- Singleton port manager prevents double-allocation
- Ports released when container removed (no leaks)
- Services bind to any available port within allocation

**Resource Limits**:
- CPU quotas prevent CPU exhaustion
- Memory limits prevent OOM on host
- Configurable per-container via ContainerConfig
- Limits enforced by container runtime

**Port Management Pattern**:
- Pre-allocation at container creation (not on-demand)
- Fixed pool per container (predictable resource usage)
- Container-scoped allocation (cleanup happens naturally)
- Detection over configuration (discover actual ports post-startup)

### Security Architecture

**Defense-in-Depth Layers**:

1. **Container Isolation**:
   - Separate Linux namespaces per session
   - Non-root execution (runs as dedicated user)
   - Resource limits prevent DoS
   - Filesystem isolation through mount namespaces

2. **Network Security**:
   - Configurable port binding (localhost vs. all interfaces)
   - Optional proxy mode for restricted environments
   - Port exhaustion prevention through fixed pools
   - Service port range isolation

3. **Execution Security**:
   - Timeout enforcement prevents infinite loops
   - Working directory restrictions
   - Command execution through controlled interfaces
   - Script generation with safe path handling

4. **Access Control**:
   - Session-based isolation (no cross-session access)
   - Path translation prevents directory traversal
   - Workspace-scoped file operations
   - Session authentication at API boundary

**Proxy Mode Design**:
- Containers inherit parent's network configuration
- Enables corporate proxy compliance
- Maintains network isolation in restricted environments
- Optional feature activated via configuration

### Observability Design

Comprehensive structured logging enables debugging, auditing, and operational monitoring.

**Log Categories**:
- **System Logs**: Infrastructure events (container lifecycle, health monitoring)
- **Command Logs**: Execution events with timing and results
- **Code Logs**: Programming language execution with full context
- **Service Logs**: Long-running process lifecycle and health

**Log Enrichment Strategy**:
- Context propagation: All logs include user_id, session_id, container_id
- Timing information: Duration tracking for performance analysis
- Error context: Stack traces, diagnostic output, pre-failure state
- Correlation IDs: Trace requests across component boundaries

**Structured Logging Benefits**:
- Machine-readable format (JSON) enables automated analysis
- Queryable by multiple dimensions (user, session, event type)
- Consistent schema across all log types
- Extensible through metadata fields

**Operational Visibility**:
- Container failures logged with diagnostic information
- Service failures include stdout/stderr snapshots
- Background thread errors logged without crashing threads
- Health monitoring events tracked for trend analysis

## Key Design Patterns

### Lazy Initialization with Auto-Creation

Resources created on first use rather than eagerly. Sessions and containers created when first accessed, not when user connects.

**Benefits**:
- Reduces resource consumption (only create what's needed)
- Faster apparent response (no upfront cost)
- Natural load distribution (creation spreads over time)

**Implementation**: `ensure_container_available()` checks existence and creates if needed transparently to caller.

### Handler Registration for Event Notification

Components register callbacks with lifecycle managers to receive notifications about events (container failures, service crashes).

**Benefits**:
- Loose coupling between components
- Easy to extend with new handlers
- Event processing isolated from detection

**Pattern**:
```python
container_manager.register_external_failure_handler(
    session_manager.handle_external_container_failure
)
```

### Copy-Before-Iterate for Thread Safety

Shared collections copied before iteration to avoid modification-during-iteration errors without holding locks during processing.

**Pattern**:
```python
with self.lock:
    items_copy = list(self.items.values())
# Process without lock
for item in items_copy:
    process(item)
```

**Trade-offs**: Memory cost of copy vs. reduced lock contention.

### Singleton Pattern for Global Resources

Shared resources like PortManager use singleton pattern to ensure single source of truth.

**Rationale**: Port allocation must be globally coordinated to prevent conflicts.

**Implementation**: Module-level instance with accessor function.

### Base Class Pattern for Common Functionality

`BaseOperator` provides common functionality (session management, container checks, logging) to all operator types (shell, code, service).

**Benefits**:
- Code reuse across operator types
- Consistent patterns for container access
- Centralized session activity tracking
- Uniform error handling

### Monitoring Pattern with Read-Only Operations

Service monitoring reads status without updating session activity, preventing monitors from keeping sessions alive indefinitely.

**Key Distinction**:
- User operations: Update session activity (keep alive)
- Monitoring operations: Read-only (don't affect lifetime)

**Implementation**: Separate code paths with `update_activity` flag.

## Key Learnings and Best Practices

### Sustained State Verification

Don't trust single status checks for critical state transitions. Container appearing "running" once doesn't guarantee stability.

**Solution**: Require multiple consecutive checks before considering state stable. Prevents race conditions where containers briefly appear running before crashing.

### Separation of Detection and Recovery

Failure detection and recovery should be separate concerns handled at different layers.

- Health monitoring detects failures and updates state
- Request handling triggers recovery when needed
- Separation enables testing each independently

### Activity-Based Lifecycle Management

Resources (sessions, containers) lifetime controlled by inactivity timeout rather than absolute TTL.

**Benefits**:
- Active sessions never expire unexpectedly
- Inactive resources reclaimed automatically
- Activity tracking simple (update timestamp on use)

### Workspace Persistence Pattern

Separating workspace storage from container lifecycle enables transparent container recreation.

- Data outlives containers
- Failures recoverable without data loss
- Container becomes disposable execution environment

### Monitoring Without Side Effects

Background monitoring must not affect system state (beyond updates to monitoring data).

**Principle**: Monitoring checks status but doesn't trigger activity updates, session creation, or container recreation.

**Rationale**: Prevents monitoring from keeping resources alive indefinitely.

### Graceful Degradation in Cleanup

Cleanup operations should never crash the cleanup process. Log errors but continue processing remaining items.

**Pattern**:
```python
for item in items:
    try:
        cleanup(item)
    except Exception as e:
        log_error(e)  # Don't crash cleanup thread
        continue
```

### Timeout Enforcement Through Process Isolation

Reliable timeout enforcement requires process isolation. Cannot reliably interrupt thread executing user code.

**Solution**: Execute commands in separate process, terminate process on timeout.

### Pre-allocated Resource Pools

Pre-allocate resources (ports) at container creation rather than on-demand.

**Benefits**:
- Predictable resource usage
- Simpler allocation logic
- Natural cleanup (resources released with container)
- Prevents resource exhaustion from gradual leaks

### State Machine Clarity

Explicit state machines with well-defined transitions make system behavior predictable.

**Examples**:
- Container status: CREATING → RUNNING → STOPPED/ERROR
- Service status: STARTING → RUNNING → STOPPED/FAILED
- Session status tracks container status

Clear states enable:
- Predictable error handling
- Simplified recovery logic
- Better observability

## Scalability Considerations

**Current Design Limits**:
- One container per session (1:1 ratio)
- Background threads poll all tracked resources
- Port pool size limits concurrent containers

**Scaling Strategies**:
- Horizontal: Multiple MCP server instances with load balancing
- Vertical: Increase container resource limits
- Port pools: Separate ranges per server instance
- Monitoring: Migrate to event-based model for large container counts

**Trade-offs Accepted**:
- Polling overhead acceptable for hundreds of containers
- One container per session provides strongest isolation
- Port pre-allocation wastes some resources for predictability
