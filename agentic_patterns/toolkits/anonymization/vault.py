"""Pseudonym vault: deterministic HMAC-based opaque pseudonyms and per-patient date shifting."""

import hashlib
import hmac
from datetime import date, timedelta


# Category prefixes to strip for short readable labels
_CATEGORY_PREFIXES = ("NAME_", "ID_", "CONTACT_", "LOCATION_")

# Short aliases for specific labels
_LABEL_ALIASES: dict[str, str] = {
    "ID_MEDICALRECORD": "MRN",
    "ID_SSN": "SSN",
    "ID_HEALTHPLAN": "HEALTHPLAN",
    "ID_ACCOUNT": "ACCOUNT",
    "ID_LICENSE": "LICENSE",
    "ID_VEHICLE": "VEHICLE",
    "ID_DEVICE": "DEVICE",
    "ID_BIOID": "BIOID",
    "ID_IDNUM": "IDNUM",
    "CONTACT_PHONE": "PHONE",
    "CONTACT_FAX": "FAX",
    "CONTACT_EMAIL": "EMAIL",
    "CONTACT_URL": "URL",
    "CONTACT_IPADDR": "IPADDR",
    "NAME_PATIENT": "PATIENT",
    "NAME_DOCTOR": "DOCTOR",
    "NAME_USERNAME": "USERNAME",
    "LOCATION_HOSPITAL": "HOSPITAL",
    "LOCATION_ORGANIZATION": "ORG",
    "LOCATION_STREET": "STREET",
    "LOCATION_CITY": "CITY",
    "LOCATION_STATE": "STATE",
    "LOCATION_COUNTRY": "COUNTRY",
    "LOCATION_ZIP": "ZIP",
    "LOCATION_OTHER": "LOCATION",
}


class PseudonymVault:
    """HMAC-SHA256 based pseudonym generator with deterministic date shifting.

    Produces opaque identifiers (LABEL_NNNN) deterministically so the same
    input always maps to the same pseudonym.
    """

    def __init__(self, secret: str = "default-vault-secret"):
        self._secret = secret.encode()

    def _hmac(self, *parts: str) -> str:
        msg = "|".join(parts).encode()
        return hmac.new(self._secret, msg, hashlib.sha256).hexdigest()

    def date_offset(self, patient_id: str, max_days: int = 30) -> int:
        """Deterministic per-patient day offset derived from HMAC. Always non-zero."""
        h = self._hmac("date_shift", patient_id)
        raw = int(h[:8], 16) % (2 * max_days) - max_days
        return raw if raw != 0 else 1

    def pseudonym(self, label: str, value: str) -> str:
        """Deterministic opaque pseudonym for a (label, value) pair.

        Returns LABEL_NNNN where LABEL is a short readable prefix and NNNN
        is an HMAC-derived index mod 10000.
        """
        h = self._hmac("pseudo", label, value)
        index = int(h[:8], 16) % 10000
        prefix = _LABEL_ALIASES.get(label)
        if not prefix:
            for cat in _CATEGORY_PREFIXES:
                if label.startswith(cat):
                    prefix = label[len(cat) :]
                    break
            else:
                prefix = label
        return f"{prefix}_{index:04d}"

    def shift_date(self, d: date, patient_id: str, max_days: int = 30) -> date:
        """Shift a date by the patient's deterministic offset (preserves intervals)."""
        offset = self.date_offset(patient_id, max_days)
        return d + timedelta(days=offset)

    def __str__(self) -> str:
        return "PseudonymVault()"
