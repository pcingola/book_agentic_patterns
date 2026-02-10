"""Shared helpers for dynamic tool generation from operation registries."""


def get_param_signature(param_name: str, param_default) -> str:
    """Generate parameter signature string for dynamic function creation."""
    type_mapping = {
        str: f", {param_name}: str = None",
        int: f", {param_name}: int = None",
        float: f", {param_name}: float = None",
        bool: f", {param_name}: bool = None",
    }

    if param_default is None:
        return f", {param_name} = None"
    if isinstance(param_default, str):
        return f", {param_name}: str = '{param_default}'"
    if isinstance(param_default, list):
        return f", {param_name}: list = None"
    if isinstance(param_default, dict):
        return f", {param_name}: dict = None"

    try:
        if param_default in type_mapping:
            return type_mapping[param_default]
    except TypeError:
        pass

    return f", {param_name} = {param_default}"


def generate_param_docs(parameters: dict) -> str:
    """Generate parameter documentation for the function docstring."""
    if not parameters:
        return ""
    lines = []
    for name, default in parameters.items():
        if default is str:
            ptype = "str"
        elif default is int:
            ptype = "int"
        elif default is float:
            ptype = "float"
        elif default is bool:
            ptype = "bool"
        elif default is None:
            ptype = "optional"
        elif isinstance(default, list):
            ptype = "list"
        elif isinstance(default, dict):
            ptype = "dict"
        else:
            ptype = type(default).__name__
        default_str = (
            f" (default: {default})"
            if default not in (str, int, float, bool, list, dict, None)
            else ""
        )
        lines.append(f"    {name}: {ptype}{default_str}")
    return "\n".join(lines)
