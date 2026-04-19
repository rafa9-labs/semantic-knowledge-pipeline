import asyncio
import argparse
import logging

from pipeline.concept_enricher import ConceptEnricher
from database.connection import SessionLocal
from database.models import Concept

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


async def main():
    parser = argparse.ArgumentParser(description="Enrich concepts with key_points and common_mistakes")
    parser.add_argument("--concept", type=int, help="Specific concept ID to enrich")
    parser.add_argument("--force", action="store_true", help="Regenerate even if already enriched")
    parser.add_argument("--limit", type=int, help="Max concepts to process")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be processed")
    args = parser.parse_args()

    enricher = ConceptEnricher()

    if args.dry_run:
        with SessionLocal() as session:
            query = session.query(Concept)
            if not args.force:
                from sqlalchemy import cast, Text
                query = query.filter(
                    Concept.key_points.is_(None)
                    | (cast(Concept.key_points, Text) == "[]")
                )
            concepts = query.all()
            if args.limit:
                concepts = concepts[:args.limit]
        print(f"Would enrich {len(concepts)} concepts")
        for c in concepts:
            print(f"  [{c.id}] {c.name} ({c.category})")
        return

    if args.concept:
        result = await enricher.enrich_concept(args.concept)
        if result.key_points or result.common_mistakes:
            enricher.store_enrichment(result, args.concept)
            print(f"Enriched '{result.concept_name}': {len(result.key_points)} key_points, {len(result.common_mistakes)} common_mistakes")
        else:
            print(f"Failed to enrich concept {args.concept}")
        return

    stats = await enricher.enrich_all(force=args.force, limit=args.limit)
    print(f"\nDone. Enriched: {stats['enriched']}, Failed: {stats['failed']}, Skipped: {stats['skipped']}")


if __name__ == "__main__":
    asyncio.run(main())
