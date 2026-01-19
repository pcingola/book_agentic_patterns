# Hands-On: Tool Discovery and Selection

When an agent has access to many tools, presenting all of them in every request becomes inefficient. Context length grows, the model's attention is diluted across irrelevant options, and the likelihood of incorrect tool selection increases. Tool discovery and selection addresses this by using a separate step to identify which tools are relevant before the main agent executes.

This hands-on explores tool selection through `example_tool_selection.ipynb`, demonstrating both a manual approach and the use of `ToolSelector` to automate the process.

## The Scaling Problem

Consider an agent with two tools: `add` and `sub`. The model easily selects the right one for any arithmetic task. Now imagine an agent with fifty tools covering file operations, database queries, API calls, text processing, and more. For a simple addition task, forty-nine of those tools are noise. The model must scan all descriptions, reason about relevance, and avoid being distracted by superficially similar but incorrect options.

Tool selection solves this by adding a preliminary step: before the task-execution agent runs, a tool-selection agent examines the task and filters the tool set down to only relevant capabilities.

## Manual Approach

The notebook begins with a manual implementation to show the mechanics. First, we define tools as Python functions:

```python
def add(a: int, b: int) -> int:
    """Add two numbers"""
    return a + b

def sub(a: int, b: int) -> int:
    """Subtract two numbers"""
    return a - b
```

To present these tools to a selection agent, we need text descriptions. The `func2descr` function extracts this from the function metadata:

```python
def func2descr(f):
    out = f'Tool: {f.__name__}({", ".join(f.__code__.co_varnames[:f.__code__.co_argcount])})\n'
    if f.__doc__:
        out += f'Description: {f.__doc__}\n'
    if f.__annotations__ and 'return' in f.__annotations__:
        out += f'Return type: {f.__annotations__["return"]}\n'
    return out
```

This produces descriptions like:

```
Tool: add(a, b)
Description: Add two numbers
Return type: <class 'int'>
```

The selection agent receives the user query and tool descriptions, then outputs a list of tool names:

```python
agent = get_agent(output_type=list[str])

prompt = f"""
Given the user query, select the tools to use

User query: {user_query}

Tools available:
{tools_descriptions_str}

Answer only using the tool names
"""
result, _ = await run_agent(agent, prompt)
tool_names = result.result.output
```

The structured output (`list[str]`) ensures we get a clean list of names rather than prose. We then filter the original tools to only those selected:

```python
tools_agent = [tools_by_name[name] for name in tool_names if name in tools_by_name]
```

Finally, the task-execution agent runs with just the filtered tools:

```python
agent = get_agent(tools=tools_agent)
result, _ = await run_agent(agent, user_query)
```

This two-stage process means the execution agent never sees irrelevant tools. Its context is focused, and tool selection is more reliable.

## Using ToolSelector

The manual approach works but requires boilerplate. The `ToolSelector` class encapsulates this pattern:

```python
from agentic_patterns.core.tools import ToolSelector

selector = ToolSelector([add, sub])
selected_tools = await selector.select(user_query)
```

Internally, `ToolSelector` uses `func_to_description` to generate richer tool descriptions that include full type signatures:

```
Tool: add(a: int, b: int) -> int
Description: Add two numbers
```

The improved descriptions help the selection agent understand not just what each tool does, but what types of arguments it expects. This matters when tools have similar names but different signatures.

After selection, using the tools is straightforward:

```python
agent = get_agent(tools=selected_tools)
result, _ = await run_agent(agent, user_query)
```

## When Tool Selection Matters

With two or three tools, tool selection adds overhead without much benefit. The model can easily reason over a small set. The pattern becomes valuable when:

The tool catalog is large. Tens or hundreds of tools overwhelm the model's context and attention. Selection reduces the working set to a manageable size.

Tools have overlapping purposes. Multiple tools might handle similar tasks in different ways. A dedicated selection step can apply more careful reasoning about which variant is appropriate.

Safety constraints apply. Some tools should only be available for certain types of tasks. The selection agent can enforce these policies before the execution agent ever sees restricted tools.

Context length is constrained. Each tool description consumes tokens. With many tools, descriptions alone might exceed context limits. Selection keeps the execution agent's context focused on what matters.

## The Two-Agent Architecture

This pattern exemplifies a broader architectural principle: separating planning from execution. The selection agent plans which capabilities are needed. The execution agent carries out the task using only those capabilities.

This separation has several benefits. The selection agent can use different prompting strategies optimized for capability matching. The execution agent operates with a cleaner context. Policies and constraints can be applied at the selection boundary. And the selection result can potentially be cached or reused across similar tasks.

## Key Takeaways

Tool selection is a two-stage process: first identify relevant tools, then execute with only those tools. This keeps the execution agent focused and reduces errors from irrelevant options.

The selection agent uses structured output to return tool names, which are then used to filter the available tools before execution.

`ToolSelector` encapsulates this pattern, handling tool description generation and the selection prompt internally.

Tool selection becomes increasingly valuable as tool catalogs grow, providing a scalable approach to managing large capability sets.
