import tempfile
import unittest
from pathlib import Path

from agentic_patterns.core.compliance.private_data import DataSensitivity
from agentic_patterns.core.connectors.openapi.api_connection_config import (
    ApiConnectionConfig,
    ApiConnectionConfigs,
)
from agentic_patterns.core.connectors.sql.db_connection_config import (
    DbConnectionConfig,
    DbConnectionConfigs,
)


class TestConnectorSensitivity(unittest.TestCase):
    """Tests for sensitivity field in connector configs."""

    def setUp(self):
        DbConnectionConfigs.reset()
        ApiConnectionConfigs.reset()

    def tearDown(self):
        DbConnectionConfigs.reset()
        ApiConnectionConfigs.reset()

    # -- DbConnectionConfig ---------------------------------------------------

    def test_db_config_defaults_to_public(self):
        config = DbConnectionConfig(db_id="test", type="sqlite")
        self.assertEqual(config.sensitivity, DataSensitivity.PUBLIC)

    def test_db_config_parses_sensitivity_from_yaml(self):
        yaml_content = """
databases:
  patients_db:
    type: sqlite
    dbname: patients.db
    sensitivity: confidential
  public_db:
    type: sqlite
    dbname: public.db
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(yaml_content)
            yaml_path = Path(f.name)

        try:
            configs = DbConnectionConfigs.get()
            configs.load_from_yaml(yaml_path)
            self.assertEqual(
                configs.get_config("patients_db").sensitivity,
                DataSensitivity.CONFIDENTIAL,
            )
            self.assertEqual(
                configs.get_config("public_db").sensitivity, DataSensitivity.PUBLIC
            )
        finally:
            yaml_path.unlink()

    # -- ApiConnectionConfig --------------------------------------------------

    def test_api_config_defaults_to_public(self):
        config = ApiConnectionConfig(
            api_id="test",
            spec_source="http://example.com/spec",
            base_url="http://example.com",
        )
        self.assertEqual(config.sensitivity, DataSensitivity.PUBLIC)

    def test_api_config_parses_sensitivity_from_yaml(self):
        yaml_content = """
apis:
  internal_api:
    spec_source: http://example.com/spec.json
    base_url: http://example.com
    sensitivity: internal
  public_api:
    spec_source: http://example.com/pub.json
    base_url: http://example.com
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(yaml_content)
            yaml_path = Path(f.name)

        try:
            configs = ApiConnectionConfigs()
            configs.load_from_yaml(yaml_path)
            self.assertEqual(
                configs.get_config("internal_api").sensitivity, DataSensitivity.INTERNAL
            )
            self.assertEqual(
                configs.get_config("public_api").sensitivity, DataSensitivity.PUBLIC
            )
        finally:
            yaml_path.unlink()


if __name__ == "__main__":
    unittest.main()
