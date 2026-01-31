"""Parser for OWL/XML (Web Ontology Language) format files.

Handles: OBI, EFO, NCIt, CDISC, Reactome and other OWL/RDF-XML ontologies.
Uses stdlib xml.etree -- no external dependencies.
"""

from pathlib import Path
from xml.etree import ElementTree as ET

from agentic_patterns.core.connectors.vocabulary.models import VocabularyTerm

OWL = "http://www.w3.org/2002/07/owl#"
RDF = "http://www.w3.org/1999/02/22-rdf-syntax-ns#"
RDFS = "http://www.w3.org/2000/01/rdf-schema#"
OBO_IN_OWL = "http://www.geneontology.org/formats/oboInOwl#"
SKOS = "http://www.w3.org/2004/02/skos/core#"
IAO_DEFINITION = "http://purl.obolibrary.org/obo/IAO_0000115"


def parse_owl(path: Path) -> list[VocabularyTerm]:
    """Parse an OWL/XML file into VocabularyTerm objects."""
    tree = ET.parse(path)
    root = tree.getroot()
    terms: list[VocabularyTerm] = []

    for cls in root.iter(f"{{{OWL}}}Class"):
        term = _parse_class(cls)
        if term and not term.metadata.get("deprecated"):
            terms.append(term)

    _resolve_children(terms)
    return terms


def _parse_class(cls: ET.Element) -> VocabularyTerm | None:
    """Parse a single owl:Class element."""
    about = cls.get(f"{{{RDF}}}about", "")
    if not about:
        return None

    term_id = _uri_to_id(about)
    label = _text(cls, f"{{{RDFS}}}label") or term_id
    definition = _text(cls, f"{{{IAO_DEFINITION}}}") or _text(cls, f"{{{SKOS}}}definition")

    synonyms: list[str] = []
    for tag in [f"{{{OBO_IN_OWL}}}hasExactSynonym", f"{{{OBO_IN_OWL}}}hasRelatedSynonym", f"{{{OBO_IN_OWL}}}hasBroadSynonym", f"{{{OBO_IN_OWL}}}hasNarrowSynonym", f"{{{SKOS}}}altLabel"]:
        for el in cls.findall(tag):
            if el.text and el.text.strip():
                synonyms.append(el.text.strip())

    parents: list[str] = []
    relationships: dict[str, list[str]] = {}
    for sc in cls.findall(f"{{{RDFS}}}subClassOf"):
        parent_uri = sc.get(f"{{{RDF}}}resource")
        if parent_uri:
            parents.append(_uri_to_id(parent_uri))
        else:
            _parse_restriction(sc, relationships)

    metadata: dict[str, str] = {}
    deprecated = cls.find(f"{{{OWL}}}deprecated")
    if deprecated is not None and deprecated.text == "true":
        metadata["deprecated"] = "true"

    return VocabularyTerm(
        id=term_id, label=label, synonyms=synonyms, definition=definition,
        parents=parents, relationships=relationships, metadata=metadata,
    )


def _parse_restriction(sc_element: ET.Element, relationships: dict[str, list[str]]) -> None:
    """Parse an owl:Restriction inside rdfs:subClassOf."""
    restriction = sc_element.find(f"{{{OWL}}}Restriction")
    if restriction is None:
        return
    prop_el = restriction.find(f"{{{OWL}}}onProperty")
    value_el = restriction.find(f"{{{OWL}}}someValuesFrom")
    if prop_el is None or value_el is None:
        return
    prop_uri = prop_el.get(f"{{{RDF}}}resource", "")
    value_uri = value_el.get(f"{{{RDF}}}resource", "")
    if prop_uri and value_uri:
        rel_type = _uri_to_id(prop_uri)
        target_id = _uri_to_id(value_uri)
        relationships.setdefault(rel_type, []).append(target_id)


def _uri_to_id(uri: str) -> str:
    """Convert a URI to a short ID (e.g., http://purl.obolibrary.org/obo/GO_0008150 -> GO:0008150)."""
    fragment = uri.rsplit("/", 1)[-1] if "/" in uri else uri
    fragment = fragment.rsplit("#", 1)[-1] if "#" in fragment else fragment
    if "_" in fragment and fragment.split("_", 1)[0].isupper():
        prefix, local = fragment.split("_", 1)
        return f"{prefix}:{local}"
    return fragment


def _text(element: ET.Element, tag: str) -> str | None:
    """Get text content of a child element."""
    child = element.find(tag)
    if child is not None and child.text:
        return child.text.strip()
    return None


def _resolve_children(terms: list[VocabularyTerm]) -> None:
    """Populate children lists from parent references."""
    by_id = {t.id: t for t in terms}
    for term in terms:
        for pid in term.parents:
            parent = by_id.get(pid)
            if parent and term.id not in parent.children:
                parent.children.append(term.id)
