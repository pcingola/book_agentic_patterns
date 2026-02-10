# Plan: Format Conversion Toolkit

## Context

We need a toolkit to convert documents between formats for LLM consumption. Two directions: ingest (PDF/Word/PPT/Excel -> Markdown/CSV) and export (Markdown -> PDF/Word/HTML). Follows the three-layer architecture established in `docs/refactor_mcp_connectors.md`.

## Dependencies

**Ingest:**
- `pymupdf` -- PDF -> Markdown (fast, built-in MD output, handles images+text)
- `python-docx` -- Word -> Markdown
- `python-pptx` -- PowerPoint -> Markdown
- `openpyxl` -- Excel -> CSV / Markdown table

**Export:**
- `pypandoc` -- Markdown -> PDF / Word / HTML (wraps pandoc CLI)
- Pandoc binary + Typst binary (for PDF engine, no LaTeX)

## Directory Layout

```
agentic_patterns/toolkits/format_conversion/
    enums.py              # InputFormat, OutputFormat enums
    ingest.py             # PDF/Word/PPT/Excel -> Markdown/CSV
    export.py             # Markdown -> PDF/Word/HTML (via pypandoc + typst)
    converter.py          # dispatch: convert(input_path, output_format) -> Path

agentic_patterns/tools/format_conversion.py          # PydanticAI wrappers
agentic_patterns/mcp/format_conversion/
    server.py             # FastMCP server
    tools.py              # MCP tool registration
```

## Layer 1: Toolkit (`toolkits/format_conversion/`)

### enums.py

```python
class InputFormat(str, Enum):
    PDF = "pdf"
    DOCX = "docx"
    PPTX = "pptx"
    XLSX = "xlsx"
    CSV = "csv"
    MD = "md"

class OutputFormat(str, Enum):
    MD = "md"
    CSV = "csv"
    PDF = "pdf"
    DOCX = "docx"
    HTML = "html"
```

### ingest.py

One function per source format, all returning `str`:

- `pdf_to_markdown(input_path: Path) -> str`
- `docx_to_markdown(input_path: Path) -> str`
- `pptx_to_markdown(input_path: Path) -> str`
- `xlsx_to_csv(input_path: Path, sheet: str | None = None) -> str`
- `xlsx_to_markdown(input_path: Path, sheet: str | None = None) -> str`

### export.py

Single function using pypandoc:

- `markdown_to(input_path: Path, output_path: Path, output_format: OutputFormat) -> Path`

Uses `--pdf-engine=typst` for PDF output.

### converter.py

Dispatcher:

- `convert(input_path: Path, output_format: OutputFormat, output_path: Path | None = None) -> str | Path`

Routes by input extension + output format. Returns `str` for text outputs (MD, CSV), `Path` for binary outputs (PDF, DOCX).

## Layer 2: Tools (`tools/format_conversion.py`)

```python
def get_all_tools() -> list:
    # convert_document -- main dispatch tool
    # Decorated with @tool_permission(ToolPermission.READ)
    # Uses workspace_to_host_path() for file paths
```

Single tool exposed: `convert_document(input_file: str, output_format: str) -> str`. The agent provides a workspace path and desired format; the tool handles routing.

## Layer 3: MCP Server (`mcp/format_conversion/`)

Thin wrapper: `register_tools(mcp)` with `ctx.info()` logging and `ToolRetryError` for bad inputs (unsupported format, file not found).

## Execution Order

1. Add dependencies to `pyproject.toml`
2. Create `toolkits/format_conversion/enums.py`
3. Create `toolkits/format_conversion/ingest.py`
4. Create `toolkits/format_conversion/export.py`
5. Create `toolkits/format_conversion/converter.py`
6. Create `tools/format_conversion.py`
7. Create `mcp/format_conversion/server.py` + `tools.py`
8. Test with sample files

## Verification

1. Unit test with sample PDF/DOCX/PPTX/XLSX in `tests/data/`
2. Run MCP server locally, call tools via FastMCP in-memory client
3. `scripts/lint.sh`
