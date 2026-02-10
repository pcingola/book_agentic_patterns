"""MCP format conversion tools -- thin wrapper delegating to toolkits/format_conversion/."""

from pathlib import PurePosixPath

from fastmcp import Context, FastMCP

from agentic_patterns.core.context.decorators import context_result
from agentic_patterns.core.mcp import ToolRetryError
from agentic_patterns.core.tools.permissions import ToolPermission, tool_permission
from agentic_patterns.core.workspace import host_to_workspace_path, workspace_to_host_path
from agentic_patterns.toolkits.format_conversion.converter import convert
from agentic_patterns.toolkits.format_conversion.enums import OutputFormat


def register_tools(mcp: FastMCP) -> None:
    """Register all format conversion tools on the given MCP server instance."""

    @mcp.tool()
    @tool_permission(ToolPermission.READ)
    @context_result()
    async def convert_document(input_file: str, output_format: str, ctx: Context) -> str:
        """Convert a document between formats.

        Supported input formats: PDF, DOCX, PPTX, XLSX, CSV, MD.
        Supported output formats: MD, CSV, PDF, DOCX, HTML.

        Args:
            input_file: Path to input file (must start with /workspace/).
            output_format: Target format (md, csv, pdf, docx, html).
        """
        try:
            fmt = OutputFormat(output_format.lower())
        except ValueError:
            raise ToolRetryError(f"Unsupported output format: {output_format}. Use one of: {', '.join(f.value for f in OutputFormat)}")

        try:
            host_input = workspace_to_host_path(PurePosixPath(input_file))
        except Exception as e:
            raise ToolRetryError(str(e)) from e

        if not host_input.exists():
            raise ToolRetryError(f"File not found: {input_file}")

        await ctx.info(f"Converting {input_file} to {fmt.value}")

        try:
            result = convert(host_input, fmt)
        except ValueError as e:
            raise ToolRetryError(str(e)) from e

        if isinstance(result, str):
            return result
        return f"Converted file saved to {host_to_workspace_path(result)}"
