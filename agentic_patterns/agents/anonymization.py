"""Anonymization agent: regex detection + LLM detection + LLM verification loop."""

from pydantic import BaseModel, Field

from agentic_patterns.core.agents.agents import get_agent, run_agent
from agentic_patterns.core.listeners import AgentListener
from agentic_patterns.core.prompt import load_prompt
from agentic_patterns.toolkits.anonymization.anonymizer import Anonymizer, _merge_spans
from agentic_patterns.toolkits.anonymization.detectors import RegexDetector
from agentic_patterns.toolkits.anonymization.models import (
    AnonymizationPolicy,
    AnonymizationResult,
    Detector,
    EntitySpan,
    PhiLabel,
    default_phi_policy,
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

    async def on_regex_done(self, spans: list[EntitySpan], text: str) -> None:
        pass

    async def on_audit_pass(self, pass_num: int, findings: list[AuditFinding]) -> None:
        pass

    async def on_verify_pass(self, pass_num: int, findings: list[AuditFinding]) -> None:
        pass


class PrintAnonymizationListener(AnonymizationListener):
    """Prints anonymization progress to stdout."""

    async def on_start(self) -> None:
        print("Anonymizing...")

    async def on_regex_done(self, spans: list[EntitySpan], text: str) -> None:
        print(f"  Regex detection: {len(spans)} spans found")
        for s in spans:
            snippet = text[s.start : s.end]
            print(
                f"    [{s.label.value}] '{snippet}' ({s.start}:{s.end}, score={s.score:.2f})"
            )

    async def on_audit_pass(self, pass_num: int, findings: list[AuditFinding]) -> None:
        print(f"  Audit pass {pass_num}: {len(findings)} findings")
        for f in findings:
            print(f"    [{f.label}] '{f.substring}' -- {f.reason}")

    async def on_verify_pass(self, pass_num: int, findings: list[AuditFinding]) -> None:
        if findings:
            print(f"  Verify pass {pass_num}: {len(findings)} leaks found")
            for f in findings:
                print(f"    [{f.label}] '{f.substring}' -- {f.reason}")
        else:
            print(f"  Verify pass {pass_num}: clean")

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
        *,
        detectors: list[Detector] | None = None,
        policy: AnonymizationPolicy | None = None,
        vault: PseudonymVault | None = None,
        config_name: str = "default",
        listener: AnonymizationListener | None = None,
        max_passes: int = 2,
        **agent_kwargs,
    ):
        self._anonymizer = Anonymizer(
            detectors or [RegexDetector()],
            policy or default_phi_policy(),
            vault or PseudonymVault(),
        )
        self._listener = listener
        if (
            listener
            and listener.stream_events
            and "event_stream_handler" not in agent_kwargs
        ):
            agent_kwargs["event_stream_handler"] = listener.as_event_stream_handler()
        self._audit_agent = get_agent(
            config_name=config_name,
            output_type=AuditResult,
            **agent_kwargs,
        )
        self._verify_agent = get_agent(
            config_name=config_name,
            output_type=AuditResult,
            **agent_kwargs,
        )
        self._max_passes = max_passes

    async def anonymize(self, text: str, meta: dict | None = None) -> AnonymizationResult:
        """Regex -> LLM audit -> pseudonymize -> LLM verify (loop)."""
        if self._listener:
            await self._listener.on_start()

        # Step 1: regex detection on original text
        all_spans = await self._detect_regex(text, meta)
        audit_spans: list[EntitySpan] = []

        for pass_num in range(1, self._max_passes + 1):
            # Step 2: LLM detects additional PHI missed by regex
            new_spans = await self._audit_pass(text, all_spans, pass_num)
            audit_spans.extend(new_spans)
            all_spans = _merge_spans(all_spans + new_spans)

            # Pseudonymize from original text using all spans found so far
            redacted_text = self._anonymizer.redact(text, all_spans)

            # Step 3: LLM verifies no real PHI remains in pseudonymized output
            leak_spans = await self._verify_pass(text, redacted_text, pass_num)
            if not leak_spans:
                break  # clean -- no leaks found
            audit_spans.extend(leak_spans)
            all_spans = _merge_spans(all_spans + leak_spans)
        else:
            # Final pseudonymize after exhausting all passes
            redacted_text = self._anonymizer.redact(text, all_spans)

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

    async def _detect_regex(self, text: str, meta: dict | None) -> list[EntitySpan]:
        """Step 1: regex detection on original text."""
        spans = self._anonymizer.detect(text, meta)
        if self._listener:
            await self._listener.on_regex_done(spans, text)
        return spans

    async def _audit_pass(self, text: str, all_spans: list[EntitySpan], pass_num: int) -> list[EntitySpan]:
        """Step 2: LLM detects additional PHI in tagged text."""
        tagged_text = self._anonymizer.redact_tagged(text, all_spans)
        prompt = load_prompt("anonymization/audit", text=tagged_text)
        agent_run, _ = await run_agent(self._audit_agent, prompt)
        output: AuditResult = agent_run.result.output

        if self._listener:
            await self._listener.on_audit_pass(pass_num, output.findings)

        if not output.findings:
            return []
        return self._findings_to_spans(text, output.findings)

    async def _verify_pass(self, text: str, redacted_text: str, pass_num: int) -> list[EntitySpan]:
        """Step 3: LLM verifies pseudonymized text for residual leaks."""
        prompt = load_prompt("anonymization/verify", text=redacted_text)
        agent_run, _ = await run_agent(self._verify_agent, prompt)
        output: AuditResult = agent_run.result.output

        if self._listener:
            await self._listener.on_verify_pass(pass_num, output.findings)

        if not output.findings:
            return []
        return self._findings_to_spans(text, output.findings)

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
