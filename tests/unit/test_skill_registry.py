import tempfile
import unittest
from pathlib import Path

from agentic_patterns.core.skills.registry import SkillRegistry


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

    def test_get_collects_asset_paths(self):
        skill_dir = self._create_test_skill("skill-with-assets", "Has assets")
        assets_dir = skill_dir / "assets"
        assets_dir.mkdir()
        (assets_dir / "template.json").write_text("{}")
        (assets_dir / "schema.yaml").write_text("type: object")

        registry = SkillRegistry()
        registry.discover([self.skills_root])
        skill = registry.get("skill-with-assets")
        self.assertEqual(len(skill.asset_paths), 2)


if __name__ == "__main__":
    unittest.main()
