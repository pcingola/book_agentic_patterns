## A2A in Detail

A2A is a protocol-level contract for agent interoperability: a small set of operations plus a strict data model that lets independently-built agents exchange messages, manage long-running tasks, and deliver incremental updates over multiple delivery mechanisms. ([A2A Protocol][13])

#### Key abstractions

A2A's main abstractions are designed to match how multi-agent work actually unfolds over time.

An **Agent Card** is the discovery and capability surface: a machine-readable document published by a remote agent that describes who it is, where its endpoint is, which authentication schemes it supports, and what capabilities and skills it claims. This supports "metadata-first" routing and policy checks before any work begins.

A **Task** is a stateful unit of work with its own identity and lifecycle. Tasks exist to support multi-turn collaboration and long-running operations, so an interaction does not have to fit into one synchronous request/response. Instead, the client can start a task, send additional messages, and retrieve updates or results later.

**Messages** are how conversational turns are exchanged, and they are structured as **parts** so that text, structured data, and file references can be represented consistently. **Artifacts** are the concrete outputs attached to a task -- documents, structured results, or other deliverables that can be stored, forwarded, audited, or fed into downstream workflows.

A useful mental model is: **Agent Card** answers "who are you and what can you do?", **Task** answers "what unit of work are we coordinating?", **Messages** carry the interaction, and **Artifacts** are the outputs worth persisting.

#### Agent discovery

A2A discovery is built around retrieving the Agent Card. A common mechanism is a well-known URL under the agent's domain (aligned with established "well-known URI" conventions), allowing clients to probe domains deterministically. Discovery is intentionally explicit: clients can validate capabilities, authentication requirements, and declared skills before initiating a task, and systems can log discovery metadata for audit and governance.

Conceptual snippet:

```python
import requests

def discover_agent_card(domain: str) -> dict:
    url = f"https://{domain}/.well-known/agent-card.json"
    r = requests.get(url, timeout=5)
    r.raise_for_status()
    return r.json()

card = discover_agent_card("billing.example.com")
# Use: card["skills"], card["authentication"], card["capabilities"], card["url"]
```

This "metadata-first" approach matters operationally: it enables capability matching, policy gating (e.g., only delegate to agents with certain auth), and safer orchestration decisions *before* sending sensitive task content.

#### A2A and MCP in composition

A2A and MCP are complementary layers. MCP standardizes how agents interact with tools and resources (structured inputs/outputs, tool schemas, permission boundaries). A2A standardizes how agents interact with *other agents* as autonomous peers (discovery, task lifecycle, messaging, artifact delivery).

A common composition is **A2A for delegation, MCP for tool-use**. A coordinator uses A2A to delegate a task to a specialist agent. The specialist agent, while executing the task, may rely on MCP internally to access databases, file systems, execution sandboxes, or enterprise services. When the specialist completes work (or makes partial progress), it returns results back to the coordinator as A2A messages and artifacts. This separation keeps each protocol focused: A2A doesn't need to understand tool schemas, and MCP doesn't need to standardize multi-agent collaboration.

A minimal task invocation at the wire level (illustrative, independent of any specific framework) looks like this:

```json
{
  "jsonrpc": "2.0",
  "id": "req_123",
  "method": "tasks/send",
  "params": {
    "message": {
      "role": "user",
      "parts": [
        { "kind": "text", "text": "Reconcile invoice #4812 and explain discrepancies." }
      ]
    }
  }
}
```

The important point is not the method name per se, but the design: JSON-RPC provides the envelope; A2A defines the task/message/artifact semantics; and implementations can remain diverse behind the boundary.

#### Ecosystem tooling

The Pydantic ecosystem documents A2A as a practical interoperability layer and provides Python tooling to expose agents as A2A servers and to build clients that can discover agents, initiate tasks, and consume artifacts -- without requiring the agent's internal design to be rewritten around protocol internals. The emphasis is on preserving your existing agent architecture while making the boundary interoperable.

FastMCP, meanwhile, is often used as a pragmatic deployment unit for MCP tool servers. In practice, this leads to a common layered architecture: A2A connects agents across boundaries; MCP connects agents to tools/resources; and FastMCP-style servers host the tool endpoints that agents call. Bridging components can translate between A2A and MCP where needed (for example, to let an A2A-facing agent expose or consume MCP-backed capabilities behind the scenes).

#### What "the spec" really is: operations + data model + bindings

At the lowest level, A2A is defined by (1) a core set of operations (send, stream, get/list/cancel tasks, subscribe, push-config management, extended agent card) and (2) a constrained object model (Task, Message, Part, Artifact, plus streaming event envelopes). ([A2A Protocol][13])

The specification then defines how those operations and objects map onto concrete transports (“protocol bindings”), notably JSON-RPC over HTTP(S), gRPC, and an HTTP+JSON/REST-style mapping. ([A2A Protocol][13])

A key design point is that the same *logical* operations are intended to be functionally equivalent across bindings; the binding decides *how* parameters and service-wide headers/metadata are carried, but not what they mean. ([A2A Protocol][13])


#### Operation surface and execution semantics

The “A2AService” operation set is designed around a task-centric model. Even if you initiate interaction by sending a message, the server may respond by creating/continuing a task, and all subsequent status and artifacts hang off that task identity. The specification’s “SendMessageRequest” carries the client message plus an optional configuration block and optional metadata. ([A2A Protocol][13])

##### `SendMessage` and the `SendMessageConfiguration` contract

`SendMessageConfiguration` is where most of the “knobs” live:

* `acceptedOutputModes`: a list of media types the client is willing to receive in response *parts* (for both messages and artifacts). Servers **should** tailor outputs to these modes. ([A2A Protocol][13])
* `historyLength`: an optional upper bound on how many recent messages of task history should be returned. The semantics are shared across operations: unset means server default; `0` means omit history; `>0` means cap to N most recent. ([A2A Protocol][13])
* `blocking`: when `true`, the server must wait until the task is terminal and return the final task state; when `false`, return immediately after task creation with an in-progress state, and the caller must obtain progress via polling/subscription/push. ([A2A Protocol][13])
* `pushNotificationConfig`: requests server-initiated updates via webhook delivery (covered below). ([A2A Protocol][13])

This configuration block is what makes A2A “async-first” without making simple request/response impossible: a client can force synchronous completion with `blocking: true`, but the spec treats streaming and async delivery as first-class rather than bolt-ons. ([A2A Protocol][13])

##### Blocking vs non-blocking as a protocol-level contract (not an implementation detail)

The `blocking` flag is normative and affects correctness expectations:

* In blocking mode, the server **MUST** wait for terminal states (`completed`, `failed`, `canceled`, `rejected`) and include the final task state with artifacts/status. ([A2A Protocol][13])
* In non-blocking mode, the server **MUST** return right after task creation and expects the client to continue via `GetTask`, subscription, or push. ([A2A Protocol][13])

This matters because it pushes queueing/execution details out of band: even if the server’s internal worker system is distributed, the *observable* behavior must match these semantics.


#### The protocol data model: the “shape” constraints that make interoperability work

A2A’s objects include both “business” fields (task IDs, status) and structural invariants (“exactly one of these fields must be present”) that keep message parsing unambiguous across languages.

##### Message identity and correlation

A `Message` is a unit of communication between client and server. The spec requires `messageId` and makes it creator-generated. This is not cosmetic: the spec explicitly allows Send Message operations to be idempotent and calls out using `messageId` to detect duplicates. ([A2A Protocol][13])

A message may include `contextId` and/or `taskId`:

* For server messages: `contextId` must be present; `taskId` is present only if a task was created.
* For client messages: both are optional, but if both are present they must match the task’s context; if only `taskId` is provided, the server infers `contextId`. ([A2A Protocol][13])

This rule is critical for multi-turn clients: it allows clients to “anchor” continuation on a known task without re-sending full conversational context.

##### Parts: a strict “oneof” content container

A `Part` is the atom of content in both messages and artifacts, and it must contain exactly one of `text`, `file`, or `data`. ([A2A Protocol][13])

That constraint enables predictable parsing and transformation pipelines:

* text → display or feed into downstream LLM steps
* file → fetch via URI or decode bytes, respecting `mediaType` and optional `name`
* data → structured JSON object for machine-to-machine exchange

File parts have their own “oneof”: exactly one of `fileWithUri` or `fileWithBytes`. The spec also frames the intended usage: prefer bytes for small payloads; prefer URI for large payloads. ([A2A Protocol][13])

##### Artifacts: outputs as first-class objects

Artifacts represent task outputs and include an `artifactId` that must be unique at least within a task, plus a list of parts (must contain at least one). ([A2A Protocol][13])

Treating outputs as artifacts rather than “just text” is what allows A2A to cover large files, structured results, and incremental generation in a uniform way.

##### Task states and task status updates

Tasks have states; the spec enumerates states including working, input-required, canceled (terminal), rejected (terminal), and auth-required (special: not terminal and not “interrupted” in the same way as input-required). ([A2A Protocol][13])

A task’s status container includes the current state, optional associated message, and timestamp. ([A2A Protocol][13])


#### Streaming updates: the `StreamResponse` envelope and event types

A2A streaming is not “stream arbitrary tokens” by default; it streams *typed updates* wrapped in a `StreamResponse` envelope. The spec is explicit: a `StreamResponse` must contain exactly one of `task`, `message`, `statusUpdate`, or `artifactUpdate`. ([A2A Protocol][13])

That invariant matters because it defines how clients must implement event loops: you do not parse “some JSON”; you dispatch on which field is present, and you get strongly-typed behavior.

##### `TaskStatusUpdateEvent`

A status update event includes `taskId`, `contextId`, `status`, and a required boolean `final` that indicates whether this is the final event in the stream for the interaction. ([A2A Protocol][13])

A practical implication is that clients should treat `final=true` as a state machine edge, not merely “stream ended”. The spec describes this as the signal for end-of-updates in the cycle and often subsequent stream close. ([A2A Protocol][14])

##### `TaskArtifactUpdateEvent` and chunked artifact reconstruction

Artifact updates are deltas. Each update carries the artifact plus two key booleans:

* `append`: if true, append content to a previously sent artifact with the same ID
* `lastChunk`: if true, this is the final chunk of the artifact ([A2A Protocol][13])

This is the protocol’s answer to “how do I stream a large file/structured output?”: the artifact is the stable identity, and the parts are chunked. A client must reconstruct by `(taskId, artifactId)` and apply append semantics to parts.


#### Push notifications: webhook delivery that reuses the same envelope

Push notifications are not a separate event schema: the spec states that webhook payloads use the same `StreamResponse` format as streaming operations, delivering exactly one of the same event types. ([A2A Protocol][13])

The push payload section is unusually explicit about responsibilities:

* Clients must ACK with 2xx, process idempotently (duplicates may occur), validate task ID, and verify source. ([A2A Protocol][13])
* Agents must attempt delivery at least once per configured webhook and may retry with exponential backoff; recommended timeouts are 10–30 seconds. ([A2A Protocol][13])

This means production-grade push is *not* “fire and forget”: both sides are expected to implement retry/idempotency logic.


#### Service parameters, versioning, and extensions: the “horizontal” control plane

A2A separates per-request metadata (arbitrary JSON) from “service parameters” (case-insensitive string keys + string values) whose transmission depends on binding (HTTP headers for HTTP-based bindings, gRPC metadata for gRPC). ([A2A Protocol][13])

Two standard service parameters are called out:

* `A2A-Version`: client’s protocol version; server returns a version-not-supported error if unsupported. ([A2A Protocol][13])
* `A2A-Extensions`: comma-separated extension URIs the client wants to use. ([A2A Protocol][13])

This is the practical mechanism for incremental evolution: extensions let you strongly-type metadata for specific use cases, while the core stays stable. ([A2A Protocol][13])


#### Protocol bindings and interface negotiation

Agents advertise one or more supported interfaces. Each `AgentInterface` couples a URL with a `protocolBinding` string; the spec calls out core bindings `JSONRPC`, `GRPC`, and `HTTP+JSON`, while keeping the field open for future bindings. ([A2A Protocol][13])

The ordering of interfaces is meaningful: clients should prefer earlier entries when multiple options are supported. ([A2A Protocol][13])

This makes interoperability practical in heterogeneous environments: a client can pick JSON-RPC for browser-like integrations, gRPC for intra-datacenter low-latency, or HTTP+JSON for simple REST stacks—while preserving the same logical semantics.


#### Implementation patterns extracted from real server stacks: broker, worker, storage

A typical A2A server splits responsibilities into:

* an HTTP/gRPC ingress layer that validates requests, checks capabilities, and emits protocol-shaped responses;
* a scheduling component (“broker”) that decides where/how tasks run;
* one or more workers that execute tasks and emit task operations/updates;
* a storage layer that persists task state and artifacts for `GetTask`, resubscription, and recovery.

This architecture is explicitly reflected in common A2A server implementations where the HTTP server schedules work via a broker abstraction intended to support both in-process and remote worker setups, and where workers receive task operations from that broker. ([Pydantic AI][40])

The key protocol-driven reason to build it this way is that A2A requires coherent behavior across:

* non-blocking calls (immediate return + later updates),
* streaming (typed update stream),
* push (webhook updates), and
* polling (`GetTask` / `ListTasks`).

You only get correct semantics if task state and artifact state are stored durably enough to be re-served and re-streamed.


### Concrete pseudocode: “correct-by-construction” client and server logic

The goal here is not a full implementation, but pseudocode that directly encodes the spec’s invariants (`oneof` objects, `blocking` semantics, chunked artifacts, idempotency, and service parameters).

#### Client: send non-blocking, then stream, reconstruct artifacts

```python
function send_and_stream(agent_url, user_text):
    msg = {
      messageId: uuid4(),              // required, creator-generated
      role: "ROLE_USER",
      parts: [{ text: user_text }]
    }

    req = {
      message: msg,
      configuration: {
        acceptedOutputModes: ["text/plain", "application/json"],
        blocking: false,
        historyLength: 0
      }
    }

    headers = {
      "A2A-Version": "0.3",            // service parameter (HTTP header in HTTP bindings)
      "A2A-Extensions": "https://example.com/extensions/citations/v1"
    }

    // Non-blocking: response may contain a task in working/input_required, etc.
    resp = POST(agent_url + "/message:send", json=req, headers=headers)

    task_id = resp.task.id   // naming varies by binding, but concept is: you now have a task handle

    // Prefer streaming for realtime updates when available.
    stream = POST_SSE(agent_url + "/message:stream", json=req, headers=headers)

    artifacts = map<artifactId, ArtifactAccumulator>()
    terminal_seen = false

    for event in stream:
        // Each SSE "data" is a StreamResponse with exactly one field set.
        sr = parse_json(event.data)

        switch which_oneof(sr):         // exactly one of: task|message|statusUpdate|artifactUpdate
            case "message":
                render_message(sr.message)

            case "task":
                // snapshot update; may contain artifacts/history depending on historyLength semantics
                update_task_cache(sr.task)

            case "statusUpdate":
                update_task_status(sr.statusUpdate.status)
                if sr.statusUpdate.final == true:
                    terminal_seen = is_terminal(sr.statusUpdate.status.state)

            case "artifactUpdate":
                a = sr.artifactUpdate.artifact
                acc = artifacts.get_or_create(a.artifactId)

                if sr.artifactUpdate.append == true:
                    acc.append_parts(a.parts)
                else:
                    acc.replace_parts(a.parts)

                if sr.artifactUpdate.lastChunk == true:
                    finalized = acc.finalize()
                    persist_artifact(task_id, finalized)

        if terminal_seen:
            break

    return (task_id, artifacts)
```

Why this matches the spec:

* It treats `messageId` as required and client-generated. ([A2A Protocol][13])
* It uses `acceptedOutputModes`, `blocking`, and `historyLength` exactly as defined, including the shared semantics of history length. ([A2A Protocol][13])
* It dispatches on the `StreamResponse` “exactly one of” invariant and handles status and artifact events accordingly. ([A2A Protocol][13])
* It reconstructs artifacts using `append` and `lastChunk`. ([A2A Protocol][13])

#### Client: idempotent retries using `messageId`

Network retries are inevitable; the spec explicitly allows using `messageId` to detect duplicates for idempotency. ([A2A Protocol][13])

```python
function send_with_retry(agent_url, msg, cfg):
    // msg.messageId is stable across retries
    req = { message: msg, configuration: cfg }

    for attempt in 1..MAX_RETRIES:
        resp = try POST(agent_url + "/message:send", json=req)
        if resp.success:
            return resp

        if resp.error.is_transient:
            sleep(backoff(attempt))
            continue

        raise resp.error

// Server side must treat same messageId as duplicate and avoid double-executing.
```

#### Server: request validation that enforces the “oneof” invariants

A2A’s “Part must contain exactly one of text/file/data” is a protocol requirement, so servers should validate it up-front (before dispatching to workers) and return a validation error if violated. ([A2A Protocol][13])

```python
function validate_message(message):
    assert message.messageId is not empty

    for part in message.parts:
        count = (part.text != null) + (part.file != null) + (part.data != null)
        if count != 1:
            raise InvalidParams("Part must have exactly one of text|file|data")

        if part.file != null:
            f = part.file
            count2 = (f.fileWithUri != null) + (f.fileWithBytes != null)
            if count2 != 1:
                raise InvalidParams("FilePart must have exactly one of uri|bytes")
```

#### Server: `blocking` semantics implemented on top of a broker/worker pipeline

In practice, servers implement A2A semantics by scheduling work and then either returning immediately (non-blocking) or awaiting terminal state (blocking). The scheduling abstraction (“broker”) exists precisely to decouple protocol ingress from task execution and allow multi-worker setups. ([Pydantic AI][40])

```python
function handle_send_message(request, service_params):
    validate_version(service_params["A2A-Version"])  // VersionNotSupported if invalid
    validate_message(request.message)

    // Optional: enforce extension negotiation based on A2A-Extensions header
    extensions = parse_csv(service_params.get("A2A-Extensions", ""))

    // Deduplicate by messageId to achieve idempotency (recommended).
    if storage.has_seen_message_id(request.message.messageId):
        return storage.get_previous_response(request.message.messageId)

    task = task_manager.create_or_resume_task(request.message)

    broker.enqueue(task.id, request.message, request.metadata)  // schedules work

    if request.configuration.blocking == true:
        task = wait_until_terminal(task.id)      // completed/failed/canceled/rejected
        resp = { task: task }
    else:
        resp = { task: task }                    // in-progress snapshot

    storage.record_message_id_response(request.message.messageId, resp)
    return resp
```

This aligns with the normative behavior: non-blocking returns after task creation; blocking waits for terminal state. ([A2A Protocol][13])

#### Server: emitting streaming updates with `StreamResponse`

Streaming endpoints emit a stream of `StreamResponse` objects where exactly one field is set. ([A2A Protocol][13])

```python
function stream_task_updates(task_id):
    // Subscribe to task events from worker/task manager
    for update in task_event_bus.subscribe(task_id):
        if update.type == "status":
            yield { statusUpdate: {
                      taskId: task_id,
                      contextId: update.context_id,
                      status: update.status,
                      final: update.final
                   } }
        else if update.type == "artifact_chunk":
            yield { artifactUpdate: {
                      taskId: task_id,
                      contextId: update.context_id,
                      artifact: update.artifact_delta,
                      append: update.append,
                      lastChunk: update.last_chunk
                   } }
        else if update.type == "message":
            yield { message: update.message }
        else if update.type == "task_snapshot":
            yield { task: update.task }
```

#### Push notification receiver: reusing the same dispatch loop as streaming

Because push payloads reuse `StreamResponse`, your webhook handler can share logic with your SSE consumer. ([A2A Protocol][13])

```python
function webhook_handler(http_request):
    sr = parse_json(http_request.body)     // StreamResponse: exactly one field set

    assert verify_source(http_request)     // signature / token / mTLS / etc.

    if which_oneof(sr) == "statusUpdate":
        apply_status(sr.statusUpdate)
        return 204
    if which_oneof(sr) == "artifactUpdate":
        apply_artifact_delta(sr.artifactUpdate)
        return 204
    if which_oneof(sr) == "task":
        cache_task(sr.task)
        return 204
    if which_oneof(sr) == "message":
        route_message(sr.message)
        return 204
```

This matches the spec's client responsibilities (ACK with 2xx; process idempotently; validate task IDs). ([A2A Protocol][13])

[13]: https://a2a-protocol.org/latest/specification/
[14]: https://a2a-protocol.org/latest/topics/streaming-and-async/
[40]: https://ai.pydantic.dev/a2a/
