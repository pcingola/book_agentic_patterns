# Hands-On: Deterministic Testing

Agentic systems present a testing challenge: the LLM at their core is non-deterministic. The same prompt can produce different outputs across runs, making traditional assertion-based testing unreliable. This hands-on explores how to achieve deterministic testing by replacing the non-deterministic components with controlled mocks.

The key insight is that while we cannot make the LLM deterministic, we can replace it entirely during testing. By substituting the model with a mock that returns predefined responses, and optionally mocking tools as well, we gain complete control over agent behavior. This enables fast, reliable tests that verify the agent's logic without network calls or API costs.

## ModelMock: Replacing the LLM

`ModelMock` is a drop-in replacement for real models. Instead of calling an LLM API, it returns responses from a predefined list in sequence. The agent code runs unchanged; only the underlying model differs.

```python
from agentic_patterns.testing import ModelMock

model = ModelMock(responses=["The capital of France is Paris."])
agent = get_agent(model=model)

agent_run, _ = await run_agent(agent, "What is the capital of France?")
output = agent_run.result.output

assert output == "The capital of France is Paris."
```

The `responses` list contains what the model will return on each invocation. For a simple request-response interaction, a single response suffices. The agent processes this response exactly as it would process a real LLM response, but the output is now deterministic and testable with exact assertions.

## Simulating Tool Calls

Agents often use tools, and the model must decide when to call them. `ModelMock` can return `ToolCallPart` objects to simulate the model requesting a tool call. The framework then executes the actual tool, and the result flows back to the model (which returns the next response from the list).

```python
from pydantic_ai.messages import ToolCallPart

def get_weather(city: str) -> str:
    """Get weather for a city."""
    return f"Weather in {city}: 22C, sunny"

model = ModelMock(responses=[
    ToolCallPart(tool_name="get_weather", args={"city": "Paris"}),
    "The weather in Paris is 22C and sunny."
])
agent = get_agent(model=model, tools=[get_weather])
```

The sequence here is: first response triggers the tool call, the tool executes and returns its result, then the second response becomes the final output. This tests that the agent correctly handles the tool-use loop, even though the decision to call the tool was predetermined.

## tool_mock: Controlling Tool Outputs

Sometimes the tool itself needs to be mocked. Real tools might call external APIs, access databases, or have side effects we want to avoid in tests. `tool_mock` wraps a function and replaces its implementation with predefined return values.

```python
from agentic_patterns.testing import tool_mock

def fetch_stock_price(symbol: str) -> float:
    """Fetch current stock price."""
    raise NotImplementedError("Real implementation would call API")

mocked_fetch = tool_mock(fetch_stock_price, return_values=[150.25, 2800.50])
```

The mocked function preserves the original's signature and docstring (which the model sees), but returns values from the list instead of executing the real code. Each call consumes one value; if called more times than values provided, an error is raised.

The mock also tracks call statistics:

```python
print(f"Tool was called {mocked_fetch.call_count} times")
print(f"Call arguments: {mocked_fetch.call_args_list}")

assert mocked_fetch.call_count == 2
assert mocked_fetch.call_args_list[0] == ((), {"symbol": "AAPL"})
```

This enables assertions not just on outputs but on how tools were invoked: which arguments were passed, in what order, and how many times.

## Complete Workflow Testing

Combining `ModelMock` and `tool_mock` enables testing of complex multi-step workflows with full determinism. Consider an agent that searches a database for users and then sends each user an email:

```python
mocked_search = tool_mock(search_database, return_values=[["user@example.com", "admin@example.com"]])
mocked_email = tool_mock(send_email, return_values=[True, True])

model = ModelMock(responses=[
    ToolCallPart(tool_name="search_database", args={"query": "active users"}),
    [ToolCallPart(tool_name="send_email", args={"to": "user@example.com", ...}),
     ToolCallPart(tool_name="send_email", args={"to": "admin@example.com", ...})],
    "Sent emails to 2 users."
])

agent = get_agent(model=model, tools=[mocked_search, mocked_email])
```

The test specifies the exact workflow: first the model calls search, then it calls email twice (as a list of tool calls in one response), then it produces the final message. After running, assertions verify the workflow executed correctly:

```python
assert mocked_search.call_count == 1
assert mocked_email.call_count == 2
assert "2 users" in agent_run.result.output
```

This pattern tests the agent's orchestration logic, the integration between model and tools, and the final output, all without any non-determinism.

## When to Use Deterministic Testing

Deterministic testing with mocks is most valuable for verifying agent logic and tool integration. It answers questions like: does the agent call the right tools in the right order? Does it handle tool outputs correctly? Does the final response incorporate tool results appropriately?

These tests complement, rather than replace, evaluation against real models. Evals assess whether the model makes good decisions; deterministic tests verify that once a decision is made, the system executes it correctly. The testing section of this chapter emphasized this layered approach: maximize deterministic testing below the model boundary, then use evals to assess the model's behavior.

By separating these concerns, test failures become easier to diagnose. A failing deterministic test points to a bug in agent logic or tool integration. A failing eval points to model behavior that needs adjustment, whether through prompt changes, different model selection, or architectural modifications.
