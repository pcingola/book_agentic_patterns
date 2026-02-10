"""Integration tests for sandbox read-only mounts and skill script execution.

Requires Docker to be running.
"""

import shutil
import tempfile
import unittest
import uuid
from pathlib import Path

from agentic_patterns.core.config.config import WORKSPACE_DIR
from agentic_patterns.core.sandbox.manager import SandboxManager
from agentic_patterns.core.skills.registry import SkillRegistry
from agentic_patterns.core.skills.tools import run_skill_script


class TestSandboxReadOnlyMounts(unittest.TestCase):
    def setUp(self):
        self.user_id = f"test-user-{uuid.uuid4().hex[:8]}"
        self.session_id = f"test-session-{uuid.uuid4().hex[:8]}"

        self.temp_dir = tempfile.TemporaryDirectory()
        self.skills_root = Path(self.temp_dir.name)

        skill_dir = self.skills_root / "my-skill"
        skill_dir.mkdir(parents=True)
        (skill_dir / "SKILL.md").write_text(
            "---\nname: my-skill\ndescription: A test skill\n---\n\n# Body\n"
        )
        scripts_dir = skill_dir / "scripts"
        scripts_dir.mkdir()
        (scripts_dir / "hello.py").write_text("print('hello from skill')")
        (scripts_dir / "greet.sh").write_text('#!/bin/bash\necho "hi $1"')
        (scripts_dir / "args.py").write_text(
            "import sys; print(' '.join(sys.argv[1:]))"
        )

        self.registry = SkillRegistry()
        self.registry.discover([self.skills_root])

        self.manager = SandboxManager(
            read_only_mounts={
                str(skill_dir): "/skills/my-skill",
            }
        )

    def tearDown(self):
        self.manager.close_session(self.user_id, self.session_id)
        ws_dir = WORKSPACE_DIR / self.user_id
        if ws_dir.exists():
            shutil.rmtree(ws_dir)
        self.temp_dir.cleanup()

    def test_mounted_file_is_readable_inside_container(self):
        exit_code, output = self.manager.execute_command(
            self.user_id, self.session_id, "cat /skills/my-skill/scripts/hello.py"
        )
        self.assertEqual(exit_code, 0)
        self.assertIn("hello from skill", output)

    def test_mounted_file_is_read_only(self):
        exit_code, _ = self.manager.execute_command(
            self.user_id, self.session_id, "touch /skills/my-skill/scripts/new_file.py"
        )
        self.assertNotEqual(exit_code, 0)

    def test_run_skill_script_python(self):
        exit_code, output = run_skill_script(
            self.manager,
            self.registry,
            self.user_id,
            self.session_id,
            "my-skill",
            "hello.py",
        )
        self.assertEqual(exit_code, 0)
        self.assertIn("hello from skill", output)

    def test_run_skill_script_shell(self):
        exit_code, output = run_skill_script(
            self.manager,
            self.registry,
            self.user_id,
            self.session_id,
            "my-skill",
            "greet.sh",
            "world",
        )
        self.assertEqual(exit_code, 0)
        self.assertIn("hi world", output)

    def test_run_skill_script_with_args(self):
        exit_code, output = run_skill_script(
            self.manager,
            self.registry,
            self.user_id,
            self.session_id,
            "my-skill",
            "args.py",
            "foo bar",
        )
        self.assertEqual(exit_code, 0)
        self.assertIn("foo bar", output)

    def test_run_skill_script_unknown_skill(self):
        exit_code, output = run_skill_script(
            self.manager,
            self.registry,
            self.user_id,
            self.session_id,
            "nonexistent",
            "run.py",
        )
        self.assertEqual(exit_code, 1)
        self.assertIn("not found", output)

    def test_run_skill_script_unknown_script(self):
        exit_code, output = run_skill_script(
            self.manager,
            self.registry,
            self.user_id,
            self.session_id,
            "my-skill",
            "missing.py",
        )
        self.assertEqual(exit_code, 1)
        self.assertIn("not found", output)


if __name__ == "__main__":
    unittest.main()
