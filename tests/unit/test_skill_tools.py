import tempfile
import unittest
from pathlib import Path

from agentic_patterns.core.skills.registry import SkillRegistry
from agentic_patterns.core.skills.tools import (
    get_skill_instructions,
    list_available_skills,
)


class TestSkillTools(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.skills_root = Path(self.temp_dir.name)
        self._create_test_skill("code-review", "Reviews code for issues")
        self._create_test_skill("file-stats", "Counts lines and words in files")

    def tearDown(self):
        self.temp_dir.cleanup()

    def _create_test_skill(
        self, name: str, description: str, body: str = "# Instructions\nDo something."
    ):
        skill_dir = self.skills_root / name
        skill_dir.mkdir(parents=True, exist_ok=True)
        (skill_dir / "SKILL.md").write_text(
            f"---\nname: {name}\ndescription: {description}\n---\n\n{body}\n"
        )
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

    def test_get_skill_instructions_returns_only_body(self):
        """Per spec, activation returns only the body (tier 2). Resources are tier 3."""
        skill_dir = self._create_test_skill(
            "with-scripts", "Has scripts", body="# Main Instructions"
        )
        scripts_dir = skill_dir / "scripts"
        scripts_dir.mkdir()
        (scripts_dir / "run.py").write_text("print('hello')")

        registry = SkillRegistry()
        registry.discover([self.skills_root])
        output = get_skill_instructions(registry, "with-scripts")
        self.assertIn("Main Instructions", output)
        self.assertNotIn("## Scripts", output)
        self.assertNotIn("run.py", output)


if __name__ == "__main__":
    unittest.main()
