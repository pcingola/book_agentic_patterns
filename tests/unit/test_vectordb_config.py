import os
import unittest
from pathlib import Path

from agentic_patterns.core.vectordb.config import (
    ChromaVectorDBConfig,
    OllamaEmbeddingConfig,
    OpenAIEmbeddingConfig,
    PgVectorDBConfig,
    SentenceTransformersEmbeddingConfig,
    _expand_config_vars,
    _expand_env_vars,
    load_vectordb_settings,
)

TEST_DATA_DIR = Path(__file__).parent.parent / "data" / "vectordb"


class TestVectorDBConfig(unittest.TestCase):
    """Tests for agentic_patterns.core.vectordb.config module."""

    def test_expand_env_vars_replaces_variable(self):
        """Test that ${VAR} patterns are replaced with env values."""
        os.environ["TEST_VAR"] = "hello"
        result = _expand_env_vars("prefix_${TEST_VAR}_suffix")
        self.assertEqual(result, "prefix_hello_suffix")
        del os.environ["TEST_VAR"]

    def test_expand_env_vars_missing_keeps_pattern(self):
        """Test that missing env vars keep the original ${VAR} pattern."""
        result = _expand_env_vars("${NONEXISTENT_VAR_12345}")
        self.assertEqual(result, "${NONEXISTENT_VAR_12345}")

    def test_expand_config_vars_recursive(self):
        """Test that _expand_config_vars works recursively on nested dicts."""
        os.environ["TEST_NESTED"] = "value"
        config = {"level1": {"level2": "${TEST_NESTED}"}, "simple": "no_vars"}
        result = _expand_config_vars(config)
        self.assertEqual(result["level1"]["level2"], "value")
        self.assertEqual(result["simple"], "no_vars")
        del os.environ["TEST_NESTED"]

    def test_load_vectordb_settings_parses_embeddings(self):
        """Test that load_vectordb_settings correctly parses embedding configs."""
        settings = load_vectordb_settings(TEST_DATA_DIR / "test_config.yaml")
        self.assertEqual(len(settings.embeddings), 3)
        self.assertIsInstance(settings.get_embedding("default"), OpenAIEmbeddingConfig)
        self.assertIsInstance(settings.get_embedding("ollama"), OllamaEmbeddingConfig)
        self.assertIsInstance(settings.get_embedding("sentence"), SentenceTransformersEmbeddingConfig)

    def test_load_vectordb_settings_parses_vectordb(self):
        """Test that load_vectordb_settings correctly parses vectordb configs."""
        settings = load_vectordb_settings(TEST_DATA_DIR / "test_config.yaml")
        self.assertEqual(len(settings.vectordb), 2)
        self.assertIsInstance(settings.get_vectordb("default"), ChromaVectorDBConfig)
        self.assertIsInstance(settings.get_vectordb("pgvector"), PgVectorDBConfig)

    def test_load_vectordb_settings_expands_env_vars(self):
        """Test that load_vectordb_settings expands environment variables."""
        os.environ["TEST_EMBEDDING_MODEL"] = "test-model"
        os.environ["TEST_API_KEY"] = "secret-key"
        os.environ["TEST_PERSIST_DIR"] = "/tmp/test"
        settings = load_vectordb_settings(TEST_DATA_DIR / "test_config_env.yaml")
        emb = settings.get_embedding("default")
        self.assertEqual(emb.model_name, "test-model")
        self.assertEqual(emb.api_key, "secret-key")
        vdb = settings.get_vectordb("default")
        self.assertEqual(vdb.persist_directory, "/tmp/test")
        del os.environ["TEST_EMBEDDING_MODEL"]
        del os.environ["TEST_API_KEY"]
        del os.environ["TEST_PERSIST_DIR"]

    def test_get_embedding_raises_on_missing(self):
        """Test that get_embedding raises ValueError for unknown config name."""
        settings = load_vectordb_settings(TEST_DATA_DIR / "test_config.yaml")
        with self.assertRaises(ValueError) as ctx:
            settings.get_embedding("nonexistent")
        self.assertIn("nonexistent", str(ctx.exception))

    def test_get_vectordb_raises_on_missing(self):
        """Test that get_vectordb raises ValueError for unknown config name."""
        settings = load_vectordb_settings(TEST_DATA_DIR / "test_config.yaml")
        with self.assertRaises(ValueError) as ctx:
            settings.get_vectordb("nonexistent")
        self.assertIn("nonexistent", str(ctx.exception))

    def test_load_vectordb_settings_raises_on_missing_file(self):
        """Test that load_vectordb_settings raises FileNotFoundError for missing file."""
        with self.assertRaises(FileNotFoundError):
            load_vectordb_settings("/nonexistent/path/config.yaml")


if __name__ == "__main__":
    unittest.main()
