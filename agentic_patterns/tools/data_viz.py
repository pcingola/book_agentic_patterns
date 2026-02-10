"""PydanticAI agent tools for data visualization -- wraps toolkits/data_viz/."""

from agentic_patterns.core.tools.permissions import ToolPermission, tool_permission
from agentic_patterns.tools.dynamic import generate_param_docs, get_param_signature
from agentic_patterns.toolkits.data_viz.executor import execute_plot, get_all_operations
from agentic_patterns.toolkits.data_viz.io import list_plot_files


def _generate_tool_function(op_name: str, op_config):
    """Generate an async tool function dynamically from a PlotConfig."""
    func_code = f"async def {op_name}_tool(input_file: str, output_file: str = None"
    for param_name, param_default in op_config.parameters.items():
        func_code += get_param_signature(param_name, param_default)

    func_code += f""") -> str:
    \"\"\"Dynamically generated tool for {op_name}.\"\"\"

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

    return await execute_plot(input_file, output_file, op_name, filtered_params)
"""

    namespace = {"execute_plot": execute_plot, "op_name": op_name}
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


def get_all_tools() -> list:
    """Get all data visualization tools for use with PydanticAI agents."""

    @tool_permission(ToolPermission.READ)
    async def list_plots() -> str:
        """List available image files (PNG, SVG) in the workspace."""
        files = list_plot_files()
        if not files:
            return "No image files found in workspace."
        return "\n".join(files)

    tools = [list_plots]

    operations = get_all_operations()
    for op_name, op_config in operations.items():
        tool_func = _generate_tool_function(op_name, op_config)
        tool_func = tool_permission(ToolPermission.WRITE)(tool_func)
        tools.append(tool_func)

    return tools
