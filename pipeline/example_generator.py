# ============================================================
# pipeline/example_generator.py — LLM Code Example Generator
# ============================================================
# This module generates code examples for each concept in our
# knowledge graph. It reads concepts from PostgreSQL, sends them
# to Gemma 4, and stores validated examples in the `examples` table.
#
# HOW IT WORKS:
#   1. Load concepts that don't have examples yet (or force all)
#   2. For each concept, send name + category + theory_text to Gemma 4
#   3. The LLM returns 2-3 code examples with explanations
#   4. Validate each example through the GeneratedExample Pydantic model
#   5. Store in the `examples` table with source_type='generated'
#
# WHY TEMPERATURE 0.4?
#   - Concept extraction used 0.2 (mostly deterministic facts)
#   - ELI5 used 0.7 (creative analogies)
#   - Examples need a middle ground: creative enough for diverse examples,
#     but constrained enough to produce correct, working code
#
# WHY 2-3 EXAMPLES PER CONCEPT?
#   - 1 example is too few (no variety in difficulty or approach)
#   - 5+ is too many (LLM quality drops, and it slows down)
#   - 2-3 gives a beginner + intermediate example, or two different use cases
#   - The entry point supports --limit to cap total concepts processed
#
# IDEMPOTENCY:
#   Re-running skips concepts that already have generated examples.
#   Use --force to regenerate all.
# ============================================================

import json
import logging
import re
from typing import Optional

from langchain_ollama import ChatOllama
from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import ValidationError

from database.connection import SessionLocal
from database.models import Concept, Example
from models.enrichment import GeneratedExample, ExampleGenerationResult
from config.models import get_model_name, OLLAMA_BASE_URL
from pipeline.json_utils import repair_json, extract_json

logger = logging.getLogger(__name__)


EXAMPLE_GENERATION_PROMPT = """You are an expert programming instructor who creates clear, educational code examples.

Your job: Given a programming concept, generate 2-3 practical code examples that help a learner understand it.

RULES:
1. Each example should demonstrate a DIFFERENT aspect or difficulty level of the concept.
2. Code must be COMPLETE and RUNNABLE — no pseudocode, no missing imports, no "..." placeholders.
3. Use realistic, practical scenarios — not "hello world" or "foo/bar" examples.
4. Keep examples concise (5-25 lines of actual code). Quality over quantity.
5. The first example should be the simplest, most direct usage.
6. Later examples should show more advanced or real-world usage.
7. Provide a brief explanation (1-3 sentences) annotating key lines.
8. Match the language to the concept's domain:
   - Python concepts → "python"
   - SQL concepts → "sql"
   - Docker concepts → "bash" or "dockerfile" or "yaml"
   - General concepts → use the most common language for that domain
   - If unsure about language, use "python"
9. CRITICAL: All string values (especially "code") must be properly escaped.
   Use \\n for newlines, \\t for tabs, \\\" for quotes inside strings.
   Do NOT use raw newlines inside JSON string values.

You MUST respond with ONLY valid JSON:
{
  "examples": [
    {
      "title": "Short descriptive title (5+ words)",
      "code": "the actual code snippet",
      "language": "python",
      "explanation": "Brief annotation of what the code does and why"
    },
    {
      "title": "Another example title",
      "code": "more code",
      "language": "python",
      "explanation": "Brief annotation"
    }
  ]
}

GOOD EXAMPLE for "async/await" (python):
{
  "examples": [
    {
      "title": "Basic async function that fetches data",
      "code": "import asyncio\\n\\nasync def fetch_user(user_id: int) -> dict:\\n    await asyncio.sleep(1)\\n    return {'id': user_id, 'name': f'User {user_id}'}\\n\\nresult = asyncio.run(fetch_user(42))\\nprint(result)",
      "language": "python",
      "explanation": "async def creates a coroutine. await asyncio.sleep simulates an I/O delay. asyncio.run executes the coroutine on the event loop."
    },
    {
      "title": "Running multiple async operations concurrently",
      "code": "import asyncio\\n\\nasync def fetch_user(uid: int) -> dict:\\n    await asyncio.sleep(1)\\n    return {'id': uid}\\n\\nasync def fetch_all() -> list[dict]:\\n    tasks = [fetch_user(i) for i in range(5)]\\n    return await asyncio.gather(*tasks)\\n\\nresults = asyncio.run(fetch_all())\\nprint(f'Fetched {len(results)} users')",
      "language": "python",
      "explanation": "asyncio.gather runs multiple coroutines concurrently. The list comprehension creates 5 coroutine tasks. gather returns results in the same order as the input tasks."
    }
  ]
}

BAD EXAMPLES (avoid these):
- Code with "..." or "TODO" or "your code here"
- Examples longer than 30 lines
- Titles like "Example 1" or "Code snippet" (not descriptive)
- Pseudocode that can't actually run
"""


class ExampleGenerator:
    """
    Generates code examples for concepts using Qwen 3.5 9B via Ollama.

    Follows the same pattern as ELI5Generator:
      - Initialize with model config
      - Call generate_for_concept() for each concept
      - LLM returns JSON → Pydantic validates → SQLAlchemy stores

    USAGE:
        gen = ExampleGenerator()
        stats = await gen.generate_all()
        print(f"Generated {stats['generated']} examples")
    """

    def __init__(
        self,
        model_name: str = None,
        base_url: str = None,
        temperature: float = 0.4,
        num_ctx: int = 8192,
        max_retries: int = 3,
        examples_per_concept: int = 3,
    ):
        self.model_name = model_name or get_model_name("example_generator")
        base_url = base_url or OLLAMA_BASE_URL
        self.max_retries = max_retries
        self.examples_per_concept = examples_per_concept

        self.llm = ChatOllama(
            model=self.model_name,
            base_url=base_url,
            temperature=temperature,
            num_ctx=num_ctx,
            format="json",
        )

        logger.info(
            f"ExampleGenerator initialized: model={self.model_name}, "
            f"ctx={num_ctx}, temp={temperature}"
        )

    async def generate_for_concept(self, concept_id: int) -> ExampleGenerationResult:
        """
        Generate code examples for a single concept.

        Args:
            concept_id: The database ID of the concept.

        Returns:
            ExampleGenerationResult with validated examples (or empty on failure).
        """
        with SessionLocal() as session:
            concept = session.query(Concept).filter(Concept.id == concept_id).first()
            if not concept:
                logger.error(f"Concept ID {concept_id} not found")
                return ExampleGenerationResult()

            concept_name = concept.name
            concept_category = concept.category
            concept_difficulty = concept.difficulty
            concept_theory = concept.theory_text or "No formal description available."

        prompt_text = (
            f"Generate {self.examples_per_concept} code examples for this concept:\n\n"
            f"**Name:** {concept_name}\n"
            f"**Category:** {concept_category}\n"
            f"**Difficulty:** {concept_difficulty}/5\n"
            f"**Description:** {concept_theory[:600]}"
        )

        messages = [
            SystemMessage(content=EXAMPLE_GENERATION_PROMPT),
            HumanMessage(content=prompt_text),
        ]

        last_error: Optional[str] = None

        for attempt in range(1, self.max_retries + 1):
            try:
                response = await self.llm.ainvoke(messages)
                raw_response = response.content

                cleaned = extract_json(raw_response)
                cleaned = re.sub(r"['\"]\/(\w+)['\"]", r'"\1"', cleaned)
                cleaned = repair_json(cleaned)
                parsed = json.loads(cleaned)

                raw_examples = parsed.get("examples", [])
                if not raw_examples:
                    logger.warning(f"LLM returned empty examples for '{concept_name}'")
                    return ExampleGenerationResult(concept_name=concept_name)

                validated: list[GeneratedExample] = []
                for raw_ex in raw_examples:
                    if not isinstance(raw_ex, dict):
                        continue
                    for key in list(raw_ex.keys()):
                        val = raw_ex[key]
                        if isinstance(val, str):
                            raw_ex[key] = val.strip("'\"")
                    try:
                        example = GeneratedExample(**raw_ex)
                        validated.append(example)
                    except ValidationError as ve:
                        logger.warning(f"Skipping invalid example for '{concept_name}': {ve}")

                logger.info(
                    f"Generated {len(validated)}/{len(raw_examples)} valid examples "
                    f"for '{concept_name}' (attempt {attempt})"
                )

                return ExampleGenerationResult(
                    examples=validated,
                    concept_name=concept_name,
                    model_name=self.model_name,
                )

            except json.JSONDecodeError as e:
                last_error = f"JSON error: {e}"
                logger.warning(f"Attempt {attempt} for '{concept_name}': {last_error}")
            except ConnectionError as e:
                last_error = f"Connection error: {e}"
                logger.warning(f"Attempt {attempt} for '{concept_name}': {last_error}")
            except Exception as e:
                last_error = f"{type(e).__name__}: {e}"
                logger.warning(f"Attempt {attempt} for '{concept_name}': {last_error}")

        logger.error(f"Failed to generate examples for '{concept_name}': {last_error}")
        return ExampleGenerationResult(concept_name=concept_name)

    def store_examples(
        self,
        result: ExampleGenerationResult,
        concept_id: int,
    ) -> int:
        """
        Store generated examples in the database.

        Args:
            result: The validated examples from the LLM.
            concept_id: The concept these examples belong to.

        Returns:
            Number of examples stored.
        """
        stored = 0

        with SessionLocal() as session:
            existing_count = (
                session.query(Example)
                .filter(
                    Example.concept_id == concept_id,
                    Example.source_type == "generated",
                )
                .count()
            )

            for i, ex in enumerate(result.examples):
                db_example = Example(
                    concept_id=concept_id,
                    title=ex.title,
                    description=None,
                    code=ex.code,
                    language=ex.language,
                    explanation=ex.explanation,
                    source_url=None,
                    source_type="generated",
                    sort_order=existing_count + i,
                )
                session.add(db_example)
                stored += 1

            try:
                session.commit()
                logger.info(
                    f"Stored {stored} examples for '{result.concept_name}'"
                )
            except Exception as e:
                session.rollback()
                logger.error(f"Failed to commit examples: {e}")
                raise

        return stored

    async def generate_all(
        self,
        force: bool = False,
        limit: Optional[int] = None,
    ) -> dict:
        """
        Generate code examples for all concepts.

        Args:
            force: If True, regenerate even for concepts that already have examples.
            limit: Max number of concepts to process.

        Returns:
            Dict with summary statistics.
        """
        with SessionLocal() as session:
            query = session.query(Concept)
            if not force:
                from sqlalchemy import exists
                has_examples = session.query(
                    Concept.id,
                ).filter(
                    exists().where(
                        Example.concept_id == Concept.id,
                        Example.source_type == "generated",
                    )
                ).subquery()

                query = query.filter(~Concept.id.in_(has_examples))

            concepts = query.all()
            total_concepts = session.query(Concept).count()

        if limit:
            concepts = concepts[:limit]

        stats = {
            "total_concepts": total_concepts,
            "concepts_to_process": len(concepts),
            "examples_generated": 0,
            "concepts_completed": 0,
            "concepts_failed": 0,
            "skipped_already_had": total_concepts - len(concepts),
        }

        logger.info(
            f"Example generation: {len(concepts)} concepts to process "
            f"({stats['skipped_already_had']} already have examples)"
        )

        for i, concept in enumerate(concepts, 1):
            try:
                result = await self.generate_for_concept(concept.id)

                if result.examples:
                    stored = self.store_examples(result, concept.id)
                    stats["examples_generated"] += stored
                    stats["concepts_completed"] += 1
                else:
                    stats["concepts_failed"] += 1

                logger.info(
                    f"[{i}/{len(concepts)}] '{concept.name}': "
                    f"{len(result.examples)} examples "
                    f"{'OK' if result.examples else 'FAILED'}"
                )

            except Exception as e:
                logger.error(f"Error processing concept '{concept.name}': {e}")
                stats["concepts_failed"] += 1

        logger.info(
            f"\n{'='*60}\n"
            f"EXAMPLE GENERATION COMPLETE\n"
            f"{'='*60}\n"
            f"Examples generated: {stats['examples_generated']}\n"
            f"Concepts completed: {stats['concepts_completed']}\n"
            f"Concepts failed: {stats['concepts_failed']}\n"
            f"Skipped (already had examples): {stats['skipped_already_had']}\n"
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
