"""Tests for the Models.get method in agentic_patterns.core.agents.config."""

import unittest
from pathlib import Path

from agentic_patterns.core.agents.config import BedrockConfig, load_models


TEST_DATA_DIR = Path(__file__).parent.parent / "data" / "agents"


class TestModelsGet(unittest.TestCase):
    """Tests for the Models.get method."""

    def test_get_existing_model(self):
        """Verify Models.get returns config for existing model name."""
        models = load_models(TEST_DATA_DIR / "valid_config.yaml")
        config = models.get("bedrock_model")

        self.assertIsInstance(config, BedrockConfig)
        self.assertEqual(config.aws_region, "us-west-2")

    def test_get_nonexistent_model(self):
        """Verify Models.get raises ValueError for unknown model name."""
        models = load_models(TEST_DATA_DIR / "valid_config.yaml")

        with self.assertRaises(ValueError) as ctx:
            models.get("nonexistent_model")
        self.assertIn("nonexistent_model", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
