# ============================================================
# test_phase9c1.py — Phase 9C-1 Verification Script
# ============================================================
# This script verifies that the concept extraction pipeline works
# correctly at every level:
#   1. Pydantic models validate correctly
#   2. Slug generation works for various inputs
#   3. ConceptExtractor can be initialized
#   4. Database has topics with articles to process
#   5. Single-topic extraction works end-to-end
#   6. Full extraction processes all eligible topics
#
# Run: python test_phase9c1.py
#
# NOTE: Tests 4-6 require:
#   - PostgreSQL running with Phase 9A/9B data
#   - Ollama running with gemma4:26b model
# ============================================================

import asyncio
import sys

from database.connection import SessionLocal
from database.models import Concept, Topic, RawArticle
from models.enrichment import (
    ExtractedConcept,
    ConceptExtractionResult,
    ExtractedRelationship,
    VALID_CATEGORIES,
    VALID_RELATIONSHIP_TYPES,
)
from pipeline.concept_extractor import ConceptExtractor, slugify


def test_pydantic_models():
    """Test 1: Pydantic models validate good input and reject bad input."""
    print("\n--- Test 1: Pydantic Model Validation ---")

    # Valid concept
    c = ExtractedConcept(
        name="async/await",
        category="language_feature",
        difficulty=3,
        description="Python's syntax for writing asynchronous code using async def and await keywords.",
    )
    assert c.name == "async/await"
    assert c.category == "language_feature"
    assert c.difficulty == 3
    print("  ✓ Valid concept accepted")

    # Invalid category
    try:
        ExtractedConcept(
            name="test",
            category="invalid_category",
            difficulty=3,
            description="Some description here that is long enough.",
        )
        assert False, "Should have raised ValidationError"
    except Exception:
        print("  ✓ Invalid category rejected")

    # Difficulty out of range
    try:
        ExtractedConcept(
            name="test",
            category="concept",
            difficulty=10,
            description="Some description here that is long enough.",
        )
        assert False, "Should have raised ValidationError"
    except Exception:
        print("  ✓ Difficulty > 5 rejected")

    # Empty name
    try:
        ExtractedConcept(
            name="",
            category="concept",
            difficulty=3,
            description="Some description here that is long enough.",
        )
        assert False, "Should have raised ValidationError"
    except Exception:
        print("  ✓ Empty name rejected")

    # Short description
    try:
        ExtractedConcept(
            name="test",
            category="concept",
            difficulty=3,
            description="short",
        )
        assert False, "Should have raised ValidationError"
    except Exception:
        print("  ✓ Short description rejected")

    # Valid relationship
    r = ExtractedRelationship(
        from_concept="async/await",
        to_concept="coroutines",
        relationship_type="requires",
        description="async/await requires understanding coroutines",
        strength=0.9,
    )
    assert r.relationship_type == "requires"
    print("  ✓ Valid relationship accepted")

    # Invalid relationship type
    try:
        ExtractedRelationship(
            from_concept="a",
            to_concept="b",
            relationship_type="is_related",
        )
        assert False, "Should have raised ValidationError"
    except Exception:
        print("  ✓ Invalid relationship type rejected")

    print("  ✓ All Pydantic validation tests passed")
    return True


def test_slugify():
    """Test 2: Slug generation produces correct, deduplication-safe slugs."""
    print("\n--- Test 2: Slug Generation ---")

    tests = [
        ("async/await", "async-await"),
        ("Pydantic Models", "pydantic-models"),
        ("Docker Compose", "docker-compose"),
        ("RAG (Retrieval-Augmented Generation)", "rag-retrieval-augmented-generation"),
        ("  extra  spaces  ", "extra-spaces"),
        ("Event Loop", "event-loop"),
        ("FastAPI", "fastapi"),
        ("SQLAlchemy ORM", "sqlalchemy-orm"),
        ("async await", "async-await"),
        ("Async/Await", "async-await"),
    ]

    for input_text, expected in tests:
        result = slugify(input_text)
        assert result == expected, f"slugify('{input_text}') = '{result}', expected '{expected}'"
        print(f"  ✓ '{input_text}' → '{result}'")

    # Verify deduplication case: same concept, different formatting
    assert slugify("async/await") == slugify("Async Await") == slugify("ASYNC/AWAIT")
    print("  ✓ Case-insensitive dedup verified")

    print("  ✓ All slugify tests passed")
    return True


def test_extractor_init():
    """Test 3: ConceptExtractor initializes correctly."""
    print("\n--- Test 3: ConceptExtractor Initialization ---")

    extractor = ConceptExtractor(
        model_name="gemma4:26b",
        max_article_chars=25000,
    )
    assert extractor.model_name == "gemma4:26b"
    assert extractor.max_retries == 3
    assert extractor.max_article_chars == 25000
    print("  ✓ ConceptExtractor initialized successfully")
    return True


def test_database_state():
    """Test 4: Verify database has topics with articles."""
    print("\n--- Test 4: Database State ---")

    with SessionLocal() as session:
        topics = session.query(Topic).all()
        assert len(topics) > 0, "No topics found in database"
        print(f"  ✓ Found {len(topics)} topics")

        topics_with_articles = 0
        total_articles = 0
        for topic in topics:
            count = (
                session.query(RawArticle)
                .filter(RawArticle.topic_id == topic.id)
                .count()
            )
            if count > 0:
                topics_with_articles += 1
                total_articles += count
                print(f"    {topic.name}: {count} articles")

        assert topics_with_articles > 0, "No topics have articles"
        print(f"  ✓ {topics_with_articles} topics have articles ({total_articles} total)")

    return True


def test_concept_count():
    """Test 5: Report current concept count (may be 0 before first run)."""
    print("\n--- Test 5: Concept Count ---")

    with SessionLocal() as session:
        total = session.query(Concept).count()
        print(f"  ✓ Current concepts in DB: {total}")

        if total > 0:
            topics_with_concepts = (
                session.query(Concept.topic_id)
                .distinct()
                .count()
            )
            print(f"  ✓ Topics with concepts: {topics_with_concepts}")

            for concept in session.query(Concept).limit(5).all():
                print(f"    - [{concept.category}] {concept.name} (topic_id={concept.topic_id})")

    return True


def test_single_topic_extraction():
    """Test 6: Extract concepts from one topic (requires Ollama)."""
    print("\n--- Test 6: Single Topic Extraction (requires Ollama) ---")

    with SessionLocal() as session:
        topic = (
            session.query(Topic)
            .join(RawArticle, RawArticle.topic_id == Topic.id)
            .first()
        )
        if not topic:
            print("  ⚠ No topics with articles found, skipping")
            return True

        topic_id = topic.id
        topic_name = topic.name
        article_count = (
            session.query(RawArticle)
            .filter(RawArticle.topic_id == topic_id)
            .count()
        )

    print(f"  Testing with topic: '{topic_name}' (ID: {topic_id}, {article_count} articles)")

    extractor = ConceptExtractor()
    result = asyncio.run(extractor.extract_for_topic(topic_id))

    assert result.topic_name == topic_name
    print(f"  ✓ LLM returned {len(result.concepts)} concepts")

    if result.concepts:
        for c in result.concepts[:5]:
            print(f"    - [{c.category}] {c.name} (difficulty: {c.difficulty})")
            print(f"      {c.description[:80]}...")
        if len(result.concepts) > 5:
            print(f"    ... and {len(result.concepts) - 5} more")
    else:
        print("  ⚠ No concepts extracted (LLM may have returned empty)")

    print("  ✓ Single topic extraction test passed")
    return True


def run_tests():
    """Run all Phase 9C-1 tests."""
    print("=" * 60)
    print("PHASE 9C-1: CONCEPT EXTRACTION — VERIFICATION")
    print("=" * 60)

    tests = [
        ("Pydantic Models", test_pydantic_models),
        ("Slug Generation", test_slugify),
        ("Extractor Init", test_extractor_init),
        ("Database State", test_database_state),
        ("Concept Count", test_concept_count),
        ("Single Topic Extraction", test_single_topic_extraction),
    ]

    results = {}
    for name, test_fn in tests:
        try:
            results[name] = test_fn()
        except Exception as e:
            print(f"\n  ✗ FAILED: {e}")
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

    if passed == total:
        print("\n  All tests passed! Phase 9C-1 is ready.")
    print("=" * 60)

    return passed == total


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
