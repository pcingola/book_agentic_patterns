"""
Chatbot with authentication, history persistence, file upload, and chat resume.

This example demonstrates:
- Password-based authentication using a JSON user database
- SQLite data layer for persisting chat history across sessions
- Chat resume to restore conversation when user returns
- File upload processing with workspace storage
- Starters for quick-start message suggestions
- User/session tracking via context variables
"""

from logging import getLogger
from pathlib import Path

import chainlit as cl

from agentic_patterns.core.agents import get_agent, run_agent
from agentic_patterns.core.context import read_file_as_string
from agentic_patterns.core.ui.chainlit.handlers import HISTORY, register_all, setup_user_session
from agentic_patterns.core.workspace import write_to_workspace_async

AGENT = 'agent'

logger = getLogger(__name__)

# Register authentication, data layer, and chat resume handlers.
# This sets up:
# - @cl.password_auth_callback: authenticates users against users.json
# - @cl.data_layer: persists chat threads to SQLite database
# - @cl.on_chat_resume: restores history when user returns to a previous chat
register_all()


async def process_uploaded_files(files: list) -> str:
    """Process uploaded files: save to workspace and return summarized content."""
    if not files:
        return ""

    file_contexts = []
    for file in files:
        filename = Path(file.name).name
        workspace_path = f"/workspace/uploads/{filename}"

        # Read file content and save to workspace
        file_content = Path(file.path).read_bytes()
        await write_to_workspace_async(workspace_path, file_content)

        # Get summarized content using context reader
        summary = read_file_as_string(file.path)

        file_contexts.append(f"[File: {workspace_path}]\n{summary}")
        logger.info(f"Processed file: {filename} -> {workspace_path}")

    return "\n\n".join(file_contexts)


@cl.step(type="tool")
async def add(a: int, b: int) -> int:
    """Add two numbers"""
    logger.info(f"Adding {a} + {b}")
    return a + b


@cl.step(type="tool")
async def sub(a: int, b: int) -> int:
    """Subtract two numbers"""
    logger.info(f"Subtracting {a} - {b}")
    return a - b


@cl.set_starters  # type: ignore
async def set_starters(user: str | None, language: str | None) -> list[cl.Starter]:
    """Create quick-start message suggestions shown to users on new chats."""
    logger.info(f"Setting starters for user: {user}")
    return [
        cl.Starter(label="Add numbers", message="What is 42 + 17?"),
        cl.Starter(label="Subtract numbers", message="What is 100 - 37?"),
        cl.Starter(label="Calculate", message="Add 25 and 75, then subtract 50 from the result"),
    ]


@cl.on_chat_start
async def on_chat_start():
    # Set user/session IDs in context variables for downstream code (workspace, logging, etc.)
    setup_user_session()

    # Initialize the agent with our tools
    agent = get_agent(tools=[add, sub])
    cl.user_session.set(AGENT, agent)

    # Reset history for new chat
    cl.user_session.set(HISTORY, [])


@cl.on_message
async def on_message(message: cl.Message):
    # Update user/session context on each message
    setup_user_session()

    # Get agent, user message and history
    agent = cl.user_session.get(AGENT)
    history = cl.user_session.get(HISTORY)
    user_message = message.content

    # Process uploaded files
    file_context = await process_uploaded_files(message.elements or [])
    if file_context:
        user_message = f"{user_message}\n\n{file_context}"

    # All messages = history + current message
    messages = list(history) if history else []
    messages.append(user_message)
    logger.info(f"Messages: {messages}")

    # Run the agent
    ret, nodes = await run_agent(agent, messages, verbose=True)  # type: ignore
    agent_response = ret.result.output
    logger.info(f"Agent response: {agent_response}")
    msg = cl.Message(content=agent_response if agent_response else "No response from the agent.")
    await msg.send()

    # Update history to add agent's response and store it
    messages.append(agent_response)
    cl.user_session.set(HISTORY, messages)
