## Connector patterns

Despite the apparent diversity of external systems, most connectors reduce to a small set of interaction archetypes. The differences between “SQL,” “GitHub,” or “Jira” are largely syntactic and operational, not conceptual. From the agent’s perspective, what matters is how information is retrieved or how actions are performed, not the underlying transport or vendor-specific API. In practice, nearly all connectors fall into three archetypes: query connectors, tool connectors, and document/blob connectors. Many real systems combine more than one, but they remain composable from these primitives.


A unified connector interface is a single, small set of operations that every data source can map onto, even if some operations are unsupported. The point is not that every connector implements every capability, but that the agent runtime can rely on the same verbs, the same control knobs, and the same result envelopes across systems. The connector is the place where transport details (HTTP vs SQL vs filesystem), pagination mechanics, auth refresh, retries, and safety constraints live. The agent sees stable primitives: addressable resources, callable tools, and policy-governed execution.

A connector therefore exposes two surfaces. The first is a resource surface for reading and navigating “things” (documents, issues, rows-as-a-virtual-resource, blobs), all addressable by URI-like identifiers and all returning metadata and provenance. The second is an action surface for executing operations (either generic CRUD-like verbs or named tools), always with typed inputs/outputs, and always subject to policy and budgeting. Anything that does not fit in one request/response is represented explicitly as either pagination (an iterator) or a long-running job (a handle you can poll or subscribe to).

```python
class Connector:
    """
    Unified connector interface.
    Methods may raise Unsupported() if the connector cannot perform that capability.
    All methods enforce policy and attach provenance.
    """

    def search(self, query, *, scope=None, limit=50):
        """Find resources matching a query string or structured query."""
        ...

    def get(self, uri, *, range=None):
        """Fetch a single resource by URI. `range` supports partial reads."""
        ...

    def list(self, uri, *, cursor=None, limit=50):
        """List children of a collection-like URI (directory, project, repo, space)."""
        ...

    def query(self, q, *, params=None, limit=1000):
        """Run a declarative query (SQL/GraphQL/CQL/search DSL) and return rows/items."""
        ...

    def create(self, uri, *, data):
        """Create a new resource under a collection URI (issue in project, file in dir)."""
        ...

    def update(self, uri, *, data):
        """Replace or update a resource (typically PUT-like semantics)."""
        ...

    def delete(self, uri):
        """Delete a resource."""
        ...

    def patch(self, uri, *, patch):
        """Apply a minimal change (diff/merge patch) to a resource."""
        ...

    def call(self, tool_name, **args):
        """Invoke a named operation (often OpenAPI-generated or app-specific)."""
        ...

    def subscribe(self, uri_or_topic, *, events, callback_url=None):
        """Register for change notifications (webhooks/push) or return a stream handle."""
        ...

    def job(self, job_id):
        """Get a handle for a long-running operation (status, logs, result retrieval)."""
        ...
```

This interface cleanly covers the connector families you care about. SQL maps primarily to query (and sometimes get for schema resources), OpenAPI maps to call and optionally CRUD verbs, files map to get/list/patch/create/update/delete, Jira/Confluence map to search/get/list/call plus guarded create/update/patch, and GitHub maps to a hybrid where query is GraphQL, call is REST actions, and repository files are resources accessed via get/list/patch.

### Query connectors

Query connectors model systems where the dominant interaction is declarative. The agent formulates a query against a known schema or query language, the system evaluates it, and returns a bounded result set. Relational databases accessed via SQL are the canonical example, but the same pattern appears in Confluence Query Language (CQL), GitHub GraphQL, search endpoints in REST APIs, and many analytics backends.

The defining characteristic of this archetype is that the *query* is the unit of reasoning. The agent is responsible for constructing a valid, well-scoped request, while the system is responsible for execution and optimization. As a result, the primary engineering concerns are schema grounding, validation before execution, pagination and result limits, and enforcement of cost or rate constraints. Query connectors work best when the underlying system supports exploratory access and expressive filtering.

This model breaks down when interaction requires stateful workflows, cross-query transactions, or procedural logic embedded outside the query language. In those cases, forcing everything into a query abstraction often leads to brittle or opaque behavior.

A minimal example of a query connector interface might expose a single, validated execution surface:

```python
def run_query(query: str, max_rows: int) -> QueryResult:
    validate_query(query)
    return database.execute(query, limit=max_rows)
```

The simplicity is intentional. Complexity belongs in schema preparation, validation, and orchestration layers, not in the connector itself.

### Tool connectors

Tool connectors model external systems as collections of typed operations with explicit inputs and outputs. Rather than asking questions declaratively, the agent invokes functions that represent capabilities of the system. OpenAPI-described services, issue trackers like Jira, and most SaaS platforms fit naturally into this model.

In this archetype, reads and writes are expressed as operations, and side effects are first-class. The agent must reason not only about inputs and outputs, but also about when an action is appropriate to perform. Consequently, the critical engineering issues shift toward tool granularity, authentication scopes, write gating, retries, idempotency, and error semantics. Fine-grained tools improve safety but increase orchestration complexity; coarse-grained tools simplify planning but reduce control.

Tool connectors become awkward when the system’s primary use case is exploratory search or bulk retrieval. In such cases, teams often reintroduce an ad-hoc query layer on top of procedural APIs, effectively recreating a query connector inside a tool abstraction.

A typical tool connector exposes operations as typed functions:

```python
def create_issue(project_id: str, title: str, description: str) -> IssueRef:
    ...

def transition_issue(issue_id: str, state: str) -> None:
    ...
```

The connector itself remains thin; policy about when and how these tools may be called lives elsewhere.

### Document and blob connectors

Document or blob connectors treat external systems as stores of addressable content objects. Filesystems, object stores, CSV or JSON artifacts, and even wiki pages fall into this category. The agent interacts with resources by reading subsets of content and applying controlled mutations.

The key abstractions here are stable identifiers, partial or range reads to control context size, versioning, and patch-based writes rather than unconstrained edits. This pattern is particularly important for managing context budgets and ensuring that agents do not inadvertently overwrite large or sensitive documents.

This model breaks down when content changes are governed by complex external workflows, such as approvals, locks, or multi-party merges, that cannot be expressed as simple read and patch operations. In those cases, document access must often be combined with tool-based workflows.

A simplified document connector interface might look like:

```python
def read_document(doc_id: str, start: int, end: int) -> str:
    ...

def apply_patch(doc_id: str, patch: Patch) -> None:
    ...
```

Again, the connector focuses on safe primitives rather than business logic.

### Composite systems and composition

Many important systems are composites rather than pure instances of a single archetype. GitHub combines query access (GraphQL and search), tool-based operations (REST actions), and document access (repository files). Jira combines search-like queries with procedural tools but lacks a true document abstraction. These systems do not invalidate the model; they reinforce it.

The connector layer should expose each archetype explicitly and allow them to compose, rather than inventing a bespoke, monolithic API per product. Composition makes behavior easier to reason about, test, and evolve over time, and it aligns naturally with agent orchestration frameworks that already distinguish between querying, acting, and reading or writing state.

The central takeaway is that connector diversity is mostly accidental complexity. By standardizing on a small number of connector archetypes and pushing authentication, rate limits, workflows, and long-running jobs into policy and orchestration layers, agentic systems can remain simple, extensible, and predictable even as the number of integrations grows.

## References

1. Fielding, R. *Architectural Styles and the Design of Network-based Software Architectures*. Doctoral dissertation, University of California, Irvine, 2000. [https://www.ics.uci.edu/~fielding/pubs/dissertation/top.htm](https://www.ics.uci.edu/~fielding/pubs/dissertation/top.htm)
2. OpenAPI Initiative. *OpenAPI Specification*. Linux Foundation, ongoing. [https://spec.openapis.org](https://spec.openapis.org)
3. Codd, E. F. *A Relational Model of Data for Large Shared Data Banks*. Communications of the ACM, 1970.
4. Gamma, E., Helm, R., Johnson, R., Vlissides, J. *Design Patterns: Elements of Reusable Object-Oriented Software*. Addison-Wesley, 1994.

