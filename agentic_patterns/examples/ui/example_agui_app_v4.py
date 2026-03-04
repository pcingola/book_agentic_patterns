"""
AG-UI application with file upload support.

Extends v3 (calculator with state) by adding a /upload REST endpoint
that implements the save-summarize-tag pattern from the file uploads chapter.
AG-UI is a text-message protocol with no built-in file attachment mechanism,
so file uploads go through a separate HTTP endpoint as a side-channel.

Run with: uvicorn agentic_patterns.examples.ui.example_agui_app_v4:app --reload
"""

from pathlib import PurePosixPath

from starlette.middleware.cors import CORSMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route

from pydantic_ai.ui import StateDeps
from pydantic_ai.ui.ag_ui.app import AGUIApp

from agentic_patterns.core.agents.agents import get_agent
from agentic_patterns.core.compliance.private_data import DataSensitivity, PrivateData
from agentic_patterns.core.context.reader import read_file_as_string
from agentic_patterns.core.workspace import (
    write_to_workspace_async,
    workspace_to_host_path,
)
from agentic_patterns.examples.ui.calculator import (
    CalculatorState,
    add,
    mul,
    show_history,
    sub,
)

UPLOAD_PREFIX = "/workspace/uploads"


async def upload_handler(request: Request) -> JSONResponse:
    """Handle file uploads: save to workspace, tag as private, summarize."""
    form = await request.form()
    file = form.get("file")
    if file is None:
        return JSONResponse({"error": "No file provided"}, status_code=400)

    content = await file.read()
    filename = file.filename or "upload"
    sandbox_path = f"{UPLOAD_PREFIX}/{filename}"

    await write_to_workspace_async(sandbox_path, content)
    PrivateData().add_private_dataset(
        f"upload:{filename}", DataSensitivity.CONFIDENTIAL
    )
    host_path = workspace_to_host_path(PurePosixPath(sandbox_path))
    summary = read_file_as_string(host_path)

    return JSONResponse({"workspace_path": sandbox_path, "summary": summary})


agent = get_agent(
    instructions=(
        "You are a calculator assistant. Use the provided tools to perform calculations. "
        "The calculation history is maintained in the shared state. "
        "When the user uploads a file, they will include its workspace path and a summary. "
        "You can reference the file content from the summary provided."
    ),
    deps_type=StateDeps[CalculatorState],
    tools=[add, sub, mul, show_history],
)

app = AGUIApp(
    agent,
    deps=StateDeps(CalculatorState()),
    routes=[Route("/upload", upload_handler, methods=["POST"])],
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)
