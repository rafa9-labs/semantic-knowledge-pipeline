# ============================================================
# enrich_examples.py — Phase 9C-3: Code Example Generation Entry Point
# ============================================================
# Generates code examples for all concepts in the database
# that don't already have generated examples.
#
# USAGE:
#   python enrich_examples.py              # Generate examples for concepts missing them
#   python enrich_examples.py --force      # Regenerate ALL examples
#   python enrich_examples.py --concept 42 # Generate for one concept only
#   python enrich_examples.py --limit 10   # Only process first 10 concepts
#   python enrich_examples.py --dry-run    # Show what would be processed, don't call LLM
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
from database.models import Concept, Example
from pipeline.example_generator import ExampleGenerator

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


def print_summary(stats: dict):
    print("\n" + "=" * 60)
    print("EXAMPLE GENERATION RESULTS")
    print("=" * 60)
    print(f"  Total concepts in DB:    {stats['total_concepts']}")
    print(f"  Concepts processed:      {stats['concepts_to_process']}")
    print(f"  Examples generated:      {stats['examples_generated']}")
    print(f"  Concepts completed:      {stats['concepts_completed']}")
    print(f"  Concepts failed:         {stats['concepts_failed']}")
    print(f"  Skipped (already had):   {stats['skipped_already_had']}")
    print("=" * 60 + "\n")

    with SessionLocal() as session:
        examples = (
            session.query(Example)
            .filter(Example.source_type == "generated")
            .order_by(Example.id.desc())
            .limit(5)
            .all()
        )
        if examples:
            print("Sample generated examples:")
            for ex in examples:
                print(f"\n  [{ex.language}] {ex.title}:")
                code_preview = ex.code[:100].replace("\n", " | ")
                print(f"    {code_preview}{'...' if len(ex.code) > 100 else ''}")


async def run(
    concept_id: int | None = None,
    force: bool = False,
    limit: int | None = None,
    dry_run: bool = False,
):
    gen = ExampleGenerator()

    if dry_run:
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
            if limit:
                concepts = concepts[:limit]

        print(f"\n[DRY RUN] Would process {len(concepts)} concepts:")
        for c in concepts:
            print(f"  - {c.name} ({c.category}, difficulty {c.difficulty})")
        return

    if concept_id:
        print(f"\nGenerating examples for concept ID {concept_id}...\n")
        result = await gen.generate_for_concept(concept_id)
        if result.examples:
            stored = gen.store_examples(result, concept_id)
            print(f"\n  Generated {stored} examples:")
            for ex in result.examples:
                print(f"    [{ex.language}] {ex.title}")
        else:
            print("\n  Failed to generate examples.")
        return

    print("\nGenerating examples for all eligible concepts...\n")
    stats = await gen.generate_all(force=force, limit=limit)
    print_summary(stats)


def main():
    parser = argparse.ArgumentParser(
        description="Phase 9C-3: Generate code examples for concepts"
    )
    parser.add_argument(
        "--concept",
        type=int,
        default=None,
        help="Generate examples for a single concept ID",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Regenerate examples for ALL concepts (even those that already have them)",
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
