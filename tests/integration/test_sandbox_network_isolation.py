"""Integration tests for sandbox network isolation with PrivateData.

Requires Docker to be running.
"""

import shutil
import unittest
import uuid

from agentic_patterns.core.compliance.private_data import DataSensitivity, PrivateData
from agentic_patterns.core.config.config import PRIVATE_DATA_DIR, WORKSPACE_DIR
from agentic_patterns.core.sandbox.manager import SandboxManager
from agentic_patterns.core.sandbox.network_mode import NetworkMode


class TestSandboxNetworkIsolation(unittest.TestCase):
    def setUp(self):
        self.user_id = f"test-user-{uuid.uuid4().hex[:8]}"
        self.session_id = f"test-session-{uuid.uuid4().hex[:8]}"
        self.manager = SandboxManager()

    def tearDown(self):
        self.manager.close_session(self.user_id, self.session_id)
        # Clean up private data files
        pd_dir = PRIVATE_DATA_DIR / self.user_id
        if pd_dir.exists():
            shutil.rmtree(pd_dir)
        # Clean up workspace dir
        ws_dir = WORKSPACE_DIR / self.user_id
        if ws_dir.exists():
            shutil.rmtree(ws_dir)

    def test_session_without_private_data_has_full_network(self):
        session = self.manager.get_or_create_session(self.user_id, self.session_id)

        self.assertEqual(session.network_mode, NetworkMode.FULL)

    def test_session_with_private_data_has_no_network(self):
        pd = PrivateData(self.user_id, self.session_id)
        pd.add_private_dataset("secret_table", DataSensitivity.CONFIDENTIAL)

        session = self.manager.get_or_create_session(self.user_id, self.session_id)

        self.assertEqual(session.network_mode, NetworkMode.NONE)

    def test_execute_command_returns_output(self):
        exit_code, output = self.manager.execute_command(
            self.user_id, self.session_id, "echo hello"
        )

        self.assertEqual(exit_code, 0)
        self.assertIn("hello", output)

    def test_network_none_blocks_outbound(self):
        pd = PrivateData(self.user_id, self.session_id)
        pd.add_private_dataset("patients", DataSensitivity.SECRET)

        # ping should fail immediately with no network interfaces
        exit_code, _ = self.manager.execute_command(
            self.user_id, self.session_id, "ping -c 1 -W 1 8.8.8.8"
        )

        self.assertNotEqual(exit_code, 0)

    def test_ratchet_recreates_container_on_private_data(self):
        session = self.manager.get_or_create_session(self.user_id, self.session_id)
        self.assertEqual(session.network_mode, NetworkMode.FULL)
        original_container_id = session.container_id

        # Tag session as private mid-conversation
        pd = PrivateData(self.user_id, self.session_id)
        pd.add_private_dataset("financials", DataSensitivity.CONFIDENTIAL)

        # Next call detects mismatch and recreates
        session = self.manager.get_or_create_session(self.user_id, self.session_id)

        self.assertEqual(session.network_mode, NetworkMode.NONE)
        self.assertNotEqual(session.container_id, original_container_id)

    def test_workspace_survives_container_recreation(self):
        # Write a file in the workspace
        self.manager.execute_command(
            self.user_id, self.session_id, "echo 'important data' > /workspace/test.txt"
        )
        session = self.manager.get_or_create_session(self.user_id, self.session_id)
        original_container_id = session.container_id

        # Trigger recreation via private data
        pd = PrivateData(self.user_id, self.session_id)
        pd.add_private_dataset("records", DataSensitivity.CONFIDENTIAL)
        session = self.manager.get_or_create_session(self.user_id, self.session_id)
        self.assertNotEqual(session.container_id, original_container_id)

        # File should still be there in the new container
        exit_code, output = self.manager.execute_command(
            self.user_id, self.session_id, "cat /workspace/test.txt"
        )

        self.assertEqual(exit_code, 0)
        self.assertIn("important data", output)

    def test_close_session_removes_container(self):
        session = self.manager.get_or_create_session(self.user_id, self.session_id)
        container_id = session.container_id

        self.manager.close_session(self.user_id, self.session_id)

        # Container should be gone
        import docker

        client = docker.from_env()
        with self.assertRaises(docker.errors.NotFound):
            client.containers.get(container_id)


if __name__ == "__main__":
    unittest.main()
