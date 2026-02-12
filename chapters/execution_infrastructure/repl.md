## REPL

The REPL pattern enables an agent to iteratively execute code in a shared, stateful environment, providing immediate feedback while preserving the illusion of a continuous execution context.

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

### The notebook and cell model

A natural way to organize a REPL for agents is to borrow the notebook metaphor from Jupyter. A **notebook** represents a session: it owns a shared namespace, tracks execution history, and persists its state to disk. Each unit of code submitted for execution is a **cell**.

A cell progresses through a lifecycle: IDLE when created, RUNNING during execution, and then either COMPLETED, ERROR, or TIMEOUT. Each cell records its outputs, execution time, and position in the notebook. A global execution counter tracks how many cells have been run, providing an ordering that both the agent and the user can reference.

This model gives the REPL a clear structure. The notebook manages the shared namespace, the accumulated import and function declarations, and the persistence lifecycle. Cells are self-contained execution units that can be inspected, re-run, or deleted independently.

### Process isolation with a persistent-state illusion

A robust REPL for agents executes each cell in a fresh subprocess. This avoids crashes, memory leaks, and infinite loops from destabilizing the host system. To preserve continuity, the namespace is serialized before execution and restored afterward.

The serialization mechanism uses pickle-based IPC through the filesystem. Before execution, the host pickles the current namespace, accumulated imports, and function definitions into an input file inside a temporary directory. The subprocess reads this input, executes the cell code, and writes the resulting namespace and outputs back to an output file in the same directory. The host then reads the output and merges the updated namespace.

Conceptually:

```
# Before execution -- host side
pickle_write(temp_dir / "input.pkl", {
    code, namespace, import_statements, function_definitions
})

# In isolated subprocess
data = pickle_read(temp_dir / "input.pkl")
namespace = data["namespace"]
replay(data["import_statements"])
replay(data["function_definitions"])
exec(data["code"], namespace)
filtered = filter_picklable(namespace)
pickle_write(temp_dir / "output.pkl", {state, outputs, filtered})

# After execution -- host side
result = pickle_read(temp_dir / "output.pkl")
namespace.update(result.namespace)
```

The important constraint is that only picklable objects can persist. Modules, open file handles, database connections, generators, and threading primitives cannot survive the process boundary. Rather than silently dropping these, a well-designed REPL provides actionable feedback: "reopen file in next cell", "use `def` instead of lambda", "reconnect in next cell". This helps the agent (or user) understand what state was lost and how to recover it.

Some objects require special handling. For example, openpyxl workbooks are not directly picklable, but they can be saved to temporary files and restored via a lightweight reference object. The reference carries the path to the temp file; when the next cell executes, the workbook is reloaded from disk. This pattern generalizes to any complex object that supports save/load semantics but not pickle.

### Sandboxing

Process isolation alone does not provide meaningful security. The subprocess inherits the host's filesystem access, network, and process namespace. A production REPL needs a sandbox layer that restricts what the subprocess can do.

Our implementation uses a generic sandbox abstraction with two backends. On Linux, it uses bubblewrap (`bwrap`), a lightweight container tool that provides filesystem, network, and PID namespace isolation. The sandbox mounts system directories (`/usr`, `/lib`, `/bin`) as read-only, exposes the Python installation for package access, and bind-mounts only the specific directories the cell needs: the workspace (for user data) and the temporary directory (for pickle IPC). Network access and PID isolation can be toggled independently.

On macOS and in development environments where bubblewrap is not available, the sandbox falls back to a plain subprocess with no isolation. A factory function selects the appropriate backend at runtime.

One useful refinement is **data-driven network isolation**. If a session has been flagged as containing private data (for example, after loading sensitive files), the sandbox enables network isolation automatically. This prevents exfiltration of sensitive data through code execution, even if the agent or user does not explicitly request it.

### Import and function tracking

One subtle challenge in isolated REPL execution is that imports and function definitions do not survive process boundaries. A common solution is to treat them as *replayable declarations*.

After each cell executes, the notebook parses the cell's code using AST analysis to extract two kinds of declarations: import statements (both `import x` and `from x import y` forms) and function definitions. These are stored as source strings on the notebook, deduplicated to avoid redundant re-execution.

Before running the next cell, all accumulated imports and function definitions are re-executed in the subprocess's namespace before the cell code runs. This works because imports are idempotent and function redefinition is generally safe.

```
# After cell execution -- notebook side
import_statements += extract_imports(cell.code)   # AST-based
function_definitions += extract_functions(cell.code)  # AST-based

# Before next cell execution -- subprocess side
for stmt in import_statements:
    exec(stmt, namespace)
for fn in function_definitions:
    exec(fn, namespace)
exec(current_code, namespace)
```

This approach preserves developer- and agent-defined APIs across executions without requiring unsafe object sharing.

### Output capture as first-class data

For agents, execution output is not only for human inspection; it is input to the next reasoning step. A REPL therefore treats outputs as structured data rather than raw text.

Each cell produces a list of typed outputs. The output types in our implementation are TEXT, ERROR, HTML, IMAGE, and DATAFRAME. Standard output becomes TEXT, exceptions become ERROR with tracebacks, and matplotlib figures are captured as IMAGE by configuring a non-interactive backend (Agg) and intercepting `plt.show()`.

A particularly important output is the **last-expression value**. Following the Jupyter convention, if the last statement in a cell is an expression (not an assignment or a control structure), its value is captured and included in the output. This is implemented by parsing the cell code as an AST: if the final node is an `Expr`, it is separated from the rest, the preceding code is `exec`'d, and the final expression is `eval`'d to obtain its value.

Separating *output storage* from *output references* is also important. Binary data such as images can be stored internally as raw bytes and exposed to the agent or client via lightweight references (a URI like `notebook://cell/0/image/0`). This prevents large binary payloads from bloating every response.

### Asynchronous execution and concurrency

In agent platforms, REPL execution often happens inside servers that must remain responsive. Even though the sandbox itself uses `asyncio.create_subprocess_exec` (which is async), the agent's code running inside the subprocess can be CPU-intensive -- data transformations, model training, heavy computation -- and the subprocess communication can block for the duration. Running this directly on the event loop would stall all other concurrent requests.

The solution is a two-layer execution model. The cell's `execute` method is async and uses `asyncio.to_thread()` to offload the entire execution to a worker thread. Inside that thread, a fresh event loop runs the async sandbox call:

```python
class Cell(BaseModel):
    async def execute(self, namespace, timeout, import_statements, function_definitions, user_id, session_id):
        self.state = CellState.RUNNING
        self.executed_at = datetime.now()

        await asyncio.to_thread(
            self._execute_sync, namespace, timeout,
            import_statements or [], function_definitions or [],
            user_id, session_id,
        )

    def _execute_sync(self, namespace, timeout, import_statements, function_definitions, user_id, session_id):
        workspace_path = WORKSPACE_DIR / user_id / session_id

        loop = asyncio.new_event_loop()
        try:
            result = loop.run_until_complete(
                execute_in_sandbox(
                    code=self.code, namespace=namespace,
                    import_statements=import_statements,
                    function_definitions=function_definitions,
                    timeout=timeout, user_id=user_id,
                    session_id=session_id, workspace_path=workspace_path,
                )
            )
        finally:
            loop.close()

        self.state = result.state
        namespace.update(result.namespace)
```

The `asyncio.to_thread` call is the key boundary: it moves the blocking work off the main event loop's thread, so the server remains responsive to other requests. Inside the worker thread, `asyncio.new_event_loop()` creates a private loop that drives the async subprocess communication. This pattern allows multiple agents or sessions to execute cells concurrently without blocking each other.

### Sessions, persistence, and multi-user concerns

Unlike a local shell, an agent REPL usually operates in a multi-user environment. Each notebook is scoped to a `(user_id, session_id)` pair and persisted to a well-known path on disk (`WORKSPACE_DIR / user_id / session_id / mcp_repl / cells.json`). The notebook saves its state -- all cells with their code, outputs, and metadata -- after every operation (add, execute, delete, clear). This ensures that work is not lost and that sessions can be resumed after failures.

Persistence also enables secondary capabilities. The notebook can be exported to Jupyter's `.ipynb` format, making it possible to continue work in a standard notebook interface or share results with collaborators who do not use the agent platform.

### Best practices distilled

Several best practices consistently emerge when implementing REPLs for agents.

Prefer process-level isolation over threads for safety and control, and add a sandbox layer (bubblewrap, containers, or similar) beyond simple subprocess isolation. Use pickle-based IPC through the filesystem for subprocess communication, serializing only data -- not execution artifacts -- and replaying imports and functions explicitly. When objects cannot persist across cells, provide actionable feedback so the agent or user knows how to recover.

Treat outputs as structured, typed objects with separate storage for binary data, and capture the last expression's value to match the interactive notebook convention. Make execution asynchronous at the API level via thread offloading so the host process remains responsive.

Persist state frequently to support recovery and reproducibility. Impose explicit limits on execution time and resource usage. Consider data-driven security policies such as automatic network isolation for sensitive sessions.

Together, these patterns allow agents to reason *through execution* without compromising system stability.

