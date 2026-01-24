## Hands-On: Context Result Decorator

Tools in agentic systems often return large amounts of data: database query results with thousands of rows, application logs spanning hours of activity, API responses with nested payloads. When this data flows directly into the model's context, it creates problems. The context window fills up with raw data, leaving less room for reasoning. Worse, models can enter what practitioners informally call "the dumb zone" where too much context degrades performance rather than improving it.

The `@context_result` decorator addresses this by truncating large tool outputs before they reach the model. The full result is saved to the workspace for later access, while the model receives a compact preview sufficient for reasoning about the data's structure and content. This hands-on explores the pattern through `example_context_result.ipynb`.

## The Problem: Tools That Produce Large Output

Consider tools that query databases or search logs. A sales data query might return 500 rows of transaction records. A log search might yield hundreds of matching entries. The notebook simulates these scenarios with generator functions:

```python
def generate_sales_data(num_rows: int = 500) -> str:
    """Generate sample sales CSV data."""
    products = ["Widget A", "Widget B", "Gadget X", "Gadget Y", "Device Z"]
    regions = ["North", "South", "East", "West"]

    lines = ["date,product,region,quantity,price,total"]
    # ... generates 500 rows of CSV data
    return "\n".join(lines)
```

The `generate_log_data` function similarly produces timestamped log entries with varying severity levels and components. These generators simulate the kind of output real tools produce.

Without any context management, a tool that returns this data passes it directly to the model:

```python
def query_sales_raw() -> str:
    """Query sales data without context management."""
    return generate_sales_data(500)

raw_data = query_sales_raw()
print(f"Raw data: {len(raw_data)} characters, {len(raw_data.split(chr(10)))} rows")
```

The output shows the scale of the problem: 500 rows of CSV data can easily exceed 30,000 characters. Every tool call that returns this much data consumes a significant portion of the context window. Chain a few such calls together, and you've exhausted your budget for reasoning.

## The Solution: Automatic Truncation

The `@context_result` decorator wraps tool functions to intercept large results. When the return value exceeds a configured threshold, it saves the full content to the workspace, truncates the result for the model, and returns a preview with the file path.

```python
from agentic_patterns.core.context.decorators import context_result

@context_result()
def query_sales(ctx=None) -> str:
    """Query sales data with automatic truncation."""
    return generate_sales_data(500)

@context_result()
def search_logs(keyword: str, ctx=None) -> str:
    """Search application logs for a keyword."""
    logs = generate_log_data(300)
    matching = [line for line in logs.split("\n") if keyword.upper() in line.upper()]
    return "\n".join(matching) if matching else "No matches found"
```

The tools themselves remain simple. They generate or retrieve data and return it as a string. The decorator handles the context management concerns.

When `query_sales()` runs, the decorator:

1. Executes the original function to get the full result
2. Checks if the result exceeds the configured threshold
3. Auto-detects the content type (CSV, JSON, plain text, etc.)
4. Saves the full content to `/workspace/results/result_<id>.csv`
5. Truncates according to content-type rules (head/tail rows for CSV, head/tail lines for text)
6. Returns the path and a truncated preview

The model sees something like:

```
Results saved to /workspace/results/result_a1b2c3d4.csv (32456 chars)

Preview:
date,product,region,quantity,price,total
2024-01-01,Widget A,North,42,199.99,8399.58
2024-01-02,Gadget X,South,17,89.50,1521.50
...
2024-12-30,Device Z,East,31,450.00,13950.00
2024-12-31,Widget B,West,28,125.75,3521.00
```

This preview contains the CSV header, a few head rows, and a few tail rows. The model can understand the data structure, see the date range, and note the column types. If more detail is needed, another tool can read specific portions from the saved file.

## Content-Type Aware Truncation

The decorator auto-detects content type and applies appropriate truncation strategies. CSV data preserves the header row and shows head/tail data rows. JSON content truncates at structural boundaries, keeping the first N and last M array elements while preserving valid JSON syntax. Plain text and logs show head/tail lines. This type awareness ensures previews remain coherent and useful.

The detection logic examines the content's structure:

- Content starting with `{` or `[` is treated as JSON
- Consistent comma counts across lines suggest CSV
- Timestamp patterns indicate log files
- Everything else defaults to plain text

Each type has its own truncation configuration. CSV shows head/tail rows with the header preserved. JSON arrays keep head/tail items with an indicator showing how many were omitted. Large objects truncate to a maximum number of keys. These defaults can be overridden by passing a config name to the decorator.

## Agent Integration

The notebook demonstrates using these context-managed tools with an agent:

```python
system_prompt = """You are a data analyst assistant. When analyzing data:
1. Summarize the structure and content from the preview
2. Identify patterns or anomalies visible in the sample
3. Note that full data is saved to the indicated path for detailed analysis"""

agent = get_agent(system_prompt=system_prompt, tools=[query_sales, search_logs])
```

The system prompt guides the agent to work with previews rather than expecting complete data. When asked to query sales data, the agent calls the tool, receives the truncated preview, and summarizes what it observes.

```python
prompt = "Query the sales data and summarize what you see."
result, _ = await run_agent(agent, prompt, verbose=True)
```

The verbose output shows the tool call returning the truncated preview. The agent's response describes the data structure (columns, date range, value ranges) based on the preview, and notes that full data is available at the workspace path.

Similarly, when searching logs for ERROR entries:

```python
prompt = "Search the logs for ERROR entries and summarize the issues."
result, _ = await run_agent(agent, prompt, verbose=True)
```

The agent calls `search_logs("ERROR")`, receives a preview of matching log lines, and summarizes the error patterns it observes. The preview shows enough context (timestamps, components, messages) for meaningful analysis without consuming excessive context.

## The ctx Parameter

The decorated functions include an optional `ctx` parameter. This carries context information (user ID, session ID) used by the workspace for file isolation. In the notebook examples, `ctx` defaults to `None`, which uses default workspace paths. In production, the agent framework passes context through this parameter, enabling multi-tenant isolation.

The decorator extracts `ctx` from keyword arguments and passes it to the workspace functions when saving the full result. Tools don't need special handling; they simply declare the parameter with a default value.

## Connection to Token Budgeting

The context result pattern is one component of a broader token budgeting strategy. By limiting how much each tool contributes to the context, you create predictable space allocation. A conversation with multiple tool calls stays within budget because each tool's contribution is bounded.

Combined with history compaction (summarizing old turns) and selective evidence retrieval, the context result decorator helps maintain the "intentional loss" principle described in context engineering: when something must be dropped, drop it deliberately based on priority rather than arbitrarily through truncation.

## Key Takeaways

Large tool outputs degrade agent performance by consuming context and overwhelming the model's attention. The `@context_result` decorator provides automatic truncation while preserving full data for later access.

The pattern saves complete results to the workspace and returns previews with file paths. Type-aware truncation ensures previews remain coherent for CSV, JSON, logs, and other formats.

Tools remain simple. They return full results as strings; the decorator handles context management. The `ctx` parameter enables workspace isolation without polluting the tool's public interface.

Design system prompts to guide agents on working with previews. Agents should summarize visible patterns and note that full data is available for detailed analysis when needed.
