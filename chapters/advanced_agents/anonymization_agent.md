## Anonymization Agent

An anonymization agent applies multiple de-identification techniques (structured rules and LLM-based detection) and then runs a verification pass to catch leaks while preserving downstream utility.

### Why an “agent” instead of a fixed redaction script

Real data rarely matches a single template. A pipeline that only uses regex misses names, nicknames, and domain-specific identifiers; a pipeline that only uses NER misses structured identifiers (account numbers, URLs, device IDs) and can over-redact common tokens. An agent wraps multiple detectors and transformation operators behind an explicit policy, then iterates: detect, transform, verify, and produce an auditable report of what was changed and why.

In practice, anonymization is usually recall-first: it is better to remove one extra token than to leak a patient name. But utility still matters (analytics, search, model training), so the agent needs controllable operators such as “mask”, “replace with type tag”, “consistent pseudonym”, or “format-preserving pseudonym”.

### Detection layer: combining deterministic and probabilistic signals

A robust agent uses layered detection, where each layer is good at a different failure mode.

Structured patterns (regex and validators) are the highest precision signal for well-defined identifiers: emails, phone numbers, SSNs, IP addresses, UUIDs, MAC addresses, credit cards (with Luhn checks), and internal IDs with known prefixes. This layer is fast, deterministic, and easy to reason about, but it does not generalize.

LLM-based detection finds entities whose surface form is unconstrained: person names, organizations, locations, and free-form dates. A capable language model can detect PHI that no fixed pattern set anticipates, and its contextual understanding handles ambiguity (is “Paris” a city or a patient name?) far better than traditional NER.

Purpose-built PII/PHI frameworks combine both: Microsoft Presidio, for example, separates “analysis” (recognizers) from “anonymization” (operators) so you can extend recognizers while reusing transformation logic. ([Microsoft][2])

In regulated domains (clinical notes, insurance), de-identification has well-studied benchmarks and error modes; the i2b2/UTHealth de-identification shared task is a common reference point for PHI-like entity categories and evaluation approaches. ([PMC][3])

### Transformation layer: masking, pseudonymization, and format preservation

Once the agent has spans (start, end, label, confidence, provenance), it applies operators. The important point is that operators must be policy-driven, not hard-coded, because different consumers require different utility.

Plain masking is irreversible and safest for high-risk fields (“John Smith” → “[PERSON]”). This is typically the default for anything that could identify a person directly.

Pseudonymization preserves linkability across a dataset (“John Smith” -> “PATIENT_0001”) by replacing real identifiers with opaque sequential tokens (`LABEL_NNNN`) stored in a persistent vault. The same input always maps to the same pseudonym, enabling joins and longitudinal analysis, but the tokens are obviously synthetic -- they cannot be confused with real data by either humans or audit models. In GDPR terminology, pseudonymisation means the data cannot be attributed to a person without additional information kept separately. ([GDPR][4])

For structured identifiers, format-preserving pseudonyms prevent breaking schemas and validators. A common approach is format-preserving encryption (FPE), standardized by NIST (FF1 / FF3-1), which can keep length and character sets intact. ([NIST Computer Security Resource Center][5])

Finally, the agent should treat quasi-identifiers carefully (dates, ZIP codes, rare job titles) because combinations can re-identify even when obvious identifiers are removed; classic privacy models like k-anonymity motivate suppression/generalization for these fields when releasing tabular data. ([ACM Digital Library][6])

### Context-aware masking: when the same token is safe in one place and sensitive in another

Context matters. “Paris” might be a travel destination in a blog post, but a patient location in a clinical note; “Apple” might be a company or a cafeteria menu item; “Dr. Lee” might be staff (often permissible in some releases) or a private practitioner in a small town (riskier). A practical way to formalize this is to treat anonymization as enforcing “appropriate information flows” relative to the context, rather than blindly stripping certain strings; this aligns with contextual integrity as a privacy framework. ([UW Law Digital Commons][7])

Operationally, context-aware masking can be implemented as a lightweight classifier over each candidate span and its window (surrounding tokens, section headers, metadata like document type). It can be rules-first (“if section == ‘Assessment’ then treat ages as PHI”) and then escalated to an LLM-based decision for ambiguous cases.

### Verification layer: a second-pass “audit” model, run locally

Even strong detector ensembles miss edge cases: rare names, misspellings, identifiers embedded in prose, or information implied indirectly (“the mayor of a town of 800”). A common production pattern is a second pass that asks a model to find remaining PII/PHI after redaction and to explain what it found. This pass should not be allowed to “rewrite” the document; it should only propose spans to review and remove, then the deterministic pipeline applies the changes.

Because the verification pass sees raw(ish) content, many teams run it on a local model for privacy -- see "Running the audit model locally" below.

### A policy-driven anonymization agent

The core design is a three-step loop: (1) regex detection on original text, (2) tag detected spans and run an LLM to find additional PHI that regex missed, merge all spans, pseudonymize from the original text, (3) run the LLM again on the pseudonymized output to verify nothing leaked -- if it finds more PHI, loop back to step 2. The loop is bounded to `max_passes` (default 2) to prevent infinite loops. The `AnonymizationAgent` is the only public API; the toolkit classes (`Anonymizer`, `RegexDetector`, `PseudonymVault`) are internal machinery.

PHI labels follow the i2b2/UTHealth 2014 de-identification taxonomy, encoded as a `PhiLabel` enum (NAME_PATIENT, NAME_DOCTOR, LOCATION_HOSPITAL, ID_SSN, ID_MEDICALRECORD, DATE, CONTACT_PHONE, AGE, etc.). The `Operator` enum defines four redaction strategies: MASK (block characters), TAG (label replacement), PSEUDONYM (opaque deterministic identifiers, `LABEL_NNNN`), and DATE_SHIFT (epoch remapping to 2000-01-01, preserving intervals).

```python
class EntitySpan(BaseModel):
    start: int
    end: int
    label: PhiLabel
    score: float = 1.0
    source: str = “unknown”    # “regex”, “ner”, “audit”

class OperatorSpec(BaseModel):
    operator: Operator
    params: dict = {}

class AnonymizationPolicy(BaseModel):
    operators: dict[PhiLabel, OperatorSpec]   # label -> how to redact
    min_score: float = 0.5
    allowlist: set[str] = set()              # tokens to never redact

class Detector(Protocol):
    def detect(self, text: str, meta: dict | None = None) -> list[EntitySpan]: ...
```

The default policy (`default_phi_policy()`) uses PSEUDONYM for all labels except DATE which uses DATE_SHIFT (epoch remapping to 2000-01-01). This produces de-identified text where “Margaret Thompson” becomes `PATIENT_0001` and “4478-2291” becomes `MRN_0001`, with tokens that are obviously synthetic rather than confusable with real data. Dates move to the year 2000, making them immediately recognizable as de-identified.

Detectors are layered. `RegexDetector` ships with patterns for structured clinical PHI (MRN prefixes, SSN, phone, email, dates, ages >89). `NerDetector` is a generic wrapper that accepts any callable returning `(start, end, label, score)` tuples, so users can plug in Presidio, SciSpacy, or custom models. The LLM audit pass (steps 2 and 3) catches entity types that regex cannot handle -- person names, organizations, locations, and contextual identifiers.

```python
class RegexDetector:
    “””Ships with patterns for MRN, SSN, phone, email, dates, ages >89.”””

    def detect(self, text: str, meta: dict | None = None) -> list[EntitySpan]:
        spans = []
        for regex, label in self._compiled:
            for m in regex.finditer(text):
                spans.append(EntitySpan(start=m.start(), end=m.end(), label=label, score=0.9, source=”regex”))
        return spans

class NerDetector:
    “””Generic wrapper for any NER callable via a label_map.”””

    def __init__(self, ner_fn: Callable, label_map: dict[str, PhiLabel], source: str = “ner”): ...
    def detect(self, text: str, meta: dict | None = None) -> list[EntitySpan]: ...
```

`PseudonymVault` is a JSON-backed persistent store that maps (label, normalized value) pairs to opaque `LABEL_NNNN` tokens. Each label type gets a sequential counter: the first patient name becomes `PATIENT_0001`, the second `PATIENT_0002`, and so on. Mappings are persisted to a JSON file, so pseudonyms are consistent across separate runs -- if “Margaret Thompson” was mapped to `PATIENT_0001` three months ago, she still is today.

For names, the vault normalizes input before lookup: it removes punctuation, lowercases, and sorts tokens alphabetically. This means “Rajesh Patel” and “Patel, Rajesh” resolve to the same pseudonym. Title stripping (“Dr.”, honorifics) is not the vault's job -- the LLM audit prompt instructs the model to return names without honorifics, which keeps the vault language-agnostic.

```python
class PseudonymVault:
    def __init__(self, path: Path): ...

    def pseudonym(self, label: str, value: str) -> str:
        “””Return pseudonym for (label, value), creating one if new.”””
        key = f”{label}|{self._normalize(label, value)}”
        if key in self._mappings:
            return self._mappings[key]
        prefix = self._prefix(label)
        idx = self._counters.get(prefix, 0) + 1
        self._counters[prefix] = idx
        pseudo = f”{prefix}_{idx:04d}”
        self._mappings[key] = pseudo
        self._save()
        return pseudo
```

The `Anonymizer` is the internal engine: detect (run all detectors, merge overlapping spans, filter by policy), then redact (apply operators right-to-left to preserve offsets). For dates, the anonymizer computes an epoch offset: it finds the earliest date in the document, calculates the delta to 2000-01-01, and applies that same delta to all dates. This moves dates to a clearly synthetic era while preserving temporal intervals (a 7-day hospital stay remains 7 days).

```python
class Anonymizer:
    def __init__(self, detectors: list[Detector], policy: AnonymizationPolicy, vault: PseudonymVault):
        ...

    def detect(self, text: str, meta: dict | None = None) -> list[EntitySpan]:
        “””Run all detectors, merge overlaps, filter by min_score and allowlist.”””
        ...

    def redact(self, text: str, spans: list[EntitySpan]) -> str:
        “””Apply operators right-to-left. Dates are epoch-shifted (earliest -> 2000-01-01).”””
        ...

    def run(self, text: str, meta: dict | None = None) -> AnonymizationResult:
        “””Full pipeline: detect + redact.”””
        ...
```

### LLM audit pass

The audit pass should output structured findings (“I see an email at ...”) rather than rewritten text. The agent then converts findings into spans, merges overlaps, applies the same operator logic, and repeats (bounded by `max_passes`) to avoid infinite loops. The audit model can be local (Ollama) or remote (compliant vendor with proper ZDR policy) -- that is a deployment configuration decision, configured via `config_name` pointing to a model in `config.yaml`.

The `AnonymizationAgent` wraps all three steps behind a single `anonymize()` call. It uses PydanticAI's structured output to get typed `AuditResult` (list of findings with label, substring, reason) from the LLM, rather than parsing free-form text.

```python
class AuditFinding(BaseModel):
    label: str       # PhiLabel value
    substring: str   # exact text found
    reason: str

class AuditResult(BaseModel):
    findings: list[AuditFinding] = []

class AnonymizationAgent:
    def __init__(self, detectors, policy, vault: PseudonymVault, *, config_name=”default”, max_passes=2):
        self._anonymizer = Anonymizer(detectors, policy, vault)
        self._audit_agent = get_agent(config_name=config_name, output_type=AuditResult)
        self._max_passes = max_passes

    async def anonymize(self, text: str, meta: dict | None = None) -> AnonymizationResult:
        # Step 1: regex detection on original text
        all_spans = self._anonymizer.detect(text, meta)

        for _ in range(self._max_passes):
            # Step 2: tag text, LLM detects additional PHI
            tagged_text = self._anonymizer.redact_tagged(text, all_spans)
            detect_output = (await self._audit_agent.run(audit_prompt(tagged_text))).output
            if detect_output.findings:
                all_spans = _merge_spans(all_spans + self._findings_to_spans(text, ...))

            # Pseudonymize from original text
            redacted_text = self._anonymizer.redact(text, all_spans)

            # Step 3: LLM verifies pseudonymized output
            verify_output = (await self._audit_agent.run(audit_prompt(redacted_text))).output
            if not verify_output.findings:
                break  # clean -- no leaks

            # Leaks found: merge new spans, loop back to step 2
            all_spans = _merge_spans(all_spans + self._findings_to_spans(text, ...))
        return AnonymizationResult(...)
```

### Running the audit model locally

The LLM audit pass sees text that still contains residual PHI -- that is the whole point of the audit. If you have access to a provider with Zero Data Retention (ZDR) policies and contractual guarantees that data will not be used for training (e.g. a BAA for healthcare), the `config_name` can point to that provider's model and no local infrastructure is needed. When such agreements are not available, the audit model must run locally instead.

Ollama exposes an OpenAI-compatible HTTP API that PydanticAI can talk to without code changes -- only the configuration differs. ([Ollama Documentation][8]) A GPU machine (an NVIDIA DGX workstation, a cloud VM with attached GPUs, or a workstation with a single high-VRAM card) runs Ollama as a service:

```yaml
# config.yaml
models:
  ollama_local:
    model_family: ollama
    model_name: llama3
    url: http://localhost:11434/v1
    timeout: 60
```

The agent selects this model via `config_name`:

```python
agent = AnonymizationAgent(
    detectors=[RegexDetector()],
    policy=default_phi_policy(),
    vault=PseudonymVault(Path("vault.json")),
    config_name="ollama_local",
)
```

The model must be capable of structured output (returning valid JSON matching `AuditResult`). Models in the Llama 3 8B+ and Qwen 2.5 7B+ families reliably produce structured PHI findings with PydanticAI's output parsing. Smaller models tend to hallucinate labels or miss context-dependent PHI; larger models (70B+) improve recall but require more hardware. An 8B model on a single GPU is enough for development, while a 70B model on a DGX node gives production-grade recall for batch anonymization.


### Hands-on

See `example_anonymization.ipynb` for a working notebook that demonstrates the full pipeline: regex detection, LLM audit, pseudonymized output with epoch-based date shifting, and pseudonym consistency across documents.

[2]: https://microsoft.github.io/presidio/ "Presidio: Data Protection and De-identification SDK"
[3]: https://pmc.ncbi.nlm.nih.gov/articles/PMC4989908/ "Overview of 2014 i2b2/UTHealth shared task Track 1 - PMC"
[4]: https://gdpr-info.eu/art-4-gdpr/ "Art. 4 GDPR -- Definitions - General Data Protection ..."
[5]: https://csrc.nist.gov/pubs/sp/800/38/g/r1/2pd "SP 800-38G Rev. 1, Recommendation for Block Cipher ..."
[6]: https://dl.acm.org/doi/10.1142/S0218488502001648 "k-anonymity: a model for protecting privacy"
[7]: https://digitalcommons.law.uw.edu/wlr/vol79/iss1/10/ "Privacy as Contextual Integrity by Helen Nissenbaum"
[8]: https://docs.ollama.com/api/introduction "Introduction"
[9]: https://microsoft.github.io/presidio/anonymizer/ "Presidio Anonymizer"
[11]: https://github.com/ollama/ollama/blob/main/docs/api.md "ollama/docs/api.md at main"
[13]: https://ico.org.uk/for-organisations/uk-gdpr-guidance-and-resources/data-sharing/anonymisation/pseudonymisation/ "Pseudonymisation | ICO"
[14]: https://csrc.nist.gov/pubs/sp/800/38/g/r1/ipd "SP 800-38G Rev. 1, Recommendation for Block Cipher Modes ..."
