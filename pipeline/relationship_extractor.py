# ============================================================
# pipeline/relationship_extractor.py — Typed Relationship Extractor
# ============================================================
# This module identifies typed edges between concepts within each topic.
# It reads concepts grouped by topic, sends them to Gemma 4, and stores
# validated relationships in the concept_relationships table.
#
# HOW IT WORKS:
#   1. Load concepts grouped by topic from PostgreSQL
#   2. For each topic, send concept names + descriptions to Gemma 4
#   3. The LLM returns typed relationships (requires, enables, is_a, etc.)
#   4. Validate each relationship with the ExtractedRelationship Pydantic model
#   5. Match concept names to database IDs (fuzzy matching by slug)
#   6. Store edges in concept_relationships table
#
# WHY ONE LLM CALL PER TOPIC (not per concept pair)?
#   - 16 topics × 1 call = 16 LLM calls
#   - Per-pair would be C(176,2) ≈ 15,000 calls (impossible)
#   - The LLM needs to see ALL concepts in a topic to find meaningful connections
#
# FUZZY NAME MATCHING:
#   The LLM returns concept names as free text. These might not exactly match
#   the names in our database (e.g., LLM says "async await" but DB has "async/await").
#   We match by slugifying both names and comparing.
#
# RELATIONSHIP TYPES (7 types from RelationshipType enum):
#   - requires:   You must know A before B
#   - enables:    Knowing A unlocks B
#   - is_a:       A is a type/subtype of B
#   - part_of:    A is a component of B
#   - related_to: General connection
#   - contrasts_with: A and B are alternatives/opposing
#   - built_on:   A is built on top of B
# ============================================================

import json
import logging
import re
from typing import Optional

from langchain_ollama import ChatOllama
from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import ValidationError
from sqlalchemy.orm import Session

from database.connection import SessionLocal
from database.models import Concept, ConceptRelationship, Topic
from models.enrichment import (
    ExtractedRelationship,
    RelationshipExtractionResult,
    VALID_RELATIONSHIP_TYPES,
)
from pipeline.concept_extractor import slugify

logger = logging.getLogger(__name__)


RELATIONSHIP_EXTRACTION_PROMPT = f"""You are a knowledge graph construction assistant. Your job is to identify TYPED RELATIONSHIPS between programming concepts.

Given a list of concepts from a learning topic, identify how they relate to each other.

VALID RELATIONSHIP TYPES (use EXACTLY these values):
- "requires" — You must know concept A before you can understand concept B
- "enables" — Knowing concept A unlocks/makes possible concept B
- "is_a" — Concept A is a specific type/subtype of concept B
- "part_of" — Concept A is a component or piece of concept B
- "related_to" — General connection between A and B (use when no specific type fits)
- "contrasts_with" — Concept A and B are alternatives, opposites, or different approaches
- "built_on" — Concept A is built on top of / uses concept B as foundation

RULES:
1. Only create relationships between concepts that are ACTUALLY related — no forced connections.
2. Each relationship should represent a real pedagogical or technical dependency.
3. Aim for 3-10 relationships per topic (quality over quantity).
4. Include a brief description explaining WHY the relationship exists.
5. Assign a strength score (0.0-1.0): 1.0 = essential connection, 0.5 = loose connection.
6. "requires" relationships are the most valuable — they form learning paths.
7. Do NOT create self-referencing relationships (A → A).
8. Prefer "requires" over "related_to" when one concept truly depends on another.

You MUST respond with ONLY valid JSON:
{{
  "relationships": [
    {{
      "from_concept": "concept name",
      "to_concept": "concept name",
      "relationship_type": "requires",
      "description": "Brief explanation of why this relationship exists",
      "strength": 0.9
    }}
  ]
}}

GOOD EXAMPLES:
Concepts: ["async/await", "coroutines", "event loop", "futures", "callbacks", "tasks"]
Output:
{{
  "relationships": [
    {{"from_concept": "async/await", "to_concept": "coroutines", "relationship_type": "requires", "description": "async/await is built on coroutine objects and requires understanding how coroutines pause and resume", "strength": 0.95}},
    {{"from_concept": "async/await", "to_concept": "event loop", "relationship_type": "requires", "description": "The event loop drives async execution — you need to understand it to use async/await effectively", "strength": 0.9}},
    {{"from_concept": "event loop", "to_concept": "callbacks", "relationship_type": "built_on", "description": "The event loop processes callbacks as its fundamental scheduling mechanism", "strength": 0.85}},
    {{"from_concept": "futures", "to_concept": "tasks", "relationship_type": "enables", "description": "Futures provide the result placeholder that Tasks wrap with coroutine execution", "strength": 0.8}}
  ]
}}
"""


class RelationshipExtractor:
    """
    Extracts typed relationships between concepts using Gemma 4 via Ollama.

    USAGE:
        extractor = RelationshipExtractor()
        stats = await extractor.extract_all()
        print(f"Created {stats['total_relationships']} edges")
    """

    def __init__(
        self,
        model_name: str = "gemma4:26b",
        base_url: str = "http://localhost:11434",
        temperature: float = 0.2,
        num_ctx: int = 8192,
        max_retries: int = 3,
    ):
        """
        Initialize the RelationshipExtractor.

        Args:
            model_name: Ollama model tag.
            base_url: Ollama server URL.
            temperature: 0.2 — low creativity, we want accurate relationship types.
            num_ctx: 16K context — concept names + descriptions fit comfortably.
            max_retries: Retry count for LLM failures.
        """
        self.model_name = model_name
        self.max_retries = max_retries

        self.llm = ChatOllama(
            model=model_name,
            base_url=base_url,
            temperature=temperature,
            num_ctx=num_ctx,
            format="json",
        )

        logger.info(
            f"RelationshipExtractor initialized: model={model_name}, "
            f"ctx={num_ctx}, temp={temperature}"
        )

    async def extract_for_topic(self, topic_id: int) -> RelationshipExtractionResult:
        """
        Extract relationships between concepts within a single topic.

        Args:
            topic_id: The database ID of the topic.

        Returns:
            RelationshipExtractionResult with validated relationships.
        """
        with SessionLocal() as session:
            topic = session.query(Topic).filter(Topic.id == topic_id).first()
            if not topic:
                logger.error(f"Topic ID {topic_id} not found")
                return RelationshipExtractionResult()

            topic_name = topic.name
            concepts = (
                session.query(Concept)
                .filter(Concept.topic_id == topic_id)
                .all()
            )

        if len(concepts) < 2:
            logger.info(
                f"Topic '{topic_name}' has {len(concepts)} concepts — "
                f"need at least 2 for relationships"
            )
            return RelationshipExtractionResult(topic_name=topic_name)

        concept_list = []
        for c in concepts:
            entry = f"  - {c.name} ({c.category}, difficulty {c.difficulty})"
            if c.theory_text:
                entry += f": {c.theory_text[:50]}"
            concept_list.append(entry)

        prompt_text = (
            f"Find the relationships between these concepts from the topic "
            f"'{topic_name}':\n\n"
            + "\n".join(concept_list)
        )

        messages = [
            SystemMessage(content=RELATIONSHIP_EXTRACTION_PROMPT),
            HumanMessage(content=prompt_text),
        ]

        last_error: Optional[str] = None

        for attempt in range(1, self.max_retries + 1):
            try:
                logger.info(
                    f"Extracting relationships for '{topic_name}' "
                    f"({len(concepts)} concepts, attempt {attempt})"
                )

                response = await self.llm.ainvoke(messages)
                raw_response = response.content

                cleaned = self._clean_json_response(raw_response)
                cleaned = re.sub(r"['\"]\/(\w+)['\"]", r'"\1"', cleaned)
                parsed = json.loads(cleaned)

                raw_rels = parsed.get("relationships", [])
                if not raw_rels:
                    logger.warning(f"LLM returned empty relationships for '{topic_name}'")
                    return RelationshipExtractionResult(topic_name=topic_name)

                validated: list[ExtractedRelationship] = []
                for raw_rel in raw_rels:
                    if not isinstance(raw_rel, dict):
                        continue
                    # Fix Gemma 4 quoted-value quirk
                    for key in list(raw_rel.keys()):
                        val = raw_rel[key]
                        if isinstance(val, str):
                            raw_rel[key] = val.strip("'\"")
                    try:
                        rel = ExtractedRelationship(**raw_rel)
                        validated.append(rel)
                    except ValidationError as ve:
                        logger.warning(f"Skipping invalid relationship: {ve}")

                logger.info(
                    f"Extracted {len(validated)}/{len(raw_rels)} valid "
                    f"relationships for '{topic_name}'"
                )

                return RelationshipExtractionResult(
                    relationships=validated,
                    topic_name=topic_name,
                    model_name=self.model_name,
                )

            except json.JSONDecodeError as e:
                last_error = f"JSON error: {e}"
                logger.warning(f"Attempt {attempt}: {last_error}")
            except ConnectionError as e:
                last_error = f"Connection error: {e}"
                logger.warning(f"Attempt {attempt}: {last_error}")
            except Exception as e:
                last_error = f"{type(e).__name__}: {e}"
                logger.warning(f"Attempt {attempt}: {last_error}")

        logger.error(f"All retries failed for '{topic_name}': {last_error}")
        return RelationshipExtractionResult(topic_name=topic_name)

    def store_relationships(
        self,
        result: RelationshipExtractionResult,
        topic_id: int,
    ) -> tuple[int, int, int]:
        """
        Store extracted relationships in the database.

        This matches LLM-returned concept names to database concept IDs
        using slug-based fuzzy matching.

        Returns:
            Tuple of (stored_count, unmatched_count, duplicate_count)
        """
        with SessionLocal() as session:
            concepts = (
                session.query(Concept)
                .filter(Concept.topic_id == topic_id)
                .all()
            )

            # Build slug → concept_id lookup for matching
            slug_to_id: dict[str, int] = {}
            name_to_id: dict[str, int] = {}
            for c in concepts:
                slug_to_id[slugify(c.name)] = c.id
                name_to_id[c.name.lower().strip()] = c.id

            # Also check existing relationships to avoid duplicates
            existing_edges: set[tuple[int, int, str]] = set()
            for c in concepts:
                for rel in c.outgoing_relationships:
                    existing_edges.add(
                        (rel.from_concept_id, rel.to_concept_id, rel.relationship_type)
                    )

        stored = 0
        unmatched = 0
        duplicates = 0

        with SessionLocal() as session:
            for rel in result.relationships:
                from_id = self._match_concept(rel.from_concept, slug_to_id, name_to_id)
                to_id = self._match_concept(rel.to_concept, slug_to_id, name_to_id)

                if not from_id or not to_id:
                    logger.debug(
                        f"Could not match: '{rel.from_concept}' → '{rel.to_concept}' "
                        f"(from_id={from_id}, to_id={to_id})"
                    )
                    unmatched += 1
                    continue

                if from_id == to_id:
                    logger.debug(f"Self-referencing relationship skipped: {rel.from_concept}")
                    unmatched += 1
                    continue

                edge_key = (from_id, to_id, rel.relationship_type)
                if edge_key in existing_edges:
                    duplicates += 1
                    continue

                db_rel = ConceptRelationship(
                    from_concept_id=from_id,
                    to_concept_id=to_id,
                    relationship_type=rel.relationship_type,
                    description=rel.description,
                    strength=rel.strength,
                    source=self.model_name,
                )
                session.add(db_rel)
                existing_edges.add(edge_key)
                stored += 1

            try:
                session.commit()
                logger.info(
                    f"Stored {stored} relationships for '{result.topic_name}' "
                    f"({unmatched} unmatched, {duplicates} duplicates)"
                )
            except Exception as e:
                session.rollback()
                logger.error(f"Failed to commit relationships: {e}")
                raise

        return stored, unmatched, duplicates

    @staticmethod
    def _match_concept(
        name: str,
        slug_to_id: dict[str, int],
        name_to_id: dict[str, int],
    ) -> Optional[int]:
        """
        Match an LLM-returned concept name to a database concept ID.

        Matching strategy (in order):
          1. Exact name match (case-insensitive)
          2. Slug match (handles formatting differences)
          3. Partial slug match (handles shortened names)
        """
        # Exact name match
        normalized = name.lower().strip()
        if normalized in name_to_id:
            return name_to_id[normalized]

        # Slug match
        name_slug = slugify(name)
        if name_slug in slug_to_id:
            return slug_to_id[name_slug]

        # Partial slug match — check if the LLM name is a substring
        # of any stored concept slug or vice versa
        for stored_slug, cid in slug_to_id.items():
            if name_slug in stored_slug or stored_slug in name_slug:
                return cid

        return None

    async def extract_all(self) -> dict:
        """
        Extract relationships for all topics that have 2+ concepts.

        Returns:
            Dict with summary statistics.
        """
        with SessionLocal() as session:
            topics = session.query(Topic).all()

        stats = {
            "topics_processed": 0,
            "total_relationships": 0,
            "total_unmatched": 0,
            "total_duplicates": 0,
            "topics_skipped": 0,
            "topics_failed": 0,
            "errors": [],
        }

        for topic in topics:
            with SessionLocal() as session:
                concept_count = (
                    session.query(Concept)
                    .filter(Concept.topic_id == topic.id)
                    .count()
                )

            if concept_count < 2:
                stats["topics_skipped"] += 1
                continue

            try:
                result = await self.extract_for_topic(topic.id)

                if not result.relationships:
                    stats["topics_processed"] += 1
                    continue

                stored, unmatched, dupes = self.store_relationships(
                    result, topic.id
                )

                stats["topics_processed"] += 1
                stats["total_relationships"] += stored
                stats["total_unmatched"] += unmatched
                stats["total_duplicates"] += dupes

                logger.info(
                    f"[{stats['topics_processed']}] '{topic.name}': "
                    f"{stored} relationships stored, {unmatched} unmatched"
                )

            except Exception as e:
                logger.error(f"Failed for topic '{topic.name}': {e}")
                stats["topics_failed"] += 1
                stats["errors"].append(f"{topic.name}: {e}")

        logger.info(
            f"\n{'='*60}\n"
            f"RELATIONSHIP EXTRACTION COMPLETE\n"
            f"{'='*60}\n"
            f"Topics processed: {stats['topics_processed']}\n"
            f"Total relationships: {stats['total_relationships']}\n"
            f"Unmatched concepts: {stats['total_unmatched']}\n"
            f"Duplicates skipped: {stats['total_duplicates']}\n"
            f"Topics skipped (<2 concepts): {stats['topics_skipped']}\n"
            f"Topics failed: {stats['topics_failed']}\n"
            f"{'='*60}"
        )

        return stats

    @staticmethod
    def _clean_json_response(text: str) -> str:
        """Extract JSON from LLM response."""
        text = re.sub(r"```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```", "", text)

        start = text.find("{")
        end = text.rfind("}") + 1
        if start >= 0 and end > start:
            return text[start:end]

        return text.strip()
