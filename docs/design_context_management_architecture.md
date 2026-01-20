# Context Management - Requirements and Architecture

This document describes the context management features in aixtools. The system addresses the fundamental challenge of AI agents working with data that exceeds model context windows.

## Problem Statement

AI agents face context window limitations when processing large files, long conversations, or multiple attachments. Without management, agents either fail with token limit errors or lose critical information.

## Architecture Overview

The solution implements four complementary strategies:

1. **File Content Processing** - Transform files into agent-readable content with enforced size limits
2. **Image Size Reduction** - Resize images to fit attachment limits while preserving visual information
3. **History Compaction** - Summarize conversation history when approaching context limits
4. **Workspace Storage** - Store large results as files rather than including them in context

These strategies work together: large query results go to workspace storage, files are processed with truncation when read, images are resized for attachments, and history is compacted as conversations grow.

## File Content Processing

The reader system (`aixtools/agents/context/`) transforms various file formats into truncated, agent-readable content.

### File Type Detection

The system detects file types by extension first, then MIME type, supporting 55+ formats including code (Python, JavaScript, Java, Go, etc.), documents (PDF, DOCX, PPTX), data files (JSON, YAML, XML, CSV, XLSX), and media (PNG, JPEG, MP3).

### Processing Strategies by Format

**Text and Code** files are truncated by line count (default 200 lines) and line length (default 1000 characters). Encoding detection handles UTF-8 and latin-1 automatically.

**Tabular data** (CSV, TSV, XLSX) never loads the entire file. The processor reads header and counts total rows, then extracts head rows (default 20) and tail rows (default 10), providing a representative sample. Columns are limited (default 50) and cell values truncated (default 500 chars).

Example transformation:
```
Original: 100 columns, 5000 rows, some cells with 2000+ chars
Result: 50 columns, 30 rows (20 head + 10 tail), cells capped at 500 chars
Truncation info: "columns: 50 of 100, rows: 30 of 5000, 15 cells truncated"
```

**Structured data** (JSON, YAML, XML) is parsed and recursively truncated: nesting depth limited to 5 levels, arrays capped at 50 items, objects at 50 keys, and strings at 500 characters. Truncation markers indicate omitted content.

**Documents** (PDF, DOCX) are converted to markdown using markitdown, cached by file hash, then truncated as text.

**Images** are validated for supported types (PNG, JPEG, GIF, WEBP), resized if exceeding 2MB, and returned as binary content with metadata.

**Audio** extracts metadata (duration, sample rate, channels) and subsamples if exceeding size or duration limits.

### Token-Based Final Truncation

After format-specific processing, a final token limit (default 5000 per file) is enforced using tiktoken. This ensures the processed content fits within model constraints regardless of format-specific truncation.

### Key Configuration

| Parameter | Default | Purpose |
|-----------|---------|---------|
| MAX_TOKENS_PER_FILE | 5000 | Token limit per processed file |
| MAX_TOTAL_OUTPUT | 50000 | Character limit for output |
| MAX_LINES | 200 | Lines shown for text files |
| MAX_LINE_LENGTH | 1000 | Characters per line |
| MAX_COLUMNS | 50 | Columns for tabular data |
| DEFAULT_ROWS_HEAD | 20 | Head rows for tabular data |
| DEFAULT_ROWS_TAIL | 10 | Tail rows for tabular data |
| MAX_CELL_LENGTH | 500 | Cell value truncation |
| MAX_NESTING_DEPTH | 5 | JSON/YAML structure depth |
| MAX_ARRAY_ITEMS | 50 | Array elements shown |
| MAX_OBJECT_KEYS | 50 | Object keys shown |

### Result Structure

Processing returns `FileExtractionResult` containing: processed content (string or binary), success status, file type, truncation information (what was shown vs total), and file metadata. Truncation info enables agents to understand what data was omitted.

## Image Size Reduction

Images attached to agent context must fit within model attachment limits (typically 2MB).

### Resize Strategies

**File-size-based**: When an image exceeds MAX_IMAGE_ATTACHMENT_SIZE (2MB), dimensions are reduced proportionally using the square root of the size ratio to achieve target file size.

**Dimension-based**: Alternative strategy limits maximum dimension while maintaining aspect ratio.

Both use LANCZOS resampling for quality. Original dimensions are recorded in truncation info.

### Supported Formats

PNG, JPEG, GIF, and WEBP are processed and resized. Other formats return metadata only with an error message.

## History Compaction

Long conversations accumulate tokens until they approach context limits. The history compactor monitors token count and summarizes when thresholds are exceeded.

### Token Counting

Messages are serialized to JSON and counted using tiktoken (cl100k_base encoding) to match API payload sizes. Fallback estimation uses 4 characters per token.

### Compaction Process

When message history exceeds HISTORY_COMPACTION_MAX_TOKENS (120K), the compactor summarizes all messages using a summarization prompt that preserves key information, decisions, and context needed for conversation continuation. The result replaces the entire history with a single summary message targeting HISTORY_COMPACTION_TARGET_TOKENS (40K).

### Fallback Truncation

If no summarization model is available, the system keeps 25% from conversation start and 75% from the end (recent context being more important), with an annotation indicating removed content.

### Integration

The compactor provides a `create_history_processor()` method returning a callable compatible with PydanticAI's history_processor parameter. A callback receives `CompactionResult` with original/compacted message counts, token counts, and summary text.

### Key Configuration

| Parameter | Default | Purpose |
|-----------|---------|---------|
| HISTORY_COMPACTION_MAX_TOKENS | 120000 | Trigger compaction threshold |
| HISTORY_COMPACTION_TARGET_TOKENS | 40000 | Target size after compaction |
| SUMMARIZER_INPUT_MAX_TOKENS | 180000 | Max input to summarizer |

## Workspace Storage

For results too large to include in context (database query results, generated files), the workspace provides isolated storage per user session.

### Path Structure

Each user session gets a dedicated directory: `<DATA_DIR>/workspaces/<user_id>/<session_id>/`. Inside sandbox containers, this mounts at `/workspace`.

### Path Conversion

`container_to_host_path()` converts sandbox paths to host filesystem paths. `host_to_container_path()` does the reverse. Both validate that paths remain within the workspace root to prevent path traversal attacks.

### Usage Pattern

Agent executes expensive operation (e.g., SQL query returning 50K rows), saves result to workspace file, returns reference to model ("Results saved to /workspace/query_results.csv"). Subsequent requests can read the file with truncation, accessing a sample without loading 50K rows into context.

### Private Data

Conversation metadata stored separately at `<DATA_DIR>/workspaces/_private-data/<user_id>/<session_id>.json`.

## Design Principles

**Progressive truncation**: Multiple layers ensure content fits context. Format-specific processing first, then cell/line length limits, then token limits.

**Metadata preservation**: Truncation info always indicates what was shown vs omitted, enabling agents to request different portions or explain limitations to users.

**Graceful degradation**: Encoding errors fall back to alternative encodings. Extraction failures return partial results. Missing models use truncation instead of summarization.

**Never load entire files**: Tabular processors read only needed rows. Document extraction streams content. This handles gigabyte files without memory issues.

**Security**: Workspace paths are validated to prevent directory traversal. All paths normalized before comparison.

## Component Locations

| Component | Location |
|-----------|----------|
| File processors | `aixtools/agents/context/processors/` |
| Reader interface | `aixtools/agents/context/reader.py` |
| Data models | `aixtools/agents/context/data_models.py` |
| History compactor | `aixtools/agents/history_compactor.py` |
| Workspace paths | `aixtools/server/path.py` |
| Configuration | `aixtools/utils/config.py` |
| Prompt building | `aixtools/agents/prompt.py` |
