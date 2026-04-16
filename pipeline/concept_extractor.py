# ============================================================
# pipeline/concept_extractor.py — LLM Concept Extraction Pipeline
# ============================================================
# This module takes scraped articles grouped by topic, sends them to
# Gemma 4 via Ollama, and extracts structured concepts.
#
# HOW IT WORKS:
#   1. Read all articles for a topic from PostgreSQL
#   2. Concatenate article text (with length limits for LLM context)
#   3. Send to Gemma 4 with a carefully crafted prompt
#   4. Parse JSON response → validate with Pydantic ExtractedConcept
#   5. Deduplicate by slug within the topic
#   6. Store validated concepts in the `concepts` table
#
# WHY ONE LLM CALL PER TOPIC (not per article)?
#   - ~23 topics × 1 call = 23 LLM calls (manageable)
#   - Per-article would be ~53 calls and produce MORE duplicates
#   - Grouping by topic gives the LLM context to identify related concepts
#     and avoid extracting the same thing under different names
#
# DEDUPLICATION STRATEGY:
#   We slugify concept names (lowercase, replace spaces/special chars with hyphens)
#   and keep only one concept per slug within each topic. If the LLM returns both
#   "Async/Await" and "async await", the slug is "async-await" for both, and we
#   keep whichever was extracted first.
#
# ERROR HANDLING:
#   - LLM might return malformed JSON → retry up to N times
#   - Ollama might be down → ConnectionError caught
#   - Individual concepts might fail validation → skip them, log warning
#   - A topic with no articles → skip it entirely
# ============================================================

import json
import logging
import re
import unicodedata
from typing import Optional

from langchain_ollama import ChatOllama
from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import ValidationError
from sqlalchemy.orm import Session

from database.connection import SessionLocal
from database.models import Concept, Topic, RawArticle
from models.enrichment import ExtractedConcept, ConceptExtractionResult

logger = logging.getLogger(__name__)


# ----------------------------------------------------------
# SYSTEM PROMPT — Concept Extraction Instructions
# ----------------------------------------------------------
# This prompt tells Gemma 4 exactly what we want: a list of concepts
# from educational documentation, each with a category and difficulty.
#
# KEY DESIGN CHOICES:
#   - We specify the 5 valid categories to avoid invalid responses
#   - We give examples (few-shot prompting) for better output quality
#   - We set MIN/MAX concept counts to control output size
#   - We ask for descriptions to populate the concept record
#   - We enforce STRICT JSON output for reliable parsing
# ----------------------------------------------------------
CONCEPT_EXTRACTION_PROMPT = """You are an educational content analyst. Your job is to identify key LEARNABLE CONCEPTS from technical documentation about programming tools and technologies.

A "concept" is a distinct thing someone needs to understand — a language feature, a framework component, a tool, a design pattern, or an abstract idea.

For each concept, provide:
1. **name**: Clear, concise name (e.g., "async/await", "SQLAlchemy ORM", "Docker Compose")
2. **category**: Exactly one of these 5 values:
   - "language_feature" — Built-in language capability (async/await, decorators, type hints)
   - "framework" — Part of a framework/library (FastAPI routes, Pydantic models, LangChain chains)
   - "tool" — Standalone tool or application (Docker, Ollama, Weaviate, Playwright)
   - "pattern" — Design pattern or architectural approach (RAG, semantic search, dependency injection)
   - "concept" — Abstract idea or principle (embeddings, vector similarity, event loop)
3. **difficulty**: Integer 1-5 where:
   - 1 = Beginner (basic syntax, simple commands)
   - 2 = Elementary (common operations, simple patterns)
   - 3 = Intermediate (requires understanding of prerequisites)
   - 4 = Advanced (complex systems, performance tuning)
   - 5 = Expert (internals, optimization, cutting-edge)
4. **description**: 1-3 sentence explanation of what this concept is and why it matters

RULES:
1. Extract 5-15 concepts per topic — focus on the MOST IMPORTANT ones.
2. Do NOT extract concepts that are too broad ("programming", "software") or too narrow ("import statement on line 5").
3. Each concept should be a distinct learnable unit — something you could write a tutorial about.
4. Avoid near-duplicates. If "async function" and "async/await" refer to the same thing, pick one.
5. Descriptions should be EDUCATIONAL — explain the concept, don't just repeat the name.

You MUST respond with ONLY valid JSON in this exact format:
{
  "concepts": [
    {"name": "...", "category": "...", "difficulty": 3, "description": "..."},
    {"name": "...", "category": "...", "difficulty": 2, "description": "..."}
  ]
}

GOOD EXAMPLES:
Input: "FastAPI is a modern web framework. It uses Pydantic for data validation and supports async endpoints."
Output:
{
  "concepts": [
    {"name": "FastAPI", "category": "framework", "difficulty": 2, "description": "A modern Python web framework designed for building APIs with automatic documentation generation."},
    {"name": "Pydantic validation", "category": "framework", "difficulty": 2, "description": "Automatic request/response validation using Python type hints, integrated deeply into FastAPI."},
    {"name": "async endpoints", "category": "framework", "difficulty": 3, "description": "FastAPI endpoints that use async/await for non-blocking I/O operations, enabling high concurrency."}
  ]
}

BAD EXAMPLES (DO NOT extract):
- {"name": "web framework", "category": "concept"} — too broad
- {"name": "import FastAPI", "category": "language_feature"} — too narrow (just an import)
- {"name": "programming", "category": "concept"} — way too broad
"""


def slugify(text: str) -> str:
    """
    Convert a concept name to a URL-friendly slug for deduplication.

    Examples:
        "async/await" → "async-await"
        "Pydantic Models" → "pydantic-models"
        "RAG (Retrieval-Augmented Generation)" → "rag-retrieval-augmented-generation"

    This follows Django's slugify approach: lowercase, replace non-alphanumeric
    with hyphens, collapse multiple hyphens, strip leading/trailing hyphens.
    """
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    text = text.lower()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    text = re.sub(r"-+", "-", text)
    text = text.strip("-")
    return text


class ConceptExtractor:
    """
    Extracts learnable concepts from scraped articles using Gemma 4 via Ollama.

    This follows the same pattern as TripleExtractor:
      - Initialize with model config
      - Call extract_for_topic() for each topic
      - LLM returns JSON → Pydantic validates → SQLAlchemy stores

    USAGE:
        extractor = ConceptExtractor()
        result = await extractor.extract_for_topic(topic_id=1)
        print(f"Extracted {len(result.concepts)} concepts")
    """

    def __init__(
        self,
        model_name: str = "gemma4:26b",
        base_url: str = "http://localhost:11434",
        temperature: float = 0.2,
        num_ctx: int = 32768,
        max_retries: int = 3,
        max_article_chars: int = 25000,
    ):
        """
        Initialize the ConceptExtractor.

        Args:
            model_name: Ollama model tag (default: "gemma4:26b" for Gemma 4 26B).
            base_url: Ollama server URL.
            temperature: 0.2 — slightly creative (we want diverse concepts)
                but still mostly deterministic (we don't want random categories).
            num_ctx: Context window in tokens. 32768 ≈ 24K words.
            max_retries: How many times to retry on LLM failure.
            max_article_chars: Truncate concatenated article text to this many
                characters to stay within the LLM's context window.
        """
        self.model_name = model_name
        self.max_retries = max_retries
        self.max_article_chars = max_article_chars

        self.llm = ChatOllama(
            model=model_name,
            base_url=base_url,
            temperature=temperature,
            num_ctx=num_ctx,
            format="json",
        )

        logger.info(
            f"ConceptExtractor initialized: model={model_name}, "
            f"ctx={num_ctx}, temp={temperature}, max_chars={max_article_chars}"
        )

    def _gather_topic_text(self, session: Session, topic_id: int) -> tuple[str, list[str]]:
        """
        Gather all article text for a topic, concatenated and truncated.

        Returns:
            Tuple of (concatenated_text, list_of_article_urls)
        """
        articles = (
            session.query(RawArticle)
            .filter(RawArticle.topic_id == topic_id)
            .all()
        )

        if not articles:
            return "", []

        parts = []
        urls = []
        total_chars = 0

        for article in articles:
            text = article.raw_text or ""
            if not text.strip():
                continue

            # Add article separator with title for context
            header = f"\n--- Article: {article.title} ---\n"
            chunk = header + text

            if total_chars + len(chunk) > self.max_article_chars:
                # Truncate this article to fit
                remaining = self.max_article_chars - total_chars - len(header)
                if remaining > 200:
                    chunk = header + text[:remaining] + "\n[...truncated...]"
                    parts.append(chunk)
                    total_chars += len(chunk)
                break

            parts.append(chunk)
            total_chars += len(chunk)
            urls.append(article.url)

        return "\n".join(parts), urls

    async def extract_for_topic(self, topic_id: int) -> ConceptExtractionResult:
        """
        Extract concepts from all articles belonging to a single topic.

        This is the main entry point. It:
          1. Loads articles from DB for the given topic
          2. Concatenates their text (truncated to fit LLM context)
          3. Sends to Gemma 4 with the concept extraction prompt
          4. Validates each concept through Pydantic
          5. Returns a ConceptExtractionResult

        Args:
            topic_id: The database ID of the topic to extract concepts for.

        Returns:
            ConceptExtractionResult with validated concepts (or empty on failure).
        """
        with SessionLocal() as session:
            topic = session.query(Topic).filter(Topic.id == topic_id).first()
            if not topic:
                logger.error(f"Topic ID {topic_id} not found in database")
                return ConceptExtractionResult(topic_name=f"unknown-{topic_id}")

            topic_name = topic.name
            logger.info(f"Extracting concepts for topic: {topic_name} (ID: {topic_id})")

            combined_text, article_urls = self._gather_topic_text(session, topic_id)

        if not combined_text.strip():
            logger.warning(f"No article text found for topic '{topic_name}', skipping")
            return ConceptExtractionResult(
                concepts=[],
                topic_name=topic_name,
            )

        logger.info(
            f"Topic '{topic_name}': {len(article_urls)} articles, "
            f"{len(combined_text)} chars of text"
        )

        messages = [
            SystemMessage(content=CONCEPT_EXTRACTION_PROMPT),
            HumanMessage(
                content=(
                    f"Identify the key learnable concepts from this documentation "
                    f"about '{topic_name}':\n\n{combined_text}"
                )
            ),
        ]

        last_error: Optional[str] = None

        for attempt in range(1, self.max_retries + 1):
            try:
                logger.info(
                    f"Calling LLM for '{topic_name}' "
                    f"(attempt {attempt}/{self.max_retries})"
                )

                response = await self.llm.ainvoke(messages)
                raw_response = response.content
                logger.debug(f"LLM response ({len(raw_response)} chars): {raw_response[:300]}")

                cleaned = self._clean_json_response(raw_response)
                # Fix Gemma 4 quirk: sometimes wraps JSON keys in extra quotes
                # e.g., {"'/name'": "..."} instead of {"name": "..."}
                cleaned = re.sub(r"['\"]\/(\w+)['\"]", r'"\1"', cleaned)
                cleaned = re.sub(r"['\"](\w+)['\"]\s*:", r'"\1":', cleaned)
                parsed = json.loads(cleaned)

                raw_concepts = parsed.get("concepts", [])
                if not raw_concepts:
                    logger.warning(f"LLM returned empty concepts list for '{topic_name}'")
                    return ConceptExtractionResult(
                        concepts=[],
                        topic_name=topic_name,
                        model_name=self.model_name,
                        total_article_chars=len(combined_text),
                    )

                validated_concepts: list[ExtractedConcept] = []
                # Fix Gemma 4 quirk: values sometimes wrapped in extra quotes
                for raw_concept in raw_concepts:
                    if not isinstance(raw_concept, dict):
                        continue
                    for key in list(raw_concept.keys()):
                        val = raw_concept[key]
                        if isinstance(val, str):
                            val = val.strip("'\"")
                            raw_concept[key] = val
                    try:
                        concept = ExtractedConcept(**raw_concept)
                        validated_concepts.append(concept)
                    except ValidationError as ve:
                        logger.warning(f"Skipping invalid concept: {ve}")
                        continue

                logger.info(
                    f"Extracted {len(validated_concepts)}/{len(raw_concepts)} "
                    f"valid concepts for '{topic_name}' (attempt {attempt})"
                )

                return ConceptExtractionResult(
                    concepts=validated_concepts,
                    topic_name=topic_name,
                    model_name=self.model_name,
                    total_article_chars=len(combined_text),
                )

            except json.JSONDecodeError as e:
                last_error = f"JSON parse error: {e}"
                logger.warning(f"Attempt {attempt} failed: {last_error}")
            except ConnectionError as e:
                last_error = f"Connection error (is Ollama running?): {e}"
                logger.warning(f"Attempt {attempt} failed: {last_error}")
            except Exception as e:
                last_error = f"Unexpected error: {type(e).__name__}: {e}"
                logger.warning(f"Attempt {attempt} failed: {last_error}")

        logger.error(
            f"All {self.max_retries} retries exhausted for '{topic_name}'. "
            f"Last error: {last_error}"
        )
        return ConceptExtractionResult(
            concepts=[],
            topic_name=topic_name,
            model_name=self.model_name,
            total_article_chars=len(combined_text),
        )

    def store_concepts(
        self,
        result: ConceptExtractionResult,
        topic_id: int,
    ) -> tuple[int, int]:
        """
        Store extracted concepts in the database, deduplicating by slug.

        This is a SYNC method (no LLM calls) — it just writes to PostgreSQL.

        DEDUPLICATION LOGIC:
          1. Slugify each concept name
          2. Check if a concept with that slug already exists for this topic
          3. If yes → skip it (keep the first one found)
          4. If no → insert it

        Returns:
            Tuple of (inserted_count, skipped_duplicates_count)
        """
        inserted = 0
        skipped = 0

        with SessionLocal() as session:
            existing_slugs = {
                row[0]
                for row in session.query(Concept.slug)
                .filter(Concept.topic_id == topic_id)
                .all()
            }

            for concept in result.concepts:
                slug = slugify(concept.name)

                if not slug:
                    logger.warning(f"Concept '{concept.name}' produced empty slug, skipping")
                    skipped += 1
                    continue

                if slug in existing_slugs:
                    logger.debug(f"Duplicate concept slug '{slug}', skipping")
                    skipped += 1
                    continue

                db_concept = Concept(
                    topic_id=topic_id,
                    name=concept.name,
                    slug=slug,
                    category=concept.category,
                    difficulty=concept.difficulty,
                    theory_text=concept.description,
                    key_points=[],
                    common_mistakes=[],
                )
                session.add(db_concept)
                existing_slugs.add(slug)
                inserted += 1

            try:
                session.commit()
                logger.info(
                    f"Stored {inserted} concepts for topic '{result.topic_name}' "
                    f"(skipped {skipped} duplicates)"
                )
            except Exception as e:
                session.rollback()
                logger.error(f"Failed to commit concepts: {e}")
                raise

        return inserted, skipped

    @staticmethod
    def _clean_json_response(text: str) -> str:
        """
        Clean LLM response to extract valid JSON.

        Handles common LLM response patterns:
          - Markdown code blocks: ```json ... ```
          - Extra text before/after JSON
          - BOM characters
        """
        text = re.sub(r"```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```", "", text)

        start = text.find("{")
        end = text.rfind("}") + 1
        if start >= 0 and end > start:
            return text[start:end]

        return text.strip()

    async def extract_all_topics(self) -> dict:
        """
        Extract concepts for ALL topics that have articles.

        This is the orchestrator method that processes every topic sequentially.
        It skips topics that already have concepts (idempotent — run multiple times
        without creating duplicates).

        Returns:
            Dict with summary statistics:
            {
                "topics_processed": 15,
                "total_concepts": 120,
                "total_duplicates_skipped": 8,
                "topics_skipped_no_articles": 3,
                "topics_failed": 0,
                "errors": []
            }
        """
        with SessionLocal() as session:
            topics = session.query(Topic).all()

        stats = {
            "topics_processed": 0,
            "total_concepts": 0,
            "total_duplicates_skipped": 0,
            "topics_skipped_no_articles": 0,
            "topics_failed": 0,
            "errors": [],
        }

        for topic in topics:
            with SessionLocal() as session:
                article_count = (
                    session.query(RawArticle)
                    .filter(RawArticle.topic_id == topic.id)
                    .count()
                )

            if article_count == 0:
                logger.info(f"Topic '{topic.name}' has no articles, skipping")
                stats["topics_skipped_no_articles"] += 1
                continue

            try:
                result = await self.extract_for_topic(topic.id)

                if not result.concepts:
                    logger.warning(
                        f"No concepts extracted for topic '{topic.name}'"
                    )
                    stats["topics_processed"] += 1
                    continue

                inserted, skipped = self.store_concepts(result, topic.id)

                stats["topics_processed"] += 1
                stats["total_concepts"] += inserted
                stats["total_duplicates_skipped"] += skipped

                logger.info(
                    f"[{stats['topics_processed']}/{len(topics)}] "
                    f"Topic '{topic.name}': {inserted} concepts inserted, "
                    f"{skipped} duplicates skipped"
                )

            except Exception as e:
                logger.error(f"Failed to process topic '{topic.name}': {e}")
                stats["topics_failed"] += 1
                stats["errors"].append(f"{topic.name}: {e}")

        logger.info(
            f"\n{'='*60}\n"
            f"CONCEPT EXTRACTION COMPLETE\n"
            f"{'='*60}\n"
            f"Topics processed: {stats['topics_processed']}\n"
            f"Total concepts: {stats['total_concepts']}\n"
            f"Duplicates skipped: {stats['total_duplicates_skipped']}\n"
            f"Topics skipped (no articles): {stats['topics_skipped_no_articles']}\n"
            f"Topics failed: {stats['topics_failed']}\n"
            f"{'='*60}"
        )

        return stats
