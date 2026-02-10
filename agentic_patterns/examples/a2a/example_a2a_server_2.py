"""
A2A server that exposes an agent with area calculation tools.
"""

from math import pi
from typing import Callable

from agentic_patterns.core.agents import get_agent
from fasta2a import Skill


def tool_to_skill(func: Callable) -> Skill:
    """Convert a tool function to an A2A Skill."""
    return Skill(
        id=func.__name__, name=func.__name__, description=func.__doc__ or func.__name__
    )


def area_triangle(base: float, height: float) -> float:
    """Calculate the area of a triangle"""
    return 0.5 * base * height


def area_rectangle(length: float, width: float) -> float:
    """Calculate the area of a rectangle"""
    return length * width


def area_circle(radius: float) -> float:
    """Calculate the area of a circle"""
    return pi * radius**2


tools = [area_triangle, area_rectangle, area_circle]
skills = [tool_to_skill(f) for f in tools]

agent = get_agent(tools=tools)
app = agent.to_a2a(
    name="AreaCalculator",
    description="An agent that can calculate areas of different shapes",
    skills=skills,
)
