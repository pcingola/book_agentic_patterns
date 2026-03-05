"""Pseudonym vault: JSON-backed persistent pseudonym store with normalization."""

import json
import re
from pathlib import Path

from agentic_patterns.core.config.config import DATA_DIR

DEFAULT_VAULT_PATH = DATA_DIR / "anonymization" / "vault.json"


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
    """JSON-backed pseudonym store.

    Maps (label, normalized_value) to opaque LABEL_NNNN tokens. Persists
    mappings to a JSON file so pseudonyms are consistent across runs.
    Name normalization is purely structural (strip punctuation, lowercase,
    sort tokens) so it works across languages. Title stripping ("Dr.", etc.)
    is handled upstream: the LLM audit prompt instructs the model to return
    names without honorifics.
    """

    def __init__(self, path: Path = DEFAULT_VAULT_PATH):
        self._path = path
        self._mappings: dict[str, str] = {}
        self._counters: dict[str, int] = {}
        if path.exists():
            self._mappings = json.loads(path.read_text())
            self._init_counters()

    def pseudonym(self, label: str, value: str) -> str:
        """Return pseudonym for (label, value), creating one if new."""
        key = f"{label}|{self._normalize(label, value)}"
        if key in self._mappings:
            return self._mappings[key]
        prefix = self._prefix(label)
        idx = self._counters.get(prefix, 0) + 1
        self._counters[prefix] = idx
        pseudo = f"{prefix}_{idx:04d}"
        self._mappings[key] = pseudo
        self._save()
        return pseudo

    def _init_counters(self) -> None:
        """Rebuild per-prefix counters from existing mappings (on load)."""
        for pseudo in self._mappings.values():
            prefix, num = pseudo.rsplit("_", 1)
            self._counters[prefix] = max(self._counters.get(prefix, 0), int(num))

    def _normalize(self, label: str, value: str) -> str:
        """Structural normalization: strip punctuation, lowercase, sort tokens for names."""
        clean = value.strip().lower()
        if label.startswith("NAME_"):
            clean = re.sub(r"[,.]", " ", clean)
            clean = " ".join(sorted(clean.split()))
        return clean

    def _prefix(self, label: str) -> str:
        prefix = _LABEL_ALIASES.get(label)
        if not prefix:
            for cat in _CATEGORY_PREFIXES:
                if label.startswith(cat):
                    return label[len(cat) :]
            return label
        return prefix

    def _save(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(json.dumps(self._mappings, indent=2))

    def __str__(self) -> str:
        return f"PseudonymVault({self._path.name}, {len(self._mappings)} mappings)"
