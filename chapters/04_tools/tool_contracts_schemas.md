## Tool Contracts and Schemas

Tool contracts and schemas define the precise, machine-verifiable interface through which a language model reasons about, invokes, and recovers from interactions with external tools.

### Historical perspective

Early attempts at tool use in language systems relied almost entirely on informal conventions. Models produced free-form text that downstream code attempted to interpret, often using fragile regular expressions or heuristics. This approach inherited problems long known in natural language interfaces: ambiguity, poor error handling, and limited composability.

Two research traditions converged to address these issues. Work on semantic parsing and program induction focused on mapping natural language to well-defined executable structures, while advances in typed data validation and schema languages emphasized explicit contracts between components. With the emergence of large language models capable of reliably emitting structured outputs, these ideas merged into a practical pattern: instead of asking models to *describe* actions, systems could require them to *produce structured objects* conforming to predefined schemas. Around 2022–2023, this approach became central to agent architectures, enabling deterministic tool invocation, validation, retries, and explicit termination.

### Tools as explicit contracts

A tool is not defined by its implementation but by its *contract*. The contract specifies what the tool does, what inputs it accepts, and what outputs it guarantees. In Python-based systems, this contract is naturally derived from function signatures, type hints, and docstrings.

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

From this definition, the framework derives a schema that is passed to the language model. The model never sees the function body—only the name, description, and input/output structure. This separation is fundamental: the model reasons over *interfaces*, not implementations.

### Structured output and tool calls

Once tool contracts are available, the model is constrained to respond using structured output. Instead of emitting arbitrary text, it chooses between producing a tool call that matches one of the schemas or producing a structured final result.

Conceptually, a tool call looks like this:

```json
{ "name": "get_weather", "arguments": { "city": "Buenos Aires", "unit": "C" } }
```

Because the arguments are validated against the schema before execution, malformed calls can be rejected early and corrected by the model. Structured output thus replaces brittle parsing with explicit validation.

### The tool call loop

Tool use is not a single action but a loop. The model emits a structured message, the framework validates and executes it, and the result is fed back to the model as new context. This continues until the model explicitly signals termination.

At a high level, the loop follows this shape:

```python
while True:
    msg = model.generate(state)
    if msg.is_final:
        return validate_final(msg)
    result = execute_tool(msg)
    state.append(result)
```

This loop is the operational core of agentic systems. Contracts and schemas ensure that every transition—model output, tool execution, and state update—is well defined.

### Explicit termination via final schemas

To avoid ambiguous stopping conditions, agent frameworks introduce an explicit final schema. Instead of “just answering,” the model must emit a structured object that represents the final result.

```python
class FinalResult(BaseModel):
    answer: str
```

Termination is therefore a validated action, not an implicit convention. This guarantees that every run ends in a well-typed result, simplifying downstream consumption, logging, and evaluation.

### Failures, retries, and recovery

Schemas also enable principled error handling. When a tool fails, the failure is returned to the model as structured data rather than an unstructured exception. The model can then reason about the error and decide whether to retry, adjust inputs, or terminate.

A retry-aware tool contract might look like:

```python
class PaymentRequest(BaseModel):
    amount_cents: int
    idempotency_key: str
```

The presence of an explicit idempotency key communicates to the model that retries are safe. Errors can be tagged as retryable or fatal, turning recovery into part of the reasoning loop rather than ad hoc control flow.

### Why this pattern matters

Tool contracts and schemas transform tool use from an informal side effect into a first-class reasoning primitive. They enable validation before execution, structured feedback after execution, and explicit termination of agent runs. More importantly, they define clear capability boundaries: the model can only act through interfaces that are precisely specified.

In this sense, contracts and schemas are the foundation that makes tool-using agents robust, debuggable, and scalable. Without them, tool use collapses back into prompt engineering; with them, it becomes an architectural pattern.

### References

1. Andreas, J., et al. *Semantic Parsing as Machine Translation*. ACL, 2013.
2. Liang, P., et al. *Neural Symbolic Machines*. ACL, 2017.
3. OpenAI. *Function Calling and Structured Outputs in Large Language Models*. Technical blog, 2023.
4. Yao, S., et al. *ReAct: Synergizing Reasoning and Acting in Language Models*. ICLR, 2023.
