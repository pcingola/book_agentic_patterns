"""Rubric construction (Stage 1) and refinement from history (Stage 2)."""

from __future__ import annotations

import hashlib
import json
import logging
from typing import TYPE_CHECKING

import numpy as np
from pydantic import BaseModel

from agentic_patterns.core.agents.agents import get_agent
from agentic_patterns.core.config.config import PROMPTS_DIR
from agentic_patterns.core.prompt import load_prompt
from agentic_patterns.core.rubric.models import RequirementLevel, Rubric, RubricItem
from agentic_patterns.core.vectordb.embeddings import embed_texts
from agentic_patterns.core.vectordb.models import Chunk, ChunkLevel, ClusterResult

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


# -- Stage 1: Build from policy --


class RubricBuilder:
    """Builds a rubric by extracting and canonicalizing requirements from a policy index."""

    def __init__(self, *, config_name: str = "default") -> None:
        self._config_name = config_name

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

        canonical = await self._canonicalize(candidates)
        items = self._assign_ids(canonical, salt=rubric_name)
        return Rubric(
            rubric_id=f"{rubric_name}_v1",
            provenance={
                "source": "policy_index",
                "version": 1,
                "n_chunks": len(candidates),
            },
            items=items,
        )

    async def _extract_all(self, policy_index: VectorDB) -> list[_CandidateRequirement]:
        result = policy_index.collection.get(include=["documents", "metadatas"])
        documents = result.get("documents", []) or []

        agent = get_agent(
            config_name=self._config_name, output_type=_ExtractedRequirements
        )
        all_candidates: list[_CandidateRequirement] = []

        for doc_text in documents:
            if not doc_text:
                continue
            prompt = load_prompt(
                RUBRIC_PROMPTS / "extract_requirements.md", chunk_text=doc_text
            )
            run_result = await agent.run(prompt)
            all_candidates.extend(run_result.output.requirements)

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
    policy_index: VectorDB,
    *,
    config_name: str = "default",
    promotion_threshold: int = 3,
    sim_threshold: float = 0.7,
) -> Rubric:
    """Refine a rubric using historical concerns (meeting minutes, audit findings, etc.)."""
    from agentic_patterns.agents.rag.clustering import label_clusters
    from agentic_patterns.core.vectordb.clustering import cluster

    concerns = await _extract_concerns(history_index, config_name=config_name)
    if not concerns:
        return rubric

    # Wrap concerns as Chunk objects for clustering
    chunks = [
        Chunk(
            doc_id=f"concern_{i}",
            text=c.text,
            level=ChunkLevel.PARAGRAPH,
            parent_id=None,
            metadata={},
        )
        for i, c in enumerate(concerns)
    ]
    cluster_result = cluster(chunks)
    cluster_result = await label_clusters(cluster_result)

    matched, unmatched_ids = await _map_clusters_to_items(
        cluster_result, rubric.items, sim_threshold
    )

    # Bump weights for matched items
    updated_items = []
    for item in rubric.items:
        if item.item_id in matched:
            n_matches = len(matched[item.item_id])
            updated = item.model_copy(update={"weight": item.weight + 0.1 * n_matches})
            updated_items.append(updated)
        else:
            updated_items.append(item)

    # Promote large unmatched clusters anchored in policy
    new_items = await _promote_unmatched(
        cluster_result,
        unmatched_ids,
        policy_index,
        promotion_threshold=promotion_threshold,
        rubric_salt=rubric.rubric_id,
        config_name=config_name,
    )
    updated_items.extend(new_items)

    # Bump version
    old_version = rubric.provenance.get("version", 1)
    return Rubric(
        rubric_id=rubric.rubric_id.rsplit("_v", 1)[0] + f"_v{old_version + 1}",
        provenance={
            **rubric.provenance,
            "version": old_version + 1,
            "history_refinement": True,
        },
        items=updated_items,
    )


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


async def _map_clusters_to_items(
    cluster_result: ClusterResult,
    items: list[RubricItem],
    sim_threshold: float = 0.7,
) -> tuple[dict[str, list[int]], list[int]]:
    """Map clusters to rubric items by cosine similarity. Returns (matched, unmatched_cluster_ids)."""
    if not cluster_result.clusters or not items:
        return {}, [c.cluster_id for c in cluster_result.clusters]

    cluster_texts = [c.summary or c.label or "" for c in cluster_result.clusters]
    item_texts = [item.requirement_text for item in items]

    cluster_embeddings = np.array(await embed_texts(cluster_texts))
    item_embeddings = np.array(await embed_texts(item_texts))

    # Normalize for cosine similarity
    cluster_norms = np.linalg.norm(cluster_embeddings, axis=1, keepdims=True)
    item_norms = np.linalg.norm(item_embeddings, axis=1, keepdims=True)
    cluster_embeddings = cluster_embeddings / np.where(
        cluster_norms == 0, 1, cluster_norms
    )
    item_embeddings = item_embeddings / np.where(item_norms == 0, 1, item_norms)

    # similarity_matrix[i][j] = cosine sim between cluster i and item j
    similarity_matrix = cluster_embeddings @ item_embeddings.T

    matched: dict[str, list[int]] = {}
    unmatched_ids: list[int] = []

    for ci, cluster in enumerate(cluster_result.clusters):
        best_j = int(np.argmax(similarity_matrix[ci]))
        best_sim = float(similarity_matrix[ci][best_j])
        if best_sim >= sim_threshold:
            item_id = items[best_j].item_id
            matched.setdefault(item_id, []).append(cluster.cluster_id)
        else:
            unmatched_ids.append(cluster.cluster_id)

    return matched, unmatched_ids


async def _promote_unmatched(
    cluster_result: ClusterResult,
    unmatched_ids: list[int],
    policy_index: VectorDB,
    *,
    promotion_threshold: int,
    rubric_salt: str,
    config_name: str,
) -> list[RubricItem]:
    """Promote unmatched clusters large enough and anchored in policy to new rubric items."""
    clusters_by_id = {c.cluster_id: c for c in cluster_result.clusters}
    new_items: list[RubricItem] = []

    agent = get_agent(config_name=config_name, output_type=_CanonicalizedItems)

    for cid in unmatched_ids:
        cluster = clusters_by_id[cid]
        if len(cluster.items) < promotion_threshold:
            continue

        # Check policy anchor
        query = cluster.summary or cluster.label or cluster.items[0].text
        anchors = policy_index.retrieve(query, max_results=3)
        if not anchors:
            continue

        # Ask LLM to formulate a new rubric item from the cluster + policy anchors
        anchor_text = "\n\n".join(f"[Policy] {a.text}" for a in anchors)
        concern_text = "\n".join(f"- {item.text}" for item in cluster.items)
        candidates_json = json.dumps(
            [
                {
                    "title": cluster.label or "Untitled",
                    "requirement_level": "SHOULD",
                    "requirement_text": f"Based on recurring concerns: {concern_text}\n\nPolicy context: {anchor_text}",
                    "evidence_required": [],
                    "framework_mappings": {},
                    "tags": [],
                }
            ],
            indent=2,
        )

        prompt = load_prompt(
            RUBRIC_PROMPTS / "canonicalize.md", candidates_json=candidates_json
        )
        run_result = await agent.run(prompt)

        for c in run_result.output.items:
            hash_input = f"{rubric_salt}:{c.requirement_text}"
            item_id = hashlib.sha256(hash_input.encode()).hexdigest()[:12]
            new_items.append(
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

    logger.info("Promoted %d new items from unmatched clusters", len(new_items))
    return new_items
