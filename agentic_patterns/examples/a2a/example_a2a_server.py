"""
A2A server that exposes an agent with arithmetic tools.
"""

from agentic_patterns.core.agents import get_agent


def add(a: int, b: int) -> int:
    """Add two numbers"""
    return a + b


def sub(a: int, b: int) -> int:
    """Subtract two numbers"""
    return a - b


agent = get_agent(tools=[add, sub])
app = agent.to_a2a()