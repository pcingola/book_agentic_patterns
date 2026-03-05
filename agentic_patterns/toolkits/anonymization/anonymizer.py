"""Core anonymization engine: detection, merging, and redaction."""

from datetime import date, datetime, timedelta

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

# Epoch date: all dates are shifted so that the earliest date maps to this
_DATE_EPOCH = date(2000, 1, 1)

# Date formats to try when parsing, ordered by specificity
_DATE_FORMATS = [
    "%B %d, %Y",  # January 15, 2024
    "%B %d %Y",  # January 15 2024
    "%d %B %Y",  # 15 January 2024
    "%Y-%m-%d",  # 2024-01-15
    "%m/%d/%Y",  # 01/15/2024
    "%m-%d-%Y",  # 01-15-2024
    "%m/%d/%y",  # 01/15/24
    "%m-%d-%y",  # 01-15-24
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
    for fmt in _DATE_FORMATS:
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
        vault: PseudonymVault,
    ):
        self._detectors = detectors
        self._policy = policy
        self._vault = vault

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

    def redact(self, text: str, spans: list[EntitySpan]) -> str:
        """Apply redaction operators to text, right-to-left to preserve offsets."""
        date_offset = self._compute_date_offset(text, spans)

        # Sort right-to-left so replacements don't shift earlier offsets
        for span in sorted(spans, key=lambda s: s.start, reverse=True):
            original = text[span.start : span.end]
            spec = self._policy.get_operator(span.label)
            replacement = self._apply_operator(
                spec.operator, span.label, original, date_offset
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
        redacted = self.redact(text, spans)
        return AnonymizationResult(
            original_text=text, redacted_text=redacted, detection_spans=spans
        )

    def _apply_operator(
        self,
        operator: Operator,
        label: PhiLabel,
        original: str,
        date_offset: timedelta,
    ) -> str:
        match operator:
            case Operator.MASK:
                return _MASK_CHAR * len(original)
            case Operator.TAG:
                return f"[{label.value}]"
            case Operator.PSEUDONYM:
                return self._vault.pseudonym(label.value, original)
            case Operator.DATE_SHIFT:
                return self._shift_date_text(original, date_offset)

    def _compute_date_offset(self, text: str, spans: list[EntitySpan]) -> timedelta:
        """Compute offset so the earliest date in the document maps to _DATE_EPOCH."""
        earliest: date | None = None
        for span in spans:
            if span.label == PhiLabel.DATE:
                parsed = _parse_date(text[span.start : span.end])
                if parsed:
                    d, _ = parsed
                    if earliest is None or d < earliest:
                        earliest = d
        if earliest is None:
            return timedelta(0)
        return _DATE_EPOCH - earliest

    def _shift_date_text(self, original: str, offset: timedelta) -> str:
        """Parse date text, shift by offset, format back preserving original format."""
        parsed = _parse_date(original)
        if not parsed:
            return _MASK_CHAR * len(original)
        d, fmt = parsed
        return (d + offset).strftime(fmt)

    def __str__(self) -> str:
        return f"Anonymizer(detectors={len(self._detectors)})"
