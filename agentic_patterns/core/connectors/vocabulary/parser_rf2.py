"""Parser for UMLS RF2 (Release Format 2) files.

Handles: SNOMED-CT, RxNorm and other UMLS-distributed terminologies.
RF2 uses tab-separated files: concepts, descriptions, and relationships.
"""

import csv
from pathlib import Path

from agentic_patterns.core.connectors.vocabulary.models import VocabularyTerm

ACTIVE = "1"
FSN_TYPE = "900000000000003001"  # Fully Specified Name
SYNONYM_TYPE = "900000000000013009"
IS_A_TYPE = "116680003"


def parse_rf2(snapshot_dir: Path) -> list[VocabularyTerm]:
    """Parse RF2 snapshot directory containing Concept, Description, and Relationship files."""
    concept_file = _find_file(snapshot_dir, "Concept")
    description_file = _find_file(snapshot_dir, "Description")
    relationship_file = _find_file(snapshot_dir, "Relationship")

    active_concepts = _load_active_concepts(concept_file)
    labels, synonyms = _load_descriptions(description_file, active_concepts)
    parents, relationships = _load_relationships(relationship_file, active_concepts)

    terms: list[VocabularyTerm] = []
    for cid in active_concepts:
        label = labels.get(cid, cid)
        term = VocabularyTerm(
            id=cid,
            label=label,
            synonyms=synonyms.get(cid, []),
            parents=parents.get(cid, []),
            relationships=relationships.get(cid, {}),
        )
        terms.append(term)

    _resolve_children(terms)
    return terms


def _find_file(snapshot_dir: Path, file_type: str) -> Path:
    """Find an RF2 file by type pattern (e.g., 'Concept', 'Description', 'Relationship')."""
    pattern = f"*{file_type}*"
    matches = list(snapshot_dir.glob(pattern))
    if not matches:
        raise FileNotFoundError(f"No {file_type} file found in {snapshot_dir}")
    return matches[0]


def _load_active_concepts(path: Path) -> set[str]:
    """Load active concept IDs from the Concept file."""
    active: set[str] = set()
    with open(path, encoding="utf-8") as f:
        reader = csv.DictReader(f, delimiter="\t")
        for row in reader:
            if row.get("active") == ACTIVE:
                active.add(row["id"])
    return active


def _load_descriptions(
    path: Path, active_concepts: set[str]
) -> tuple[dict[str, str], dict[str, list[str]]]:
    """Load labels (FSN) and synonyms from the Description file."""
    labels: dict[str, str] = {}
    synonyms: dict[str, list[str]] = {}
    with open(path, encoding="utf-8") as f:
        reader = csv.DictReader(f, delimiter="\t")
        for row in reader:
            if row.get("active") != ACTIVE:
                continue
            cid = row.get("conceptId", "")
            if cid not in active_concepts:
                continue
            term_text = row.get("term", "")
            type_id = row.get("typeId", "")
            if type_id == FSN_TYPE:
                # Strip semantic tag: "Heart (body structure)" -> "Heart"
                label = (
                    term_text.rsplit("(", 1)[0].strip()
                    if "(" in term_text
                    else term_text
                )
                labels[cid] = label
            elif type_id == SYNONYM_TYPE:
                synonyms.setdefault(cid, []).append(term_text)
    return labels, synonyms


def _load_relationships(
    path: Path, active_concepts: set[str]
) -> tuple[dict[str, list[str]], dict[str, dict[str, list[str]]]]:
    """Load is_a parents and other relationships from the Relationship file."""
    parents: dict[str, list[str]] = {}
    relationships: dict[str, dict[str, list[str]]] = {}
    with open(path, encoding="utf-8") as f:
        reader = csv.DictReader(f, delimiter="\t")
        for row in reader:
            if row.get("active") != ACTIVE:
                continue
            source_id = row.get("sourceId", "")
            dest_id = row.get("destinationId", "")
            type_id = row.get("typeId", "")
            if source_id not in active_concepts:
                continue
            if type_id == IS_A_TYPE:
                parents.setdefault(source_id, []).append(dest_id)
            else:
                relationships.setdefault(source_id, {}).setdefault(type_id, []).append(
                    dest_id
                )
    return parents, relationships


def _resolve_children(terms: list[VocabularyTerm]) -> None:
    """Populate children lists from parent references."""
    by_id = {t.id: t for t in terms}
    for term in terms:
        for pid in term.parents:
            parent = by_id.get(pid)
            if parent and term.id not in parent.children:
                parent.children.append(term.id)
