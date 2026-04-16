# ============================================================
# enrich_concepts.py — Phase 9C-1: Concept Extraction Entry Point
# ============================================================
# This script runs the concept extraction pipeline:
#   1. Connects to PostgreSQL to read topics and their scraped articles
#   2. Sends article text to Gemma 4 via Ollama (1 LLM call per topic)
#   3. Extracts concept names with category, difficulty, and description
#   4. Deduplicates by slug and stores in the `concepts` table
#
# USAGE:
#   python enrich_concepts.py              # Process all topics
#   python enrich_concepts.py --topic 5    # Process only topic ID 5
#   python enrich_concepts.py --dry-run    # Run LLM but don't store in DB
#
# PREREQUISITES:
#   - PostgreSQL running with Phase 9A tables migrated
#   - Ollama running with gemma4:26b model pulled
#   - Articles scraped (Phase 9B completed)
# ============================================================

import argparse
import asyncio
import json
import logging
import sys

from database.connection import SessionLocal
from database.models import Concept, Topic, RawArticle
from pipeline.concept_extractor import ConceptExtractor

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


def print_pre_run_summary():
    """Show database state before running extraction."""
    with SessionLocal() as session:
        topics = session.query(Topic).all()
        total_articles = session.query(RawArticle).count()
        articles_with_topic = (
            session.query(RawArticle)
            .filter(RawArticle.topic_id.isnot(None))
            .count()
        )
        existing_concepts = session.query(Concept).count()

        print("\n" + "=" * 60)
        print("PHASE 9C-1: CONCEPT EXTRACTION — PRE-RUN SUMMARY")
        print("=" * 60)
        print(f"  Topics in database:       {len(topics)}")
        print(f"  Total articles:           {total_articles}")
        print(f"  Articles with topic_id:   {articles_with_topic}")
        print(f"  Existing concepts:        {existing_concepts}")
        print()
        print("  Topics with articles:")
        for topic in topics:
            count = (
                session.query(RawArticle)
                .filter(RawArticle.topic_id == topic.id)
                .count()
            )
            concepts_count = (
                session.query(Concept)
                .filter(Concept.topic_id == topic.id)
                .count()
            )
            status = f"{count} articles, {concepts_count} concepts"
            marker = "  ✓" if count > 0 else "  ✗"
            print(f"    {marker} {topic.name}: {status}")
        print("=" * 60 + "\n")


def print_post_run_summary(stats: dict):
    """Show results after extraction completes."""
    with SessionLocal() as session:
        total_concepts = session.query(Concept).count()

        print("\n" + "=" * 60)
        print("PHASE 9C-1: CONCEPT EXTRACTION — RESULTS")
        print("=" * 60)
        print(f"  Topics processed:         {stats['topics_processed']}")
        print(f"  New concepts inserted:    {stats['total_concepts']}")
        print(f"  Duplicates skipped:       {stats['total_duplicates_skipped']}")
        print(f"  Topics skipped (empty):   {stats['topics_skipped_no_articles']}")
        print(f"  Topics failed:            {stats['topics_failed']}")
        print(f"  Total concepts in DB now: {total_concepts}")

        if stats.get("errors"):
            print("\n  ERRORS:")
            for error in stats["errors"]:
                print(f"    - {error}")

        print()

        topics = session.query(Topic).all()
        for topic in topics:
            concepts = (
                session.query(Concept)
                .filter(Concept.topic_id == topic.id)
                .all()
            )
            if concepts:
                print(f"  {topic.name} ({len(concepts)} concepts):")
                for c in concepts:
                    print(f"    - [{c.category}] {c.name} (difficulty: {c.difficulty})")

        print("=" * 60 + "\n")


async def run_extraction(topic_id: int | None = None, dry_run: bool = False):
    """Run concept extraction for one topic or all topics."""
    extractor = ConceptExtractor()

    if topic_id:
        print(f"\nExtracting concepts for single topic ID: {topic_id}\n")
        result = await extractor.extract_for_topic(topic_id)

        print(f"\n  Topic: {result.topic_name}")
        print(f"  Concepts extracted: {len(result.concepts)}")
        for c in result.concepts:
            print(f"    - [{c.category}] {c.name} (difficulty: {c.difficulty})")
            print(f"      {c.description[:100]}...")

        if not dry_run and result.concepts:
            inserted, skipped = extractor.store_concepts(result, topic_id)
            print(f"\n  Stored: {inserted} inserted, {skipped} duplicates skipped")
        elif dry_run:
            print("\n  (dry-run mode — not storing in database)")
    else:
        print_pre_run_summary()
        stats = await extractor.extract_all_topics()
        if not dry_run:
            print_post_run_summary(stats)
        else:
            print("\n  (dry-run mode — concepts were NOT stored in database)")
            print(f"  Would have inserted: {stats['total_concepts']} concepts")


def main():
    parser = argparse.ArgumentParser(
        description="Phase 9C-1: Extract concepts from scraped articles using LLM"
    )
    parser.add_argument(
        "--topic",
        type=int,
        default=None,
        help="Process only this topic ID (default: process all topics)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run LLM extraction but don't store results in database",
    )
    parser.add_argument(
        "--model",
        type=str,
        default="gemma4:26b",
        help="Ollama model to use (default: gemma4:26b)",
    )
    args = parser.parse_args()

    try:
        asyncio.run(run_extraction(topic_id=args.topic, dry_run=args.dry_run))
    except KeyboardInterrupt:
        print("\n\nInterrupted by user.")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
