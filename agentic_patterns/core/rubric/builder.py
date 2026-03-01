"""Rubric construction (Stage 1) and refinement from history (Stage 2)."""

from __future__ import annotations

import hashlib
import json
import logging
from typing import TYPE_CHECKING

from pydantic import BaseModel

from agentic_patterns.core.agents.agents import get_agent
from agentic_patterns.core.config.config import PROMPTS_DIR
from agentic_patterns.core.prompt import load_prompt
from agentic_patterns.core.rubric.listener import RubricBuilderListener, RubricRefinerListener
from agentic_patterns.core.rubric.models import RequirementLevel, Rubric, RubricItem

if TYPE_CHECKING:
    from agentic_patterns.core.vectordb.vectordb import VectorDB

logger = logging.getLogger(__name__)

RUBRIC_PROMPTS = PROMPTS_DIR / "rubric"


# -- Internal LLM output models --


class _CandidateRequirement(BaseModel):
    title: str
    requirement_level: RequirementLevel
    requirement_text: str
    evidence_required: list[str]
    framework_mappings: dict[str, list[str]] = {}
    tags: list[str] = []


class _ExtractedRequirements(BaseModel):
    requirements: list[_CandidateRequirement]


class _CanonicalizedItems(BaseModel):
    items: list[_CandidateRequirement]


class _ConcernSentence(BaseModel):
    text: str


class _ExtractedConcerns(BaseModel):
    concerns: list[_ConcernSentence]


class _MappedConcern(BaseModel):
    concern_text: str
    item_id: str


class _NewConcern(BaseModel):
    concern_text: str
    title: str
    requirement_level: RequirementLevel
    requirement_text: str
    evidence_required: list[str]


class _ConcernMappingResult(BaseModel):
    mapped: list[_MappedConcern]
    new_concerns: list[_NewConcern]


# -- Stage 1: Build from policy --


class RubricBuilder:
    """Builds a rubric by extracting and canonicalizing requirements from a policy index."""

    def __init__(self, *, config_name: str = "default", listener: RubricBuilderListener | None = None) -> None:
        self._config_name = config_name
        self._listener = listener

    async def build_from_policy(
        self, policy_index: VectorDB, rubric_name: str = "rubric"
    ) -> Rubric:
        """Extract requirements from all policy chunks, deduplicate, and return a versioned Rubric."""
        candidates = await self._extract_all(policy_index)
        if not candidates:
            return Rubric(
                rubric_id=f"{rubric_name}_v1",
                provenance={"source": "policy_index", "version": 1},
                items=[],
            )

        if self._listener:
            await self._listener.on_canonicalize_start(len(candidates))
        canonical = await self._canonicalize(candidates)
        items = self._assign_ids(canonical, salt=rubric_name)
        rubric = Rubric(
            rubric_id=f"{rubric_name}_v1",
            provenance={
                "source": "policy_index",
                "version": 1,
                "n_chunks": len(candidates),
            },
            items=items,
        )
        if self._listener:
            await self._listener.on_done(rubric)
        return rubric

    async def _extract_all(self, policy_index: VectorDB) -> list[_CandidateRequirement]:
        result = policy_index.collection.get(include=["documents", "metadatas"])
        documents = result.get("documents", []) or []

        agent = get_agent(
            config_name=self._config_name, output_type=_ExtractedRequirements
        )
        all_candidates: list[_CandidateRequirement] = []

        if self._listener:
            await self._listener.on_extract_start(len(documents))

        for i, doc_text in enumerate(documents, 1):
            if not doc_text:
                continue
            prompt = load_prompt(
                RUBRIC_PROMPTS / "extract_requirements.md", chunk_text=doc_text
            )
            run_result = await agent.run(prompt)
            reqs = run_result.output.requirements
            all_candidates.extend(reqs)
            if self._listener:
                await self._listener.on_chunk_extracted(i, len(documents), len(reqs))

        logger.info(
            "Extracted %d candidate requirements from %d chunks",
            len(all_candidates),
            len(documents),
        )
        return all_candidates

    async def _canonicalize(
        self, candidates: list[_CandidateRequirement]
    ) -> list[_CandidateRequirement]:
        candidates_json = json.dumps([c.model_dump() for c in candidates], indent=2)
        agent = get_agent(
            config_name=self._config_name, output_type=_CanonicalizedItems
        )
        prompt = load_prompt(
            RUBRIC_PROMPTS / "canonicalize.md", candidates_json=candidates_json
        )
        run_result = await agent.run(prompt)
        logger.info(
            "Canonicalized %d candidates into %d items",
            len(candidates),
            len(run_result.output.items),
        )
        return run_result.output.items

    def _assign_ids(
        self, candidates: list[_CandidateRequirement], salt: str
    ) -> list[RubricItem]:
        items = []
        for c in candidates:
            hash_input = f"{salt}:{c.requirement_text}"
            item_id = hashlib.sha256(hash_input.encode()).hexdigest()[:12]
            items.append(
                RubricItem(
                    item_id=item_id,
                    title=c.title,
                    requirement_level=c.requirement_level,
                    requirement_text=c.requirement_text,
                    evidence_required=c.evidence_required,
                    framework_mappings=c.framework_mappings,
                    tags=set(c.tags),
                )
            )
        return items


# -- Stage 2: Refine with history --


async def refine_with_history(
    rubric: Rubric,
    history_index: VectorDB,
    *,
    config_name: str = "default",
    listener: RubricRefinerListener | None = None,
) -> Rubric:
    """Refine a rubric using historical audit findings.

    Each concern is mapped by the LLM to an existing rubric item (weight bump)
    or flagged as a genuinely new control gap (promoted to a new item).
    """
    concerns = await _extract_concerns(history_index, config_name=config_name)
    if not concerns:
        return rubric

    if listener:
        await listener.on_concerns_extracted(len(concerns))

    mapping = await _map_concerns(concerns, rubric.items, config_name=config_name)

    # Count how many concerns mapped to each item
    match_counts: dict[str, int] = {}
    for m in mapping.mapped:
        match_counts[m.item_id] = match_counts.get(m.item_id, 0) + 1

    updated_items = []
    for item in rubric.items:
        if item.item_id in match_counts:
            new_weight = round(item.weight + 0.1 * match_counts[item.item_id], 2)
            updated = item.model_copy(update={"weight": new_weight})
            if listener:
                await listener.on_weight_bumped(item, item.weight, new_weight)
            updated_items.append(updated)
        else:
            updated_items.append(item)

    # Promote genuinely new concerns
    new_items = []
    for nc in mapping.new_concerns:
        hash_input = f"{rubric.rubric_id}:{nc.requirement_text}"
        item_id = hashlib.sha256(hash_input.encode()).hexdigest()[:12]
        new_item = RubricItem(
            item_id=item_id,
            title=nc.title,
            requirement_level=nc.requirement_level,
            requirement_text=nc.requirement_text,
            evidence_required=nc.evidence_required,
        )
        new_items.append(new_item)
        if listener:
            await listener.on_item_promoted(new_item)
    updated_items.extend(new_items)

    old_version = rubric.provenance.get("version", 1)
    refined = Rubric(
        rubric_id=rubric.rubric_id.rsplit("_v", 1)[0] + f"_v{old_version + 1}",
        provenance={
            **rubric.provenance,
            "version": old_version + 1,
            "history_refinement": True,
        },
        items=updated_items,
    )
    if listener:
        await listener.on_done(refined)
    return refined


async def _extract_concerns(
    history_index: VectorDB, *, config_name: str
) -> list[_ConcernSentence]:
    result = history_index.collection.get(include=["documents"])
    documents = result.get("documents", []) or []

    agent = get_agent(config_name=config_name, output_type=_ExtractedConcerns)
    all_concerns: list[_ConcernSentence] = []

    for doc_text in documents:
        if not doc_text:
            continue
        prompt = load_prompt(
            RUBRIC_PROMPTS / "extract_concerns.md", chunk_text=doc_text
        )
        run_result = await agent.run(prompt)
        all_concerns.extend(run_result.output.concerns)

    logger.info(
        "Extracted %d concerns from %d history chunks",
        len(all_concerns),
        len(documents),
    )
    return all_concerns


async def _map_concerns(
    concerns: list[_ConcernSentence],
    items: list[RubricItem],
    *,
    config_name: str,
) -> _ConcernMappingResult:
    rubric_items_json = json.dumps(
        [{"item_id": i.item_id, "title": i.title, "requirement_text": i.requirement_text} for i in items],
        indent=2,
    )
    concerns_json = json.dumps([c.text for c in concerns], indent=2)
    agent = get_agent(config_name=config_name, output_type=_ConcernMappingResult)
    prompt = load_prompt(
        RUBRIC_PROMPTS / "map_concerns.md",
        rubric_items_json=rubric_items_json,
        concerns_json=concerns_json,
    )
    result = await agent.run(prompt)
    logger.info(
        "Mapped %d concerns: %d matched, %d new",
        len(concerns),
        len(result.output.mapped),
        len(result.output.new_concerns),
    )
    return result.output
