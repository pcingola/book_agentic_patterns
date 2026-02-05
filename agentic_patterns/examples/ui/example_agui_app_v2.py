"""
AG-UI application with tools.

This example demonstrates:
- Agent with tools exposed via AG-UI protocol
- Tools are visible in the AG-UI event stream

Run with: uvicorn agentic_patterns.examples.ui.example_agui_app_v2:app --reload
"""

from starlette.middleware.cors import CORSMiddleware

from pydantic_ai.ui.ag_ui.app import AGUIApp

from agentic_patterns.core.agents.agents import get_agent


async def add(a: int, b: int) -> int:
    """Add two numbers."""
    return a + b


async def sub(a: int, b: int) -> int:
    """Subtract two numbers."""
    return a - b


async def mul(a: int, b: int) -> int:
    """Multiply two numbers."""
    return a * b


agent = get_agent(
    instructions='You are a calculator assistant. Use the provided tools to perform calculations.',
    tools=[add, sub, mul],
)

app = AGUIApp(agent)
app.add_middleware(
    CORSMiddleware,
    allow_origins=['http://localhost:5173'],
    allow_methods=['*'],
    allow_headers=['*'],
)
