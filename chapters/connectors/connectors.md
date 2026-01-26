# Connector patterns

Agents are only as useful as the data they can reliably read and safely change, so “connectors” should expose a small set of predictable operations that cover most everyday data access needs.

## Connector patterns

A connector, in the agent sense, is a tool surface that turns an external system into a few stable verbs the agent can call directly. The key design constraint is that the verbs must be generic enough to work across many backends, but opinionated enough to provide real leverage (validation, previews, schema discovery, safe writes, and bounded reads). A raw “HTTP request tool” is too generic to be dependable, while a “SQL connector” is generic in a useful way because SQL is itself a strong abstraction and most databases provide the same introspection and query semantics.

In practice, three connector archetypes solve the majority of day-to-day enterprise use cases for agents: file/object storage connectors, SQL connectors, and OpenAPI/REST connectors.

### File and object-storage connectors

The simplest and most widely applicable connector is “file-like access.” This includes local files, network shares, and object stores such as S3, GCS, and Azure Blob. Although their underlying semantics differ (paths vs keys, atomic rename vs versioned objects), the agent rarely needs those details. What the agent needs is the ability to locate content, preview it, read bounded slices, and apply small edits safely.

A practical, agent-facing file connector typically exposes a small set of operations that map well to both filesystems and object stores:

```python
# Listing and metadata
files.list("docs/")                 # returns children + basic metadata
files.stat("docs/runbook.md")       # size, modified time, etag/version if available

# Bounded reads (critical to keep tool calls cheap and predictable)
files.head("logs/app.log", n=200)   # first N lines (or bytes)
files.tail("logs/app.log", n=200)   # last N lines (or bytes)
files.read("docs/runbook.md", start=0, length=20_000)  # byte-range read

# Writes with safe semantics
files.write("notes/todo.md", content=text, if_match=etag)  # optimistic concurrency
files.append("logs/agent.log", content=line)               # if the backend supports it

# Small edits without re-uploading entire objects when feasible
files.replace_lines("docs/runbook.md", start_line=40, end_line=55, new_lines=patch)
```

The “bounded read” methods (head/tail/range) are not a convenience; they are what makes file connectors workable for agents at scale. Object stores and blob APIs explicitly support metadata reads and range reads (or equivalent headers), which lets a tool implement preview and partial retrieval efficiently. ([AWS Documentation][1])

A common trap is over-generalizing editing. Agents frequently need to make small changes, but arbitrary in-place mutation is not uniformly supported across object stores. The connector should therefore define edits in terms of safe, portable behavior: read the smallest necessary slice, apply a patch deterministically, and write back with concurrency control (ETag / version preconditions) so the agent does not overwrite someone else’s update.

#### Format-aware “specializations” that remain generic

File-like connectors become substantially more useful when they add a few format-aware helpers for the formats that dominate private enterprise data: plain text/markdown/code, CSV/TSV, and JSON.

For text-like content, line-oriented operations are enough:

```python
text = files.read("src/service.py", start=0, length=40_000)
files.replace_lines("src/service.py", 120, 138, new_lines=fixed_block)
```

For CSV, the agent usually wants either a preview table or a cell/row update without manually counting commas. A connector can offer a minimal table abstraction while still being backend-agnostic:

```python
preview = csv.preview("data/customers.csv", rows=20)
csv.update_cell("data/customers.csv", row=12, column="status", value="active")
csv.update_row("data/customers.csv", key={"customer_id": "C-1932"},
               values={"status": "inactive", "churned_at": "2026-01-15"})
```

For JSON, the agent typically needs to inspect a subtree and update a field. JSONPath-like addressing (or a constrained pointer syntax) is enough; the tool should validate that the edit is local and does not accidentally rewrite large unrelated sections:

```python
sub = json.get("config/app.json", path="$.features.rollout")
json.set("config/app.json", path="$.features.rollout.percent", value=25)
```

The important pattern is that format-aware methods do not replace the generic file connector; they sit alongside it as “sharp tools” for the top few formats. This keeps the connector surface small while still being meaningfully usable.

### SQL database connectors

SQL databases are a canonical “80% connector” because SQL provides a stable query abstraction across vendors, and databases expose standardized metadata and query planning interfaces. This makes it possible to offer a single agent-facing connector that works broadly, independent of schema or engine.

A useful SQL connector for agents typically starts with schema discovery, then read-only querying, then (optionally) controlled mutation:

```python
# Schema discovery: the agent should be able to orient itself without prior knowledge
db.list_schemas()
db.list_tables(schema="public")
db.describe_table("public", "invoices")   # columns, types, indexes, constraints
db.sample_rows("public.invoices", limit=10)

# Read-only query with guardrails
db.validate_query("SELECT ...")           # parse + policy checks + cost checks
rows = db.query("SELECT * FROM public.invoices WHERE status = ?", ["overdue"],
                limit=500)

# Optional: writes behind stricter policy gates
db.begin()
db.execute("UPDATE public.invoices SET status = ? WHERE invoice_id = ?",
           ["paid", "INV-1042"])
db.commit()
```

Two details matter more for agents than for traditional application code.

First, “schema first” is not optional. Agents do not have compile-time types or ORM models; they need a reliable way to ask “what tables exist” and “what columns mean.” Schema discovery functions should be optimized for readability (names, types, constraints, and a few sample rows), because this is what enables the agent to generate correct queries and interpret results.

Second, validation must be a first-class operation, not an afterthought. An agent should be able to ask the connector to reject unsafe queries (for example, unbounded scans, cross-joins without predicates, or queries that violate access policy) before execution. Many systems implement this as a combination of parsing, allow/deny lists, parameterization enforcement, and optionally an “explain” step to estimate cost. Even when the connector supports writes, mutation should be explicit (separate method), transactional by default, and subject to stricter policy (table allowlists, row-level constraints, and mandatory WHERE clauses for UPDATE/DELETE).

This is one of the rare places where “generic” remains very effective: the connector can be broadly applicable because SQL itself is the abstraction, and schema discovery works regardless of application domain.

### OpenAPI / REST API connectors

HTTP APIs can be too generic to be reliable for agents unless the connector gives the agent meaningful structure: what endpoints exist, what parameters are required, what schemas are expected, how authentication works, and how pagination or idempotency is handled.

OpenAPI is the standard mechanism for supplying that structure. When an API is described with OpenAPI, a connector can list endpoints, describe the request/response shapes, validate inputs, and normalize error handling and pagination without embedding service-specific code in the agent. ([OpenAPI Initiative Publications][2])

A practical agent-facing surface looks like this:

```python
# Discovery
api.list_endpoints()                       # e.g., "GET /tickets", "POST /tickets"
api.describe("POST /tickets")              # summary, required fields, auth scopes

# Safe calling with validation
req = {"title": "VPN broken", "priority": "P1", "assignee": "netops"}
api.validate("POST /tickets", req)         # schema + enum checks + required fields
resp2 = api.call("POST /tickets", req, idempotency_key="case-1042")

# Pagination normalization
for page in api.paginate("GET /tickets", params={"status": "open"}, page_size=200):
    process(page.items)
```

The design goal is to avoid a “generic API connector” that is just `http_get(url)` and `http_post(url, body)`. Those primitives push complexity onto the agent, which then must infer required fields, handle pagination styles, encode authentication correctly, and interpret error responses. By contrast, an OpenAPI-driven connector can make the agent reliably productive by turning undocumented details into discoverable tool affordances, and by ensuring that calls are validated before they hit production services. ([OpenAPI Initiative Publications][2])

## Graph and relationship connectors

Graph and relationship stores appear whenever the primary question is not “what records match this filter,” but “how things are connected.” Ownership hierarchies, dependency graphs, identity and access models, data lineage, and knowledge graphs all fall into this category. In these systems, the value is not in individual rows or documents, but in traversals, neighborhoods, and paths.

From an agent’s perspective, graph databases do not fit cleanly into file or SQL connectors. While many graph systems expose SQL-like interfaces or can be flattened into tables, doing so discards the semantics that make graphs useful in the first place. At the same time, exposing a full graph query language (Cypher, Gremlin, SPARQL) directly to an agent is unnecessarily complex and brittle.

The connector pattern that works for agents is therefore deliberately constrained. Instead of arbitrary queries, the graph connector exposes a small set of verbs that capture the most common reasoning tasks while keeping execution bounded and predictable.

The first responsibility of a graph connector is structural discovery. An agent must be able to orient itself without prior knowledge of the domain model:

```python
graph.list_node_types()
graph.list_edge_types()
graph.describe_node_type("Service")
graph.describe_edge_type("DEPENDS_ON")
```

This mirrors schema discovery in SQL connectors. The goal is not to expose every internal detail, but to give the agent enough context to reason about what kinds of entities exist and how they may be related.

Once oriented, the agent typically needs to retrieve individual nodes and their immediate context:

```python
service = graph.get_node("Service", id="payments-api")
deps = graph.neighbors(
    node_type="Service",
    node_id="payments-api",
    edge_type="DEPENDS_ON",
    direction="out",
    depth=1
)
```

Neighborhood queries like this account for a large fraction of practical graph usage. They allow the agent to answer questions such as “what does this service depend on,” “who owns this resource,” or “what systems are affected if this component fails,” without traversing the entire graph.

More advanced reasoning often requires limited path exploration. Here again, the connector should favor bounded, intention-revealing operations rather than open-ended graph queries:

```python
path = graph.find_path(
    from_node=("User", "alice"),
    to_node=("Service", "billing"),
    max_depth=4
)
```

By requiring explicit depth limits and start/end nodes, the connector ensures that graph exploration remains tractable and auditable. This is analogous to requiring LIMIT clauses or query validation in SQL connectors.

Importantly, graph connectors for agents are almost always read-heavy. Mutation operations (adding or removing nodes or edges) are far less common and typically subject to strict governance, because graph structure often encodes critical organizational or security knowledge. When writes are supported, they should be explicit, heavily validated, and rarely part of autonomous agent workflows.

Graph connectors are especially valuable in enterprise environments for system dependency analysis, IAM and authorization reasoning, ownership and escalation paths, and data lineage or provenance tracking. Including this connector archetype closes one of the few remaining gaps not covered by file, SQL, or OpenAPI connectors, while still respecting the core design principle: expose only those abstractions that agents can use reliably and safely.

In practice, this makes the graph connector a specialized but high-leverage addition. It does not replace SQL or file access, but complements them in domains where relationships, not records, are the primary unit of meaning.

You are right to call this out. **Controlled vocabularies and ontologies are a distinct connector archetype**, and they are not fully covered by files, SQL, or graphs—even though they may be implemented on top of any of those.

They matter because they constrain *meaning*, not just *structure*. For agents operating over private data, this is often the difference between “technically correct” and “organizationally correct.”

Below is a subsection that fits naturally after Graph connectors.

---

## Controlled vocabularies and ontology connectors

Controlled vocabularies and ontologies define the *allowed language* of a system: canonical terms, enumerations, synonyms, hierarchies, and semantic relationships. They are common in regulated, data-intensive, or long-lived domains such as healthcare, finance, life sciences, enterprise architecture, and data governance.

While these resources are often stored in files, databases, or graph stores, exposing them through generic connectors loses their primary purpose. Agents do not need raw tables of codes; they need to know which values are valid, what they mean, and how they relate to each other.

A vocabulary or ontology connector therefore focuses on **term discovery, validation, and normalization**, rather than arbitrary querying.

The most basic capability is listing and describing vocabularies:

```python
vocab.list_vocabularies()
vocab.describe("ticket_priority")
```

This allows an agent to discover that a controlled set exists at all, rather than inventing free-text values that later fail validation.

Once a vocabulary is known, the agent must be able to enumerate and interpret its terms:

```python
vocab.list_terms("ticket_priority")
vocab.describe_term("ticket_priority", code="P1")
```

Descriptions typically include human-readable labels, definitions, allowed contexts, and deprecation status. This information is essential for agents generating user-facing text or structured updates.

Validation is the most critical operation. Before writing to a database or calling an API, the agent should be able to check that a value conforms to the controlled vocabulary:

```python
vocab.validate("ticket_priority", value="P1")
vocab.validate("ticket_priority", value="high")   # returns false + suggestions
```

In many systems, normalization is equally important. Agents often encounter synonyms, legacy codes, or user-provided text that must be mapped to canonical terms:

```python
canonical = vocab.normalize("ticket_priority", value="high")
# returns "P1"
```

More sophisticated ontologies introduce hierarchy and semantic relations. In those cases, the connector can expose limited navigational operations without becoming a full graph API:

```python
vocab.parents("diagnosis_code", code="E11.9")
vocab.children("incident_category", code="NETWORK")
```

This allows agents to reason about generalization and specialization (for example, rolling up metrics or selecting the appropriate level of specificity) while keeping traversal depth constrained.

Controlled vocabulary connectors are especially important when agents perform writes: updating records, generating tickets, classifying documents, or calling APIs with enumerated fields. Without this connector, agents tend to hallucinate plausible but invalid values, leading to brittle workflows and hidden failures.

Conceptually, this connector sits between schema and semantics. SQL schemas define *what shape* data can take; vocabularies define *what meanings* are allowed. Treating vocabularies as first-class connectors acknowledges that meaning is shared infrastructure, not incidental metadata.

Including this archetype strengthens the chapter by making explicit how agents stay aligned with organizational language, policies, and domain standards—something that cannot be reliably achieved through generic file or database access alone.

## References

1. OpenAPI Initiative. *OpenAPI Specification v3.1.0*. Specification, 2021. ([OpenAPI Initiative Publications][2])
2. OpenAPI Initiative. *OpenAPI Specification 3.1.0 Released*. OpenAPI Initiative Blog, 2021. ([OpenAPI Initiative][3])
3. Amazon Web Services. *Amazon S3 API Reference: HeadObject*. AWS Documentation. ([AWS Documentation][1])
4. Amazon Web Services. *Amazon S3 API Reference: GetObject*. AWS Documentation. ([AWS Documentation][4])
5. Amazon Web Services. *Amazon S3 API Reference: PutObject*. AWS Documentation. ([AWS Documentation][5])
6. Google Cloud. *Cloud Storage JSON API: Objects: get*. Google Cloud Documentation. ([Google Cloud Documentation][6])
7. Microsoft. *Specifying the range header for Blob service operations*. Microsoft Learn, 2023. ([Microsoft Learn][7])

[1]: https://docs.aws.amazon.com/AmazonS3/latest/API/API_HeadObject.html?utm_source=chatgpt.com "HeadObject - Amazon Simple Storage Service"
[2]: https://spec.openapis.org/oas/v3.1.0.html?utm_source=chatgpt.com "OpenAPI Specification v3.1.0"
[3]: https://www.openapis.org/blog/2021/02/18/openapi-specification-3-1-released?utm_source=chatgpt.com "OpenAPI Specification 3.1.0 Released"
[4]: https://docs.aws.amazon.com/AmazonS3/latest/API/API_GetObject.html?utm_source=chatgpt.com "GetObject - Amazon Simple Storage Service"
[5]: https://docs.aws.amazon.com/AmazonS3/latest/API/API_PutObject.html?utm_source=chatgpt.com "PutObject - Amazon Simple Storage Service"
[6]: https://docs.cloud.google.com/storage/docs/json_api/v1/objects/get?utm_source=chatgpt.com "Objects: get | Cloud Storage"
[7]: https://learn.microsoft.com/en-us/rest/api/storageservices/specifying-the-range-header-for-blob-service-operations?utm_source=chatgpt.com "Specify the range header for Blob service operations"
