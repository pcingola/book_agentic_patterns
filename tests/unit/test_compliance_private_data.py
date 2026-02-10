import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from agentic_patterns.core.compliance.private_data import (
    DataSensitivity,
    PRIVATE_DATA_FILENAME,
    PrivateData,
    mark_session_private,
    session_has_private_data,
)
from agentic_patterns.core.user_session import set_user_session


class TestPrivateData(unittest.TestCase):
    """Tests for agentic_patterns.core.compliance.private_data module."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.workspace_dir = Path(self.temp_dir.name)
        self.patcher = patch(
            "agentic_patterns.core.compliance.private_data.PRIVATE_DATA_DIR",
            self.workspace_dir,
        )
        self.patcher.start()
        set_user_session("test_user", "test_session")

    def tearDown(self):
        self.patcher.stop()
        self.temp_dir.cleanup()

    def _private_data_path(self) -> Path:
        return self.workspace_dir / "test_user" / "test_session" / PRIVATE_DATA_FILENAME

    # -- basic flag -----------------------------------------------------------

    def test_new_session_has_no_private_data(self):
        pd = PrivateData()
        self.assertFalse(pd.has_private_data)
        self.assertEqual(pd.get_private_datasets(), [])

    def test_set_private_data_flag_persists_to_disk(self):
        pd = PrivateData()
        pd.has_private_data = True
        self.assertTrue(self._private_data_path().exists())
        data = json.loads(self._private_data_path().read_text())
        self.assertTrue(data["has_private_data"])

    def test_clear_private_data_deletes_file(self):
        pd = PrivateData()
        pd.has_private_data = True
        self.assertTrue(self._private_data_path().exists())
        pd.has_private_data = False
        self.assertFalse(self._private_data_path().exists())

    def test_clear_private_data_resets_datasets(self):
        pd = PrivateData()
        pd.add_private_dataset("patients")
        pd.has_private_data = False
        self.assertEqual(pd.get_private_datasets(), [])

    # -- dataset management ---------------------------------------------------

    def test_add_private_dataset_sets_flag(self):
        pd = PrivateData()
        pd.add_private_dataset("patients")
        self.assertTrue(pd.has_private_data)
        self.assertTrue(pd.has_private_dataset("patients"))
        self.assertEqual(pd.get_private_datasets(), ["patients"])

    def test_add_private_dataset_is_idempotent(self):
        pd = PrivateData()
        pd.add_private_dataset("patients")
        pd.add_private_dataset("patients")
        self.assertEqual(pd.get_private_datasets(), ["patients"])

    def test_multiple_datasets(self):
        pd = PrivateData()
        pd.add_private_dataset("patients")
        pd.add_private_dataset("financials")
        self.assertEqual(len(pd.get_private_datasets()), 2)
        self.assertTrue(pd.has_private_dataset("patients"))
        self.assertTrue(pd.has_private_dataset("financials"))

    def test_get_private_datasets_returns_copy(self):
        pd = PrivateData()
        pd.add_private_dataset("patients")
        datasets = pd.get_private_datasets()
        datasets.append("tampered")
        self.assertEqual(pd.get_private_datasets(), ["patients"])

    # -- sensitivity ----------------------------------------------------------

    def test_default_sensitivity_is_confidential(self):
        pd = PrivateData()
        self.assertEqual(pd.sensitivity, DataSensitivity.CONFIDENTIAL)

    def test_sensitivity_escalates_to_highest(self):
        pd = PrivateData()
        pd.add_private_dataset("internal_docs", DataSensitivity.INTERNAL)
        pd.add_private_dataset("passwords", DataSensitivity.SECRET)
        self.assertEqual(pd.sensitivity, DataSensitivity.SECRET)

    def test_sensitivity_does_not_downgrade(self):
        pd = PrivateData()
        pd.add_private_dataset("passwords", DataSensitivity.SECRET)
        pd.add_private_dataset("public_stuff", DataSensitivity.PUBLIC)
        self.assertEqual(pd.sensitivity, DataSensitivity.SECRET)

    # -- persistence round-trip -----------------------------------------------

    def test_save_and_load_round_trip(self):
        pd = PrivateData()
        pd.add_private_dataset("patients", DataSensitivity.SECRET)
        pd.add_private_dataset("financials")

        pd2 = PrivateData()
        self.assertTrue(pd2.has_private_data)
        self.assertEqual(pd2.get_private_datasets(), ["patients", "financials"])
        self.assertEqual(pd2.sensitivity, DataSensitivity.SECRET)

    # -- session isolation ----------------------------------------------------

    def test_different_sessions_are_isolated(self):
        pd = PrivateData(user_id="alice", session_id="s1")
        pd.has_private_data = True

        pd2 = PrivateData(user_id="alice", session_id="s2")
        self.assertFalse(pd2.has_private_data)

    # -- module-level helpers -------------------------------------------------

    def test_mark_session_private(self):
        pd = mark_session_private()
        self.assertTrue(pd.has_private_data)
        # calling again is idempotent
        pd2 = mark_session_private()
        self.assertTrue(pd2.has_private_data)

    def test_session_has_private_data_false_by_default(self):
        self.assertFalse(session_has_private_data())

    def test_session_has_private_data_true_after_marking(self):
        mark_session_private()
        self.assertTrue(session_has_private_data())


if __name__ == "__main__":
    unittest.main()
