"""A2A server with well-defined agent card for doctor analysis."""

from typing import Callable

from fasta2a.schema import Skill

from agentic_patterns.core.agents import get_agent


def tool_to_skill(func: Callable, tags: list[str]) -> Skill:
    """Convert a tool function to an A2A Skill."""
    return Skill(
        id=func.__name__,
        name=func.__name__.replace("_", " ").title(),
        description=func.__doc__ or func.__name__,
        tags=tags,
        inputModes=["application/json"],
        outputModes=["application/json"],
    )  # type: ignore


def add_numbers(a: float, b: float) -> float:
    """Add two numbers and return the sum."""
    return a + b


def subtract_numbers(a: float, b: float) -> float:
    """Subtract the second number from the first and return the difference."""
    return a - b


def multiply_numbers(a: float, b: float) -> float:
    """Multiply two numbers and return the product."""
    return a * b


def divide_numbers(a: float, b: float) -> float:
    """Divide the first number by the second and return the quotient. Raises ValueError if b is zero."""
    if b == 0:
        raise ValueError("Cannot divide by zero")
    return a / b


tools = [add_numbers, subtract_numbers, multiply_numbers, divide_numbers]
skills = [tool_to_skill(f, tags=["math", "arithmetic"]) for f in tools]

agent = get_agent(tools=tools)
app = agent.to_a2a(
    name="calculator",
    description="A calculator agent that performs basic arithmetic operations: addition, subtraction, multiplication, and division.",
    skills=skills,
)
