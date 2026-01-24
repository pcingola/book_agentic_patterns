"""Utility functions for A2A integration."""

import re
import uuid


def create_message(text: str, message_id: str | None = None) -> dict:
    """Create a user message with text content."""
    return {
        "role": "user",
        "kind": "message",
        "parts": [{"kind": "text", "text": text}],
        "message_id": message_id or str(uuid.uuid4()),
    }


def extract_text(task: dict) -> str | None:
    """Extract text content from task artifacts."""
    texts = []
    for artifact in task.get("artifacts") or []:
        for part in artifact.get("parts") or []:
            if part.get("kind") == "text":
                texts.append(part["text"])
    return "\n".join(texts) if texts else None


def extract_question(task: dict) -> str:
    """Extract question from an input-required task status."""
    status = task.get("status", {})
    msg = status.get("message")
    if msg and isinstance(msg, dict):
        for part in msg.get("parts") or []:
            if part.get("kind") == "text":
                return part["text"]
    return "Agent requires input"


def card_to_prompt(card: dict) -> str:
    """Format agent card for inclusion in coordinator system prompt."""
    lines = [f"## {card['name']}", card.get("description") or "", "", "Skills:"]
    for skill in card.get("skills") or []:
        lines.append(f"- {skill['name']}: {skill.get('description') or ''}")
    return "\n".join(lines)


def slugify(name: str) -> str:
    """Convert name to a valid Python identifier."""
    return re.sub(r"[^0-9a-zA-Z_]", "_", name.lower())
