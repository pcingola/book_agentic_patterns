"""
Utility functions for agent operations.
"""

from typing import Sequence

from pydantic_ai import ModelMessage, ToolCallPart


def get_usage(node):
    """Get usage information from a node."""
    if node and hasattr(node, "usage"):
        return node.usage
    response = None
    if hasattr(node, "response"):
        response = node.response
    elif hasattr(node, "model_response"):
        response = node.model_response
    if response and hasattr(response, "usage"):
        return response.usage
    return None


def has_tool_calls(msg: ModelMessage) -> bool:
    """Check if the message contains any ToolCallPart."""
    return any(isinstance(part, ToolCallPart) for part in msg.parts)


def nodes_to_message_history(
    nodes: list, remove_last_call_tool: bool = True
) -> Sequence[ModelMessage]:
    """Convert a list of nodes to message history."""
    messages = []
    for n in nodes:
        if hasattr(n, "request"):
            messages.append(n.request)
        elif hasattr(n, "response"):
            messages.append(n.response)
        elif hasattr(n, "model_response"):
            messages.append(n.model_response)
    # Optionally remove the last CallToolsNode
    if remove_last_call_tool and len(messages) >= 2 and has_tool_calls(messages[-1]):  # noqa: PLR2004
        # Remove the last CallToolsNode if present
        messages = messages[:-1]
    return messages
