"""MCP tool registration for the data visualization server -- thin wrapper delegating to toolkits/data_viz/."""

from fastmcp import Context, FastMCP

from agentic_patterns.core.mcp import ToolFatalError, ToolRetryError
from agentic_patterns.tools.dynamic import generate_param_docs, get_param_signature
from agentic_patterns.core.tools.permissions import ToolPermission, tool_permission
from agentic_patterns.toolkits.data_viz.executor import execute_plot, get_all_operations
from agentic_patterns.toolkits.data_viz.io import list_plot_files


def _generate_tool_function(op_name: str, op_config):
    """Generate an async MCP tool function dynamically from a PlotConfig."""
    func_code = f"async def {op_name}_tool(input_file: str, output_file: str = None"
    for param_name, param_default in op_config.parameters.items():
        func_code += get_param_signature(param_name, param_default)

    func_code += f""", ctx: Context = None) -> str:
    \"\"\"Dynamically generated tool for {op_name}.\"\"\"
    if ctx:
        await ctx.info("{op_name} called on " + str(input_file))

    filtered_params = {{}}
"""

    for param_name, param_default in op_config.parameters.items():
        func_code += f"""
    if {param_name} is not None:
        filtered_params['{param_name}'] = {param_name}"""

        if param_default not in (str, int, float, bool, list, dict, None):
            if isinstance(param_default, str):
                func_code += f"""
    else:
        filtered_params['{param_name}'] = '{param_default}'"""
            else:
                func_code += f"""
    else:
        filtered_params['{param_name}'] = {param_default}"""

    func_code += """

    try:
        return await execute_plot(input_file, output_file, op_name, filtered_params)
    except ValueError as e:
        raise ToolRetryError(str(e)) from e
    except RuntimeError as e:
        raise ToolFatalError(str(e)) from e
"""

    namespace = {"execute_plot": execute_plot, "op_name": op_name, "Context": Context, "ToolRetryError": ToolRetryError, "ToolFatalError": ToolFatalError}
    exec(func_code, namespace)  # noqa: S102
    tool_func = namespace[f"{op_name}_tool"]

    tool_func.__name__ = op_name
    tool_func.__doc__ = f"""{op_config.description}

Args:
    input_file: Path to the input CSV file (workspace path)
    output_file: Path to save the plot image (auto-generated if not provided)
{generate_param_docs(op_config.parameters)}
"""
    return tool_func


def register_tools(mcp: FastMCP) -> None:
    """Register all tools on the given MCP server instance."""

    @mcp.tool()
    @tool_permission(ToolPermission.READ)
    async def list_plots(ctx: Context) -> str:
        """List available image files (PNG, SVG) in the workspace."""
        await ctx.info("list_plots called")
        files = list_plot_files()
        if not files:
            return "No image files found in workspace."
        return "\n".join(files)

    operations = get_all_operations()
    for op_name, op_config in operations.items():
        tool_func = _generate_tool_function(op_name, op_config)
        tool_func = tool_permission(ToolPermission.WRITE)(tool_func)
        mcp.tool()(tool_func)
        setattr(mcp, f"_auto_tool_{op_name}", tool_func)
