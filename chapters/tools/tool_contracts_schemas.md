## Tool Contracts and Schemas

Tool contracts and schemas define the precise, machine-verifiable interface through which a language model reasons about, invokes, composes, and recovers from interactions with external tools.

### Tools as explicit contracts

A tool is defined not by its implementation, but by its *contract*. This contract specifies the tool’s name, intent, inputs, outputs, and operational constraints. In Python-centric systems, contracts are naturally derived from function signatures, type annotations, and docstrings.

A minimal example illustrates the idea:

```python
class WeatherRequest(BaseModel):
    city: str
    unit: str  # "C" or "F"

class WeatherResponse(BaseModel):
    temperature: float
    unit: str

def get_weather(req: WeatherRequest) -> WeatherResponse:
    """Return the current temperature for a city."""
    ...
```

From this definition, the runtime derives a schema that is passed to the language model. The model never sees executable code—only the interface. This separation is critical: the model reasons about *capabilities*, not implementations.

### Contracts in the tool call loop

The tool call loop described earlier—where the model proposes an action, the framework executes it, and the result feeds back as context—depends entirely on contracts for correctness. Contracts ensure that every transition in this loop is well defined and inspectable: arguments are validated before execution, and if validation fails, the error is returned to the model as structured feedback, allowing it to correct itself.

### Explicit termination via final schemas

To avoid ambiguous stopping conditions, frameworks introduce an explicit final schema. Rather than replying with unconstrained text, the model must emit a structured object representing completion.

```python
class FinalResult(BaseModel):
    answer: str
```

Termination is therefore a validated action, not an implicit convention. This guarantees that every agent run ends in a well-typed result, simplifying downstream processing, logging, and evaluation.

### Retries as part of the contract

Retries are not an implementation detail; they are part of the tool contract. A tool’s schema and documentation can communicate whether retries are safe, under what conditions they should occur, and which inputs must remain stable.

A retry-aware contract might include an explicit idempotency key:

```python
class PaymentRequest(BaseModel):
    amount_cents: int
    idempotency_key: str
```

When a tool fails, the failure is returned as structured data rather than an exception. Errors can be marked as retryable or fatal, allowing the model to reason explicitly about recovery. Because retries are mediated through the same schema, repeated calls remain safe, auditable, and deterministic.

This design shifts retry logic from opaque control flow into the reasoning loop itself.

### Parallel tool calls

Not all tool calls are sequential. In many cases, the model can identify independent actions that may be executed concurrently. Modern agent runtimes allow the model to emit *multiple* tool calls in a single step when their contracts indicate no dependency.

Conceptually:

```json
[
  { "name": "fetch_user_profile", "arguments": { "user_id": "123" } },
  { "name": "fetch_recent_orders", "arguments": { "user_id": "123" } }
]
```

The framework executes these calls in parallel and returns their results together as structured state updates. From the model’s perspective, this is still a single reasoning step, but one that expands the available context more efficiently.

Parallelism is only safe because contracts make dependencies explicit. Without schemas, concurrent execution would be speculative; with schemas, it becomes a controlled optimization.

### Why this pattern matters

Tool contracts and schemas transform tool use from an informal convention into a disciplined interface. They enable validation before execution, structured feedback after execution, principled retries, safe parallelism, and explicit termination.

More importantly, they define clear capability boundaries. The model can act only through interfaces that are precisely specified, making agent behavior predictable, debuggable, and scalable. In practice, this pattern is what allows tool use to serve as the foundation of reliable agentic systems rather than an ad hoc extension of prompting.

