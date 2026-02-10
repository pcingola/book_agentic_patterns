import unittest
from pathlib import Path

from agentic_patterns.core.mcp import get_mcp_client, get_mcp_server

TEST_DATA_DIR = Path(__file__).parent.parent / "data" / "mcp"


class TestMCP(unittest.TestCase):
    def test_get_mcp_client_raises_on_server_config(self):
        with self.assertRaises(ValueError) as ctx:
            get_mcp_client("server1", TEST_DATA_DIR / "test_config.yaml")
        self.assertIn("not a client config", str(ctx.exception))

    def test_get_mcp_server_raises_on_client_config(self):
        with self.assertRaises(ValueError) as ctx:
            get_mcp_server("client1", TEST_DATA_DIR / "test_config.yaml")
        self.assertIn("not a server config", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
