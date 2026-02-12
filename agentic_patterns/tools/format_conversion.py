"""Agent tools for format conversion -- wraps toolkits/format_conversion/."""

from pathlib import PurePosixPath

from pydantic_ai import ModelRetry

from agentic_patterns.core.tools.permissions import ToolPermission, tool_permission
from agentic_patterns.core.workspace import (
    WorkspaceError,
    host_to_workspace_path,
    workspace_to_host_path,
)
from agentic_patterns.toolkits.format_conversion.converter import convert
from agentic_patterns.toolkits.format_conversion.enums import OutputFormat


def get_all_tools() -> list:
    """Get all format conversion tools."""

    @tool_permission(ToolPermission.READ)
    def convert_document(input_file: str, output_format: str) -> str:
        """Convert a document between formats.

        Supported input formats: PDF, DOCX, PPTX, XLSX, CSV, MD.
        Supported output formats: MD, CSV, PDF, DOCX, HTML.

        Args:
            input_file: Path to input file (must start with /workspace/).
            output_format: Target format (md, csv, pdf, docx, html).
        """
        try:
            fmt = OutputFormat(output_format.lower())
            host_input = workspace_to_host_path(PurePosixPath(input_file))
            if not host_input.exists():
                raise ValueError(f"File not found: {input_file}")

            result = convert(host_input, fmt)

            if isinstance(result, str):
                return result
            # Binary output -- result is a host Path
            return f"Converted file saved to {host_to_workspace_path(result)}"
        except (ValueError, WorkspaceError) as e:
            raise ModelRetry(str(e)) from e

    return [convert_document]
