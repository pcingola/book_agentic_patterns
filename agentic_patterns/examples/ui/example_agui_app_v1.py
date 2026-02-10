"""
Minimal AG-UI application: Basic agent exposed via AG-UI protocol.

Run with:
    uvicorn agentic_patterns.examples.ui.example_agui_app_v1:app --reload
"""

from starlette.middleware.cors import CORSMiddleware

from pydantic_ai.ui.ag_ui.app import AGUIApp

from agentic_patterns.core.agents.agents import get_agent


agent = get_agent(
    instructions="You are a helpful assistant. Keep responses concise.",
)

app = AGUIApp(agent)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)
