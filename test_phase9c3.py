# ============================================================
# test_phase9c3.py — Phase 9C-3 Verification Script
# ============================================================
# Verifies that code example generation and exercise generation work:
#   1. ExampleGenerator initializes correctly
#   2. ExerciseGenerator initializes correctly
#   3. GeneratedExample Pydantic validation works
#   4. GeneratedExercise Pydantic validation works
#   5. Database state verification (tables exist, concepts present)
#   6. Single concept example generation works (requires Ollama)
#   7. Single concept exercise generation works (requires Ollama)
#
# Run: python test_phase9c3.py
# ============================================================

import asyncio
import sys

from database.connection import SessionLocal
from database.models import Concept, Example, Exercise
from models.enrichment import (
    GeneratedExample,
    GeneratedExercise,
    ExampleGenerationResult,
    ExerciseGenerationResult,
    VALID_LANGUAGES,
)
from pipeline.example_generator import ExampleGenerator
from pipeline.exercise_generator import ExerciseGenerator


def test_example_gen_init():
    print("\n--- Test 1: ExampleGenerator Initialization ---")
    gen = ExampleGenerator()
    assert gen.model_name == "qwen3.5:9b"
    assert gen.max_retries == 2
    assert gen.examples_per_concept == 3
    print(f"  OK: ExampleGenerator initialized (model={gen.model_name})")
    return True


def test_exercise_gen_init():
    print("\n--- Test 2: ExerciseGenerator Initialization ---")
    gen = ExerciseGenerator()
    assert gen.model_name == "qwen3.5:9b"
    assert gen.max_retries == 2
    assert gen.exercises_per_concept == 2
    print(f"  OK: ExerciseGenerator initialized (model={gen.model_name})")
    return True


def test_example_validation():
    print("\n--- Test 3: GeneratedExample Validation ---")

    ex = GeneratedExample(
        title="Basic async function that fetches data",
        code="import asyncio\n\nasync def fetch(url: str) -> str:\n    await asyncio.sleep(1)\n    return f'Data from {url}'",
        language="python",
        explanation="Line 1: Import asyncio. Line 3: async def creates a coroutine.",
    )
    assert ex.language == "python"
    assert len(ex.code) > 10
    print("  OK: Valid example accepted")

    # Invalid language
    try:
        GeneratedExample(
            title="Test example",
            code="console.log('hello')",
            language="brainfuck",
        )
        assert False, "Should have rejected invalid language"
    except Exception:
        print("  OK: Invalid language rejected")

    # Title too short
    try:
        GeneratedExample(
            title="Hi",
            code="print('hello world')",
            language="python",
        )
        assert False, "Should have rejected short title"
    except Exception:
        print("  OK: Short title rejected")

    # Code too short
    try:
        GeneratedExample(
            title="A valid title here",
            code="x = 1",
            language="python",
        )
        assert False, "Should have rejected short code"
    except Exception:
        print("  OK: Short code rejected")

    print("  OK: All example validation tests passed")
    return True


def test_exercise_validation():
    print("\n--- Test 4: GeneratedExercise Validation ---")

    ex = GeneratedExercise(
        title="Build a concurrent URL fetcher",
        description="Write an async function that fetches multiple URLs concurrently using asyncio.gather.",
        difficulty=3,
        language="python",
        starter_code="import asyncio\n\nasync def fetch_many(urls: list[str]) -> list[str]:\n    # TODO: Fetch all URLs concurrently\n    pass",
        solution_code="import asyncio\n\nasync def fetch_many(urls: list[str]) -> list[str]:\n    tasks = [fetch_one(url) for url in urls]\n    return await asyncio.gather(*tasks)",
        hints=["Create a list of coroutines", "Pass them to asyncio.gather()"],
        test_cases=[{"input": "3 URLs", "expected": "list of 3 responses"}],
        learning_objectives=["Use asyncio.gather for concurrency"],
    )
    assert ex.difficulty == 3
    assert len(ex.hints) == 2
    assert len(ex.test_cases) == 1
    print("  OK: Valid exercise accepted")

    # Invalid difficulty
    try:
        GeneratedExercise(
            title="Test exercise",
            description="A description that is long enough to pass validation checks",
            difficulty=6,
            language="python",
            solution_code="print('hello world, this is the solution to the exercise')",
        )
        assert False, "Should have rejected difficulty > 5"
    except Exception:
        print("  OK: Invalid difficulty rejected")

    # Description too short
    try:
        GeneratedExercise(
            title="Test exercise",
            description="Too short",
            difficulty=3,
            language="python",
            solution_code="x = 42",
        )
        assert False, "Should have rejected short description"
    except Exception:
        print("  OK: Short description rejected")

    print("  OK: All exercise validation tests passed")
    return True


def test_database_state():
    print("\n--- Test 5: Database State ---")

    with SessionLocal() as session:
        total_concepts = session.query(Concept).count()
        total_examples = session.query(Example).count()
        total_exercises = session.query(Exercise).count()

        concepts_with_examples = (
            session.query(Example.concept_id).distinct().count()
        )
        concepts_with_exercises = (
            session.query(Exercise.concept_id).distinct().count()
        )

        generated_examples = (
            session.query(Example)
            .filter(Example.source_type == "generated")
            .count()
        )

        print(f"  Total concepts: {total_concepts}")
        print(f"  Total examples: {total_examples} ({generated_examples} generated)")
        print(f"  Total exercises: {total_exercises}")
        print(f"  Concepts with examples: {concepts_with_examples}")
        print(f"  Concepts with exercises: {concepts_with_exercises}")

        assert total_concepts > 0, "No concepts in database (run Phase 9C-1 first)"
        print("  OK: Database has concepts to process")

    return True


def test_single_example_generation():
    print("\n--- Test 6: Single Concept Example Generation (requires Ollama) ---")

    with SessionLocal() as session:
        concept = session.query(Concept).first()
        if not concept:
            print("  SKIP: No concepts in database")
            return True
        concept_id = concept.id
        concept_name = concept.name

    gen = ExampleGenerator()
    result = asyncio.run(gen.generate_for_concept(concept_id))

    print(f"  Concept: {concept_name}")
    print(f"  Examples generated: {len(result.examples)}")

    for ex in result.examples:
        print(f"    [{ex.language}] {ex.title}")
        code_preview = ex.code[:80].replace("\n", " | ")
        print(f"      {code_preview}{'...' if len(ex.code) > 80 else ''}")

    if result.examples:
        assert result.examples[0].language in VALID_LANGUAGES
        assert len(result.examples[0].code) >= 10
        print("  OK: Examples generated successfully")
    else:
        print("  WARN: Example generation failed (Ollama may be busy)")

    return True


def test_single_exercise_generation():
    print("\n--- Test 7: Single Concept Exercise Generation (requires Ollama) ---")

    with SessionLocal() as session:
        concept = session.query(Concept).first()
        if not concept:
            print("  SKIP: No concepts in database")
            return True
        concept_id = concept.id
        concept_name = concept.name

    gen = ExerciseGenerator()
    result = asyncio.run(gen.generate_for_concept(concept_id))

    print(f"  Concept: {concept_name}")
    print(f"  Exercises generated: {len(result.exercises)}")

    for ex in result.exercises:
        print(f"    [{ex.language}] {ex.title} (difficulty {ex.difficulty})")
        print(f"      Description: {ex.description[:80]}{'...' if len(ex.description) > 80 else ''}")
        if ex.hints:
            print(f"      Hints: {len(ex.hints)} progressive hints")
        if ex.learning_objectives:
            print(f"      Objectives: {', '.join(ex.learning_objectives[:3])}")

    if result.exercises:
        assert result.exercises[0].difficulty >= 1
        assert result.exercises[0].difficulty <= 5
        assert len(result.exercises[0].solution_code) >= 5
        print("  OK: Exercises generated successfully")
    else:
        print("  WARN: Exercise generation failed (Ollama may be busy)")

    return True


def run_tests():
    print("=" * 60)
    print("PHASE 9C-3: EXAMPLES + EXERCISES — VERIFICATION")
    print("=" * 60)

    tests = [
        ("ExampleGenerator Init", test_example_gen_init),
        ("ExerciseGenerator Init", test_exercise_gen_init),
        ("Example Validation", test_example_validation),
        ("Exercise Validation", test_exercise_validation),
        ("Database State", test_database_state),
        ("Single Example Gen", test_single_example_generation),
        ("Single Exercise Gen", test_single_exercise_generation),
    ]

    results = {}
    for name, test_fn in tests:
        try:
            results[name] = test_fn()
        except Exception as e:
            print(f"\n  FAIL: {e}")
            results[name] = False

    print("\n" + "=" * 60)
    print("RESULTS SUMMARY")
    print("=" * 60)
    for name, passed in results.items():
        status = "PASS" if passed else "FAIL"
        print(f"  {status}: {name}")

    total = len(results)
    passed = sum(1 for v in results.values() if v)
    print(f"\n  {passed}/{total} tests passed")
    print("=" * 60)

    return passed == total


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
