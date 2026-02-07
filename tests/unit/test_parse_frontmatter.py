import unittest

from agentic_patterns.core.skills.registry import _parse_frontmatter


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


if __name__ == "__main__":
    unittest.main()
