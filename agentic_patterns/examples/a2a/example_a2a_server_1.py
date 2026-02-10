"""
A2A server that exposes an agent with arithmetic tools.
"""

from typing import Callable

from agentic_patterns.core.agents import get_agent
from fasta2a import Skill


def tool_to_skill(func: Callable) -> Skill:
    """Convert a tool function to an A2A Skill."""
    return Skill(
        id=func.__name__, name=func.__name__, description=func.__doc__ or func.__name__
    )


def add(a: int, b: int) -> int:
    """Add two numbers: a + b"""
    return a + b


def sub(a: int, b: int) -> int:
    """Subtract two numbers: a - b"""
    return a - b


def mul(a: int, b: int) -> int:
    """Multiply two numbers: a * b"""
    return a * b


def div(a: int, b: int) -> float:
    """Divide two numbers: a / b"""
    if b == 0:
        raise ValueError("Cannot divide by zero")
    return a / b


tools = [add, sub, mul, div]
skills = [tool_to_skill(f) for f in tools]

agent = get_agent(tools=tools)
app = agent.to_a2a(
    name="Arithmetic",
    description="An agent that can perform basic arithmetic operations",
    skills=skills,
)
