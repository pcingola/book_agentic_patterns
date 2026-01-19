
"""
A simple example of an A2A (Agent to Agent) server
"""

from aixtools.agents import get_agent

def add(a: int, b: int) -> int:
    """Add two numbers"""
    print(f"Adding {a} + {b}")
    return a + b

def sub(a: int, b: int) -> int:
    """Substract two numbers"""
    print(f"Substracting {a} - {b}")
    return a - b


agent = get_agent(tools=[add, sub])

app = agent.to_a2a()