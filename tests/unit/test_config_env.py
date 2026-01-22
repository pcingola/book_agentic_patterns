import os
import unittest

from agentic_patterns.core.config.env import get_variable_env


class TestConfigEnv(unittest.TestCase):
    """Tests for agentic_patterns.core.config.env module."""

    def test_get_variable_env_returns_existing_variable(self):
        """Test that get_variable_env returns the value of an existing environment variable."""
        os.environ["TEST_VAR_EXISTS"] = "test_value"
        result = get_variable_env("TEST_VAR_EXISTS")
        self.assertEqual(result, "test_value")
        del os.environ["TEST_VAR_EXISTS"]

    def test_get_variable_env_returns_default_when_not_set(self):
        """Test that get_variable_env returns default value when variable is not set."""
        result = get_variable_env("TEST_VAR_NOT_EXISTS", default="default_value")
        self.assertEqual(result, "default_value")

    def test_get_variable_env_returns_none_when_not_set_no_default(self):
        """Test that get_variable_env returns None when variable is not set and no default."""
        result = get_variable_env("TEST_VAR_NOT_EXISTS_NO_DEFAULT")
        self.assertIsNone(result)

    def test_get_variable_env_raises_when_empty_not_allowed(self):
        """Test that get_variable_env raises ValueError when allow_empty=False and var not set."""
        with self.assertRaises(ValueError) as ctx:
            get_variable_env("TEST_VAR_MUST_EXIST", allow_empty=False)
        self.assertIn("TEST_VAR_MUST_EXIST", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
