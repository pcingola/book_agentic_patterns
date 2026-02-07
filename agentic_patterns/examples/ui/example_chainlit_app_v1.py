"""
Echo application: It just repeats the message sent by the user.
"""

import chainlit as cl


@cl.on_message
async def on_message(message: cl.Message):
    # Get user message
    user_message = message.content
    # Repeat message
    msg = cl.Message(content=f"Echo:\n{user_message}")
    await msg.send()
