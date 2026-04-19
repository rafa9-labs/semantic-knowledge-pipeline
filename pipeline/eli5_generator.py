# ============================================================
# pipeline/eli5_generator.py — ELI5 (Explain Like I'm 5) Generator
# ============================================================
# This module generates simple, analogy-based explanations for each
# concept in our knowledge graph. It reads concepts from PostgreSQL,
# sends them to Gemma 4, and stores the ELI5 text back.
#
# HOW IT WORKS:
#   1. Load concepts that don't have a simple_explanation yet
#   2. For each concept, send name + category + theory_text to Gemma 4
#   3. The LLM returns a short analogy-based explanation
#   4. Store in concepts.simple_explanation column
#
# WHY HIGHER TEMPERATURE (0.7)?
#   - Concept extraction used temperature=0.2 for deterministic facts
#   - ELI5 generation needs CREATIVITY — we want diverse analogies
#   - A concept like "embeddings" could be explained as "like a ZIP code
#     for meaning" or "like sorting books by topic instead of title"
#   - Higher temperature = more varied, memorable analogies
#
# WHY ONE LLM CALL PER CONCEPT (not batched)?
#   - Each concept needs a focused, tailored analogy
#   - Batching would produce generic, shorter explanations
#   - ~176 calls at ~10s each ≈ 30 minutes total (acceptable)
#   - Can be resumed — skips concepts that already have ELI5
#
# IDEMPOTENCY:
#   Re-running the pipeline skips concepts that already have
#   simple_explanation set. Use --force to regenerate all.
# ============================================================

import json
import logging
import re
from typing import Optional

from langchain_ollama import ChatOllama
from langchain_core.messages import HumanMessage, SystemMessage

from database.connection import SessionLocal
from database.models import Concept
from config.models import get_model_name, OLLAMA_BASE_URL
from pipeline.json_utils import repair_json, extract_json

logger = logging.getLogger(__name__)


ELI5_SYSTEM_PROMPT = """You are an expert teacher who explains complex programming concepts using simple, relatable analogies.

Your job: Given a programming concept, its category, and a formal description, write an "Explain Like I'm 5" (ELI5) version.

RULES:
1. Use a CONCRETE REAL-WORLD ANALOGY — compare the concept to something anyone would understand.
   - "API" is like a waiter taking your order to the kitchen
   - "Docker container" is like a shipping container that works on any ship
   - "Async/await" is like putting a letter in the mail and doing other things while waiting for a reply
2. Keep it to 2-4 sentences MAXIMUM.
3. Do NOT use jargon or technical terms in the analogy itself.
4. After the analogy, add one sentence explaining WHY it matters (the practical benefit).
5. Be creative — different concepts should get different analogies, not recycled ones.

You MUST respond with ONLY valid JSON:
{
  "eli5": "Your explanation here",
  "analogy_source": "What real-world thing you compared it to (e.g., 'restaurant waiter', 'shipping container')"
}

BAD EXAMPLES (too technical):
- "async/await is syntactic sugar over Promises that allows non-blocking execution" ← jargon
- "embeddings are dense vector representations of tokens in a latent space" ← way too technical

GOOD EXAMPLES:
Input: "Docker container" (tool)
Output:
{
  "eli5": "A Docker container is like a lunchbox — it packs everything your app needs (code, settings, libraries) into one portable box that works the same on any computer. This means your app runs identically on your laptop, a coworker's machine, or a cloud server.",
  "analogy_source": "lunchbox"
}

Input: "SQL JOIN" (language_feature)
Output:
{
  "eli5": "A SQL JOIN is like matching name tags at a party — you take two lists of people and connect them by a shared detail (like their company). This lets you combine information from two separate tables into one useful result.",
  "analogy_source": "matching name tags at a party"
}
"""


class ELI5Generator:
    """
    Generates ELI5 explanations for concepts using Gemma 4 via Ollama.

    Follows the same pattern as ConceptExtractor:
      - Initialize with model config
      - Call generate_for_concept() for each concept
      - LLM returns JSON → extract eli5 text → store in DB

    USAGE:
        gen = ELI5Generator()
        count = await gen.generate_all()
        print(f"Generated {count} ELI5 explanations")
    """

    def __init__(
        self,
        model_name: str = None,
        base_url: str = None,
        temperature: float = 0.7,
        num_ctx: int = 8192,
        max_retries: int = 2,
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

        logger.info(
            f"ELI5Generator initialized: model={self.model_name}, "
            f"ctx={num_ctx}, temp={temperature}"
        )

    async def generate_for_concept(self, concept_id: int) -> Optional[str]:
        """
        Generate an ELI5 explanation for a single concept.

        Args:
            concept_id: The database ID of the concept.

        Returns:
            The ELI5 explanation string, or None on failure.
        """
        with SessionLocal() as session:
            concept = session.query(Concept).filter(Concept.id == concept_id).first()
            if not concept:
                logger.error(f"Concept ID {concept_id} not found")
                return None

            concept_name = concept.name
            concept_category = concept.category
            concept_theory = concept.theory_text or "No formal description available."

        prompt_text = (
            f"Generate an ELI5 explanation for this concept:\n\n"
            f"**Name:** {concept_name}\n"
            f"**Category:** {concept_category}\n"
            f"**Technical description:** {concept_theory[:500]}"
        )

        messages = [
            SystemMessage(content=ELI5_SYSTEM_PROMPT),
            HumanMessage(content=prompt_text),
        ]

        last_error: Optional[str] = None

        for attempt in range(1, self.max_retries + 1):
            try:
                response = await self.llm.ainvoke(messages)
                raw_response = response.content

                cleaned = self._clean_json_response(raw_response)
                parsed = json.loads(cleaned)

                eli5_text = parsed.get("eli5", "").strip()
                if not eli5_text or len(eli5_text) < 20:
                    logger.warning(
                        f"ELI5 too short for '{concept_name}': '{eli5_text[:50]}'"
                    )
                    continue

                logger.info(
                    f"Generated ELI5 for '{concept_name}' "
                    f"({len(eli5_text)} chars, attempt {attempt})"
                )

                return eli5_text

            except json.JSONDecodeError as e:
                last_error = f"JSON error: {e}"
                logger.warning(f"Attempt {attempt} for '{concept_name}': {last_error}")
            except ConnectionError as e:
                last_error = f"Connection error: {e}"
                logger.warning(f"Attempt {attempt} for '{concept_name}': {last_error}")
            except Exception as e:
                last_error = f"{type(e).__name__}: {e}"
                logger.warning(f"Attempt {attempt} for '{concept_name}': {last_error}")

        logger.error(
            f"Failed to generate ELI5 for '{concept_name}': {last_error}"
        )
        return None

    def store_eli5(self, concept_id: int, eli5_text: str) -> bool:
        """
        Store the ELI5 explanation in the database.

        Returns:
            True if stored successfully, False otherwise.
        """
        with SessionLocal() as session:
            concept = session.query(Concept).filter(Concept.id == concept_id).first()
            if not concept:
                return False

            concept.simple_explanation = eli5_text
            concept.simple_explanation_source = self.model_name

            try:
                session.commit()
                return True
            except Exception as e:
                session.rollback()
                logger.error(f"Failed to store ELI5 for concept {concept_id}: {e}")
                return False

    async def generate_all(self, force: bool = False) -> dict:
        """
        Generate ELI5 explanations for all concepts that don't have one.

        Args:
            force: If True, regenerate even for concepts that already have ELI5.

        Returns:
            Dict with summary statistics.
        """
        with SessionLocal() as session:
            query = session.query(Concept)
            if not force:
                query = query.filter(
                    (Concept.simple_explanation == None)
                    | (Concept.simple_explanation == "")
                )
            concepts = query.all()
            total_concepts = session.query(Concept).count()

        stats = {
            "total_concepts": total_concepts,
            "concepts_to_process": len(concepts),
            "generated": 0,
            "failed": 0,
            "skipped": total_concepts - len(concepts),
        }

        logger.info(
            f"ELI5 generation: {len(concepts)} concepts to process "
            f"({stats['skipped']} already have ELI5)"
        )

        for i, concept in enumerate(concepts, 1):
            try:
                eli5 = await self.generate_for_concept(concept.id)

                if eli5:
                    stored = self.store_eli5(concept.id, eli5)
                    if stored:
                        stats["generated"] += 1
                    else:
                        stats["failed"] += 1
                else:
                    stats["failed"] += 1

                logger.info(
                    f"[{i}/{len(concepts)}] '{concept.name}': "
                    f"{'OK' if eli5 else 'FAILED'}"
                )

            except Exception as e:
                logger.error(f"Error processing concept '{concept.name}': {e}")
                stats["failed"] += 1

        logger.info(
            f"\n{'='*60}\n"
            f"ELI5 GENERATION COMPLETE\n"
            f"{'='*60}\n"
            f"Generated: {stats['generated']}\n"
            f"Failed: {stats['failed']}\n"
            f"Skipped (already had ELI5): {stats['skipped']}\n"
            f"{'='*60}"
        )

        return stats

    @staticmethod
    def _clean_json_response(text: str) -> str:
        """Extract JSON from LLM response, handling code blocks and extra text."""
        text = re.sub(r"```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```", "", text)

        start = text.find("{")
        end = text.rfind("}") + 1
        if start >= 0 and end > start:
            return text[start:end]

        return text.strip()
