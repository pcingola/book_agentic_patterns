import tempfile
import unittest
from pathlib import Path

from pydantic_ai import Agent
from pydantic_ai.messages import ToolCallPart

from agentic_patterns.core.skills.models import Skill, SkillMetadata
from agentic_patterns.core.skills.registry import SkillRegistry, _parse_frontmatter
from agentic_patterns.core.skills.tools import get_skill_instructions, list_available_skills
from agentic_patterns.testing import ModelMock


class TestSkillMetadata(unittest.TestCase):

    def test_str_representation(self):
        meta = SkillMetadata(name="test-skill", description="A test skill", path=Path("/tmp/test"))
        self.assertEqual(str(meta), "test-skill: A test skill")


class TestSkill(unittest.TestCase):

    def test_str_representation(self):
        skill = Skill(
            name="test-skill",
            description="A test skill",
            path=Path("/tmp/test"),
            frontmatter={"name": "test-skill", "description": "A test skill"},
            body="# Test\nSome instructions",
            script_paths=[],
            reference_paths=[],
        )
        self.assertEqual(str(skill), "Skill(test-skill)")


class TestParseFrontmatter(unittest.TestCase):

    def test_valid_frontmatter(self):
        content = """---
name: my-skill
description: My description
---

# Body content"""
        frontmatter, body = _parse_frontmatter(content)
        self.assertEqual(frontmatter["name"], "my-skill")
        self.assertEqual(frontmatter["description"], "My description")
        self.assertEqual(body, "# Body content")

    def test_no_frontmatter(self):
        content = "# Just body content"
        frontmatter, body = _parse_frontmatter(content)
        self.assertIsNone(frontmatter)
        self.assertEqual(body, content)

    def test_incomplete_frontmatter(self):
        content = "---\nname: incomplete"
        frontmatter, body = _parse_frontmatter(content)
        self.assertIsNone(frontmatter)
        self.assertEqual(body, content)


class TestSkillRegistry(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.skills_root = Path(self.temp_dir.name)
        self._create_test_skill("skill-one", "First skill for testing")
        self._create_test_skill("skill-two", "Second skill for testing")

    def tearDown(self):
        self.temp_dir.cleanup()

    def _create_test_skill(self, name: str, description: str, body: str = "# Instructions\nDo something."):
        skill_dir = self.skills_root / name
        skill_dir.mkdir(parents=True, exist_ok=True)
        skill_md = skill_dir / "SKILL.md"
        skill_md.write_text(f"""---
name: {name}
description: {description}
---

{body}
""")
        return skill_dir

    def test_discover_finds_skills(self):
        registry = SkillRegistry()
        metadata = registry.discover([self.skills_root])
        self.assertEqual(len(metadata), 2)
        names = {m.name for m in metadata}
        self.assertEqual(names, {"skill-one", "skill-two"})

    def test_discover_ignores_hidden_directories(self):
        hidden_dir = self.skills_root / ".hidden-skill"
        hidden_dir.mkdir()
        (hidden_dir / "SKILL.md").write_text("---\nname: hidden\ndescription: Hidden\n---\n# Body")

        registry = SkillRegistry()
        metadata = registry.discover([self.skills_root])
        names = {m.name for m in metadata}
        self.assertNotIn(".hidden-skill", names)
        self.assertNotIn("hidden", names)

    def test_discover_ignores_dirs_without_skill_md(self):
        (self.skills_root / "not-a-skill").mkdir()

        registry = SkillRegistry()
        metadata = registry.discover([self.skills_root])
        self.assertEqual(len(metadata), 2)

    def test_list_all_returns_cached_metadata(self):
        registry = SkillRegistry()
        registry.discover([self.skills_root])
        cached = registry.list_all()
        self.assertEqual(len(cached), 2)

    def test_get_returns_full_skill(self):
        registry = SkillRegistry()
        registry.discover([self.skills_root])
        skill = registry.get("skill-one")
        self.assertIsNotNone(skill)
        self.assertEqual(skill.name, "skill-one")
        self.assertEqual(skill.description, "First skill for testing")
        self.assertIn("Instructions", skill.body)

    def test_get_returns_none_for_unknown(self):
        registry = SkillRegistry()
        registry.discover([self.skills_root])
        skill = registry.get("nonexistent")
        self.assertIsNone(skill)

    def test_get_collects_script_paths(self):
        skill_dir = self._create_test_skill("skill-with-scripts", "Has scripts")
        scripts_dir = skill_dir / "scripts"
        scripts_dir.mkdir()
        (scripts_dir / "run.py").write_text("print('hello')")
        (scripts_dir / "helper.py").write_text("# helper")

        registry = SkillRegistry()
        registry.discover([self.skills_root])
        skill = registry.get("skill-with-scripts")
        self.assertEqual(len(skill.script_paths), 2)

    def test_get_collects_reference_paths(self):
        skill_dir = self._create_test_skill("skill-with-refs", "Has references")
        refs_dir = skill_dir / "references"
        refs_dir.mkdir()
        (refs_dir / "api.md").write_text("# API docs")

        registry = SkillRegistry()
        registry.discover([self.skills_root])
        skill = registry.get("skill-with-refs")
        self.assertEqual(len(skill.reference_paths), 1)


class TestSkillTools(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.skills_root = Path(self.temp_dir.name)
        self._create_test_skill("code-review", "Reviews code for issues")
        self._create_test_skill("file-stats", "Counts lines and words in files")

    def tearDown(self):
        self.temp_dir.cleanup()

    def _create_test_skill(self, name: str, description: str, body: str = "# Instructions\nDo something."):
        skill_dir = self.skills_root / name
        skill_dir.mkdir(parents=True, exist_ok=True)
        (skill_dir / "SKILL.md").write_text(f"---\nname: {name}\ndescription: {description}\n---\n\n{body}\n")
        return skill_dir

    def test_list_available_skills_formats_output(self):
        registry = SkillRegistry()
        registry.discover([self.skills_root])
        output = list_available_skills(registry)
        self.assertIn("code-review:", output)
        self.assertIn("file-stats:", output)
        self.assertIn("Reviews code", output)

    def test_list_available_skills_empty_registry(self):
        registry = SkillRegistry()
        registry.discover([])
        output = list_available_skills(registry)
        self.assertEqual(output, "No skills available.")

    def test_get_skill_instructions_returns_body(self):
        registry = SkillRegistry()
        registry.discover([self.skills_root])
        output = get_skill_instructions(registry, "code-review")
        self.assertIsNotNone(output)
        self.assertIn("Instructions", output)

    def test_get_skill_instructions_returns_none_for_unknown(self):
        registry = SkillRegistry()
        registry.discover([self.skills_root])
        output = get_skill_instructions(registry, "nonexistent")
        self.assertIsNone(output)

    def test_get_skill_instructions_includes_script_paths(self):
        skill_dir = self._create_test_skill("with-scripts", "Has scripts")
        scripts_dir = skill_dir / "scripts"
        scripts_dir.mkdir()
        (scripts_dir / "run.py").write_text("print('hello')")

        registry = SkillRegistry()
        registry.discover([self.skills_root])
        output = get_skill_instructions(registry, "with-scripts")
        self.assertIn("## Scripts", output)
        self.assertIn("run.py", output)

    def test_get_skill_instructions_includes_reference_paths(self):
        skill_dir = self._create_test_skill("with-refs", "Has refs")
        refs_dir = skill_dir / "references"
        refs_dir.mkdir()
        (refs_dir / "api.md").write_text("# API")

        registry = SkillRegistry()
        registry.discover([self.skills_root])
        output = get_skill_instructions(registry, "with-refs")
        self.assertIn("## References", output)
        self.assertIn("api.md", output)


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

        model = ModelMock(responses=[
            ToolCallPart(tool_name="list_skills", args={}),
            ToolCallPart(tool_name="activate_skill", args={"name": "data-analysis"}),
            "I've loaded the data-analysis skill. It helps analyze CSV or JSON files.",
        ])

        agent = Agent(model=model, tools=[list_skills, activate_skill])
        result = await agent.run("What skills are available and how do I analyze data?")

        self.assertIn("data-analysis", result.output)

    async def test_agent_handles_unknown_skill(self):
        """Test that an agent handles requests for unknown skills gracefully."""

        def activate_skill(name: str) -> str:
            """Activate a skill by name and get its instructions."""
            result = get_skill_instructions(self.registry, name)
            return result if result else f"Skill '{name}' not found."

        model = ModelMock(responses=[
            ToolCallPart(tool_name="activate_skill", args={"name": "nonexistent-skill"}),
            "The skill 'nonexistent-skill' was not found.",
        ])

        agent = Agent(model=model, tools=[activate_skill])
        result = await agent.run("Activate the nonexistent-skill")

        self.assertIn("not found", result.output)


if __name__ == "__main__":
    unittest.main()
