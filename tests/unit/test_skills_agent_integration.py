import tempfile
import unittest
from pathlib import Path

from pydantic_ai import Agent
from pydantic_ai.messages import ToolCallPart

from agentic_patterns.core.skills.registry import SkillRegistry
from agentic_patterns.core.skills.tools import (
    get_skill_instructions,
    list_available_skills,
)
from agentic_patterns.testing import ModelMock


class TestSkillsAgentIntegration(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.skills_root = Path(self.temp_dir.name)
        skill_dir = self.skills_root / "data-analysis"
        skill_dir.mkdir(parents=True)
        (skill_dir / "SKILL.md").write_text("""---
name: data-analysis
description: Analyzes data files and produces statistics
---

# Data Analysis Skill

Use this skill to analyze CSV or JSON data files.

## Steps
1. Load the data file
2. Compute statistics
3. Return summary
""")
        scripts_dir = skill_dir / "scripts"
        scripts_dir.mkdir()
        (scripts_dir / "analyze.py").write_text("# analysis script")

        self.registry = SkillRegistry()
        self.registry.discover([self.skills_root])

    def tearDown(self):
        self.temp_dir.cleanup()

    async def test_agent_can_list_and_activate_skill(self):
        """Test that an agent with skill tools can list and activate skills."""

        def list_skills() -> str:
            """List all available skills."""
            return list_available_skills(self.registry)

        def activate_skill(name: str) -> str:
            """Activate a skill by name and get its instructions."""
            result = get_skill_instructions(self.registry, name)
            return result if result else f"Skill '{name}' not found."

        model = ModelMock(
            responses=[
                ToolCallPart(tool_name="list_skills", args={}),
                ToolCallPart(
                    tool_name="activate_skill", args={"name": "data-analysis"}
                ),
                "I've loaded the data-analysis skill. It helps analyze CSV or JSON files.",
            ]
        )

        agent = Agent(model=model, tools=[list_skills, activate_skill])
        result = await agent.run("What skills are available and how do I analyze data?")

        self.assertIn("data-analysis", result.output)

    async def test_agent_handles_unknown_skill(self):
        """Test that an agent handles requests for unknown skills gracefully."""

        def activate_skill(name: str) -> str:
            """Activate a skill by name and get its instructions."""
            result = get_skill_instructions(self.registry, name)
            return result if result else f"Skill '{name}' not found."

        model = ModelMock(
            responses=[
                ToolCallPart(
                    tool_name="activate_skill", args={"name": "nonexistent-skill"}
                ),
                "The skill 'nonexistent-skill' was not found.",
            ]
        )

        agent = Agent(model=model, tools=[activate_skill])
        result = await agent.run("Activate the nonexistent-skill")

        self.assertIn("not found", result.output)


if __name__ == "__main__":
    unittest.main()
