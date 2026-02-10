import unittest
from pathlib import Path

from agentic_patterns.core.skills.models import SkillMetadata


class TestSkillMetadata(unittest.TestCase):
    def test_str_representation(self):
        meta = SkillMetadata(
            name="test-skill", description="A test skill", path=Path("/tmp/test")
        )
        self.assertEqual(str(meta), "test-skill: A test skill")


if __name__ == "__main__":
    unittest.main()
