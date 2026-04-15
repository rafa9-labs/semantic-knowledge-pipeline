# ============================================================
# scripts/cleanup_triples.py — Clean Garbage Triples from Database
# ============================================================
# This script scans the knowledge_triples table in PostgreSQL,
# runs each triple through our TripleFilter, and DELETES any
# that are hallucinations or low-quality garbage.
#
# WHEN TO RUN THIS:
#   - After adding the triple_filter.py module
#   - After re-scraping articles (new triples might have garbage)
#   - Periodically as a quality audit
#
# WHAT IT DOES:
#   1. Reads ALL triples from the database
#   2. Runs each through the TripleFilter (6 rules)
#   3. Shows a DETAILED report of what would be deleted
#   4. Asks for confirmation
#   5. Deletes the bad triples
#
# SAFETY:
#   - Uses a --dry-run flag by default (no deletions)
#   - Shows exactly what will be deleted before deleting
#   - Creates a backup report in JSON format
# ============================================================

import sys
import os
import json
import logging
from datetime import datetime

# Add parent directory to path so we can import our modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.connection import get_engine, get_session_factory
from database.models import KnowledgeTripleDB
from pipeline.triple_filter import TripleFilter
from models.knowledge import KnowledgeTriple

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)


def load_triples_from_db(session) -> list[dict]:
    """
    Load all triples from PostgreSQL as dictionaries.

    Returns raw DB rows (not Pydantic models) because we need
    the database ID for deletion.
    """
    rows = session.query(KnowledgeTripleDB).all()
    return [
        {
            "id": row.id,
            "subject": row.subject,
            "predicate": row.predicate,
            "object_value": row.object_value,
            "confidence": row.confidence or 0.0,
            "source_url": row.source_url,
        }
        for row in rows
    ]


def db_row_to_pydantic(row: dict) -> KnowledgeTriple:
    """
    Convert a database row dict to a Pydantic KnowledgeTriple.

    We need Pydantic models because our TripleFilter expects them.
    The "object_value" DB column maps to the "object_" Pydantic field.
    """
    return KnowledgeTriple(
        subject=row["subject"],
        predicate=row["predicate"],
        object_=row["object_value"],  # DB column → Pydantic field
        source_url=row["source_url"],
        confidence=row["confidence"],
    )


def run_cleanup(dry_run: bool = True):
    """
    Main cleanup routine.

    Args:
        dry_run: If True, show what WOULD be deleted but don't delete.
    """
    print("=" * 60)
    print("🧹 Triple Quality Cleanup")
    print(f"   Mode: {'DRY RUN (no changes)' if dry_run else 'LIVE (will delete!)'}")
    print("=" * 60)

    # Connect to database
    engine = get_engine()
    Session = get_session_factory(engine)
    session = Session()

    try:
        # Load all triples
        rows = load_triples_from_db(session)
        print(f"\n📊 Found {len(rows)} triples in database\n")

        if not rows:
            print("No triples to clean. Exiting.")
            return

        # Convert to Pydantic models and filter
        quality_filter = TripleFilter(min_confidence=0.0)  # Don't filter on confidence for cleanup
        pydantic_triples = []
        for row in rows:
            try:
                triple = db_row_to_pydantic(row)
                pydantic_triples.append((row["id"], triple))
            except Exception as e:
                print(f"  ⚠️  Could not parse triple ID={row['id']}: {e}")
                print(f"      {row['subject']} → {row['predicate']} → {row['object_value']}")

        # Run filter
        only_triples = [t for _, t in pydantic_triples]
        filter_result = quality_filter.filter_batch(only_triples)

        # Map back to DB IDs for deletion
        id_to_triple = {id_: t for id_, t in pydantic_triples}
        ids_to_delete = set()
        rejected_details = []

        for triple, reason in filter_result.rejected:
            # Find the DB ID for this rejected triple
            for db_id, pydantic_triple in pydantic_triples:
                if (pydantic_triple.subject == triple.subject
                    and pydantic_triple.predicate == triple.predicate
                    and pydantic_triple.object_ == triple.object_):
                    ids_to_delete.add(db_id)
                    rejected_details.append({
                        "id": db_id,
                        "subject": triple.subject,
                        "predicate": triple.predicate,
                        "object": triple.object_,
                        "confidence": triple.confidence,
                        "reason": reason,
                    })
                    break

        # Print report
        print(f"{'─' * 60}")
        print(f"  ✅ ACCEPTED: {len(filter_result.accepted)} triples")
        print(f"  ❌ REJECTED: {len(filter_result.rejected)} triples")
        print(f"  📈 Pass rate: {filter_result.acceptance_rate:.0%}")
        print(f"{'─' * 60}")

        if rejected_details:
            print(f"\n🗑️  Triples to be removed:\n")
            for detail in rejected_details:
                print(
                    f"  [{detail['id']:>3}] "
                    f'"{detail["subject"]}" → "{detail["predicate"]}" → "{detail["object"]}"'
                )
                print(f"       Reason: {detail['reason']}")
                print()

        # Rejection breakdown
        if filter_result.stats.get("rejections_by_rule"):
            print("📈 Rejection breakdown by rule:")
            for rule, count in filter_result.stats["rejections_by_rule"].items():
                print(f"   {rule}: {count}")
            print()

        # Save report
        report_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            f"cleanup_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
        )
        with open(report_path, "w") as f:
            json.dump({
                "timestamp": datetime.now().isoformat(),
                "dry_run": dry_run,
                "total_triples": len(rows),
                "accepted": len(filter_result.accepted),
                "rejected": len(filter_result.rejected),
                "ids_to_delete": sorted(ids_to_delete),
                "rejected_details": rejected_details,
                "stats": filter_result.stats,
            }, f, indent=2)
        print(f"📄 Report saved to: {report_path}")

        # Delete if not dry run
        if not dry_run and ids_to_delete:
            print(f"\n⚠️  About to DELETE {len(ids_to_delete)} triples from the database!")
            confirm = input("Type 'DELETE' to confirm: ").strip()

            if confirm == "DELETE":
                # Delete in bulk
                deleted = (
                    session.query(KnowledgeTripleDB)
                    .filter(KnowledgeTripleDB.id.in_(ids_to_delete))
                    .delete(synchronize_session=False)
                )
                session.commit()
                print(f"\n✅ Deleted {deleted} triples from database")
            else:
                print("\n❌ Cancelled — no changes made")
        elif dry_run and ids_to_delete:
            print(f"\n💡 Run with --live flag to actually delete these triples:")
            print(f"   python scripts/cleanup_triples.py --live")

    except Exception as e:
        session.rollback()
        logger.error(f"Cleanup failed: {e}")
        raise
    finally:
        session.close()
        engine.dispose()


if __name__ == "__main__":
    # Parse --live flag
    dry_run = "--live" not in sys.argv
    run_cleanup(dry_run=dry_run)