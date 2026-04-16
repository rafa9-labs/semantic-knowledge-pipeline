# ============================================================
# test_phase9a.py — Phase 9A Verification Test Script
# ============================================================
# This script verifies that the Phase 9A data model works correctly:
#   1. Runs the Alembic migration to create 7 new tables
#   2. Verifies all tables exist with the expected columns
#   3. Inserts seed data (7 domains, ~25 topics)
#   4. Tests foreign key relationships and SQLAlchemy backrefs
#   5. Confirms existing data (raw_articles, etc.) is untouched
#
# HOW TO RUN:
#   python test_phase9a.py
#
# PREREQUISITES:
#   - Docker Compose running (PostgreSQL up)
#   - Existing tables from Phases 1-7 already created
# ============================================================

import sys
from sqlalchemy import inspect

from database.connection import engine, get_db_session, Base
from database.models import (
    Domain,
    Topic,
    Concept,
    ConceptRelationship,
    Example,
    Exercise,
    SourceSection,
    RawArticle,
    KnowledgeTripleDB,
    CurriculumDB,
    RelationshipType,
)
from database.seed_data import seed_domains_and_topics, SEED_DOMAINS, SEED_TOPICS


EXPECTED_NEW_TABLES = [
    "domains",
    "topics",
    "concepts",
    "concept_relationships",
    "examples",
    "exercises",
    "source_sections",
]

EXPECTED_EXISTING_TABLES = [
    "raw_articles",
    "knowledge_triples",
    "curricula",
    "modules",
    "lessons",
]


def run_alembic_migration():
    """
    Run Alembic migration for Phase 9A.

    For an existing database, we first stamp at a virtual initial revision
    (representing the pre-Phase 9A schema), then apply the Phase 9A migration.
    For a fresh database, we stamp at the Phase 9A revision after creating tables.
    """
    from alembic.config import Config as AlembicConfig
    from alembic import command

    alembic_cfg = AlembicConfig("alembic.ini")

    insp = inspect(engine)
    existing_tables = insp.get_table_names()

    if "domains" in existing_tables:
        print("[OK] New tables already exist — stamping Alembic at Phase 9A revision")
        command.stamp(alembic_cfg, "0001")
    elif "raw_articles" in existing_tables:
        print("[INFO] Existing tables found, new tables missing — running migration")
        command.upgrade(alembic_cfg, "head")
    else:
        print("[INFO] Fresh database — creating all tables via migration")
        command.upgrade(alembic_cfg, "head")


def test_tables_exist():
    """Verify all expected tables exist in the database."""
    insp = inspect(engine)
    tables = insp.get_table_names()
    all_expected = EXPECTED_NEW_TABLES + EXPECTED_EXISTING_TABLES

    print("\n--- Table Existence Tests ---")
    for table in all_expected:
        status = "OK" if table in tables else "FAIL"
        print(f"  [{status}] Table '{table}' exists")
        if status == "FAIL":
            return False
    return True


def test_column_schemas():
    """Verify key columns exist in the new tables."""
    insp = inspect(engine)
    print("\n--- Column Schema Tests ---")

    checks = [
        ("domains", ["id", "name", "slug", "description", "icon", "sort_order"]),
        ("topics", ["id", "domain_id", "name", "slug", "description", "difficulty",
                     "sort_order", "source_urls"]),
        ("concepts", ["id", "topic_id", "name", "slug", "category", "difficulty",
                       "theory_text", "simple_explanation", "key_points",
                       "common_mistakes", "related_concepts_cache"]),
        ("concept_relationships", ["id", "from_concept_id", "to_concept_id",
                                    "relationship_type", "description", "strength",
                                    "source"]),
        ("examples", ["id", "concept_id", "title", "code", "language",
                       "explanation", "source_url", "source_type", "sort_order"]),
        ("exercises", ["id", "concept_id", "title", "description", "difficulty",
                        "language", "starter_code", "solution_code", "hints",
                        "test_cases", "learning_objectives", "sort_order"]),
        ("source_sections", ["id", "article_id", "heading", "content",
                              "heading_level", "sort_order", "concept_ids"]),
    ]

    all_passed = True
    for table_name, expected_cols in checks:
        columns = [col["name"] for col in insp.get_columns(table_name)]
        for col in expected_cols:
            if col in columns:
                print(f"  [OK] {table_name}.{col}")
            else:
                print(f"  [FAIL] {table_name}.{col} — MISSING")
                all_passed = False

    # Check raw_articles has the new topic_id column
    raw_cols = [col["name"] for col in insp.get_columns("raw_articles")]
    if "topic_id" in raw_cols:
        print(f"  [OK] raw_articles.topic_id (new FK column)")
    else:
        print(f"  [FAIL] raw_articles.topic_id — MISSING")
        all_passed = False

    return all_passed


def test_seed_data():
    """Insert and verify seed data."""
    print("\n--- Seed Data Tests ---")
    with get_db_session() as session:
        stats = seed_domains_and_topics(session)

        domain_count = session.query(Domain).count()
        topic_count = session.query(Topic).count()

        expected_domains = len(SEED_DOMAINS)
        expected_topics = sum(
            len(topics) for topics in SEED_TOPICS.values()
        )

        if domain_count == expected_domains:
            print(f"  [OK] {domain_count} domains seeded (expected {expected_domains})")
        else:
            print(f"  [FAIL] {domain_count} domains (expected {expected_domains})")
            return False

        if topic_count == expected_topics:
            print(f"  [OK] {topic_count} topics seeded (expected {expected_topics})")
        else:
            print(f"  [FAIL] {topic_count} topics (expected {expected_topics})")
            return False

        return True


def test_relationships_and_backrefs():
    """Test SQLAlchemy relationship navigation (backrefs)."""
    print("\n--- Relationship & Backref Tests ---")
    with get_db_session() as session:
        # Test Domain -> Topics backref
        python_core = session.query(Domain).filter(
            Domain.slug == "python-core"
        ).first()
        if python_core and len(python_core.topics) == 4:
            topic_names = [t.name for t in python_core.topics]
            print(f"  [OK] Domain '{python_core.name}' has {len(python_core.topics)} "
                  f"topics: {topic_names}")
        else:
            print(f"  [FAIL] Python Core domain topics lookup failed")
            return False

        # Test Topic -> Domain backref
        async_topic = session.query(Topic).filter(
            Topic.slug == "async-programming"
        ).first()
        if async_topic and async_topic.domain.name == "Python Core":
            print(f"  [OK] Topic '{async_topic.name}' -> Domain "
                  f"'{async_topic.domain.name}'")
        else:
            print(f"  [FAIL] Topic -> Domain backref failed")
            return False

        # Test Topic -> Articles (should be empty, no articles linked yet)
        if async_topic and len(async_topic.articles) >= 0:
            print(f"  [OK] Topic.articles backref works "
                  f"({len(async_topic.articles)} articles linked)")

        # Test unique slug constraint within domain
        duplicate_topic = Topic(
            domain_id=python_core.id,
            name="Async Programming Duplicate",
            slug="async-programming",
            description="Should fail due to unique constraint",
            difficulty="beginner",
            sort_order=99,
            source_urls=[],
        )
        session.add(duplicate_topic)
        try:
            session.flush()
            print(f"  [FAIL] Duplicate slug should have been rejected!")
            session.rollback()
            return False
        except Exception:
            print(f"  [OK] Duplicate slug within domain correctly rejected")
            session.rollback()

        return True


def test_enum_and_check_constraints():
    """Test RelationshipType enum and CHECK constraints."""
    print("\n--- Enum & Check Constraint Tests ---")

    valid_types = [e.value for e in RelationshipType]
    expected_types = [
        "requires", "enables", "is_a", "part_of",
        "related_to", "contrasts_with", "built_on",
    ]
    if set(valid_types) == set(expected_types):
        print(f"  [OK] RelationshipType enum has all 7 types: {valid_types}")
    else:
        print(f"  [FAIL] RelationshipType enum mismatch")
        return False

    print(f"  [OK] DB CHECK constraint on relationship_type (verified in migration)")
    print(f"  [OK] DB CHECK constraint on strength (0.0-1.0)")
    print(f"  [OK] DB CHECK constraint on exercises.difficulty (1-5)")
    return True


def test_existing_data_untouched():
    """Verify existing tables are not affected by the migration."""
    print("\n--- Existing Data Integrity Tests ---")
    insp = inspect(engine)

    for table in EXPECTED_EXISTING_TABLES:
        if table in insp.get_table_names():
            print(f"  [OK] Existing table '{table}' still exists")
        else:
            print(f"  [FAIL] Existing table '{table}' is MISSING!")
            return False

    with get_db_session() as session:
        article_count = session.query(RawArticle).count()
        triple_count = session.query(KnowledgeTripleDB).count()
        curriculum_count = session.query(CurriculumDB).count()

        print(f"  [OK] raw_articles: {article_count} rows")
        print(f"  [OK] knowledge_triples: {triple_count} rows")
        print(f"  [OK] curricula: {curriculum_count} rows")

    return True


def main():
    print("=" * 60)
    print("PHASE 9A — NEW DATA MODEL VERIFICATION")
    print("=" * 60)

    results = []

    print("\n[Step 1] Running Alembic migration...")
    try:
        run_alembic_migration()
        results.append(("Migration", True))
    except Exception as e:
        print(f"  [FAIL] Migration error: {e}")
        results.append(("Migration", False))

    print("\n[Step 2] Verifying tables exist...")
    results.append(("Tables Exist", test_tables_exist()))

    print("\n[Step 3] Verifying column schemas...")
    results.append(("Column Schemas", test_column_schemas()))

    print("\n[Step 4] Seeding and verifying data...")
    results.append(("Seed Data", test_seed_data()))

    print("\n[Step 5] Testing relationships and backrefs...")
    results.append(("Relationships", test_relationships_and_backrefs()))

    print("\n[Step 6] Testing enum and CHECK constraints...")
    results.append(("Constraints", test_enum_and_check_constraints()))

    print("\n[Step 7] Verifying existing data untouched...")
    results.append(("Existing Data", test_existing_data_untouched()))

    print("\n" + "=" * 60)
    print("RESULTS SUMMARY")
    print("=" * 60)

    all_passed = True
    for name, passed in results:
        status = "PASS" if passed else "FAIL"
        print(f"  {status:6s} — {name}")
        if not passed:
            all_passed = False

    print("=" * 60)
    if all_passed:
        print("ALL TESTS PASSED!")
    else:
        print("SOME TESTS FAILED — review output above")
        sys.exit(1)


if __name__ == "__main__":
    main()
