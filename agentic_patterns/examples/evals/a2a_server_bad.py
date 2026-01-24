"""A2A server with poorly defined agent card for doctor analysis."""

from agentic_patterns.core.agents import get_agent


def do_thing(x):
    """Does thing."""
    return x


def proc(a, b):
    """Process."""
    return a + b


agent = get_agent(tools=[do_thing, proc])
app = agent.to_a2a(name="helper", description="helps")
