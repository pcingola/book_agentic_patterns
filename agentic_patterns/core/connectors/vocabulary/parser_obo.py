"""Parser for OBO (Open Biomedical Ontology) format files.

Handles: GO, ChEBI, HPO, DO, SO, CL and any standard OBO-format ontology.
"""

import re
from pathlib import Path

from agentic_patterns.core.connectors.vocabulary.models import VocabularyTerm


def parse_obo(path: Path) -> list[VocabularyTerm]:
    """Parse an OBO file into VocabularyTerm objects."""
    terms: list[VocabularyTerm] = []
    text = path.read_text(encoding="utf-8")
    blocks = text.split("\n[Term]\n")

    for block in blocks[1:]:  # skip header
        if block.startswith("[Typedef]") or "\n[Typedef]\n" in block:
            block = block.split("\n[Typedef]\n")[0]
        term = _parse_term_block(block)
        if term and not term.metadata.get("is_obsolete"):
            terms.append(term)

    _resolve_children(terms)
    return terms


def _parse_term_block(block: str) -> VocabularyTerm | None:
    """Parse a single [Term] block."""
    term_id = ""
    label = ""
    definition = None
    synonyms: list[str] = []
    parents: list[str] = []
    relationships: dict[str, list[str]] = {}
    metadata: dict[str, str] = {}
    xrefs: list[str] = []

    for line in block.strip().split("\n"):
        line = line.strip()
        if not line or line.startswith("!"):
            continue

        if line.startswith("id: "):
            term_id = line[4:].strip()
        elif line.startswith("name: "):
            label = line[6:].strip()
        elif line.startswith("def: "):
            definition = _extract_quoted(line[5:])
        elif line.startswith("synonym: "):
            syn = _extract_quoted(line[9:])
            if syn:
                synonyms.append(syn)
        elif line.startswith("is_a: "):
            parent_id = line[6:].split("!")[0].strip()
            parents.append(parent_id)
        elif line.startswith("relationship: "):
            parts = line[14:].split("!", 1)[0].strip().split(None, 1)
            if len(parts) == 2:
                rel_type, target_id = parts[0], parts[1].strip()
                relationships.setdefault(rel_type, []).append(target_id)
        elif line.startswith("xref: "):
            xrefs.append(line[6:].strip())
        elif line.startswith("is_obsolete: true"):
            metadata["is_obsolete"] = "true"
        elif line.startswith("namespace: "):
            metadata["namespace"] = line[11:].strip()
        elif line.startswith("alt_id: "):
            metadata.setdefault("alt_ids", "")
            if metadata["alt_ids"]:
                metadata["alt_ids"] += ","
            metadata["alt_ids"] += line[8:].strip()

    if not term_id:
        return None

    if xrefs:
        metadata["xrefs"] = ",".join(xrefs)

    return VocabularyTerm(
        id=term_id, label=label, synonyms=synonyms, definition=definition,
        parents=parents, relationships=relationships, metadata=metadata,
    )


def _extract_quoted(text: str) -> str | None:
    """Extract text between the first pair of double quotes."""
    match = re.search(r'"([^"]*)"', text)
    return match.group(1) if match else None


def _resolve_children(terms: list[VocabularyTerm]) -> None:
    """Populate children lists from parent references."""
    by_id = {t.id: t for t in terms}
    for term in terms:
        for pid in term.parents:
            parent = by_id.get(pid)
            if parent and term.id not in parent.children:
                parent.children.append(term.id)
