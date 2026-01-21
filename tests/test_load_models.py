"""Tests for the load_models function in agentic_patterns.core.agents.config."""

import unittest
from pathlib import Path

from agentic_patterns.core.agents.config import (
    AzureConfig,
    BedrockConfig,
    OllamaConfig,
    OpenAIConfig,
    OpenRouterConfig,
    load_models,
)


TEST_DATA_DIR = Path(__file__).parent / "data" / "agents"


class TestLoadModels(unittest.TestCase):
    """Tests for the load_models function."""

    def test_load_valid_config(self):
        """Verify load_models correctly parses all model families from YAML."""
        models = load_models(TEST_DATA_DIR / "valid_config.yaml")

        self.assertIsInstance(models.get("openai_model"), OpenAIConfig)
        self.assertIsInstance(models.get("bedrock_model"), BedrockConfig)
        self.assertIsInstance(models.get("ollama_model"), OllamaConfig)
        self.assertIsInstance(models.get("azure_model"), AzureConfig)
        self.assertIsInstance(models.get("openrouter_model"), OpenRouterConfig)

    def test_load_parses_config_values(self):
        """Verify load_models correctly extracts config field values."""
        models = load_models(TEST_DATA_DIR / "valid_config.yaml")
        openai_config = models.get("openai_model")

        self.assertEqual(openai_config.model_name, "gpt-4")
        self.assertEqual(openai_config.api_key, "test-key")
        self.assertEqual(openai_config.timeout, 60)

    def test_load_file_not_found(self):
        """Verify load_models raises FileNotFoundError for missing files."""
        with self.assertRaises(FileNotFoundError):
            load_models(TEST_DATA_DIR / "nonexistent.yaml")

    def test_load_missing_models_key(self):
        """Verify load_models raises ValueError when 'models' key is missing."""
        with self.assertRaises(ValueError) as ctx:
            load_models(TEST_DATA_DIR / "missing_models_key.yaml")
        self.assertIn("models", str(ctx.exception))

    def test_load_unknown_family(self):
        """Verify load_models raises ValueError for unsupported model_family."""
        with self.assertRaises(ValueError) as ctx:
            load_models(TEST_DATA_DIR / "unknown_family.yaml")
        self.assertIn("unsupported_provider", str(ctx.exception).lower())


if __name__ == "__main__":
    unittest.main()
