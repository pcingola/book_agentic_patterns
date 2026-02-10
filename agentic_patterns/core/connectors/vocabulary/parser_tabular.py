"""Parsers for JSON, CSV, TSV, MeSH XML, and GMT formats.

Handles: NDC (JSON), UNII (JSON), HGNC (TSV/JSON), Ensembl Biotypes (JSON),
MeSH (XML), WikiPathways (GMT).
"""

import csv
import json
from pathlib import Path
from xml.etree import ElementTree as ET

from agentic_patterns.core.connectors.vocabulary.models import VocabularyTerm


def parse_json_flat(
    path: Path,
    id_field: str = "id",
    label_field: str = "label",
    synonym_fields: list[str] | None = None,
    definition_field: str | None = "definition",
) -> list[VocabularyTerm]:
    """Parse a JSON file with flat term objects (no hierarchy). For Ensembl Biotypes, NDC, UNII."""
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, dict):
        # Try common wrapper keys
        for key in ("terms", "results", "data", "records"):
            if key in data:
                data = data[key]
                break
    if not isinstance(data, list):
        raise ValueError(
            f"Expected a JSON array or dict with list field, got {type(data).__name__}"
        )

    terms: list[VocabularyTerm] = []
    for item in data:
        term_id = str(item.get(id_field, ""))
        if not term_id:
            continue
        label = str(item.get(label_field, term_id))
        synonyms = []
        for sf in synonym_fields or []:
            val = item.get(sf)
            if isinstance(val, list):
                synonyms.extend(str(v) for v in val)
            elif val:
                synonyms.append(str(val))
        definition = (
            str(item[definition_field])
            if definition_field and definition_field in item
            else None
        )
        terms.append(
            VocabularyTerm(
                id=term_id, label=label, synonyms=synonyms, definition=definition
            )
        )
    return terms


def parse_json_hierarchical(
    path: Path,
    id_field: str = "id",
    label_field: str = "label",
    parent_field: str = "parents",
    children_field: str = "children",
    synonym_fields: list[str] | None = None,
    definition_field: str | None = "definition",
) -> list[VocabularyTerm]:
    """Parse a JSON file with hierarchical terms (parent/children fields)."""
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, dict):
        for key in ("terms", "results", "data", "records"):
            if key in data:
                data = data[key]
                break

    terms: list[VocabularyTerm] = []
    for item in data:
        term_id = str(item.get(id_field, ""))
        if not term_id:
            continue
        label = str(item.get(label_field, term_id))
        parents = item.get(parent_field, [])
        children = item.get(children_field, [])
        synonyms = []
        for sf in synonym_fields or []:
            val = item.get(sf)
            if isinstance(val, list):
                synonyms.extend(str(v) for v in val)
            elif val:
                synonyms.append(str(val))
        definition = (
            str(item[definition_field])
            if definition_field and definition_field in item
            else None
        )
        terms.append(
            VocabularyTerm(
                id=term_id,
                label=label,
                parents=parents,
                children=children,
                synonyms=synonyms,
                definition=definition,
            )
        )
    return terms


def parse_csv(
    path: Path,
    id_field: str = "id",
    label_field: str = "label",
    delimiter: str | None = None,
    synonym_fields: list[str] | None = None,
    definition_field: str | None = "definition",
    parent_field: str | None = None,
) -> list[VocabularyTerm]:
    """Parse CSV/TSV into VocabularyTerm objects. Auto-detects delimiter if not given."""
    text = path.read_text(encoding="utf-8")
    if delimiter is None:
        delimiter = "\t" if path.suffix in (".tsv", ".tab") else ","

    reader = csv.DictReader(text.splitlines(), delimiter=delimiter)
    terms: list[VocabularyTerm] = []
    for row in reader:
        term_id = row.get(id_field, "").strip()
        if not term_id:
            continue
        label = row.get(label_field, term_id).strip()
        synonyms = []
        for sf in synonym_fields or []:
            val = (row.get(sf) or "").strip()
            if val:
                synonyms.extend(s.strip() for s in val.split("|") if s.strip())
        definition = (
            (row.get(definition_field) or "").strip() if definition_field else None
        )
        parents = []
        if parent_field:
            pval = (row.get(parent_field) or "").strip()
            if pval:
                parents = [p.strip() for p in pval.split("|") if p.strip()]
        terms.append(
            VocabularyTerm(
                id=term_id,
                label=label,
                synonyms=synonyms,
                definition=definition or None,
                parents=parents,
            )
        )

    if parent_field:
        _resolve_children(terms)
    return terms


def parse_mesh_xml(path: Path) -> list[VocabularyTerm]:
    """Parse MeSH XML (descriptor records) into VocabularyTerm objects."""
    tree = ET.parse(path)
    root = tree.getroot()
    terms: list[VocabularyTerm] = []

    for record in root.iter("DescriptorRecord"):
        uid_el = record.find("DescriptorUI")
        name_el = record.find("DescriptorName/String")
        if uid_el is None or name_el is None:
            continue
        term_id = uid_el.text.strip()
        label = name_el.text.strip()

        synonyms: list[str] = []
        for concept in record.iter("Concept"):
            for term_el in concept.iter("Term"):
                string_el = term_el.find("String")
                if string_el is not None and string_el.text:
                    syn = string_el.text.strip()
                    if syn != label:
                        synonyms.append(syn)

        definition = None
        scope_note = record.find(".//ScopeNote")
        if scope_note is not None and scope_note.text:
            definition = scope_note.text.strip()

        parents: list[str] = []
        for tree_num in record.iter("TreeNumber"):
            if tree_num.text:
                tn = tree_num.text.strip()
                if "." in tn:
                    parents.append(tn.rsplit(".", 1)[0])

        terms.append(
            VocabularyTerm(
                id=term_id,
                label=label,
                synonyms=synonyms,
                definition=definition,
                metadata={
                    "tree_numbers": ",".join(
                        tn.text.strip() for tn in record.iter("TreeNumber") if tn.text
                    )
                },
            )
        )

    return terms


def parse_gmt(path: Path) -> list[VocabularyTerm]:
    """Parse GMT (Gene Matrix Transposed) format for pathway databases like WikiPathways."""
    terms: list[VocabularyTerm] = []
    for line in path.read_text(encoding="utf-8").strip().split("\n"):
        parts = line.split("\t")
        if len(parts) < 3:
            continue
        label = parts[0].strip()
        description = parts[1].strip() if parts[1].strip() else None
        genes = [g.strip() for g in parts[2:] if g.strip()]
        term_id = label.replace(" ", "_")
        terms.append(
            VocabularyTerm(
                id=term_id,
                label=label,
                definition=description,
                metadata={"genes": ",".join(genes), "gene_count": str(len(genes))},
            )
        )
    return terms


def _resolve_children(terms: list[VocabularyTerm]) -> None:
    """Populate children lists from parent references."""
    by_id = {t.id: t for t in terms}
    for term in terms:
        for pid in term.parents:
            parent = by_id.get(pid)
            if parent and term.id not in parent.children:
                parent.children.append(term.id)
