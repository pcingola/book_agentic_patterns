"""Unit tests for the anonymization toolkit."""

import json
import tempfile
import unittest
from pathlib import Path

from agentic_patterns.toolkits.anonymization.anonymizer import Anonymizer
from agentic_patterns.toolkits.anonymization.detectors import RegexDetector
from agentic_patterns.toolkits.anonymization.models import (
    EntitySpan,
    PhiLabel,
    default_phi_policy,
)
from agentic_patterns.toolkits.anonymization.vault import PseudonymVault

CLINICAL_NOTE = """\
DISCHARGE SUMMARY
Patient: Margaret Thompson
MRN: 4478-2291
SSN: 321-54-9876
Age: 94 y/o
Admission Date: January 10, 2025
Discharge Date: January 17, 2025
Attending: Dr. Rajesh Patel
Phone: (555) 867-5309
"""


def _temp_vault() -> PseudonymVault:
    return PseudonymVault(Path(tempfile.mktemp(suffix=".json")))


class TestAnonymization(unittest.TestCase):
    def test_anonymizer_detect_merges_overlaps(self) -> None:
        regex = RegexDetector()
        anonymizer = Anonymizer([regex], default_phi_policy(), _temp_vault())
        spans = anonymizer.detect(CLINICAL_NOTE)
        sorted_spans = sorted(spans, key=lambda s: s.start)
        for i in range(len(sorted_spans) - 1):
            self.assertLessEqual(sorted_spans[i].end, sorted_spans[i + 1].start)

    def test_anonymizer_redact_tagged(self) -> None:
        spans = [
            EntitySpan(
                start=0, end=4, label=PhiLabel.NAME_PATIENT, score=0.9, source="regex"
            ),
            EntitySpan(
                start=10, end=15, label=PhiLabel.ID_SSN, score=0.9, source="regex"
            ),
        ]
        anonymizer = Anonymizer([], default_phi_policy(), _temp_vault())
        result = anonymizer.redact_tagged("John Smith 321-54-9876 rest", spans)
        self.assertIn("[NAME_PATIENT]", result)
        self.assertIn("[ID_SSN]", result)
        self.assertNotIn("John", result)

    def test_anonymizer_run_pseudonymizes(self) -> None:
        regex = RegexDetector()
        anonymizer = Anonymizer([regex], default_phi_policy(), _temp_vault())
        result = anonymizer.run(CLINICAL_NOTE)
        self.assertNotIn("321-54-9876", result.redacted_text)
        self.assertNotIn("4478-2291", result.redacted_text)
        self.assertNotIn("(555) 867-5309", result.redacted_text)
        self.assertRegex(result.redacted_text, r"SSN_\d{4}")
        self.assertRegex(result.redacted_text, r"MRN_\d{4}")

    def test_date_shift_epoch_remapping(self) -> None:
        """Earliest date maps to 2000-01-01, intervals are preserved."""
        regex = RegexDetector()
        anonymizer = Anonymizer([regex], default_phi_policy(), _temp_vault())
        result = anonymizer.run(CLINICAL_NOTE)
        self.assertIn("January 01, 2000", result.redacted_text)
        self.assertIn("January 08, 2000", result.redacted_text)
        self.assertNotIn("2025", result.redacted_text)

    def test_regex_detector_finds_phi(self) -> None:
        detector = RegexDetector()
        spans = detector.detect(CLINICAL_NOTE)
        labels_found = {s.label for s in spans}
        self.assertIn(PhiLabel.ID_MEDICALRECORD, labels_found)
        self.assertIn(PhiLabel.ID_SSN, labels_found)
        self.assertIn(PhiLabel.CONTACT_PHONE, labels_found)
        self.assertIn(PhiLabel.DATE, labels_found)
        self.assertIn(PhiLabel.AGE, labels_found)

    def test_vault_pseudonym_consistency(self) -> None:
        vault = _temp_vault()
        p1 = vault.pseudonym("NAME_PATIENT", "John Smith")
        p2 = vault.pseudonym("NAME_PATIENT", "John Smith")
        self.assertEqual(p1, p2)
        p3 = vault.pseudonym("NAME_PATIENT", "Jane Doe")
        self.assertNotEqual(p1, p3)

    def test_vault_pseudonym_format(self) -> None:
        vault = _temp_vault()
        cases = [
            ("NAME_PATIENT", "John Smith", r"PATIENT_\d{4}"),
            ("NAME_DOCTOR", "Dr. Lee", r"DOCTOR_\d{4}"),
            ("ID_SSN", "123-45-6789", r"SSN_\d{4}"),
            ("ID_MEDICALRECORD", "4478-2291", r"MRN_\d{4}"),
            ("CONTACT_PHONE", "(555) 867-5309", r"PHONE_\d{4}"),
            ("CONTACT_EMAIL", "a@b.com", r"EMAIL_\d{4}"),
            ("LOCATION_CITY", "Springfield", r"CITY_\d{4}"),
            ("LOCATION_HOSPITAL", "General Hospital", r"HOSPITAL_\d{4}"),
            ("AGE", "94 y/o", r"AGE_\d{4}"),
            ("PROFESSION", "Engineer", r"PROFESSION_\d{4}"),
        ]
        for label, value, pattern in cases:
            with self.subTest(label=label):
                result = vault.pseudonym(label, value)
                self.assertRegex(result, f"^{pattern}$", f"{label}: {result}")

    def test_vault_name_normalization(self) -> None:
        """Structural normalization: punctuation, case, token order."""
        vault = _temp_vault()
        p1 = vault.pseudonym("NAME_DOCTOR", "Rajesh Patel")
        p2 = vault.pseudonym("NAME_DOCTOR", "Patel, Rajesh")
        p3 = vault.pseudonym("NAME_DOCTOR", "rajesh patel")
        self.assertEqual(p1, p2)
        self.assertEqual(p2, p3)

    def test_vault_persistence(self) -> None:
        """Vault loaded from existing JSON returns the same pseudonyms."""
        path = Path(tempfile.mktemp(suffix=".json"))
        vault1 = PseudonymVault(path)
        p1 = vault1.pseudonym("NAME_PATIENT", "Margaret Thompson")
        vault2 = PseudonymVault(path)
        p2 = vault2.pseudonym("NAME_PATIENT", "Margaret Thompson")
        self.assertEqual(p1, p2)
        self.assertTrue(path.exists())
        data = json.loads(path.read_text())
        self.assertEqual(len(data), 1)
