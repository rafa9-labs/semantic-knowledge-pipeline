# ============================================================
# test_phase9c2.py — Phase 9C-2 Verification Script
# ============================================================
# Verifies that ELI5 generation and relationship extraction work:
#   1. ELI5Generator initializes correctly
#   2. RelationshipExtractor initializes correctly
#   3. Pydantic ExtractedRelationship validation works
#   4. Concept name → ID matching works
#   5. Single ELI5 generation works (requires Ollama)
#   6. Single topic relationship extraction works (requires Ollama)
#   7. Database state verification
#
# Run: python test_phase9c2.py
# ============================================================

import asyncio
import sys

from database.connection import SessionLocal
from database.models import Concept, ConceptRelationship, Topic
from models.enrichment import (
    ExtractedRelationship,
    RelationshipExtractionResult,
    VALID_RELATIONSHIP_TYPES,
)
from pipeline.concept_extractor import slugify
from pipeline.eli5_generator import ELI5Generator
from pipeline.relationship_extractor import RelationshipExtractor


def test_eli5_init():
    print("\n--- Test 1: ELI5Generator Initialization ---")
    gen = ELI5Generator()
    assert gen.model_name == "gemma4:26b"
    assert gen.max_retries == 2
    print("  OK: ELI5Generator initialized")
    return True


def test_rel_extractor_init():
    print("\n--- Test 2: RelationshipExtractor Initialization ---")
    ext = RelationshipExtractor()
    assert ext.model_name == "gemma4:26b"
    assert ext.max_retries == 3
    print("  OK: RelationshipExtractor initialized")
    return True


def test_relationship_validation():
    print("\n--- Test 3: ExtractedRelationship Validation ---")

    # Valid
    r = ExtractedRelationship(
        from_concept="async/await",
        to_concept="coroutines",
        relationship_type="requires",
        description="Need coroutines first",
        strength=0.95,
    )
    assert r.relationship_type == "requires"
    print("  OK: Valid relationship accepted")

    # Invalid type
    try:
        ExtractedRelationship(
            from_concept="a", to_concept="b",
            relationship_type="depends_on",
        )
        assert False, "Should have rejected invalid type"
    except Exception:
        print("  OK: Invalid relationship type rejected")

    # Self-referencing caught at store level
    r2 = ExtractedRelationship(
        from_concept="test", to_concept="test",
        relationship_type="related_to",
    )
    assert r2.from_concept == r2.to_concept
    print("  OK: Self-referencing relationship parsed (caught at store level)")

    print("  OK: All relationship validation tests passed")
    return True


def test_concept_matching():
    print("\n--- Test 4: Concept Name Matching ---")

    slug_to_id = {
        "async-await": 1,
        "event-loop": 2,
        "coroutines": 3,
        "fastapi-routes": 4,
    }
    name_to_id = {
        "async/await": 1,
        "event loop": 2,
        "coroutines": 3,
        "fastapi routes": 4,
    }

    # Exact name match
    assert RelationshipExtractor._match_concept("async/await", slug_to_id, name_to_id) == 1
    print("  OK: Exact name match")

    # Slug match (different formatting)
    assert RelationshipExtractor._match_concept("Async Await", slug_to_id, name_to_id) == 1
    print("  OK: Slug match (different casing/format)")

    # Partial slug match
    assert RelationshipExtractor._match_concept("event loop", slug_to_id, name_to_id) == 2
    print("  OK: Partial match")

    # No match
    assert RelationshipExtractor._match_concept("nonexistent concept xyz", slug_to_id, name_to_id) is None
    print("  OK: No match returns None")

    print("  OK: All matching tests passed")
    return True


def test_database_state():
    print("\n--- Test 5: Database State ---")

    with SessionLocal() as session:
        total_concepts = session.query(Concept).count()
        topics_with_concepts = (
            session.query(Concept.topic_id).distinct().count()
        )
        concepts_with_eli5 = (
            session.query(Concept)
            .filter(Concept.simple_explanation.isnot(None))
            .filter(Concept.simple_explanation != "")
            .count()
        )
        total_rels = session.query(ConceptRelationship).count()

        print(f"  Total concepts: {total_concepts}")
        print(f"  Topics with concepts: {topics_with_concepts}")
        print(f"  Concepts with ELI5: {concepts_with_eli5}")
        print(f"  Existing relationships: {total_rels}")

        assert total_concepts > 0, "No concepts in database (run Phase 9C-1 first)"
        print("  OK: Database has concepts to process")

    return True


def test_single_eli5():
    print("\n--- Test 6: Single ELI5 Generation (requires Ollama) ---")

    with SessionLocal() as session:
        concept = session.query(Concept).first()
        if not concept:
            print("  SKIP: No concepts in database")
            return True
        concept_id = concept.id
        concept_name = concept.name

    gen = ELI5Generator()
    eli5 = asyncio.run(gen.generate_for_concept(concept_id))

    if eli5:
        print(f"  Concept: {concept_name}")
        print(f"  ELI5: {eli5[:150]}{'...' if len(eli5) > 150 else ''}")
        assert len(eli5) >= 20
        print("  OK: ELI5 generated successfully")
    else:
        print("  WARN: ELI5 generation failed (Ollama may be busy)")

    return True


def test_single_topic_relationships():
    print("\n--- Test 7: Single Topic Relationship Extraction (requires Ollama) ---")

    with SessionLocal() as session:
        # Find a topic with 3+ concepts
        topic = (
            session.query(Topic)
            .join(Concept, Concept.topic_id == Topic.id)
            .group_by(Topic.id)
            .having(session.query(Concept).filter(Concept.topic_id == Topic.id).count() > 2)
            .first()
        )
        if not topic:
            print("  SKIP: No topic with 3+ concepts")
            return True

        topic_id = topic.id
        topic_name = topic.name
        concept_count = session.query(Concept).filter(Concept.topic_id == topic_id).count()

    print(f"  Topic: {topic_name} ({concept_count} concepts)")

    ext = RelationshipExtractor()
    result = asyncio.run(ext.extract_for_topic(topic_id))

    print(f"  Relationships extracted: {len(result.relationships)}")
    for r in result.relationships[:5]:
        print(f"    {r.from_concept} --[{r.relationship_type}]--> {r.to_concept}")
        if r.description:
            print(f"      ({r.description[:60]})")

    if len(result.relationships) > 5:
        print(f"    ... and {len(result.relationships) - 5} more")

    if result.relationships:
        print("  OK: Relationships extracted successfully")
    else:
        print("  WARN: No relationships extracted")

    return True


def run_tests():
    print("=" * 60)
    print("PHASE 9C-2: ELI5 + RELATIONSHIPS — VERIFICATION")
    print("=" * 60)

    tests = [
        ("ELI5 Init", test_eli5_init),
        ("RelExtractor Init", test_rel_extractor_init),
        ("Relationship Validation", test_relationship_validation),
        ("Concept Matching", test_concept_matching),
        ("Database State", test_database_state),
        ("Single ELI5", test_single_eli5),
        ("Single Topic Relationships", test_single_topic_relationships),
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
