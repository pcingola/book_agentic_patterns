## REPL

The REPL pattern enables an agent to iteratively execute code in a shared, stateful environment, providing immediate feedback while preserving the illusion of a continuous execution context.

### Historical perspective

The REPL (Read–Eval–Print Loop) is one of the oldest interaction models in computing. It emerged in the 1960s with interactive Lisp systems, where programmers could incrementally define functions, evaluate expressions, and inspect results without recompiling entire programs. This interactive style strongly influenced later environments such as Smalltalk workspaces and, decades later, Python and MATLAB shells.

In the context of AI systems, early program synthesis and symbolic reasoning tools already relied on REPL-like loops to test hypotheses and refine partial solutions. More recently, the rise of notebook environments and agentic systems has renewed interest in REPL semantics as a way to let models explore, test, and refine code through execution. The key research shift has been from “single-shot” code generation to **execution-aware reasoning**, where intermediate results guide subsequent steps.

### The REPL pattern in agentic systems

In an agent setting, a REPL is not merely a convenience for developers; it is a reasoning primitive. The agent alternates between generating code, executing it, observing outputs or errors, and deciding what to do next. This loop allows the agent to ground abstract reasoning in concrete runtime behavior.

A typical agent-driven REPL follows a conceptual loop:

```
while not task_complete:
    code = agent.propose_next_step(observations)
    result = execute(code, state)
    observations = observations + result
```

Two properties distinguish a production-grade REPL from a simple shell.

First, **state continuity**. Each execution step must see the effects of previous steps. Variables, user-defined functions, and imports should persist across executions so that the agent can build solutions incrementally.

Second, **isolation and safety**. Arbitrary code execution is dangerous in long-running systems. Modern REPL designs therefore decouple *logical continuity* from *physical isolation*: each execution runs in a constrained environment, yet the system reconstructs enough context to make the experience appear continuous.

### Process isolation with a persistent-state illusion

A robust REPL for agents typically executes each step in a fresh process. This avoids crashes, memory leaks, and infinite loops from destabilizing the host system. To preserve continuity, the environment state is serialized before execution and merged back afterward.

Conceptually:

```
# Before execution
snapshot = serialize(namespace_without_modules)

# In isolated process
namespace = deserialize(snapshot)
replay(imports)
replay(function_definitions)
exec(code, namespace)
delta = extract_updated_variables(namespace)

# After execution
namespace.update(delta)
```

The important constraint is that only serializable objects can persist. Modules and other non-serializable artifacts are handled indirectly, usually by tracking their source representation rather than their in-memory form.

### Import and function tracking

One subtle challenge in isolated REPL execution is that imports and function definitions do not survive process boundaries. A common solution is to treat them as *replayable declarations*.

Each execution step is analyzed to extract:

* Import statements, stored as source strings.
* Function definitions, stored as their full source.

Before running the next step, all prior imports and function definitions are re-executed in order. This works because imports are idempotent and function redefinition is generally safe.

A simplified illustration:

```
# On parsing a cell
imports += extract_imports(code)
functions += extract_functions(code)

# On next execution
for stmt in imports:
    exec(stmt, namespace)
for fn in functions:
    exec(fn, namespace)
exec(current_code, namespace)
```

This approach preserves developer- and agent-defined APIs across executions without requiring unsafe object sharing.

### Output capture as first-class data

For agents, execution output is not only for human inspection; it is input to the next reasoning step. A REPL therefore treats outputs as structured data rather than raw text.

Typical output categories include:

* Standard output and error streams.
* The value of the last expression.
* Exceptions and tracebacks.
* Structured artifacts such as tables, HTML, or images.

Separating *output storage* from *output references* is a useful best practice. Binary data (for example, images) can be stored internally and exposed via lightweight references, allowing the agent or client to fetch them on demand without bloating every response.

### Asynchronous execution and concurrency

In agent platforms, REPL execution often happens inside servers that must remain responsive. Blocking execution directly in the event loop does not scale. A common pattern is to expose an asynchronous API while offloading the actual execution to worker threads or subprocesses.

Conceptually:

```
async def execute_step(code):
    result = await run_in_worker(process_execute, code)
    return result
```

This separation allows multiple agents or sessions to execute code concurrently while preserving responsiveness.

### Sessions, persistence, and multi-user concerns

Unlike a local shell, an agent REPL usually operates in a multi-user environment. Each session must be isolated, identifiable, and recoverable. Persisting execution history and state to disk after each operation ensures that work is not lost and that sessions can be resumed after failures.

Persistence also enables secondary capabilities, such as exporting the session into a notebook format or replaying execution steps for audit and debugging.

### Best practices distilled

Several best practices consistently emerge when implementing REPLs for agents:

* Prefer process-level isolation over threads for safety and control.
* Serialize only data, not execution artifacts; replay imports and functions explicitly.
* Treat outputs as structured, inspectable objects.
* Make execution asynchronous at the API level.
* Persist state frequently to support recovery and reproducibility.
* Impose explicit limits on execution time and resource usage.

Together, these patterns allow agents to reason *through execution* without compromising system stability.

### References

1. McCarthy, J. *LISP 1.5 Programmer’s Manual*. MIT Press, 1962.
2. Abelson, H., Sussman, G. J., Sussman, J. *Structure and Interpretation of Computer Programs*. MIT Press, 1996.
3. Kluyver, T. et al. *Jupyter Notebooks – a publishing format for reproducible computational workflows*. IOS Press, 2016.
4. Chen, M. et al. *Evaluating Large Language Models Trained on Code*. arXiv, 2021.
