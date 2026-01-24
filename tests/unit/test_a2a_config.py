"""Tests for agentic_patterns.core.a2a.config module."""

import unittest
from pathlib import Path

from agentic_patterns.core.a2a.config import A2AClientConfig, load_a2a_settings
import agentic_patterns.core.a2a.config as config_module


TEST_DATA_DIR = Path(__file__).parent.parent / "data" / "a2a"


class TestA2AConfig(unittest.TestCase):

    def setUp(self):
        config_module._settings = None

    def test_client_config_defaults(self):
        config = A2AClientConfig(url="http://localhost:8000")
        self.assertEqual(config.timeout, 300)
        self.assertEqual(config.poll_interval, 1.0)
        self.assertEqual(config.max_retries, 3)
        self.assertEqual(config.retry_delay, 1.0)

    def test_get_raises_on_missing(self):
        settings = load_a2a_settings(TEST_DATA_DIR / "test_config.yaml")
        with self.assertRaises(ValueError):
            settings.get("nonexistent")

    def test_load_raises_on_missing_file(self):
        with self.assertRaises(FileNotFoundError):
            load_a2a_settings("/nonexistent/config.yaml")


if __name__ == "__main__":
    unittest.main()
