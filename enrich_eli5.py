# ============================================================
# enrich_eli5.py — Phase 9C-2: ELI5 Generation Entry Point
# ============================================================
# Generates "Explain Like I'm 5" explanations for all concepts
# in the database that don't already have one.
#
# USAGE:
#   python enrich_eli5.py              # Generate ELI5 for concepts missing one
#   python enrich_eli5.py --force      # Regenerate ALL ELI5s
#   python enrich_eli5.py --concept 42 # Generate for one concept only
#   python enrich_eli5.py --limit 10   # Only process first 10 concepts
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
from database.models import Concept
from pipeline.eli5_generator import ELI5Generator

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


def print_summary(stats: dict):
    print("\n" + "=" * 60)
    print("ELI5 GENERATION RESULTS")
    print("=" * 60)
    print(f"  Total concepts in DB:    {stats['total_concepts']}")
    print(f"  Concepts processed:      {stats['concepts_to_process']}")
    print(f"  ELI5 generated:          {stats['generated']}")
    print(f"  Failed:                  {stats['failed']}")
    print(f"  Skipped (already had):   {stats['skipped']}")
    print("=" * 60 + "\n")

    with SessionLocal() as session:
        sample = (
            session.query(Concept)
            .filter(Concept.simple_explanation.isnot(None))
            .limit(5)
            .all()
        )
        if sample:
            print("Sample ELI5 explanations:")
            for c in sample:
                eli5 = c.simple_explanation or ""
                print(f"\n  {c.name}:")
                print(f"    {eli5[:120]}{'...' if len(eli5) > 120 else ''}")


async def run(concept_id: int | None = None, force: bool = False, limit: int | None = None):
    gen = ELI5Generator()

    if concept_id:
        print(f"\nGenerating ELI5 for concept ID {concept_id}...\n")
        eli5 = await gen.generate_for_concept(concept_id)
        if eli5:
            gen.store_eli5(concept_id, eli5)
            print(f"\n  ELI5: {eli5}")
        else:
            print("\n  Failed to generate ELI5.")
        return

    print("\nGenerating ELI5 for all eligible concepts...\n")
    stats = await gen.generate_all(force=force)
    print_summary(stats)


def main():
    parser = argparse.ArgumentParser(
        description="Phase 9C-2: Generate ELI5 explanations for concepts"
    )
    parser.add_argument(
        "--concept",
        type=int,
        default=None,
        help="Generate ELI5 for a single concept ID",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Regenerate ELI5 for ALL concepts (even those that already have one)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Only process this many concepts",
    )
    args = parser.parse_args()

    try:
        asyncio.run(run(concept_id=args.concept, force=args.force, limit=args.limit))
    except KeyboardInterrupt:
        print("\n\nInterrupted by user.")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
