# MCP REPL Design Document

## Project Purpose

MCP REPL is a Jupyter-like notebook implementation exposed as an MCP (Model Context Protocol) server, allowing language models to execute Python code in a cell-based environment. The system prioritizes process-level isolation, rich output support, and multi-user concurrency in a server environment.

## Core Design Principles

1. **Simplicity over abstraction**: Direct two-tier model (Notebook and Cell) without unnecessary abstraction layers
2. **Process-level isolation**: Each cell execution runs in a separate Python process for security and stability
3. **Persistent state illusion**: Despite process isolation, maintains the appearance of continuous execution environment through namespace serialization
4. **Multi-user support**: User and session-based isolation allows concurrent notebook sessions
5. **Rich output capture**: Support for text, errors, matplotlib figures, HTML, and dataframes
6. **Async-first API**: Non-blocking execution using asyncio for server scalability

## Architecture Overview

### Three-Layer Architecture

```
┌─────────────────────────────────────────┐
│         MCP Server Layer                │
│  (FastMCP + aixtools integration)       │
│  - Tools: add_cell, execute_cell, etc.  │
│  - Resources: cell data, images, ipynb  │
└─────────────────────────────────────────┘
                  ↓
┌─────────────────────────────────────────┐
│         Notebook Layer                  │
│  - Cell collection management           │
│  - Shared namespace dictionary          │
│  - Import/function tracking             │
│  - Persistence to disk                  │
└─────────────────────────────────────────┘
                  ↓
┌─────────────────────────────────────────┐
│           Cell Layer                    │
│  - Code execution in subprocess         │
│  - Output capture (stdout, stderr, etc) │
│  - State management (idle/running/done) │
│  - Timeout handling                     │
└─────────────────────────────────────────┘
```

### Component Models

**Notebook Model**: Container for cells with shared execution context
```
Notebook:
  - user_id: str
  - session_id: str
  - cells: list[Cell]
  - namespace: dict[str, Any]
  - import_statements: list[str]
  - function_definitions: list[str]
  - execution_count: int
```

**Cell Model**: Individual executable unit
```
Cell:
  - id: str (UUID)
  - cell_number: int
  - code: str
  - state: CellState (IDLE | RUNNING | COMPLETED | ERROR | TIMEOUT)
  - outputs: list[CellOutput]
  - execution_count: int | None
  - execution_time: float | None
```

## Key Design Patterns

### 1. Process Isolation Pattern

Each cell executes in a fresh Python process to ensure security and prevent interference between executions.

**Conceptual Flow**:
```
Cell.execute(namespace, timeout):
    1. Set state to RUNNING
    2. Create pipe for inter-process communication
    3. Clean namespace (remove module objects, keep data)
    4. Spawn subprocess with:
       - Cell code
       - Clean namespace
       - Import statements from previous cells
       - Function definitions from previous cells
    5. Wait for subprocess completion (with timeout)
    6. Receive results through pipe:
       - Updated namespace
       - Captured outputs
       - Execution state
    7. Merge updated namespace back to notebook
    8. Terminate subprocess
```

**Benefits**:
- Strong isolation between cell executions
- Protection from infinite loops via timeout
- Server stability (cell crash doesn't crash server)
- Future extensibility to Docker containers

### 2. Namespace Serialization Pattern

Despite process isolation, variables persist across cells through serialization.

**Conceptual Implementation**:
```
Before execution:
    clean_namespace = filter_out_modules(notebook.namespace)
    serialized_namespace = pickle.dumps(clean_namespace)

In subprocess:
    namespace = pickle.loads(serialized_namespace)
    re_execute(all_import_statements)
    re_execute(all_function_definitions)
    exec(cell_code, namespace)
    updated_vars = capture_new_or_modified_variables(namespace)
    return pickle.dumps(updated_vars)

After execution:
    updated_namespace = pickle.loads(result)
    notebook.namespace.update(updated_namespace)
```

**Key Points**:
- Only pickleable objects can persist across cells
- Module objects are tracked separately as import statements
- Functions are tracked as source code strings and re-executed
- Each cell sees all variables from previous cells

### 3. Import and Function Tracking Pattern

Imports and function definitions are tracked separately to maintain availability across process boundaries.

**Conceptual Tracking**:
```
On cell execution:
    1. Parse cell code AST
    2. Extract import statements:
       - "import numpy as np"
       - "from pandas import DataFrame"
    3. Extract function definitions (full source):
       - "def my_function(x): return x * 2"
    4. Store in notebook's import_statements and function_definitions lists
    5. On next cell execution:
       - Re-execute all previous imports
       - Re-execute all previous function definitions
       - Then execute new cell code
```

**Why This Works**:
- Import statements are idempotent
- Function redefinition is acceptable
- Maintains library availability across processes
- Preserves user-defined functions

### 4. Three-Class Image Architecture

Separates image storage from image reference for efficient API responses.

**Class Hierarchy**:
```
ImageBase (abstract):
  - format: str
  - width: int | None
  - height: int | None
  - source: str | None
  - metadata: dict
  - Abstract: serialize(), __str__()

Image (concrete):
  - data: bytes
  - Methods:
    - get_data_base64() -> str
    - save_to_file(path)
    - show()
    - from_matplotlib_figure(fig) -> Image

ImageReference (concrete):
  - resource_uri: str
  - Methods:
    - from_image(image, uri) -> ImageReference
```

**Usage Pattern**:
```
Internal storage:
    image = Image.from_matplotlib_figure(fig)
    cell.outputs.append(Output(type=IMAGE, content=image))

API response:
    for output in cell.outputs:
        if isinstance(output.content, Image):
            uri = f"notebook://cell/{cell.number}/image/{index}"
            output.content = ImageReference.from_image(output.content, uri)
    return cell  # Now serializable without binary data

Client retrieval:
    # Client receives ImageReference with URI
    # Client calls get_cell_image(cell_id, image_index)
    # Server returns binary PNG data
```

**Benefits**:
- Avoids sending binary data in every response
- Preserves all image metadata
- On-demand image fetching reduces bandwidth
- Clean separation of concerns

### 5. Matplotlib Capture Pattern

Captures matplotlib figures without requiring display or GUI.

**Conceptual Implementation**:
```
Before execution in subprocess:
    import matplotlib
    matplotlib.use('agg')  # Non-interactive backend

    # Replace plt.show() with no-op
    import matplotlib.pyplot as plt
    plt.show = lambda: None

After code execution:
    figures = plt.get_fignums()
    for fig_num in figures:
        fig = plt.figure(fig_num)
        image = Image.from_matplotlib_figure(fig)
        outputs.append(Output(type=IMAGE, content=image))
        plt.close(fig)
```

**Key Techniques**:
- Use 'agg' backend (non-interactive)
- Replace plt.show() with no-op
- Capture all active figures after execution
- Save figures as PNG in memory (BytesIO)
- Clean up figures after capture

### 6. Session and Persistence Pattern

Multi-user support through hierarchical session management.

**Directory Structure**:
```
workspace/
  mcp_repl/
    {user_id}/
      {session_id}/
        cells.json
        outputs/
          cell_{id}_output_0.png
          cell_{id}_output_1.png
```

**Session Management**:
```
Notebook identification:
    user_id = get_system_username()  # or from authentication
    session_id = generate_uuid()     # per server start
    notebook = Notebook.load(user_id, session_id)

Automatic persistence:
    notebook.add_cell(code)
    notebook.save()  # Automatic

    notebook.execute_cell(id)
    notebook.save()  # Automatic

    notebook.delete_cell(id)
    notebook.save()  # Automatic

In-memory caching:
    cache_key = (user_id, session_id)
    if cache_key in notebook_cache:
        return notebook_cache[cache_key]
    else:
        notebook = Notebook.load(user_id, session_id)
        notebook_cache[cache_key] = notebook
        return notebook
```

### 7. Async Execution Pattern

Non-blocking execution for server scalability.

**Pattern**:
```
async def add_cell(code: str, execute: bool = True):
    cell = Cell(code=code)
    notebook.cells.append(cell)

    if execute:
        await cell.execute(notebook.namespace)

    notebook.save()
    return cell

Cell.execute():
    async def execute(namespace, timeout):
        # Offload blocking subprocess work to thread
        await asyncio.to_thread(
            self._execute_sync,
            namespace,
            timeout
        )

    def _execute_sync(namespace, timeout):
        # Create subprocess
        process = multiprocessing.Process(...)
        process.start()

        # Wait with timeout (blocking in thread, not event loop)
        if pipe.poll(timeout):
            result = pipe.recv()
            # Update namespace
        else:
            # Handle timeout
```

**Benefits**:
- Non-blocking API for MCP server
- Multiple concurrent cell executions possible
- Event loop remains responsive during execution
- Clean separation of async and sync code

### 8. MCP Integration Pattern

Expose notebook functionality through MCP tools and resources.

**Tool Pattern**:
```
@mcp.tool()
async def add_cell(
    code: str,
    execute: bool = True,
    cell_number: int | None = None,
    timeout: int = DEFAULT_CELL_TIMEOUT
) -> CellInfo:
    logger.debug(f"Tool: add_cell")

    notebook = get_current_notebook()
    cell = await notebook.add_cell(code, execute, cell_number, timeout)

    # Convert Image to ImageReference for response
    cell_info = CellInfo.from_cell(cell)
    return cell_info
```

**Resource Pattern**:
```
@mcp.resource("notebook://cell/{cell_id_or_number}")
async def get_cell_resource(cell_id_or_number: str) -> str:
    notebook = get_current_notebook()
    cell = notebook.get_cell(cell_id_or_number)
    return json.dumps(CellInfo.from_cell(cell))

@mcp.resource("notebook://cell/{cell_id}/image/{index}")
async def get_cell_image(cell_id: str, index: int) -> bytes:
    notebook = get_current_notebook()
    cell = notebook.get_cell(cell_id)
    image = cell.outputs[index].content
    return image.data  # Binary PNG data
```

**Available Tools**:
- create_notebook() - Initialize session
- add_cell(code, execute, number, timeout) - Add and execute code
- execute_cell(cell_id_or_number, timeout) - Re-execute cell
- delete_cell(cell_id_or_number) - Remove cell
- get_cell(cell_id_or_number) - Retrieve cell info
- list_cells() - Get all cells overview
- clear_notebook() - Reset notebook
- export_notebook_as_ipynb() - Export to Jupyter format
- get_cell_image(cell_id_or_number, index) - Fetch image

**Available Resources**:
- notebook://cell/{id_or_number} - Cell details
- notebook://cell/{id_or_number}/image/{index} - Cell image (binary)
- notebook://notebooks - List all notebooks
- notebook://current/cells - List current notebook cells
- notebook://current/info - Current notebook metadata
- notebook://current/ipynb - Notebook in Jupyter format

## Key Technical Decisions

### Why Multiprocessing Instead of Threading?

- **Isolation**: Each process has its own memory space
- **Security**: Code execution can't affect server directly
- **Timeout**: Can forcefully terminate runaway processes
- **Future-proof**: Similar pattern to Docker-based isolation

### Why Track Imports and Functions Separately?

- **Module objects aren't pickleable**: Can't serialize imports
- **Idempotent re-execution**: Re-importing is safe
- **Function preservation**: User functions need to persist

### Why Three Image Classes?

- **Separation of concerns**: Storage vs. reference
- **API efficiency**: Don't send binary data unless needed
- **Metadata preservation**: All info available without data
- **Bandwidth optimization**: On-demand image fetching

### Why Automatic Save After Operations?

- **Data safety**: No work lost on crash
- **Simplicity**: No need to remember to save
- **Consistency**: Disk always reflects current state
- **Recovery**: Can resume after server restart

### Why Cell Numbering (0-based)?

- **Jupyter compatibility**: Matches Jupyter behavior
- **API clarity**: "Execute cell 3" is clear
- **Export compatibility**: Jupyter notebooks use cell numbers
- **User familiarity**: Developers expect 0-based indexing

## Configuration and Limits

**Default Values**:
```
DEFAULT_CELL_TIMEOUT = 30  # seconds
MAX_CELLS = 100            # per notebook
SERVICE_NAME = "mcp_repl"  # for directory naming
```

**Why These Limits**:
- Timeout prevents infinite loops from blocking server
- Cell limit prevents memory exhaustion
- Configurable for different deployment scenarios

## Output Types Supported

```
OutputType:
  - STREAM: stdout/stderr text
  - EXECUTE_RESULT: last expression value
  - ERROR: exception messages and tracebacks
  - IMAGE: matplotlib figures, PNG/JPG images
  - HTML: rich HTML content
  - DATAFRAME: pandas DataFrame outputs
```

## State Machine

**Cell States**:
```
IDLE → RUNNING → SUCCESS
             ↓
        TIMEOUT | ERROR
```

**State Transitions**:
- IDLE: Cell created, not executed
- RUNNING: Currently executing in subprocess
- SUCCESS: Execution completed without error
- ERROR: Python exception occurred
- TIMEOUT: Execution exceeded timeout limit

## Error Handling Patterns

**Subprocess Errors**:
```
try:
    exec(code, namespace)
except Exception as e:
    return {
        'state': ERROR,
        'outputs': [{
            'type': ERROR,
            'content': traceback.format_exc()
        }]
    }
```

**Timeout Handling**:
```
if pipe.poll(timeout):
    result = pipe.recv()
else:
    state = TIMEOUT
    outputs = [Error(f"Timed out after {timeout}s")]
    process.terminate()
```

**Serialization Errors**:
```
# Only pickleable objects persist
clean_namespace = {
    k: v for k, v in namespace.items()
    if not isinstance(v, types.ModuleType)
}
```

## Future Extensions

**Docker-based Isolation** (currently multiprocessing):
```
async def execute_in_docker(code, namespace, timeout):
    container = docker.create_container(
        image='python-notebook',
        volumes=[f'{user_dir}:/workspace'],
        mem_limit='512m',
        cpu_quota=50000
    )

    container.start()
    result = container.exec(code, timeout=timeout)
    container.stop()
    container.remove()

    return result
```

**Benefits of Docker Extension**:
- Stronger isolation (OS-level)
- Resource limits (CPU, memory, network)
- Custom package environments per notebook
- Network restrictions

## Testing Strategy

**Unit Tests**:
- Cell execution with various code types
- Namespace serialization and persistence
- Import and function tracking
- Image capture and serialization
- Timeout handling
- Error capture

**Integration Tests**:
- Multi-cell notebooks with variable persistence
- Matplotlib figure generation and capture
- MCP server tool invocations
- Resource fetching
- Jupyter export format

**Key Test Patterns**:
```
async def test_variable_persistence():
    notebook = Notebook(user_id="test", session_id="test")

    cell1 = await notebook.add_cell("x = 42")
    assert notebook.namespace['x'] == 42

    cell2 = await notebook.add_cell("y = x * 2")
    assert notebook.namespace['y'] == 84

async def test_import_tracking():
    notebook = Notebook(user_id="test", session_id="test")

    await notebook.add_cell("import numpy as np")
    assert "import numpy as np" in notebook.import_statements

    cell2 = await notebook.add_cell("x = np.array([1, 2, 3])")
    assert cell2.state == CellState.SUCCESS

async def test_matplotlib_capture():
    notebook = Notebook(user_id="test", session_id="test")

    code = """
    import matplotlib.pyplot as plt
    plt.plot([1, 2, 3])
    plt.show()
    """

    cell = await notebook.add_cell(code)
    images = [o for o in cell.outputs if o.output_type == OutputType.IMAGE]
    assert len(images) == 1
    assert isinstance(images[0].content, Image)
```

## Summary

MCP REPL demonstrates several elegant design patterns for building a secure, scalable code execution environment:

1. **Process isolation** provides security without complexity
2. **Namespace serialization** creates the illusion of continuity despite isolation
3. **Import/function tracking** solves the module persistence problem
4. **Three-class image architecture** optimizes API efficiency
5. **Async-first design** enables server scalability
6. **Automatic persistence** ensures data safety
7. **MCP integration** exposes clean programmatic interface

The architecture is simple, extensible, and production-ready for multi-user server environments while maintaining the familiar Jupyter notebook experience for end users.
