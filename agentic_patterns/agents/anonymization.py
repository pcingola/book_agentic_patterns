"""Anonymization agent: regex detection + LLM detection + LLM verification loop."""

from pydantic import BaseModel, Field

from agentic_patterns.core.agents.agents import get_agent
from agentic_patterns.core.config.config import PROMPTS_DIR
from agentic_patterns.core.listeners import AgentListener
from agentic_patterns.core.prompt import load_prompt
from agentic_patterns.toolkits.anonymization.anonymizer import Anonymizer, _merge_spans
from agentic_patterns.toolkits.anonymization.models import (
    AnonymizationPolicy,
    AnonymizationResult,
    Detector,
    EntitySpan,
    PhiLabel,
)
from agentic_patterns.toolkits.anonymization.vault import PseudonymVault


class AuditFinding(BaseModel):
    """A single PHI finding from the LLM audit pass."""

    label: str
    substring: str
    reason: str


class AuditResult(BaseModel):
    """Structured output from the LLM audit agent."""

    findings: list[AuditFinding] = Field(default_factory=list)


class AnonymizationListener(AgentListener[AnonymizationResult]):
    """Hooks for anonymization progress. Override to customise."""


class PrintAnonymizationListener(AnonymizationListener):
    """Prints anonymization progress to stdout."""

    async def on_start(self) -> None:
        print("Anonymizing...")

    async def on_done(self, result: AnonymizationResult) -> None:
        n_det = len(result.detection_spans)
        n_aud = len(result.audit_spans)
        print(f"Done: {n_det} detections, {n_aud} audit findings")


# Map from audit finding label strings to PhiLabel enum values (case-insensitive)
_AUDIT_LABEL_MAP: dict[str, PhiLabel] = {
    label.value.upper(): label for label in PhiLabel
}


class AnonymizationAgent:
    """Three-step anonymization: regex -> LLM detection -> LLM verification loop.

    Step 1: Regex detection on original text.
    Step 2: Tag text with [LABEL], LLM detects additional PHI, merge spans, pseudonymize.
    Step 3: LLM verifies pseudonymized text. If findings remain, loop back to step 2.
    Bounded to max_passes to prevent infinite loops.
    """

    def __init__(
        self,
        detectors: list[Detector],
        policy: AnonymizationPolicy,
        vault: PseudonymVault | None = None,
        *,
        config_name: str = "default",
        listener: AnonymizationListener | None = None,
        max_passes: int = 2,
    ):
        self._anonymizer = Anonymizer(detectors, policy, vault)
        self._policy = policy
        self._listener = listener
        self._audit_agent = get_agent(config_name=config_name, output_type=AuditResult)
        self._max_passes = max_passes

    async def anonymize(
        self, text: str, meta: dict | None = None
    ) -> AnonymizationResult:
        """Regex -> LLM detect -> pseudonymize -> LLM verify (loop)."""
        if self._listener:
            await self._listener.on_start()

        # Step 1: regex detection on original text
        all_spans = self._anonymizer.detect(text, meta)
        audit_spans: list[EntitySpan] = []

        for _ in range(self._max_passes):
            # Step 2: tag text, LLM detects additional PHI
            tagged_text = self._anonymizer.redact_tagged(text, all_spans)
            prompt = load_prompt(
                PROMPTS_DIR / "anonymization" / "audit.md", text=tagged_text
            )
            detect_output: AuditResult = (await self._audit_agent.run(prompt)).output

            if detect_output.findings:
                new_spans = self._findings_to_spans(text, detect_output.findings)
                audit_spans.extend(new_spans)
                all_spans = _merge_spans(all_spans + new_spans)

            # Pseudonymize from original text
            redacted_text = self._anonymizer.redact(text, all_spans, meta)

            # Step 3: LLM verifies pseudonymized output
            verify_prompt = load_prompt(
                PROMPTS_DIR / "anonymization" / "audit.md", text=redacted_text
            )
            verify_output: AuditResult = (
                await self._audit_agent.run(verify_prompt)
            ).output

            if not verify_output.findings:
                break  # clean -- no leaks found

            # Leaks found: convert findings to spans in original text, loop back
            leak_spans = self._findings_to_spans(text, verify_output.findings)
            if not leak_spans:
                break  # findings didn't map to original text
            audit_spans.extend(leak_spans)
            all_spans = _merge_spans(all_spans + leak_spans)
        else:
            # Final pseudonymize after exhausting passes
            redacted_text = self._anonymizer.redact(text, all_spans, meta)

        detection_spans = [s for s in all_spans if s.source != "audit"]
        result = AnonymizationResult(
            original_text=text,
            redacted_text=redacted_text,
            detection_spans=detection_spans,
            audit_spans=audit_spans,
        )

        if self._listener:
            await self._listener.on_done(result)
        return result

    def _findings_to_spans(
        self, text: str, findings: list[AuditFinding]
    ) -> list[EntitySpan]:
        """Locate all occurrences of audit findings in original text."""
        spans: list[EntitySpan] = []
        for finding in findings:
            label = _AUDIT_LABEL_MAP.get(finding.label.upper())
            if not label:
                continue
            start = 0
            while True:
                idx = text.find(finding.substring, start)
                if idx == -1:
                    break
                spans.append(
                    EntitySpan(
                        start=idx,
                        end=idx + len(finding.substring),
                        label=label,
                        score=1.0,
                        source="audit",
                    )
                )
                start = idx + len(finding.substring)
        return _merge_spans(spans)

    def __str__(self) -> str:
        return f"AnonymizationAgent(detectors={len(self._anonymizer._detectors)})"
