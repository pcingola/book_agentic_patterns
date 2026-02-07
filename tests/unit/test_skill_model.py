import unittest
from pathlib import Path

from agentic_patterns.core.skills.models import Skill


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
            asset_paths=[],
        )
        self.assertEqual(str(skill), "Skill(test-skill)")


if __name__ == "__main__":
    unittest.main()
