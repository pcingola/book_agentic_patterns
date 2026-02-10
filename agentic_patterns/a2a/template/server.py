"""Template A2A server demonstrating requirements 1, 2, and 6.

Shows how to build the skills list from all four sources:
  - tool_to_skill():              local tool functions
  - mcp_to_skills():              connected MCP server tools (async)
  - card_to_skills():             sub-agent A2A agent cards
  - skill_metadata_to_a2a_skill(): SKILL.md metadata from the skill registry

Run with: uvicorn agentic_patterns.a2a.template.server:app --port 8001
"""

from agentic_patterns.core.a2a import AuthSessionMiddleware, tool_to_skill
from agentic_patterns.core.agents import get_agent
from agentic_patterns.core.config.config import PROMPTS_DIR
from agentic_patterns.core.prompt import load_prompt

from agentic_patterns.a2a.template.tools import ALL_TOOLS

system_prompt = load_prompt(PROMPTS_DIR / "a2a" / "template" / "system_prompt.md")


# -- Skills from local tools (always present) ---------------------------------
skills = [tool_to_skill(f) for f in ALL_TOOLS]


# -- Skills from connected MCP servers (uncomment when MCP servers are configured)
# skills += asyncio.run(mcp_to_skills("my_mcp_server"))

# -- Skills from A2A sub-agents (uncomment when sub-agents are available)
# from agentic_patterns.core.a2a import get_a2a_client
# sub_agent = get_a2a_client("my_sub_agent")
# card = asyncio.run(sub_agent.get_agent_card())
# skills += card_to_skills(card)

# -- Skills from SKILL.md registry (uncomment when skills directory exists)
# from agentic_patterns.core.skills.registry import SkillRegistry
# registry = SkillRegistry()
# registry.discover([Path("skills/")])
# skills += [skill_metadata_to_a2a_skill(m) for m in registry.list_all()]


agent = get_agent(tools=ALL_TOOLS, instructions=system_prompt)
app = agent.to_a2a(
    name="TextProcessor",
    description="An agent that can perform simple text-processing operations.",
    skills=skills,
)
app.add_middleware(AuthSessionMiddleware)
