"""Core anonymization engine: detection, merging, and redaction."""

import re
from datetime import date, datetime

from agentic_patterns.toolkits.anonymization.models import (
    AnonymizationPolicy,
    AnonymizationResult,
    Detector,
    EntitySpan,
    Operator,
    PhiLabel,
)
from agentic_patterns.toolkits.anonymization.vault import PseudonymVault


# Unicode full-block character for masking
_MASK_CHAR = "\u2588"

# Date formats to try when parsing, ordered by specificity
_DATE_FORMATS = [
    ("%B %d, %Y", True),  # January 15, 2024
    ("%B %d %Y", True),  # January 15 2024
    ("%d %B %Y", True),  # 15 January 2024
    ("%Y-%m-%d", False),  # 2024-01-15
    ("%m/%d/%Y", False),  # 01/15/2024
    ("%m-%d-%Y", False),  # 01-15-2024
    ("%m/%d/%y", False),  # 01/15/24
    ("%m-%d-%y", False),  # 01-15-24
]


def _merge_spans(spans: list[EntitySpan]) -> list[EntitySpan]:
    """Merge overlapping spans, keeping the higher-scored one on overlap."""
    if not spans:
        return []
    sorted_spans = sorted(spans, key=lambda s: (s.start, -s.score))
    merged: list[EntitySpan] = [sorted_spans[0]]
    for span in sorted_spans[1:]:
        prev = merged[-1]
        if span.start < prev.end:
            # Overlapping -- keep the one with higher score
            if span.score > prev.score:
                merged[-1] = span
        else:
            merged.append(span)
    return merged


def _parse_date(text: str) -> tuple[date, str] | None:
    """Try to parse a date string, returning (date, format_string) or None."""
    clean = text.strip().rstrip(",")
    for fmt, _ in _DATE_FORMATS:
        try:
            dt = datetime.strptime(clean, fmt)
            return dt.date(), fmt
        except ValueError:
            continue
    return None


class Anonymizer:
    """Detects PHI spans and applies redaction operators."""

    def __init__(
        self,
        detectors: list[Detector],
        policy: AnonymizationPolicy,
        vault: PseudonymVault | None = None,
    ):
        self._detectors = detectors
        self._policy = policy
        self._vault = vault or PseudonymVault()

    def detect(self, text: str, meta: dict | None = None) -> list[EntitySpan]:
        """Run all detectors, merge overlaps, filter by policy."""
        all_spans: list[EntitySpan] = []
        for detector in self._detectors:
            all_spans.extend(detector.detect(text, meta))

        # Filter by min_score and allowlist
        filtered = [
            s
            for s in all_spans
            if s.score >= self._policy.min_score
            and text[s.start : s.end] not in self._policy.allowlist
        ]
        return _merge_spans(filtered)

    def redact(
        self, text: str, spans: list[EntitySpan], meta: dict | None = None
    ) -> str:
        """Apply redaction operators to text, right-to-left to preserve offsets."""
        meta = meta or {}
        patient_id = meta.get("patient_id") or self._extract_patient_id(text, spans)

        # Sort right-to-left so replacements don't shift earlier offsets
        for span in sorted(spans, key=lambda s: s.start, reverse=True):
            original = text[span.start : span.end]
            spec = self._policy.get_operator(span.label)
            replacement = self._apply_operator(
                spec.operator, span.label, original, patient_id, spec.params
            )
            text = text[: span.start] + replacement + text[span.end :]
        return text

    def redact_tagged(self, text: str, spans: list[EntitySpan]) -> str:
        """Replace spans with [LABEL] tags. Used to produce audit-safe text."""
        for span in sorted(spans, key=lambda s: s.start, reverse=True):
            text = text[: span.start] + f"[{span.label.value}]" + text[span.end :]
        return text

    def run(self, text: str, meta: dict | None = None) -> AnonymizationResult:
        """Full pipeline: detect + redact."""
        spans = self.detect(text, meta)
        redacted = self.redact(text, spans, meta)
        return AnonymizationResult(
            original_text=text, redacted_text=redacted, detection_spans=spans
        )

    def _apply_operator(
        self,
        operator: Operator,
        label: PhiLabel,
        original: str,
        patient_id: str,
        params: dict,
    ) -> str:
        match operator:
            case Operator.MASK:
                return _MASK_CHAR * len(original)
            case Operator.TAG:
                return f"[{label.value}]"
            case Operator.PSEUDONYM:
                return self._vault.pseudonym(label.value, original)
            case Operator.DATE_SHIFT:
                return self._shift_date_text(
                    original, patient_id, params.get("max_days", 30)
                )

    def _extract_patient_id(self, text: str, spans: list[EntitySpan]) -> str:
        """Extract patient_id from MEDICALRECORD spans, or return 'unknown'."""
        for span in spans:
            if span.label == PhiLabel.ID_MEDICALRECORD:
                # Extract digits from the MRN span
                mrn_text = text[span.start : span.end]
                digits = re.sub(r"\D", "", mrn_text)
                if digits:
                    return digits
        return "unknown"

    def _shift_date_text(self, original: str, patient_id: str, max_days: int) -> str:
        """Parse date text, shift it, and format back preserving original format."""
        parsed = _parse_date(original)
        if not parsed:
            return _MASK_CHAR * len(original)
        d, fmt = parsed
        shifted = self._vault.shift_date(d, patient_id, max_days)
        return shifted.strftime(fmt)

    def __str__(self) -> str:
        return f"Anonymizer(detectors={len(self._detectors)})"
