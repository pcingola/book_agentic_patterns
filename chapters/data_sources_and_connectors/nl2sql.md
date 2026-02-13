## NL2SQL (Natural Language to SQL)

NL2SQL is the execution pattern in which an agent translates a natural language question into a validated, read-only SQL query, executes it safely, and returns results in a form suitable for both human inspection and downstream processing.

#### The NL2SQL execution pattern

NL2SQL should be understood as a controlled execution pipeline rather than a simple text-to-SQL transformation. The database is a high-impact tool, and the schema is the primary grounding mechanism that constrains the model’s reasoning.

A typical workflow begins with a natural language question. Before any SQL is generated, the agent is provided with a complete, annotated schema describing tables, columns, relationships, and conventions. Using this context, the agent proposes a SQL query. That query is then passed through explicit validation steps that enforce security and correctness constraints, such as read-only access and single-statement execution. Only validated queries are executed, and results are returned in a bounded form.

This separation between reasoning, validation, and execution is what makes NL2SQL robust enough for real-world use.

#### Schema as first-class context

One of the most important lessons from production NL2SQL systems is that schema preparation belongs offline. Instead of querying database catalogs dynamically at runtime, schemas are extracted once, enriched, and cached as structured metadata. This cached schema becomes the authoritative reference for all NL2SQL reasoning.

A “good” schema for agents is not minimal. It is intentionally verbose and explanatory, especially around ambiguous or overloaded fields. Confusing column names are clarified in comments, enum-like fields explicitly list their allowed values, and small samples of real data illustrate typical usage.

A representative schema fragment might look like this:

```sql
-- Table: orders
-- Purpose: Customer purchase orders in the e-commerce system

CREATE TABLE orders (
    order_id INTEGER PRIMARY KEY,
        -- Unique identifier for each order

    status VARCHAR(20),
        -- Current lifecycle state of the order
        -- Allowed values (controlled vocabulary):
        --   pending    : order placed, not yet processed
        --   shipped    : order shipped to customer
        --   cancelled  : order cancelled before shipment

    channel VARCHAR(20),
        -- Sales channel through which the order was placed
        -- Allowed values:
        --   web, mobile_app, phone_support

    total_amount DECIMAL(10,2),
        -- Total order value in USD, including taxes

    created_at TIMESTAMP,
        -- Order creation timestamp in UTC

    customer_id INTEGER
        -- References customers.customer_id
);

-- Sample data (illustrative):
-- order_id , status   , channel     , total_amount
-- 10231    , shipped  , web         , 149.99
-- 10232    , pending  , mobile_app  ,  29.50
```

This level of annotation significantly reduces ambiguity for the agent. It also discourages the model from inventing values that do not exist in the database, a common failure mode when schemas are underspecified.

#### Controlled vocabularies and query reliability

Well-designed NL2SQL schemas emphasize controlled vocabularies. Fields such as status codes, categories, types, or channels should be treated as explicit enums, even if the underlying database does not enforce them strictly.

From an agent’s perspective, controlled vocabularies serve two purposes. First, they constrain generation: when the model knows that `status` can only be one of a small, named set, it is far less likely to hallucinate invalid filter conditions. Second, they improve semantic alignment between user language and database values. Natural language phrases like “open orders” or “completed orders” can be reliably mapped to documented enum values rather than guessed strings.

Embedding enum values directly in schema comments, along with short explanations, makes this mapping explicit. In practice, this often matters more than formal database constraints, because the agent reasons over the schema text rather than the physical DDL alone.

#### Query generation and validation

Even with a high-quality schema, generated SQL must be treated as untrusted input. NL2SQL systems therefore apply multiple validation layers before execution.

At a minimum, only read-only queries are permitted, and multiple statements are rejected, but syntactic validation alone is insufficient because harmful queries may still be possible. A simple syntactic validation step can catch common violations:

```python
query = query.strip()

# WARNING: This is just a quick validation step, ALWAYS rely on DB permissions for security
if not query.upper().startswith("SELECT"):
    raise ValueError("Only SELECT queries are allowed")

if query.rstrip(";").count(";") > 0:
    raise ValueError("Multiple SQL statements are not allowed")
```

Much more effective is to have "READ-ONLY" database users that are restricted by permissions at the database level. This way, even if the agent generates a malicious query, it cannot perform harmful operations.

Beyond syntactic checks, execution safeguards are typically applied. Query timeouts prevent expensive scans from monopolizing database resources, and explicit limits on result size protect both the database and the agent’s context window.

#### Result handling and the workspace

Large result sets should not be injected directly into the agent context. Instead, results are written to files in a shared workspace, and only a small preview is returned.

```python
df.to_csv("workspace/results/orders_summary.csv")

preview = df.head(10)
```

The agent can then summarize the findings, show a few representative rows, and provide the file path for full inspection. This pattern keeps prompts small while preserving complete, reusable data for humans or downstream tools.

#### Security and access control

Production NL2SQL systems operate under strict security constraints. Database access is typically read-only, and credentials are managed externally through a secrets manager. Queries are executed on behalf of users without exposing raw credentials to the agent.

This design supports auditing, user-specific permissions, and credential rotation without modifying agent logic. The agent interacts with the database only through a constrained execution interface.

#### Architectural considerations

Successful NL2SQL systems usually adopt a layered architecture. Database-specific logic is isolated behind abstract interfaces, while business logic operates on standardized result types. This separation allows the same NL2SQL agent to work across multiple databases with minimal changes.

Equally important is minimizing runtime complexity. Schema extraction, annotation, enum detection, and example query generation are expensive operations that belong in offline pipelines. At runtime, the agent should rely entirely on cached metadata and focus on reasoning, validation, and execution.
