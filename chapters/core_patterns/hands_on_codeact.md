## Hands-On: CodeAct

CodeAct is a pattern where an agent reasons primarily by writing and executing code, using program execution itself as the main feedback loop. Instead of text-based actions like ReAct's `LookupOrder[id]`, the agent generates actual Python code that runs in a sandboxed environment. Execution results, including errors, become first-class feedback that guides the next iteration.

This hands-on explores CodeAct using `example_codeact.ipynb`, demonstrating how executable code becomes the agent's primary mode of thought.

### Why Code as the Action Modality?

ReAct and similar patterns use structured text commands that a parser converts into function calls. This works well for predefined actions, but becomes limiting when tasks require flexibility. Consider asking an agent to analyze a dataset: you would need to predefine every possible analysis operation as a discrete action.

CodeAct sidesteps this limitation by letting the agent write arbitrary code. The agent can express any computation directly, observe the results, and adapt. This is particularly powerful for tasks involving data manipulation, numerical computation, or any domain where the solution space is too large to enumerate as discrete actions.

### The Execution Sandbox

The sandbox provides a controlled environment where the agent's code runs. Two properties are essential: isolation (the code cannot affect the host system) and persistence (variables survive across executions so the agent can build state incrementally).

```python
class CodeSandbox:
    def __init__(self):
        self.namespace = {"__builtins__": __builtins__}

    def execute(self, code: str, timeout: float = 5.0) -> str:
        stdout_capture = io.StringIO()
        try:
            with redirect_stdout(stdout_capture):
                exec(code, self.namespace)
            output = stdout_capture.getvalue()
            return output if output else "(code executed successfully, no output)"
        except Exception as e:
            return f"Error: {type(e).__name__}: {e}"
```

The `namespace` dictionary persists across calls to `execute()`. When the agent writes `x = 42` in one execution, `x` remains available in subsequent executions. This allows the agent to work incrementally, defining data structures, computing intermediate results, and building toward a final answer across multiple steps.

Errors are captured and returned as strings rather than raised. This is intentional: errors are informative feedback, not failures. A `NameError` tells the agent it referenced an undefined variable. A `TypeError` reveals a misunderstanding about data types. The agent incorporates this information and tries again.

### The CodeAct Prompt

The prompt establishes the code-centric interaction pattern:

```python
CODEACT_PROMPT = """You are a code-execution agent. Solve tasks by writing and executing Python code.

Rules:
1. Write code in ```python blocks. Each block will be executed and you'll see the output.
2. Use print() to show results - this is how you see what's happening.
3. Variables persist between executions, so you can build on previous code.
4. If you get an error, analyze it and fix your code in the next iteration.
5. When the task is complete, write DONE followed by a brief summary.
...
"""
```

The prompt explicitly tells the model that `print()` is how it observes results. Without this, the model might write code that computes correct values but never displays them, leaving it blind to its own progress. The persistence rule enables multi-step problem solving: the agent can define helper functions, store intermediate results, and reference them later.

### The CodeAct Loop

The loop orchestrates the interaction between the model and the sandbox:

```python
async def codeact_loop(task: str, max_steps: int = 6) -> str:
    agent = get_agent(system_prompt=CODEACT_PROMPT)
    sandbox = CodeSandbox()
    trajectory = f"Task: {task}\n"

    for step in range(max_steps):
        agent_run, _ = await run_agent(agent, trajectory)
        response = agent_run.result.output.strip()
        trajectory += f"\nAssistant: {response}\n"

        code_blocks = extract_code_blocks(response)
        if code_blocks:
            for code in code_blocks:
                output = sandbox.execute(code.strip())
                trajectory += f"\n[Execution output: {output}]\n"

        if "DONE" in response.upper():
            return response
```

The trajectory accumulates the entire interaction history. Each iteration, the model sees the original task, all previous code it wrote, and all execution outputs. This context allows the model to reason about what worked, what failed, and what to try next.

Code blocks are extracted using a regex that matches markdown-style fenced code:

```python
def extract_code_blocks(text: str) -> list[str]:
    pattern = r"```python\s*(.*?)```"
    return re.findall(pattern, text, re.DOTALL)
```

### Example: Data Analysis

The first example asks the agent to analyze sales data. The task requires computing totals, finding maximums, and calculating averages, all operations that benefit from direct code execution.

```
Task: Analyze this sales data and find total revenue, best selling product, average order value.
Data: orders = [{"product": "Widget A", "quantity": 5, "price": 10.00}, ...]
```

The agent might respond:

```
I'll start by loading the data and calculating total revenue.

```python
orders = [
    {"product": "Widget A", "quantity": 5, "price": 10.00},
    {"product": "Widget B", "quantity": 3, "price": 25.00},
    ...
]
total_revenue = sum(o["quantity"] * o["price"] for o in orders)
print(f"Total revenue: ${total_revenue:.2f}")
```

[Execution output: Total revenue: $455.00]
```

The agent sees the output and continues:

```
Now I'll find the best selling product by quantity.

```python
from collections import defaultdict
product_qty = defaultdict(int)
for o in orders:
    product_qty[o["product"]] += o["quantity"]
best = max(product_qty.items(), key=lambda x: x[1])
print(f"Best selling: {best[0]} with {best[1]} units")
```

[Execution output: Best selling: Widget A with 13 units]
```

Notice how the agent builds on the `orders` variable defined in the first execution. The persistent namespace enables this incremental approach.

### Error Recovery

The second example demonstrates error handling. When the agent makes a mistake, the error message becomes feedback:

```
Task: Calculate the mean and standard deviation of [4, 8, 15, 16, 23, 42].
Do not import any libraries.
```

The agent might first attempt:

```python
numbers = [4, 8, 15, 16, 23, 42]
mean = sum(numbers) / len(numbers)
variance = sum((x - mean) ** 2 for x in numbers) / len(numbers)
std_dev = sqrt(variance)
print(f"Mean: {mean}, Std Dev: {std_dev}")
```

```
[Execution output: Error: NameError: name 'sqrt' is not defined]
```

The agent observes the error and corrects:

```python
std_dev = variance ** 0.5
print(f"Mean: {mean:.2f}, Std Dev: {std_dev:.2f}")
```

```
[Execution output: Mean: 18.00, Std Dev: 12.17]
```

The error did not crash the session. Instead, it provided specific information (undefined `sqrt`) that guided the fix (use `** 0.5`). This is the core insight of CodeAct: execution failures are learning signals, not terminal conditions.

### CodeAct vs ReAct

ReAct uses text-based actions with predefined semantics: `LookupOrder[id]` always means the same thing. This makes ReAct suitable for systems with well-defined APIs and limited action spaces. CodeAct is more flexible but less constrained. The agent can write any valid Python, which is powerful for open-ended tasks but requires more careful sandboxing.

In practice, many systems combine both approaches. Predefined tools handle common operations with guaranteed semantics, while a code execution capability handles edge cases and complex computations. The choice depends on the task domain and the acceptable tradeoff between flexibility and predictability.

### Key Takeaways

CodeAct treats executable code as the agent's primary action modality. The agent writes code, observes execution results, and iterates. This tight feedback loop grounds reasoning in actual program behavior rather than hypothetical outcomes.

Persistent execution environments enable incremental problem solving. The agent can define variables, build data structures, and reference previous work across multiple iterations. This mirrors how humans use REPLs and notebooks for exploratory programming.

Errors are informative feedback, not failures. A well-designed CodeAct system captures exceptions and returns them as observations. The agent learns from errors and corrects its approach, turning mistakes into progress.

The pattern is particularly suited to data analysis, numerical computation, and tasks where the solution space is too large to enumerate as discrete actions. When the task requires flexibility and the domain supports programmatic solutions, CodeAct provides a natural and powerful execution model.
