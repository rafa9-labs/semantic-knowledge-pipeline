# ============================================================
# enrich_relationships.py — Phase 9C-2: Relationship Extraction Entry Point
# ============================================================
# Extracts typed relationships between concepts within each topic.
#
# USAGE:
#   python enrich_relationships.py              # Process all topics
#   python enrich_relationships.py --topic 5    # Process only topic ID 5
#   python enrich_relationships.py --dry-run    # Run LLM but don't store
#
# PREREQUISITES:
#   - PostgreSQL running with Phase 9A tables + Phase 9C-1 concepts
#   - Ollama running with gemma4:26b model pulled
#   - At least some topics with 2+ concepts
# ============================================================

import argparse
import asyncio
import logging
import sys

from database.connection import SessionLocal
from database.models import Concept, ConceptRelationship, Topic
from pipeline.relationship_extractor import RelationshipExtractor

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


def print_pre_summary():
    with SessionLocal() as session:
        topics = session.query(Topic).all()
        total_concepts = session.query(Concept).count()
        total_rels = session.query(ConceptRelationship).count()

        print("\n" + "=" * 60)
        print("RELATIONSHIP EXTRACTION — PRE-RUN SUMMARY")
        print("=" * 60)
        print(f"  Topics:              {len(topics)}")
        print(f"  Total concepts:      {total_concepts}")
        print(f"  Existing edges:      {total_rels}")
        print()

        for topic in topics:
            cc = session.query(Concept).filter(Concept.topic_id == topic.id).count()
            rc = (
                session.query(ConceptRelationship)
                .join(Concept, ConceptRelationship.from_concept_id == Concept.id)
                .filter(Concept.topic_id == topic.id)
                .count()
            )
            if cc >= 2:
                print(f"  [eligible] {topic.name}: {cc} concepts, {rc} relationships")
            elif cc == 1:
                print(f"  [skip]     {topic.name}: 1 concept (need 2+)")
            else:
                print(f"  [empty]    {topic.name}: no concepts")
        print("=" * 60 + "\n")


def print_post_summary(stats: dict):
    with SessionLocal() as session:
        total_rels = session.query(ConceptRelationship).count()

        print("\n" + "=" * 60)
        print("RELATIONSHIP EXTRACTION — RESULTS")
        print("=" * 60)
        print(f"  Topics processed:      {stats['topics_processed']}")
        print(f"  New relationships:     {stats['total_relationships']}")
        print(f"  Unmatched concepts:    {stats['total_unmatched']}")
        print(f"  Duplicates skipped:    {stats['total_duplicates']}")
        print(f"  Topics skipped (<2):   {stats['topics_skipped']}")
        print(f"  Total edges in DB now: {total_rels}")

        if stats.get("errors"):
            print("\n  ERRORS:")
            for e in stats["errors"]:
                print(f"    - {e}")

        print()

        # Show sample relationships by type
        from collections import Counter
        rel_types = [r.relationship_type for r in session.query(ConceptRelationship).all()]
        type_counts = Counter(rel_types)
        print("  Relationship type distribution:")
        for rtype, count in type_counts.most_common():
            print(f"    {rtype}: {count}")

        print()

        # Show a few sample edges
        samples = session.query(ConceptRelationship).limit(8).all()
        if samples:
            print("  Sample edges:")
            for rel in samples:
                from_name = session.query(Concept).get(rel.from_concept_id)
                to_name = session.query(Concept).get(rel.to_concept_id)
                fn = from_name.name if from_name else "?"
                tn = to_name.name if to_name else "?"
                print(f"    {fn} --[{rel.relationship_type}]--> {tn}")

        print("=" * 60 + "\n")


async def run(topic_id: int | None = None, dry_run: bool = False):
    extractor = RelationshipExtractor()

    if topic_id:
        print(f"\nExtracting relationships for topic ID {topic_id}...\n")
        result = await extractor.extract_for_topic(topic_id)

        print(f"\n  Topic: {result.topic_name}")
        print(f"  Relationships: {len(result.relationships)}")
        for r in result.relationships[:10]:
            print(f"    {r.from_concept} --[{r.relationship_type}]--> {r.to_concept}")
            if r.description:
                print(f"      ({r.description[:80]})")

        if not dry_run and result.relationships:
            stored, unmatched, dupes = extractor.store_relationships(result, topic_id)
            print(f"\n  Stored: {stored}, Unmatched: {unmatched}, Duplicates: {dupes}")
        elif dry_run:
            print("\n  (dry-run — not storing)")
    else:
        print_pre_summary()
        stats = await extractor.extract_all()
        if not dry_run:
            print_post_summary(stats)
        else:
            print(f"\n  (dry-run — {stats['total_relationships']} relationships would be stored)")


def main():
    parser = argparse.ArgumentParser(
        description="Phase 9C-2: Extract typed relationships between concepts"
    )
    parser.add_argument(
        "--topic",
        type=int,
        default=None,
        help="Process only this topic ID",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run extraction but don't store in database",
    )
    args = parser.parse_args()

    try:
        asyncio.run(run(topic_id=args.topic, dry_run=args.dry_run))
    except KeyboardInterrupt:
        print("\n\nInterrupted by user.")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
