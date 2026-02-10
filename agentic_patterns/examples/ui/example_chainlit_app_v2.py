"""
This is a simple chatbot that uses the LLM model to generate responses to user messages.
"""

import chainlit as cl

from agentic_patterns.core.agents import get_agent, run_agent

# Initialize the agent
agent = get_agent()


@cl.on_message
async def on_message(message: cl.Message):
    user_message = (
        message.content
    )  # Here we DON'T use the history, so it has no memory of the previous messages
    ret, nodes = await run_agent(agent, user_message, verbose=True)
    output = ret.result.output
    msg = cl.Message(content=output if output else "No response from the agent.")
    await msg.send()
