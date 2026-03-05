"""PHI detectors: regex-based and generic NER wrapper."""

import re
from collections.abc import Callable

from agentic_patterns.toolkits.anonymization.models import EntitySpan, PhiLabel


# -- Regex patterns for structured clinical PHI --

_PATTERNS: list[tuple[str, PhiLabel]] = [
    # MRN (common prefixes)
    (
        r"(?i)\b(?:MRN|Medical Record(?:\s*#)?|Med\s*Rec(?:\s*#)?)\s*[:#]?\s*(\d[\d\-]{4,})",
        PhiLabel.ID_MEDICALRECORD,
    ),
    # SSN
    (r"\b\d{3}-\d{2}-\d{4}\b", PhiLabel.ID_SSN),
    # Phone / Fax
    (r"(?:\+?1[\s.-]?)?\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4}", PhiLabel.CONTACT_PHONE),
    (r"(?i)\bfax\s*[:#]?\s*\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4}", PhiLabel.CONTACT_FAX),
    # Email
    (r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b", PhiLabel.CONTACT_EMAIL),
    # URL
    (r"https?://[^\s<>\"']+", PhiLabel.CONTACT_URL),
    # IP address
    (r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b", PhiLabel.CONTACT_IPADDR),
    # ZIP (5-digit or 5+4)
    (r"\b\d{5}(?:-\d{4})?\b", PhiLabel.LOCATION_ZIP),
    # Dates: MM/DD/YYYY, MM-DD-YYYY, Month DD YYYY, YYYY-MM-DD
    (r"\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b", PhiLabel.DATE),
    (r"\b\d{4}-\d{2}-\d{2}\b", PhiLabel.DATE),
    (
        r"\b(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{4}\b",
        PhiLabel.DATE,
    ),
    (
        r"\b\d{1,2}\s+(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{4}\b",
        PhiLabel.DATE,
    ),
    # Age > 89
    (
        r"\b(?:age[d]?\s*[:#]?\s*)?(?:9\d|[1-9]\d{2,})\s*(?:year|yr|y/?o)\b",
        PhiLabel.AGE,
    ),
]


class RegexDetector:
    """Detects PHI using regex patterns for structured clinical data."""

    def __init__(self, extra_patterns: list[tuple[str, PhiLabel]] | None = None):
        self._patterns = _PATTERNS + (extra_patterns or [])
        self._compiled = [(re.compile(p), label) for p, label in self._patterns]

    def detect(self, text: str, meta: dict | None = None) -> list[EntitySpan]:
        spans: list[EntitySpan] = []
        for regex, label in self._compiled:
            for m in regex.finditer(text):
                # If there's a capturing group, use it; otherwise use the full match
                if m.lastindex:
                    start, end = m.start(m.lastindex), m.end(m.lastindex)
                else:
                    start, end = m.start(), m.end()
                spans.append(
                    EntitySpan(
                        start=start, end=end, label=label, score=0.9, source="regex"
                    )
                )
        return spans

    def __str__(self) -> str:
        return f"RegexDetector(patterns={len(self._patterns)})"


class NerDetector:
    """Protocol-based NER detector shell. Wraps any callable that returns spans."""

    def __init__(
        self,
        ner_fn: Callable[[str, dict | None], list[tuple[int, int, str, float]]],
        label_map: dict[str, PhiLabel],
        source: str = "ner",
    ):
        self._ner_fn = ner_fn
        self._label_map = label_map
        self._source = source

    def detect(self, text: str, meta: dict | None = None) -> list[EntitySpan]:
        raw = self._ner_fn(text, meta)
        spans: list[EntitySpan] = []
        for start, end, raw_label, score in raw:
            label = self._label_map.get(raw_label)
            if label:
                spans.append(
                    EntitySpan(
                        start=start,
                        end=end,
                        label=label,
                        score=score,
                        source=self._source,
                    )
                )
        return spans

    def __str__(self) -> str:
        return f"NerDetector(source={self._source}, labels={len(self._label_map)})"
