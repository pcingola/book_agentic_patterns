# Advanced Agents

## Anonymization Agent

An anonymization agent applies multiple de-identification techniques (structured rules, statistical NER, and context-aware masking) and then runs a verification pass to catch leaks while preserving downstream utility.

### Why an “agent” instead of a fixed redaction script

Real data rarely matches a single template. A pipeline that only uses regex misses names, nicknames, and domain-specific identifiers; a pipeline that only uses NER misses structured identifiers (account numbers, URLs, device IDs) and can over-redact common tokens. An agent wraps multiple detectors and transformation operators behind an explicit policy, then iterates: detect, transform, verify, and produce an auditable report of what was changed and why.

In practice, anonymization is usually recall-first: it is better to remove one extra token than to leak a patient name. But utility still matters (analytics, search, model training), so the agent needs controllable operators such as “mask”, “replace with type tag”, “consistent pseudonym”, or “format-preserving pseudonym”.

### Detection layer: combining deterministic and probabilistic signals

A robust agent uses layered detection, where each layer is good at a different failure mode.

Structured patterns (regex and validators) are the highest precision signal for well-defined identifiers: emails, phone numbers, SSNs, IP addresses, UUIDs, MAC addresses, credit cards (with Luhn checks), and internal IDs with known prefixes. This layer is fast, deterministic, and easy to reason about, but it does not generalize.

NER-based detection finds entities whose surface form is unconstrained: person names, organizations, locations, and free-form dates. Off-the-shelf NER (for example spaCy’s entity recognizer) is often “good enough” for generic text and can be fine-tuned for domain text when necessary. ([spaCy][1])

Purpose-built PII/PHI frameworks combine both: Microsoft Presidio, for example, separates “analysis” (recognizers) from “anonymization” (operators) so you can extend recognizers while reusing transformation logic. ([Microsoft][2])

In regulated domains (clinical notes, insurance), de-identification has well-studied benchmarks and error modes; the i2b2/UTHealth de-identification shared task is a common reference point for PHI-like entity categories and evaluation approaches. ([PMC][3])

### Transformation layer: masking, pseudonymization, and format preservation

Once the agent has spans (start, end, label, confidence, provenance), it applies operators. The important point is that operators must be policy-driven, not hard-coded, because different consumers require different utility.

Plain masking is irreversible and safest for high-risk fields (“John Smith” → “[PERSON]”). This is typically the default for anything that could identify a person directly.

Pseudonymization preserves linkability across a dataset (“John Smith” → “PERSON_00491”), which is essential when you still need joins, longitudinal analysis, or entity-centric retrieval. In GDPR terminology, pseudonymisation means the data cannot be attributed to a person without additional information kept separately. ([GDPR][4])

For structured identifiers, format-preserving pseudonyms prevent breaking schemas and validators. A common approach is format-preserving encryption (FPE), standardized by NIST (FF1 / FF3-1), which can keep length and character sets intact. ([NIST Computer Security Resource Center][5])

Finally, the agent should treat quasi-identifiers carefully (dates, ZIP codes, rare job titles) because combinations can re-identify even when obvious identifiers are removed; classic privacy models like k-anonymity motivate suppression/generalization for these fields when releasing tabular data. ([ACM Digital Library][6])

### Context-aware masking: when the same token is safe in one place and sensitive in another

Context matters. “Paris” might be a travel destination in a blog post, but a patient location in a clinical note; “Apple” might be a company or a cafeteria menu item; “Dr. Lee” might be staff (often permissible in some releases) or a private practitioner in a small town (riskier). A practical way to formalize this is to treat anonymization as enforcing “appropriate information flows” relative to the context, rather than blindly stripping certain strings; this aligns with contextual integrity as a privacy framework. ([UW Law Digital Commons][7])

Operationally, context-aware masking can be implemented as a lightweight classifier over each candidate span and its window (surrounding tokens, section headers, metadata like document type). It can be rules-first (“if section == ‘Assessment’ then treat ages as PHI”) and then escalated to an LLM-based decision for ambiguous cases.

### Verification layer: a second-pass “audit” model, run locally

Even strong detector ensembles miss edge cases: rare names, misspellings, identifiers embedded in prose, or information implied indirectly (“the mayor of a town of 800”). A common production pattern is a second pass that asks a model to find remaining PII/PHI after redaction and to explain what it found. This pass should not be allowed to “rewrite” the document; it should only propose spans to review and remove, then the deterministic pipeline applies the changes.

Because the verification pass sees raw(ish) content, many teams run it locally for privacy. Ollama exposes a local HTTP API (including chat generation) that can be hosted on an internal machine or cluster node. ([Ollama Documentation][8])

### A policy-driven anonymization agent (Python-like)

The core design is: (1) normalize inputs into a document abstraction, (2) run multiple detectors, (3) merge and resolve overlaps, (4) apply policy-selected operators, (5) run an audit pass, (6) emit outputs plus an audit trail.

```python
class EntitySpan(BaseModel):
    start: int
    end: int
    label: str              # PERSON, EMAIL, MRN, ADDRESS, ...
    score: float
    source: str             # "regex", "ner", "dict", "llm_audit"

class OperatorSpec(BaseModel):
    op: str                 # "mask", "tag", "pseudonym", "fpe"
    params: dict = {}       # e.g. {"prefix": "PERSON_"} or {"alphabet": "0123456789"}

class AnonymizationPolicy(BaseModel):
    rules: dict[str, OperatorSpec]    # label -> operator
    min_score: float = 0.50
    allowlist_labels: set[str] = set()
    denylist_labels: set[str] = set()
    keep_structure: bool = True       # prefer FPE for structured IDs when possible
    stable_pseudonyms: bool = True    # consistent within dataset via keyed mapping

class Detector(Protocol):
    def detect(self, text: str, meta: dict) -> list[EntitySpan]: ...
```

```python
class RegexDetector:
    def __init__(self, patterns: list[tuple[str, str]]):
        self.patterns = patterns  # (label, regex)

    def detect(self, text: str, meta: dict) -> list[EntitySpan]:
        spans = []
        for label, rx in self.patterns:
            for m in finditer(rx, text):
                spans.append(EntitySpan(
                    start=m.start(), end=m.end(),
                    label=label, score=1.0, source="regex"
                ))
        return spans
```

```python
class NerDetector:
    def __init__(self, ner_model):
        self.ner = ner_model  # spaCy, Presidio analyzer, domain model, etc.

    def detect(self, text: str, meta: dict) -> list[EntitySpan]:
        ents = self.ner(text)
        return [
            EntitySpan(start=e.start, end=e.end, label=e.label, score=e.score, source="ner")
            for e in ents
        ]
```

```python
class PseudonymVault:
    def __init__(self, secret_key: bytes, namespace: str):
        self.secret_key = secret_key
        self.namespace = namespace

    def pseudonym(self, label: str, value: str) -> str:
        # Deterministic, secret-keyed mapping; store reverse map separately if needed.
        digest = hmac_sha256(self.secret_key, f"{self.namespace}:{label}:{value}")
        return f"{label}_{base32(digest)[:10]}"
```

```python
class Anonymizer:
    def __init__(self, detectors: list[Detector], policy: AnonymizationPolicy, vault: PseudonymVault):
        self.detectors = detectors
        self.policy = policy
        self.vault = vault

    def run(self, text: str, meta: dict) -> tuple[str, list[EntitySpan]]:
        spans = []
        for d in self.detectors:
            spans.extend(d.detect(text, meta))

        spans = self._merge(spans)
        spans = [s for s in spans if s.score >= self.policy.min_score]
        spans = [s for s in spans if s.label not in self.policy.allowlist_labels]
        spans = [s for s in spans if s.label not in self.policy.denylist_labels]

        redacted = self._apply(text, spans, meta)
        return redacted, spans

    def _apply(self, text: str, spans: list[EntitySpan], meta: dict) -> str:
        # Apply from right-to-left to preserve offsets.
        out = text
        for s in sorted(spans, key=lambda x: x.start, reverse=True):
            spec = self.policy.rules.get(s.label, OperatorSpec(op="tag", params={"tag": f"[{s.label}]"}))
            raw = out[s.start:s.end]

            replacement = self._transform(raw, s.label, spec)
            out = out[:s.start] + replacement + out[s.end:]
        return out

    def _transform(self, raw: str, label: str, spec: OperatorSpec) -> str:
        if spec.op == "mask":
            return "█" * len(raw)
        if spec.op == "tag":
            return spec.params.get("tag", f"[{label}]")
        if spec.op == "pseudonym":
            return self.vault.pseudonym(label, raw)
        if spec.op == "fpe":
            return fpe_encrypt(self.vault.secret_key, raw, alphabet=spec.params["alphabet"])
        return f"[{label}]"
```

### Local LLM audit pass via Ollama

The audit pass should output structured findings (“I see an email at …”) rather than rewritten text. The agent then converts findings into spans, applies the same operator logic, and repeats once (bounded) to avoid infinite loops.

```python
class LocalAuditModel:
    def __init__(self, base_url: str, model: str):
        self.base_url = base_url
        self.model = model

    def find_leaks(self, text: str, meta: dict) -> list[EntitySpan]:
        prompt = (
            "You are a privacy auditor. Identify any remaining PII/PHI in the text.\n"
            "Return findings as: <label>\t<exact substring>\t<reason>\n"
            "Do not rewrite the text.\n\n"
            f"TEXT:\n{text}"
        )

        resp = http_post(
            f"{self.base_url}/api/chat",
            json={
                "model": self.model,
                "stream": False,
                "messages": [{"role": "user", "content": prompt}],
            },
            timeout_s=60,
        )

        return parse_findings_into_spans(text, resp["message"]["content"], source="llm_audit")
```

Ollama documents the local API endpoints for chat generation, including non-streaming usage. ([Ollama Documentation][8])

### Distributed execution: Spark on an internal DGX-class machine

The key constraint is that raw text should not leave the private environment. In Spark, you typically broadcast the policy and secrets (or secret handles) to executors, run the anonymizer in a partition function, and only persist anonymized outputs plus audit metadata.

```python
policy_bc = spark.sparkContext.broadcast(policy)
vault_bc  = spark.sparkContext.broadcast(vault_config)  # not the raw key if you can avoid it

def anonymize_partition(rows_iter):
    anonymizer = build_anonymizer(policy_bc.value, vault_bc.value)
    auditor    = LocalAuditModel(base_url="http://127.0.0.1:11434", model="mistral")

    for row in rows_iter:
        text, meta = row.text, row.meta

        redacted, spans = anonymizer.run(text, meta)

        # Second pass: audit only if needed (sampling, high-risk docs, or always for strict mode).
        audit_spans = auditor.find_leaks(redacted, meta)
        if audit_spans:
            redacted = anonymizer._apply(redacted, audit_spans, meta)
            spans = spans + audit_spans

        yield row.with_updates(redacted_text=redacted, anonymization_report=spans)

df_out = df_in.rdd.mapPartitions(anonymize_partition).toDF()
```

This pattern also keeps the “verification model” local to the executor node (or a node-local service) so sensitive content is never sent to an external endpoint.

## References (references.md)

1. Microsoft. *Presidio: Data Protection and De-identification SDK*. Documentation. [https://microsoft.github.io/presidio/](https://microsoft.github.io/presidio/) ([Microsoft][2])
2. Microsoft. *Presidio Anonymizer*. Documentation. [https://microsoft.github.io/presidio/anonymizer/](https://microsoft.github.io/presidio/anonymizer/) ([Microsoft][9])
3. spaCy. *Linguistic Features: Named Entity Recognition*. Documentation. [https://spacy.io/usage/linguistic-features](https://spacy.io/usage/linguistic-features) ([spaCy][1])
4. spaCy. *EntityRecognizer API*. Documentation. [https://spacy.io/api/entityrecognizer](https://spacy.io/api/entityrecognizer) ([spaCy][10])
5. Ollama. *API Introduction*. Documentation. [https://docs.ollama.com/api/introduction](https://docs.ollama.com/api/introduction) ([Ollama Documentation][8])
6. Ollama. *API: Generate a chat completion (POST /api/chat)*. Source documentation. [https://github.com/ollama/ollama/blob/main/docs/api.md](https://github.com/ollama/ollama/blob/main/docs/api.md) ([GitHub][11])
7. Helen Nissenbaum. *Privacy as Contextual Integrity*. Washington Law Review, 2004. [https://digitalcommons.law.uw.edu/wlr/vol79/iss1/10/](https://digitalcommons.law.uw.edu/wlr/vol79/iss1/10/) ([UW Law Digital Commons][7])
8. Helen Nissenbaum. *Privacy as Contextual Integrity*. 2004 (PDF copy). [https://crypto.stanford.edu/portia/papers/RevnissenbaumDTP31.pdf](https://crypto.stanford.edu/portia/papers/RevnissenbaumDTP31.pdf) ([Applied Cryptography Group][12])
9. European Union. *General Data Protection Regulation, Article 4(5): Definition of ‘pseudonymisation’*. [https://gdpr-info.eu/art-4-gdpr/](https://gdpr-info.eu/art-4-gdpr/) ([GDPR][4])
10. Information Commissioner’s Office (UK). *Pseudonymisation*. Guidance. [https://ico.org.uk/for-organisations/uk-gdpr-guidance-and-resources/data-sharing/anonymisation/pseudonymisation/](https://ico.org.uk/for-organisations/uk-gdpr-guidance-and-resources/data-sharing/anonymisation/pseudonymisation/) ([ICO][13])
11. Morris Dworkin (NIST). *Recommendation for Block Cipher Modes of Operation: Methods for Format-Preserving Encryption (SP 800-38G Rev. 1)*. NIST, 2019/2025. [https://csrc.nist.gov/pubs/sp/800/38/g/r1/ipd](https://csrc.nist.gov/pubs/sp/800/38/g/r1/ipd) ([NIST Computer Security Resource Center][14])
12. Latanya Sweeney. *k-anonymity: A Model for Protecting Privacy*. International Journal on Uncertainty, Fuzziness and Knowledge-based Systems, 2002. [https://dl.acm.org/doi/10.1142/S0218488502001648](https://dl.acm.org/doi/10.1142/S0218488502001648) ([ACM Digital Library][6])
13. A. Stubbs, C. Kotfila, Ö. Uzuner. *Automated systems for the de-identification of longitudinal clinical narratives: Overview of the 2014 i2b2/UTHealth shared task Track 1*. Journal of Biomedical Informatics, 2015. [https://pmc.ncbi.nlm.nih.gov/articles/PMC4989908/](https://pmc.ncbi.nlm.nih.gov/articles/PMC4989908/) ([PMC][3])
14. i2b2. *2014 i2b2/UTHealth NLP Shared Task: De-identification Track*. [https://www.i2b2.org/NLP/HeartDisease/](https://www.i2b2.org/NLP/HeartDisease/)

[1]: https://spacy.io/usage/linguistic-features?utm_source=chatgpt.com "Linguistic Features · spaCy Usage Documentation"
[2]: https://microsoft.github.io/presidio/?utm_source=chatgpt.com "Presidio: Data Protection and De-identification SDK"
[3]: https://pmc.ncbi.nlm.nih.gov/articles/PMC4989908/?utm_source=chatgpt.com "Overview of 2014 i2b2/UTHealth shared task Track 1 - PMC"
[4]: https://gdpr-info.eu/art-4-gdpr/?utm_source=chatgpt.com "Art. 4 GDPR – Definitions - General Data Protection ..."
[5]: https://csrc.nist.gov/pubs/sp/800/38/g/r1/2pd?utm_source=chatgpt.com "SP 800-38G Rev. 1, Recommendation for Block Cipher ..."
[6]: https://dl.acm.org/doi/10.1142/S0218488502001648?utm_source=chatgpt.com "k-anonymity: a model for protecting privacy"
[7]: https://digitalcommons.law.uw.edu/wlr/vol79/iss1/10/?utm_source=chatgpt.com "\"Privacy as Contextual Integrity\" by Helen Nissenbaum"
[8]: https://docs.ollama.com/api/introduction?utm_source=chatgpt.com "Introduction"
[9]: https://microsoft.github.io/presidio/anonymizer/?utm_source=chatgpt.com "Presidio Anonymizer"
[10]: https://spacy.io/api/entityrecognizer?utm_source=chatgpt.com "EntityRecognizer · spaCy API Documentation"
[11]: https://github.com/ollama/ollama/blob/main/docs/api.md?utm_source=chatgpt.com "ollama/docs/api.md at main"
[12]: https://crypto.stanford.edu/portia/papers/RevnissenbaumDTP31.pdf?utm_source=chatgpt.com "101 PRIVACY AS CONTEXTUAL INTEGRITY Helen ..."
[13]: https://ico.org.uk/for-organisations/uk-gdpr-guidance-and-resources/data-sharing/anonymisation/pseudonymisation/?utm_source=chatgpt.com "Pseudonymisation | ICO"
[14]: https://csrc.nist.gov/pubs/sp/800/38/g/r1/ipd?utm_source=chatgpt.com "SP 800-38G Rev. 1, Recommendation for Block Cipher Modes ..."
