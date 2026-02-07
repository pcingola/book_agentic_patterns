"""
Chainlit app with FileConnector tools.

Demonstrates how to plug connector methods into a Chainlit web interface.
The agent can create, read, edit, and search files through the workspace sandbox.

Run with: chainlit run agentic_patterns/examples/connectors/example_chainlit.py
"""

from logging import getLogger

import chainlit as cl

from agentic_patterns.core.agents import get_agent, run_agent
from agentic_patterns.core.connectors.file import FileConnector
from agentic_patterns.core.user_session import set_user_session

logger = getLogger(__name__)

AGENT = "agent"
HISTORY = "history"

# FileConnector methods become agent tools directly
connector = FileConnector()
tools = [
    connector.write,
    connector.read,
    connector.edit,
    connector.list,
    connector.find,
    connector.head,
]


@cl.set_starters  # type: ignore
async def set_starters(user: str | None, language: str | None) -> list[cl.Starter]:
    """Suggested actions shown when a new chat starts."""
    return [
        cl.Starter(label="Create a file", message="Create a file /workspace/notes.md with a title '# Meeting Notes' and three bullet points about a project kickoff."),
        cl.Starter(label="List files", message="List all files in /workspace/"),
        cl.Starter(label="Find files", message="Find all markdown files in /workspace/"),
    ]


@cl.on_chat_start
async def on_chat_start():
    set_user_session("demo_user", "demo_session")
    agent = get_agent(tools=tools)
    cl.user_session.set(AGENT, agent)
    cl.user_session.set(HISTORY, [])


@cl.on_message
async def on_message(message: cl.Message):
    agent = cl.user_session.get(AGENT)
    history = cl.user_session.get(HISTORY)

    messages = list(history) if history else []
    messages.append(message.content)

    ret, nodes = await run_agent(agent, messages, verbose=True)
    agent_response = ret.result.output

    msg = cl.Message(content=agent_response if agent_response else "No response.")
    await msg.send()

    messages.append(agent_response)
    cl.user_session.set(HISTORY, messages)
