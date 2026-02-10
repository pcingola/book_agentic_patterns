"""MCP tool registration for the data analysis server -- thin wrapper delegating to toolkits/data_analysis/."""

from fastmcp import Context, FastMCP

from agentic_patterns.core.context.decorators import context_result
from agentic_patterns.core.mcp import ToolFatalError, ToolRetryError
from agentic_patterns.tools.dynamic import generate_param_docs, get_param_signature
from agentic_patterns.core.tools.permissions import ToolPermission, tool_permission
from agentic_patterns.toolkits.data_analysis.executor import execute_operation, get_all_operations
from agentic_patterns.toolkits.data_analysis.io import list_dataframe_files


def _generate_tool_function(op_name: str, op_config):
    """Generate an async MCP tool function dynamically from an OperationConfig."""
    func_code = f"async def {op_name}_tool(input_file: str, output_file: str = None"
    for param_name, param_default in op_config.parameters.items():
        func_code += get_param_signature(param_name, param_default)

    func_code += f""", ctx: Context = None) -> str:
    \"\"\"Dynamically generated tool for {op_name}.\"\"\"
    if ctx:
        await ctx.info("{op_name} called on " + str(input_file))

    if output_file is None and not {op_config.view_only} and {op_config.returns_df}:
        output_file = f"{{input_file.rsplit('.', 1)[0]}}_{op_name}_output.pkl"

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
        return await execute_operation(input_file, output_file, op_name, filtered_params)
    except ValueError as e:
        raise ToolRetryError(str(e)) from e
    except RuntimeError as e:
        raise ToolFatalError(str(e)) from e
"""

    namespace = {"execute_operation": execute_operation, "op_name": op_name, "Context": Context, "ToolRetryError": ToolRetryError, "ToolFatalError": ToolFatalError}
    exec(func_code, namespace)  # noqa: S102
    tool_func = namespace[f"{op_name}_tool"]

    tool_func.__name__ = op_name
    tool_func.__doc__ = f"""{op_config.description}

Args:
    input_file: Path to the input dataframe file
    output_file: Path to save the result (auto-generated if not provided)
{generate_param_docs(op_config.parameters)}
"""
    return tool_func


def register_tools(mcp: FastMCP) -> None:
    """Register all tools on the given MCP server instance."""

    @mcp.tool()
    @tool_permission(ToolPermission.READ)
    async def list_dataframes(ctx: Context) -> str:
        """List available dataframe files (CSV/pickle) in the workspace."""
        await ctx.info("list_dataframes called")
        files = list_dataframe_files()
        if not files:
            return "No dataframe files found in workspace."
        return "\n".join(files)

    operations = get_all_operations()
    for op_name, op_config in operations.items():
        tool_func = _generate_tool_function(op_name, op_config)

        permission = ToolPermission.READ if op_config.view_only else ToolPermission.WRITE
        tool_func = context_result(save=not op_config.view_only)(tool_func)
        tool_func = tool_permission(permission)(tool_func)
        mcp.tool()(tool_func)
        setattr(mcp, f"_auto_tool_{op_name}", tool_func)
