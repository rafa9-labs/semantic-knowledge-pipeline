# ============================================================
# pipeline/exercise_generator.py — LLM Exercise Generator
# ============================================================
# This module generates practice exercises for each concept in our
# knowledge graph. It reads concepts from PostgreSQL, sends them to
# Gemma 4, and stores validated exercises in the `exercises` table.
#
# HOW IT WORKS:
#   1. Load concepts that don't have exercises yet (or force all)
#   2. For each concept, send name + category + theory_text + ELI5 to Gemma 4
#   3. The LLM returns 1-2 exercises with starter code, solutions, hints, tests
#   4. Validate each exercise through the GeneratedExercise Pydantic model
#   5. Store in the `exercises` table
#
# WHY INCLUDE ELI5 IN THE PROMPT?
#   The ELI5 explanation gives the LLM context about the concept's real-world
#   analogy. This helps generate exercises that are practical and relatable
#   rather than abstract textbook problems.
#
# WHY 1-2 EXERCISES PER CONCEPT?
#   - Exercises are longer (starter + solution + hints + tests)
#   - Generating more than 2 per concept fills the LLM context and reduces quality
#   - With 176 concepts × 2 exercises = 352 exercises (plenty for MVP)
#   - Future: add a --count flag to generate more on demand
#
# WHY TEMPERATURE 0.3?
#   - Lower than examples (0.4) because exercises need CORRECT solutions
#   - Solution code must be syntactically valid and actually work
#   - Test cases must be logically consistent
#   - We sacrifice creativity for correctness
#
# IDEMPOTENCY:
#   Re-running skips concepts that already have exercises.
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
from database.models import Concept, Exercise
from models.enrichment import GeneratedExercise, ExerciseGenerationResult
from config.models import get_model_name, OLLAMA_BASE_URL
from pipeline.json_utils import repair_json, extract_json

logger = logging.getLogger(__name__)


EXERCISE_GENERATION_PROMPT = """You are an expert programming instructor who creates PRACTICE EXERCISES to help learners master programming concepts.

Your job: Given a programming concept, create 1-2 practice exercises that test the learner's understanding.

RULES:
1. Each exercise must be SOLVABLE — the solution_code must actually work.
2. starter_code should have a clear TODO comment showing what to implement.
3. solution_code must be COMPLETE, RUNNABLE, and CORRECT — include all imports.
4. Provide 2-3 progressive hints:
   - Hint 1: Gentle nudge (points to the right direction)
   - Hint 2: More specific (names a function or approach)
   - Hint 3: Nearly gives the answer (shows the key line)
5. Provide at least 1 test case with input and expected output.
6. Learning objectives should list 1-3 specific skills the exercise tests.
7. Difficulty should be close to the concept's difficulty (±1).
8. Use the same language as the concept's domain (Python for Python concepts, etc.).
   If unsure about language, use "python".
9. Exercises should be PRACTICAL — build something useful, not just demonstrate syntax.
10. CRITICAL: All string values (especially "starter_code" and "solution_code") must be
    properly escaped. Use \\n for newlines, \\t for tabs, \\\" for quotes inside strings.
    Do NOT use raw newlines inside JSON string values.

You MUST respond with ONLY valid JSON:
{
  "exercises": [
    {
      "title": "Descriptive exercise title (7+ words)",
      "description": "What the learner needs to build or achieve (20+ chars)",
      "difficulty": 3,
      "language": "python",
      "starter_code": "import asyncio\\n\\ndef fetch_data(url: str) -> str:\\n    # TODO: Make this function async\\n    ...",
      "solution_code": "import asyncio\\n\\nasync def fetch_data(url: str) -> str:\\n    await asyncio.sleep(1)\\n    return f'Data from {url}'",
      "hints": ["Add the 'async' keyword before 'def'", "Use 'await' for the sleep call"],
      "test_cases": [{"input": "url='http://test.com'", "expected": "'Data from http://test.com'"}],
      "learning_objectives": ["Define async functions", "Use await for async operations"]
    }
  ]
}
"""


class ExerciseGenerator:
    """
    Generates practice exercises for concepts using Qwen 3.5 9B via Ollama.

    Follows the same pattern as ExampleGenerator and ELI5Generator:
      - Initialize with model config
      - Call generate_for_concept() for each concept
      - LLM returns JSON → Pydantic validates → SQLAlchemy stores

    USAGE:
        gen = ExerciseGenerator()
        stats = await gen.generate_all()
        print(f"Generated {stats['exercises_generated']} exercises")
    """

    def __init__(
        self,
        model_name: str = None,
        base_url: str = None,
        temperature: float = 0.3,
        num_ctx: int = 8192,
        max_retries: int = 3,
        exercises_per_concept: int = 2,
    ):
        self.model_name = model_name or get_model_name("exercise_generator")
        base_url = base_url or OLLAMA_BASE_URL
        self.max_retries = max_retries
        self.exercises_per_concept = exercises_per_concept

        self.llm = ChatOllama(
            model=self.model_name,
            base_url=base_url,
            temperature=temperature,
            num_ctx=num_ctx,
            format="json",
        )

        logger.info(
            f"ExerciseGenerator initialized: model={self.model_name}, "
            f"ctx={num_ctx}, temp={temperature}"
        )

    async def generate_for_concept(self, concept_id: int) -> ExerciseGenerationResult:
        """
        Generate practice exercises for a single concept.

        Args:
            concept_id: The database ID of the concept.

        Returns:
            ExerciseGenerationResult with validated exercises (or empty on failure).
        """
        with SessionLocal() as session:
            concept = session.query(Concept).filter(Concept.id == concept_id).first()
            if not concept:
                logger.error(f"Concept ID {concept_id} not found")
                return ExerciseGenerationResult()

            concept_name = concept.name
            concept_category = concept.category
            concept_difficulty = concept.difficulty
            concept_theory = concept.theory_text or "No formal description available."
            concept_eli5 = concept.simple_explanation or ""

        context_parts = [
            f"Generate {self.exercises_per_concept} practice exercises for this concept:\n",
            f"**Name:** {concept_name}",
            f"**Category:** {concept_category}",
            f"**Difficulty:** {concept_difficulty}/5",
            f"\n**Technical description:** {concept_theory[:500]}",
        ]

        if concept_eli5:
            context_parts.append(
                f"\n**Simple explanation (ELI5):** {concept_eli5[:300]}"
            )

        prompt_text = "\n".join(context_parts)

        messages = [
            SystemMessage(content=EXERCISE_GENERATION_PROMPT),
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

                raw_exercises = parsed.get("exercises", [])
                if not raw_exercises:
                    logger.warning(f"LLM returned empty exercises for '{concept_name}'")
                    return ExerciseGenerationResult(concept_name=concept_name)

                validated: list[GeneratedExercise] = []
                for raw_ex in raw_exercises:
                    if not isinstance(raw_ex, dict):
                        continue
                    for key in list(raw_ex.keys()):
                        val = raw_ex[key]
                        if isinstance(val, str):
                            raw_ex[key] = val.strip("'\"")
                    try:
                        exercise = GeneratedExercise(**raw_ex)
                        validated.append(exercise)
                    except ValidationError as ve:
                        logger.warning(
                            f"Skipping invalid exercise for '{concept_name}': {ve}"
                        )

                logger.info(
                    f"Generated {len(validated)}/{len(raw_exercises)} valid exercises "
                    f"for '{concept_name}' (attempt {attempt})"
                )

                return ExerciseGenerationResult(
                    exercises=validated,
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

        logger.error(
            f"Failed to generate exercises for '{concept_name}': {last_error}"
        )
        return ExerciseGenerationResult(concept_name=concept_name)

    def store_exercises(
        self,
        result: ExerciseGenerationResult,
        concept_id: int,
    ) -> int:
        """
        Store generated exercises in the database.

        Args:
            result: The validated exercises from the LLM.
            concept_id: The concept these exercises belong to.

        Returns:
            Number of exercises stored.
        """
        stored = 0

        with SessionLocal() as session:
            existing_count = (
                session.query(Exercise)
                .filter(Exercise.concept_id == concept_id)
                .count()
            )

            for i, ex in enumerate(result.exercises):
                db_exercise = Exercise(
                    concept_id=concept_id,
                    title=ex.title,
                    description=ex.description,
                    difficulty=ex.difficulty,
                    language=ex.language,
                    starter_code=ex.starter_code,
                    solution_code=ex.solution_code,
                    hints=ex.hints,
                    test_cases=ex.test_cases,
                    learning_objectives=ex.learning_objectives,
                    sort_order=existing_count + i,
                )
                session.add(db_exercise)
                stored += 1

            try:
                session.commit()
                logger.info(
                    f"Stored {stored} exercises for '{result.concept_name}'"
                )
            except Exception as e:
                session.rollback()
                logger.error(f"Failed to commit exercises: {e}")
                raise

        return stored

    async def generate_all(
        self,
        force: bool = False,
        limit: Optional[int] = None,
    ) -> dict:
        """
        Generate exercises for all concepts that don't have them yet.

        Args:
            force: If True, regenerate even for concepts that already have exercises.
            limit: Max number of concepts to process.

        Returns:
            Dict with summary statistics.
        """
        with SessionLocal() as session:
            query = session.query(Concept)
            if not force:
                from sqlalchemy import exists
                has_exercises = session.query(
                    Concept.id,
                ).filter(
                    exists().where(Exercise.concept_id == Concept.id)
                ).subquery()

                query = query.filter(~Concept.id.in_(has_exercises))

            concepts = query.all()
            total_concepts = session.query(Concept).count()

        if limit:
            concepts = concepts[:limit]

        stats = {
            "total_concepts": total_concepts,
            "concepts_to_process": len(concepts),
            "exercises_generated": 0,
            "concepts_completed": 0,
            "concepts_failed": 0,
            "skipped_already_had": total_concepts - len(concepts),
        }

        logger.info(
            f"Exercise generation: {len(concepts)} concepts to process "
            f"({stats['skipped_already_had']} already have exercises)"
        )

        for i, concept in enumerate(concepts, 1):
            try:
                result = await self.generate_for_concept(concept.id)

                if result.exercises:
                    stored = self.store_exercises(result, concept.id)
                    stats["exercises_generated"] += stored
                    stats["concepts_completed"] += 1
                else:
                    stats["concepts_failed"] += 1

                logger.info(
                    f"[{i}/{len(concepts)}] '{concept.name}': "
                    f"{len(result.exercises)} exercises "
                    f"{'OK' if result.exercises else 'FAILED'}"
                )

            except Exception as e:
                logger.error(f"Error processing concept '{concept.name}': {e}")
                stats["concepts_failed"] += 1

        logger.info(
            f"\n{'='*60}\n"
            f"EXERCISE GENERATION COMPLETE\n"
            f"{'='*60}\n"
            f"Exercises generated: {stats['exercises_generated']}\n"
            f"Concepts completed: {stats['concepts_completed']}\n"
            f"Concepts failed: {stats['concepts_failed']}\n"
            f"Skipped (already had exercises): {stats['skipped_already_had']}\n"
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
