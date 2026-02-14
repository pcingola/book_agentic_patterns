# Context & Memory

Context management controls what enters the LLM's context window and how it evolves over time. The library provides three mechanisms: prompt templates for composing system prompts from reusable fragments, the `@context_result()` decorator for bounding tool output size (documented in [Tools](tools.md#context-result-decorator)), and `HistoryCompactor` for summarizing conversation history when it grows too large.


## Prompt Templates

Prompt templates live as markdown files in the `prompts/` directory. The `load_prompt()` function loads a template, resolves `{% include %}` directives, and substitutes `{variable}` placeholders.

```python
from agentic_patterns.core.prompt import load_prompt
from pathlib import Path

prompt = load_prompt(
    Path("prompts/analysis.md"),
    database="bookstore",
    max_rows=100,
)
```

### Include directives

Templates can include other templates using `{% include 'path.md' %}`. Paths are resolved relative to the `PROMPTS_DIR` directory (configured in `core/config/config.py`).

```markdown
# Analysis Agent

You are a data analysis agent.

{% include 'shared/workspace.md' %}
{% include 'shared/file_tools.md' %}

Analyze the {database} database. Limit results to {max_rows} rows.
```

This allows reusable prompt blocks (workspace instructions, tool descriptions, safety policies) to be shared across agents without duplication.

### Variable substitution

Variables use Python's `str.format()` syntax: `{variable_name}`. `load_prompt()` validates that all template variables are provided and that no extra variables are passed. Missing or unused variables raise `ValueError`.

### Convenience functions

```python
from agentic_patterns.core.prompt import get_system_prompt, get_prompt, get_instructions

# Loads prompts/system_prompt.md
system = get_system_prompt(agent_name="sql")

# Loads prompts/{name}.md
p = get_prompt("analysis", database="bookstore")

# Loads prompts/instructions.md
instr = get_instructions()
```

### Prompt layers

PydanticAI agents accept both `system_prompt` and `instructions`. These serve different purposes:

`system_prompt` establishes persistent identity and invariant rules. It is included in the stored message history and persists across multi-turn conversations.

`instructions` provide per-run task guidance. They are applied fresh on each agent call but are not replayed from prior turns in message history.

```python
from agentic_patterns.core.agents import get_agent

agent = get_agent(
    system_prompt="You are an expert Python developer.",
    instructions="When explaining code, always include a brief example.",
)
```

Use system prompts for invariants (role, safety policies, output constraints). Use instructions for task-specific procedure that may change between runs.


## Context Processing Pipeline

The context module (`agentic_patterns.core.context`) handles reading, type detection, and truncation of files that agents encounter. It ensures that large files are processed into bounded representations that fit within the LLM's context window without losing structural information.

### FileType

`FileType` is a `(str, Enum)` that classifies files for processor dispatch:

ARCHIVE, AUDIO, BINARY, CODE, CSV, DOCX, IMAGE, JSON, MARKDOWN, PDF, PPTX, SPREADSHEET (xlsx), TEXT, XML, YAML.

Detection uses file extension first (e.g., `.py` maps to CODE, `.csv` to CSV), falling back to MIME type for ambiguous cases. Unknown types resolve to BINARY.

### ContextConfig

`ContextConfig` is a Pydantic model loaded from `config.yaml` that controls all truncation thresholds. Key groups:

**File processing** -- `max_tokens_per_file` (5000), `max_total_output` (50000), `max_lines` (200), `max_line_length` (1000).

**Structured data** -- `max_nesting_depth` (5), `max_array_items` (50), `max_object_keys` (50), `max_string_value_length` (500).

**Tabular data** -- `max_columns` (50), `max_cell_length` (500), `rows_head` (20), `rows_tail` (10).

**Named truncation configs** -- `TruncationConfig` presets (default, sql_query, log_search) with their own thresholds for `rows_head`, `rows_tail`, `json_array_head`, `max_preview_tokens`, etc. The `@context_result()` decorator selects a named config via its first argument.

### Reading files

`read_file()` is the main entry point. It detects the file type, dispatches to the appropriate processor, and applies a final token limit:

```python
from agentic_patterns.core.context.reader import read_file
from agentic_patterns.core.context.config import load_context_config

config = load_context_config()
result = read_file(Path("data/large_report.json"), config=config)

result.content       # Truncated content string
result.file_type     # FileType.JSON
result.truncation_info  # TruncationInfo with stats
result.metadata      # FileMetadata (size, modified time, MIME type)
```

`read_file_as_string()` is a convenience wrapper that returns just the content string or an error message.

### Processors

Each file type has a dedicated processor in `agentic_patterns.core.context.processors`:

**text/code** -- Encoding detection (UTF-8, Latin-1 fallback), line range selection, long line truncation.

**csv** -- Delimiter auto-detection, head+tail row sampling for large files, column and cell truncation.

**json** -- Recursive structure truncation: limits nesting depth, array items, object keys, and string values. Preserves structure shape while bounding size.

**yaml/xml** -- Parsed into structures, then truncated using the same recursive logic as JSON.

**document** (PDF, DOCX, PPTX) -- Converted to markdown via `markitdown`, with file-based caching. Truncated by lines.

**spreadsheet** (XLSX) -- Multi-sheet processing with head+tail row sampling per sheet, column and cell truncation.

**image** -- Resized by file size or dimensions via Pillow. Returns `BinaryContent` for multimodal model attachment.

### Data models

`FileExtractionResult` is the standard return type from `read_file()`:

| Field | Type | Description |
|---|---|---|
| `content` | `str \| BinaryContent \| None` | Processed content |
| `success` | `bool` | Whether processing succeeded |
| `file_type` | `FileType \| None` | Detected file type |
| `truncation_info` | `TruncationInfo \| None` | What was truncated and by how much |
| `metadata` | `FileMetadata \| None` | File size, modified time, MIME type |

`TruncationInfo` tracks what was cut: lines shown, rows shown, columns shown, cells truncated, tokens shown vs total tokens, and whether the total output limit was reached.


## History Compaction

Long conversations accumulate message history that eventually exceeds the context window or degrades model performance. `HistoryCompactor` monitors token usage and, when a threshold is exceeded, uses an LLM to summarize older messages into a compact narrative.

### Basic usage

```python
from agentic_patterns.core.context.history import HistoryCompactor, CompactionConfig
from agentic_patterns.core.agents import get_agent

compactor = HistoryCompactor(config=CompactionConfig(max_tokens=120_000, target_tokens=40_000))
agent = get_agent(system_prompt="You are a helpful assistant.", history_compactor=compactor)
```

The `history_compactor` parameter wires the compactor into PydanticAI's history processor pipeline. Compaction happens automatically before each agent call when the history exceeds `max_tokens`.

### Configuration

`CompactionConfig` has two parameters:

| Parameter | Default | Description |
|---|---|---|
| `max_tokens` | 120,000 | Token threshold that triggers compaction |
| `target_tokens` | 40,000 | Target token count after summarization |

`target_tokens` must be less than `max_tokens`. If neither is provided, defaults are loaded from `config.yaml`.

### How compaction works

When the accumulated message history exceeds `max_tokens`:

1. The compactor finds a safe boundary that preserves tool call/return pairing (see below).
2. Messages before the boundary are serialized into a conversation transcript.
3. An LLM summarizes the transcript, preserving key information, decisions, and context needed to continue.
4. The summary replaces the old messages as a single continuation message.
5. Recent messages (after the boundary) are preserved unchanged.

The model sees the summary followed by the current prompt. It does not know compaction occurred.

### Tool call/return pairing

The OpenAI API requires that tool return messages always follow their corresponding tool call messages. The compactor respects this constraint by finding a "safe boundary" that never orphans tool returns. If no safe boundary exists (e.g., the only recent messages are a tool call/return pair), compaction is deferred to the next turn.

### Fallback behavior

When LLM summarization fails or the conversation text exceeds the summarizer's own limits, the compactor falls back to truncation. It preserves the head and tail of the conversation with a marker showing how many tokens were removed. This is less effective than summarization but ensures the system degrades gracefully.

### Manual usage

You can also use the compactor directly without PydanticAI's history processor:

```python
compactor = HistoryCompactor(config=CompactionConfig(max_tokens=500, target_tokens=200))

# Check if compaction is needed
if compactor.needs_compaction(messages):
    messages = await compactor.compact(messages)

# Count tokens in a message list
tokens = compactor.count_tokens(messages)
```

### Compaction callback

Pass `on_compaction` to receive notifications when compaction occurs:

```python
async def log_compaction(result: CompactionResult):
    print(f"Compacted {result.original_messages} -> {result.compacted_messages} messages")
    print(f"Tokens: {result.original_tokens} -> {result.compacted_tokens}")

compactor = HistoryCompactor(
    config=CompactionConfig(max_tokens=500, target_tokens=200),
    on_compaction=log_compaction,
)
```


## API Reference

### `agentic_patterns.core.prompt`

| Name | Kind | Description |
|---|---|---|
| `load_prompt(prompt_path, **kwargs)` | Function | Load template, resolve includes, substitute variables |
| `get_system_prompt(**kwargs)` | Function | Load `prompts/system_prompt.md` |
| `get_prompt(prompt_name, **kwargs)` | Function | Load `prompts/{prompt_name}.md` |
| `get_instructions(**kwargs)` | Function | Load `prompts/instructions.md` |

### `agentic_patterns.core.context`

| Name | Kind | Description |
|---|---|---|
| `FileType` | Enum | File type classification (CODE, CSV, JSON, etc.) |
| `ContextConfig` | Pydantic model | Truncation thresholds for all content types |
| `TruncationConfig` | Pydantic model | Named truncation preset (threshold, row/array limits) |
| `FileExtractionResult` | Dataclass | Content + metadata + truncation info from file processing |
| `TruncationInfo` | Dataclass | What was truncated and by how much |
| `FileMetadata` | Dataclass | File size, modified time, MIME type, encoding |
| `read_file(path, config, ...)` | Function | Read and process a file with type detection and truncation |
| `read_file_as_string(path, config, ...)` | Function | Convenience wrapper returning content string |
| `load_context_config()` | Function | Load ContextConfig from config.yaml (cached) |
| `get_truncation_config(name)` | Function | Get a named TruncationConfig preset |

### `agentic_patterns.core.context.history`

| Name | Kind | Description |
|---|---|---|
| `CompactionConfig` | Pydantic model | `max_tokens` and `target_tokens` thresholds |
| `CompactionResult` | Pydantic model | Compaction statistics (message/token counts, summary text) |
| `HistoryCompactor` | Class | Main compactor; `compact()`, `needs_compaction()`, `count_tokens()`, `create_history_processor()` |


## Examples

See the notebooks in `agentic_patterns/examples/context_memory/`:

- `example_prompts.ipynb` -- prompt layers, system prompts vs instructions, message history interaction
- `example_context_result.ipynb` -- `@context_result()` decorator with CSV, JSON, and log data
- `example_history_compaction.ipynb` -- `HistoryCompactor` with observable compaction across multi-turn conversations
