
"""
A simple example of an A2A (Agent to Agent) server
"""
from aixtools.agents import get_agent
from a2a_utils import tool2skill


def area_triangle(base: float, height: float) -> float:
    """Calculate the area of a triangle"""
    print(f"Calculating area of triangle with base {base} and height {height}")
    return 0.5 * base * height


def area_rectangle(length: float, width: float) -> float:
    """Calculate the area of a rectangle"""
    print(f"Calculating area of rectangle with length {length} and width {width}")
    return length * width


def area_circle(radius: float) -> float:
    """Calculate the area of a circle"""
    from math import pi
    print(f"Calculating area of circle with radius {radius}")
    return pi * radius ** 2


tools=[area_triangle, area_rectangle, area_circle]
skills = [tool2skill(tool) for tool in tools]

agent = get_agent(tools=tools)
app = agent.to_a2a(name="AreaCalculator", description="An agent that can calculate areas of different shapes", skills=skills)