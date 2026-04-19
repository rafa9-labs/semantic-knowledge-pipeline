import json
import logging
import re
from typing import Optional

from langchain_ollama import ChatOllama
from langchain_core.messages import HumanMessage, SystemMessage

from database.connection import SessionLocal
from database.models import Concept
from models.enrichment import ConceptEnrichmentResult
from config.models import get_model_name, OLLAMA_BASE_URL
from pipeline.json_utils import repair_json, extract_json

logger = logging.getLogger(__name__)

CONCEPT_ENRICHMENT_PROMPT = """You are an expert programming educator creating study materials.

Given a programming concept, generate:
1. **key_points**: 4-6 essential bullet points that a learner MUST understand about this concept.
   Each point should be a single clear sentence. Cover: what it is, when to use it, what it replaces/improves, and a practical tip.

2. **common_mistakes**: 3-4 common errors or misconceptions that beginners have with this concept.
   Each should describe the mistake AND briefly explain why it's wrong or how to avoid it.

RULES:
- Be specific to THIS concept — no generic advice like "practice more" or "read the docs"
- Use practical, concrete language — not abstract theory
- key_points should cover: definition, use case, gotcha, best practice, comparison to alternatives
- common_mistakes should be REAL mistakes people make (not hypothetical)

You MUST respond with ONLY valid JSON:
{
  "key_points": [
    "Clear, specific point about this concept",
    "Another essential point",
    "A practical tip for using this concept",
    "When you should (or shouldn't) use this concept"
  ],
  "common_mistakes": [
    "Mistake: description of what people get wrong. Fix: how to do it correctly.",
    "Another common error and its resolution."
  ]
}
"""


class ConceptEnricher:
    def __init__(
        self,
        model_name: str = None,
        base_url: str = None,
        temperature: float = 0.3,
        num_ctx: int = 8192,
        max_retries: int = 3,
    ):
        self.model_name = model_name or get_model_name("eli5_generator")
        base_url = base_url or OLLAMA_BASE_URL
        self.max_retries = max_retries

        self.llm = ChatOllama(
            model=self.model_name,
            base_url=base_url,
            temperature=temperature,
            num_ctx=num_ctx,
            format="json",
        )

        logger.info(f"ConceptEnricher initialized: model={self.model_name}")

    async def enrich_concept(self, concept_id: int) -> ConceptEnrichmentResult:
        with SessionLocal() as session:
            concept = session.query(Concept).filter(Concept.id == concept_id).first()
            if not concept:
                logger.error(f"Concept ID {concept_id} not found")
                return ConceptEnrichmentResult()

            concept_name = concept.name
            concept_category = concept.category
            concept_theory = concept.theory_text or "No formal description available."
            concept_eli5 = concept.simple_explanation or ""

        context_parts = [
            f"Generate study materials for this concept:\n",
            f"**Name:** {concept_name}",
            f"**Category:** {concept_category}",
            f"\n**Technical description:** {concept_theory}",
        ]
        if concept_eli5:
            context_parts.append(f"\n**Simple explanation:** {concept_eli5}")

        messages = [
            SystemMessage(content=CONCEPT_ENRICHMENT_PROMPT),
            HumanMessage(content="\n".join(context_parts)),
        ]

        last_error: Optional[str] = None

        for attempt in range(1, self.max_retries + 1):
            try:
                response = await self.llm.ainvoke(messages)
                raw = response.content

                cleaned = extract_json(raw)
                cleaned = repair_json(cleaned)
                parsed = json.loads(cleaned)

                key_points = parsed.get("key_points", [])
                common_mistakes = parsed.get("common_mistakes", [])

                if not key_points and not common_mistakes:
                    logger.warning(f"Empty enrichment for '{concept_name}'")
                    return ConceptEnrichmentResult(concept_name=concept_name)

                logger.info(
                    f"Enriched '{concept_name}': {len(key_points)} key_points, "
                    f"{len(common_mistakes)} common_mistakes (attempt {attempt})"
                )

                return ConceptEnrichmentResult(
                    key_points=[str(p).strip() for p in key_points if str(p).strip()],
                    common_mistakes=[str(m).strip() for m in common_mistakes if str(m).strip()],
                    concept_name=concept_name,
                    model_name=self.model_name,
                )

            except json.JSONDecodeError as e:
                last_error = f"JSON error: {e}"
                logger.warning(f"Attempt {attempt} for '{concept_name}': {last_error}")
            except Exception as e:
                last_error = f"{type(e).__name__}: {e}"
                logger.warning(f"Attempt {attempt} for '{concept_name}': {last_error}")

        logger.error(f"Failed to enrich '{concept_name}': {last_error}")
        return ConceptEnrichmentResult(concept_name=concept_name)

    def store_enrichment(self, result: ConceptEnrichmentResult, concept_id: int) -> bool:
        with SessionLocal() as session:
            concept = session.query(Concept).filter(Concept.id == concept_id).first()
            if not concept:
                return False

            concept.key_points = result.key_points
            concept.common_mistakes = result.common_mistakes

            try:
                session.commit()
                return True
            except Exception as e:
                session.rollback()
                logger.error(f"Failed to store enrichment for concept {concept_id}: {e}")
                return False

    async def enrich_all(self, force: bool = False, limit: Optional[int] = None) -> dict:
        with SessionLocal() as session:
            query = session.query(Concept)
            if not force:
                from sqlalchemy import cast, Text
                query = query.filter(
                    Concept.key_points.is_(None)
                    | (cast(Concept.key_points, Text) == "[]")
                    | Concept.common_mistakes.is_(None)
                    | (cast(Concept.common_mistakes, Text) == "[]")
                )
            concepts = query.all()
            total = session.query(Concept).count()

        if limit:
            concepts = concepts[:limit]

        stats = {
            "total_concepts": total,
            "to_process": len(concepts),
            "enriched": 0,
            "failed": 0,
            "skipped": total - len(concepts),
        }

        logger.info(f"Concept enrichment: {len(concepts)} to process ({stats['skipped']} already enriched)")

        for i, concept in enumerate(concepts, 1):
            try:
                result = await self.enrich_concept(concept.id)
                if result.key_points or result.common_mistakes:
                    stored = self.store_enrichment(result, concept.id)
                    if stored:
                        stats["enriched"] += 1
                    else:
                        stats["failed"] += 1
                else:
                    stats["failed"] += 1

                from pipeline.cli_colors import progress, status_ok, status_fail
                msg = f"{len(result.key_points)}kp {len(result.common_mistakes)}cm"
                print(progress(i, len(concepts), concept.name, msg))

            except Exception as e:
                logger.error(f"Error enriching '{concept.name}': {e}")
                stats["failed"] += 1

        logger.info(
            f"\n{'='*60}\n"
            f"CONCEPT ENRICHMENT COMPLETE\n"
            f"{'='*60}\n"
            f"Enriched: {stats['enriched']}\n"
            f"Failed: {stats['failed']}\n"
            f"Skipped: {stats['skipped']}\n"
            f"{'='*60}"
        )

        return stats
