
"""
A simple example of an A2A (Agent to Agent) server
"""

from aixtools.agents import get_agent
from fasta2a import Skill

from a2a_utils import tool2skill

def add(a: int, b: int) -> int:
    """Add two numbers: a + b"""
    print(f"Adding {a} + {b}")
    return a + b


def sub(a: int, b: int) -> int:
    """Substract two numbers: a - b"""
    print(f"Substracting {a} - {b}")
    return a - b


def mul(a: int, b: int) -> int:
    """Multiply two numbers: a * b"""
    print(f"Multiplying {a} * {b}")
    return a * b


def div(a: int, b: int) -> float:
    """Divide two numbers: a / b"""
    if b == 0:
        raise ValueError("Cannot divide by zero")
    print(f"Dividing {a} / {b}")
    return a / b


tools = [add, sub, mul, div]
skills = [tool2skill(tool) for tool in tools]

agent = get_agent(tools=[add])

app = agent.to_a2a(name="Arithmetic", description="An agent that can perform basic arithmetic operations", skills=skills)