"""Utility functions for A2A integration."""

import re
import uuid
from collections.abc import Callable

from fasta2a import Skill


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


def tool_to_skill(func: Callable) -> Skill:
    """Convert a tool function to an A2A Skill using its name and docstring."""
    return Skill(id=func.__name__, name=func.__name__, description=func.__doc__ or func.__name__)


def card_to_skills(card: dict) -> list[Skill]:
    """Extract skills from an A2A agent card."""
    return [
        Skill(id=s.get("id", s["name"]), name=s["name"], description=s.get("description") or s["name"])
        for s in card.get("skills") or []
    ]


async def mcp_to_skills(config_name: str, config_path: "Path | str | None" = None) -> list[Skill]:
    """Connect to an MCP server by config name and convert its tools to A2A Skills."""
    from agentic_patterns.core.mcp import get_mcp_client
    client = get_mcp_client(config_name, config_path)
    tools = await client.list_tools()
    return [Skill(id=t.name, name=t.name, description=t.description or t.name) for t in tools]


def skill_metadata_to_a2a_skill(meta: "SkillMetadata") -> Skill:
    """Convert a core SkillMetadata to a fasta2a Skill."""
    return Skill(id=slugify(meta.name), name=meta.name, description=meta.description)
