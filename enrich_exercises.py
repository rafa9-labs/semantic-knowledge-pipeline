# ============================================================
# enrich_exercises.py — Phase 9C-3: Exercise Generation Entry Point
# ============================================================
# Generates practice exercises for all concepts in the database
# that don't already have exercises.
#
# USAGE:
#   python enrich_exercises.py              # Generate exercises for concepts missing them
#   python enrich_exercises.py --force      # Regenerate ALL exercises
#   python enrich_exercises.py --concept 42 # Generate for one concept only
#   python enrich_exercises.py --limit 10   # Only process first 10 concepts
#   python enrich_exercises.py --dry-run    # Show what would be processed, don't call LLM
#
# PREREQUISITES:
#   - PostgreSQL running with Phase 9A tables + Phase 9C-1 concepts
#   - Ollama running with gemma4:26b model pulled
# ============================================================

import argparse
import asyncio
import logging
import sys

from database.connection import SessionLocal
from database.models import Concept, Exercise
from pipeline.exercise_generator import ExerciseGenerator

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


def print_summary(stats: dict):
    print("\n" + "=" * 60)
    print("EXERCISE GENERATION RESULTS")
    print("=" * 60)
    print(f"  Total concepts in DB:    {stats['total_concepts']}")
    print(f"  Concepts processed:      {stats['concepts_to_process']}")
    print(f"  Exercises generated:     {stats['exercises_generated']}")
    print(f"  Concepts completed:      {stats['concepts_completed']}")
    print(f"  Concepts failed:         {stats['concepts_failed']}")
    print(f"  Skipped (already had):   {stats['skipped_already_had']}")
    print("=" * 60 + "\n")

    with SessionLocal() as session:
        exercises = (
            session.query(Exercise)
            .order_by(Exercise.id.desc())
            .limit(5)
            .all()
        )
        if exercises:
            print("Sample generated exercises:")
            for ex in exercises:
                print(f"\n  [{ex.language}] {ex.title} (difficulty {ex.difficulty}):")
                print(f"    {ex.description[:100]}{'...' if len(ex.description) > 100 else ''}")
                if ex.hints:
                    print(f"    Hints: {len(ex.hints)} progressive hints")


async def run(
    concept_id: int | None = None,
    force: bool = False,
    limit: int | None = None,
    dry_run: bool = False,
):
    gen = ExerciseGenerator()

    if dry_run:
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
            if limit:
                concepts = concepts[:limit]

        print(f"\n[DRY RUN] Would process {len(concepts)} concepts:")
        for c in concepts:
            print(f"  - {c.name} ({c.category}, difficulty {c.difficulty})")
        return

    if concept_id:
        print(f"\nGenerating exercises for concept ID {concept_id}...\n")
        result = await gen.generate_for_concept(concept_id)
        if result.exercises:
            stored = gen.store_exercises(result, concept_id)
            print(f"\n  Generated {stored} exercises:")
            for ex in result.exercises:
                print(f"    [{ex.language}] {ex.title} (difficulty {ex.difficulty})")
        else:
            print("\n  Failed to generate exercises.")
        return

    print("\nGenerating exercises for all eligible concepts...\n")
    stats = await gen.generate_all(force=force, limit=limit)
    print_summary(stats)


def main():
    parser = argparse.ArgumentParser(
        description="Phase 9C-3: Generate practice exercises for concepts"
    )
    parser.add_argument(
        "--concept",
        type=int,
        default=None,
        help="Generate exercises for a single concept ID",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Regenerate exercises for ALL concepts (even those that already have them)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Only process this many concepts",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be processed without calling the LLM",
    )
    args = parser.parse_args()

    try:
        asyncio.run(
            run(
                concept_id=args.concept,
                force=args.force,
                limit=args.limit,
                dry_run=args.dry_run,
            )
        )
    except KeyboardInterrupt:
        print("\n\nInterrupted by user.")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
