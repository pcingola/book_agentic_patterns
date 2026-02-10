"""Unit tests for API connection configuration."""

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from agentic_patterns.core.connectors.openapi.api_connection_config import (
    ApiConnectionConfig,
    ApiConnectionConfigs,
)


class TestApiConnectionConfig(unittest.TestCase):
    def test_create_config(self):
        config = ApiConnectionConfig(
            api_id="test_api",
            spec_source="https://example.com/openapi.json",
            base_url="https://api.example.com",
        )
        self.assertEqual(config.api_id, "test_api")


class TestApiConnectionConfigs(unittest.TestCase):
    def setUp(self):
        ApiConnectionConfigs.reset()

    def test_singleton(self):
        configs1 = ApiConnectionConfigs.get()
        configs2 = ApiConnectionConfigs.get()
        self.assertIs(configs1, configs2)

    def test_load_from_yaml(self):
        with TemporaryDirectory() as tmpdir:
            yaml_content = """
apis:
  test_api:
    spec_source: https://example.com/openapi.json
    base_url: https://api.example.com
  local_api:
    spec_source: specs/local.yaml
    base_url: http://localhost:8000
"""
            yaml_path = Path(tmpdir) / "apis.yaml"
            yaml_path.write_text(yaml_content)

            configs = ApiConnectionConfigs.get()
            configs.load_from_yaml(yaml_path)

            self.assertEqual(len(configs), 2)
            self.assertIn("test_api", configs.list_api_ids())
            self.assertIn("local_api", configs.list_api_ids())

            test_config = configs.get_config("test_api")
            self.assertEqual(
                test_config.spec_source, "https://example.com/openapi.json"
            )

    def test_env_var_expansion(self):
        import os

        os.environ["TEST_API_URL"] = "https://test.example.com"

        with TemporaryDirectory() as tmpdir:
            yaml_content = """
apis:
  test_api:
    spec_source: ${TEST_API_URL}/openapi.json
    base_url: ${TEST_API_URL}
"""
            yaml_path = Path(tmpdir) / "apis.yaml"
            yaml_path.write_text(yaml_content)

            configs = ApiConnectionConfigs.get()
            configs.load_from_yaml(yaml_path)

            test_config = configs.get_config("test_api")
            self.assertEqual(
                test_config.spec_source, "https://test.example.com/openapi.json"
            )
            self.assertEqual(test_config.base_url, "https://test.example.com")


if __name__ == "__main__":
    unittest.main()
