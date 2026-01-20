# Context Management Implementation Plan

This document outlines the architecture and implementation plan for context management in `agentic_patterns/core`.

## Goals

1. Manage agent context window limits through file processing, history compaction, and workspace storage
2. Provide easy-to-use integration mechanisms (decorators, factory methods) instead of requiring explicit calls
3. Maintain compatibility with PydanticAI agents
4. Follow the library's design principles: simplicity, type hints, Pydantic models, async-first

## Architecture Overview

```
agentic_patterns/core/
├── context/
│   ├── models.py                # Data models (FileType, TruncationInfo, FileExtractionResult)
│   ├── reader.py                # Main file reading interface with type detection
│   ├── history.py               # History compaction for long conversations
│   ├── decorators.py            # @context_result decorator
│   └── processors/
│       ├── common.py            # Shared utilities
│       ├── text.py              # Text/code/markdown
│       ├── json_processor.py    # JSON/JSONL
│       ├── yaml_processor.py    # YAML
│       ├── xml_processor.py     # XML
│       ├── csv_processor.py     # CSV/TSV
│       ├── spreadsheet.py       # XLSX/XLS/ODS
│       ├── document.py          # PDF/DOCX/PPTX
│       └── image.py             # Image resizing
├── workspace.py                 # EXISTING: Enhanced with result storage helper
├── agents/agents.py             # EXISTING: Enhanced with history_processor support
└── config.yaml                  # Configuration including context/truncation settings
```

## Configuration

All context management settings in `config.yaml`:

```yaml
context:
  # File processing limits
  max_tokens_per_file: 5000
  max_total_output: 50000
  max_lines: 200
  max_line_length: 1000

  # Structured data limits
  max_nesting_depth: 5
  max_array_items: 50
  max_object_keys: 50

  # Tabular data limits
  max_columns: 50
  rows_head: 20
  rows_tail: 10
  max_cell_length: 500

  # Image limits
  max_image_size_bytes: 2097152  # 2MB

  # History compaction
  history_max_tokens: 120000
  history_target_tokens: 40000
  summarizer_max_tokens: 180000

  # Truncation configs for @context_result decorator
  truncation:
    default:
      threshold: 5000
      max_preview_tokens: 500

    sql_query:
      threshold: 2000
      max_preview_tokens: 1000
      rows_head: 30
      rows_tail: 10

    log_search:
      threshold: 10000
      max_preview_tokens: 300
      lines_head: 50
      lines_tail: 20
```

## Component Design

### 1. Data Models (`context/models.py`)

```python
class FileType(str, Enum):
    CODE = "code"
    TEXT = "text"
    MARKDOWN = "markdown"
    JSON = "json"
    YAML = "yaml"
    XML = "xml"
    CSV = "csv"
    SPREADSHEET = "xlsx"
    PDF = "pdf"
    DOCX = "docx"
    PPTX = "pptx"
    IMAGE = "image"
    AUDIO = "audio"
    ARCHIVE = "archive"
    BINARY = "binary"

@dataclass
class TruncationInfo:
    lines_shown: str | None = None
    columns_shown: str | None = None
    rows_shown: str | None = None
    cells_truncated: int = 0
    tokens_shown: int | None = None
    total_tokens: int | None = None
    total_output_limit_reached: bool = False

@dataclass
class FileMetadata:
    size_bytes: int
    modified_time: str | None = None
    mime_type: str | None = None
    encoding: str | None = None

@dataclass
class BinaryContent:
    data: bytes
    mime_type: str

@dataclass
class FileExtractionResult:
    content: str | BinaryContent | None
    success: bool
    error_message: str | None = None
    file_type: FileType | None = None
    truncation_info: TruncationInfo | None = None
    metadata: FileMetadata | None = None
```

### 2. File Reader (`context/reader.py`)

Main interface for reading files with automatic truncation.

```python
def read_file(file_path: Path | str, max_tokens: int | None = None, **kwargs) -> FileExtractionResult:
    """Read and process file with automatic type detection and truncation.

    Uses max_tokens_per_file from config.yaml if max_tokens not specified.
    """
    ...

def read_file_as_string(file_path: Path | str, max_tokens: int | None = None, **kwargs) -> str:
    """Convenience wrapper that returns content string or error message."""
    result = read_file(file_path, max_tokens, **kwargs)
    if result.success and isinstance(result.content, str):
        return result.content
    return f"[Error reading {file_path}: {result.error_message}]"
```

Type detection by extension first, then MIME type. Routes to appropriate processor. Final token-based truncation.

### 3. History Compaction (`context/history.py`)

Manages conversation history when approaching context window limits.

```python
class CompactionConfig(BaseModel):
    max_tokens: int  # from config.yaml context.history_max_tokens
    target_tokens: int  # from config.yaml context.history_target_tokens

class CompactionResult(BaseModel):
    original_messages: int
    compacted_messages: int
    original_tokens: int
    compacted_tokens: int
    summary: str

class HistoryCompactor:
    def __init__(
        self,
        config: CompactionConfig | None = None,
        model: Model | None = None,
        on_compaction: Callable[[CompactionResult], Awaitable[None]] | None = None,
    ):
        """Config loaded from config.yaml if not provided."""
        ...

    def count_tokens(self, messages: list[ModelMessage]) -> int:
        """Count tokens using tiktoken."""
        ...

    def needs_compaction(self, messages: list[ModelMessage]) -> bool:
        """Check if history exceeds max_tokens threshold."""
        ...

    async def compact(self, messages: list[ModelMessage]) -> list[ModelMessage]:
        """Summarize messages if threshold exceeded."""
        ...

    def create_history_processor(self) -> Callable[[list[ModelMessage]], Awaitable[list[ModelMessage]]]:
        """Create PydanticAI-compatible history_processor callable."""
        ...
```

### 4. Context Result Decorator (`context/decorators.py`)

Single decorator for tool results that exceed context limits.

```python
def context_result(config_name: str = "default"):
    """Decorator for tools that may return large results.

    If result exceeds threshold:
    1. Auto-detect content type
    2. Save full content to workspace
    3. Truncate according to content type
    4. Return path + truncated preview

    Config loaded from config.yaml context.truncation.<config_name>
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, ctx=None, **kwargs):
            config = get_truncation_config(config_name)
            result = await func(*args, ctx=ctx, **kwargs) if asyncio.iscoroutinefunction(func) else func(*args, ctx=ctx, **kwargs)

            if not isinstance(result, str) or len(result) <= config.threshold:
                return result

            content_type = detect_content_type(result)
            path = save_to_workspace(result, content_type, ctx)
            preview = truncate_by_type(result, content_type, config)

            return f"Results saved to {path} ({len(result)} chars)\n\nPreview:\n{preview}"
        return wrapper
    return decorator
```

Usage:

```python
@context_result()  # Uses 'default' config
async def some_tool() -> str:
    ...

@context_result("sql_query")  # Uses 'sql_query' config
async def run_sql_query(sql: str, ctx=None) -> str:
    ...
```

### 5. Processors (`context/processors/`)

Format-specific processors. Common signature:

```python
def process_<type>(
    file_path: Path,
    config: ContextConfig,  # Loaded from config.yaml
    tokenizer: Callable[[str], int] | None = None,
    **type_specific_args
) -> FileExtractionResult:
    ...
```

Processors to port from aixtools:
- `text.py`: Text, code, markdown (line-based truncation)
- `json_processor.py`: JSON, JSONL (recursive structure truncation)
- `yaml_processor.py`: YAML (recursive structure truncation)
- `xml_processor.py`: XML (depth/element truncation)
- `csv_processor.py`: CSV, TSV (head/tail row sampling)
- `spreadsheet.py`: XLSX, XLS, ODS (multi-sheet, row/column truncation)
- `document.py`: PDF, DOCX, PPTX (markdown conversion + line truncation)
- `image.py`: Image resizing for attachment limits
- `common.py`: Shared utilities (truncate_string, create_metadata, detect_encoding)

### 6. Integration with Existing Modules

**agents/agents.py** - Add history_compactor parameter:

```python
def get_agent(
    model=None,
    *,
    config_name: str = "default",
    history_compactor: HistoryCompactor | None = None,
    **kwargs
) -> Agent:
    ...
    if history_compactor:
        kwargs['history_processor'] = history_compactor.create_history_processor()
    ...
```

**workspace.py** - Add result storage helper:

```python
def store_result(content: str | bytes, content_type: FileType, ctx: Any = None) -> str:
    """Store content in workspace and return sandbox path.

    Determines file extension from content_type.
    """
    ext = get_extension_for_type(content_type)
    filename = f"result_{uuid4().hex[:8]}{ext}"
    path = f"/workspace/results/{filename}"
    write_to_workspace(path, content, ctx)
    return path
```

## Implementation Phases

### Phase 1: Core Models and Configuration

Files:
- `context/__init__.py`
- `context/models.py`

Add to `config.yaml`: context section with all settings.

### Phase 2: Common Utilities and Text Processor

Files:
- `context/processors/__init__.py`
- `context/processors/common.py`
- `context/processors/text.py`

Port from aixtools, adapt config loading.

### Phase 3: Structured Data Processors

Files:
- `context/processors/json_processor.py`
- `context/processors/yaml_processor.py`
- `context/processors/xml_processor.py`

### Phase 4: Tabular Data Processors

Files:
- `context/processors/csv_processor.py`
- `context/processors/spreadsheet.py`

### Phase 5: Document and Media Processors

Files:
- `context/processors/document.py`
- `context/processors/image.py`

### Phase 6: Main Reader Interface

Files:
- `context/reader.py`

### Phase 7: History Compaction

Files:
- `context/history.py`

### Phase 8: Decorator and Integration

Files:
- `context/decorators.py`

Modify:
- `agents/agents.py`
- `workspace.py`

### Phase 9: Tests

Files:
- `tests/test_context_reader.py`
- `tests/test_context_history.py`
- `tests/test_context_decorators.py`
- `tests/data/` (test files)

## Dependencies

Required:
- `tiktoken` - Token counting

Optional:
- `markitdown` - PDF/DOCX to markdown
- `openpyxl` - Excel reading
- `pillow` - Image processing

## Migration from aixtools

Source -> Destination:
- `aixtools/agents/context/data_models.py` -> `context/models.py`
- `aixtools/agents/context/reader.py` -> `context/reader.py`
- `aixtools/agents/context/processors/*` -> `context/processors/*`
- `aixtools/agents/history_compactor.py` -> `context/history.py`

Changes:
- Import paths: `aixtools.*` -> `agentic_patterns.core.context.*`
- Logger: `aixtools.logging` -> `logging.getLogger`
- Config: Load from config.yaml instead of module constants
- Naming: `json.py` -> `json_processor.py` (avoid stdlib collision)
