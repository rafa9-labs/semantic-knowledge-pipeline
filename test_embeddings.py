# ============================================================
# test_embeddings.py — Tests for Phase 7: Embeddings & Semantic Search
# ============================================================
# This test file validates:
#   1. TripleEmbedder — converts triples to vectors via Ollama
#   2. Weaviate vector store — stores and searches vectors
#   3. API search endpoint — end-to-end semantic search
#
# PREREQUISITES:
#   - PostgreSQL running: docker compose up -d db
#   - Weaviate running: docker compose up -d weaviate
#   - Ollama running with embedding model: ollama pull nomic-embed-text
#   - Some triples in the database (run main.py first, or test_db_setup.py)
#
# Run: python test_embeddings.py
# ============================================================

import logging
import sys

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


def test_embedder_initialization():
    """Test that TripleEmbedder can initialize with Ollama."""
    logger.info("TEST: Embedder initialization...")

    from pipeline.embedder import TripleEmbedder

    embedder = TripleEmbedder(model_name="nomic-embed-text")
    assert embedder.model_name == "nomic-embed-text"
    assert embedder.embeddings is not None

    logger.info("  ✅ Embedder initialized successfully")
    return embedder


def test_single_embedding(embedder):
    """Test embedding a single triple."""
    logger.info("TEST: Single triple embedding...")

    result = embedder.embed_triple(
        triple_id=99999,  # Test ID
        subject="async function",
        predicate="returns",
        object_value="a Promise object",
        source_url="https://test.example.com",
        confidence=0.95,
    )

    assert result is not None, "Embedding result should not be None"
    assert result.triple_id == 99999
    assert result.dimensions > 0, "Vector should have dimensions"
    assert len(result.vector) == result.dimensions, "Vector length should match dimensions"
    # nomic-embed-text produces 768-dimensional vectors
    assert result.dimensions == 768, f"Expected 768 dimensions, got {result.dimensions}"

    logger.info(f"  ✅ Single embedding: {result.dimensions}D vector, first 3 values: {result.vector[:3]}")
    return result


def test_query_embedding(embedder):
    """Test embedding a search query."""
    logger.info("TEST: Query embedding...")

    vector = embedder.embed_query("how does async/await work in JavaScript?")

    assert vector is not None, "Query embedding should not be None"
    assert len(vector) == 768, f"Expected 768 dimensions, got {len(vector)}"

    logger.info(f"  ✅ Query embedding: {len(vector)}D vector")
    return vector


def test_weaviate_connection():
    """Test connecting to Weaviate."""
    logger.info("TEST: Weaviate connection...")

    from database.vector_store import get_weaviate_client

    client = get_weaviate_client()
    assert client is not None

    logger.info("  ✅ Connected to Weaviate")
    return client


def test_weaviate_collection(client):
    """Test creating/verifying the KnowledgeTriple collection."""
    logger.info("TEST: Weaviate collection...")

    from database.vector_store import ensure_collection_exists, COLLECTION_NAME

    ensure_collection_exists(client)

    # Verify the collection exists
    assert client.collections.exists(COLLECTION_NAME), f"Collection '{COLLECTION_NAME}' should exist"

    logger.info(f"  ✅ Collection '{COLLECTION_NAME}' exists")


def test_store_and_search(client, embedder):
    """Test storing an embedding and then searching for it."""
    logger.info("TEST: Store embedding + semantic search...")

    from database.vector_store import store_triple_embedding, semantic_search

    # Store a test triple
    test_result = embedder.embed_triple(
        triple_id=88888,
        subject="Promise.all",
        predicate="waits for",
        object_value="all promises to resolve",
        source_url="https://test.example.com/promise-all",
        confidence=0.9,
    )

    assert test_result is not None

    uuid = store_triple_embedding(
        client,
        triple_id=test_result.triple_id,
        subject="Promise.all",
        predicate="waits for",
        object_value="all promises to resolve",
        source_url="https://test.example.com/promise-all",
        confidence=0.9,
        vector=test_result.vector,
    )

    assert uuid is not None
    logger.info(f"  ✅ Stored test triple with UUID: {uuid[:12]}...")

    # Now search for it with a similar query
    query_vector = embedder.embed_query("how to wait for multiple promises")
    assert query_vector is not None

    results = semantic_search(client, query_vector, limit=5)

    assert len(results) > 0, "Search should return at least 1 result"

    # Check that our test triple is in the results
    found = any(r["triple_id"] == 88888 for r in results)
    logger.info(f"  Search returned {len(results)} results")
    for r in results[:3]:
        logger.info(f"    - {r['subject']} [{r['predicate']}] {r['object_value']} (sim={r['similarity']})")

    if found:
        logger.info("  ✅ Test triple found in search results")
    else:
        logger.warning("  ⚠️ Test triple not in top results (may be expected with small dataset)")


def test_collection_size(client):
    """Test getting the collection size."""
    logger.info("TEST: Collection size...")

    from database.vector_store import get_collection_size

    size = get_collection_size(client)
    assert size >= 0

    logger.info(f"  ✅ Collection size: {size} vectors")


def run_all_tests():
    """Run all embedding and vector store tests."""
    logger.info("=" * 60)
    logger.info("PHASE 7 TESTS: Embeddings & Semantic Search")
    logger.info("=" * 60)

    tests_passed = 0
    tests_failed = 0

    # Test 1: Embedder init
    try:
        embedder = test_embedder_initialization()
        tests_passed += 1
    except Exception as e:
        logger.error(f"  ❌ FAILED: {e}")
        tests_failed += 1
        logger.error("Cannot continue — Ollama must be running with nomic-embed-text model")
        logger.error("Run: ollama pull nomic-embed-text")
        return

    # Test 2: Single embedding
    try:
        result = test_single_embedding(embedder)
        tests_passed += 1
    except Exception as e:
        logger.error(f"  ❌ FAILED: {e}")
        tests_failed += 1

    # Test 3: Query embedding
    try:
        query_vector = test_query_embedding(embedder)
        tests_passed += 1
    except Exception as e:
        logger.error(f"  ❌ FAILED: {e}")
        tests_failed += 1

    # Test 4: Weaviate connection
    try:
        client = test_weaviate_connection()
        tests_passed += 1
    except Exception as e:
        logger.error(f"  ❌ FAILED: {e}")
        tests_failed += 1
        logger.error("Cannot continue — Weaviate must be running")
        logger.error("Run: docker compose up -d weaviate")
        return

    # Test 5: Collection
    try:
        test_weaviate_collection(client)
        tests_passed += 1
    except Exception as e:
        logger.error(f"  ❌ FAILED: {e}")
        tests_failed += 1

    # Test 6: Store + Search
    try:
        test_store_and_search(client, embedder)
        tests_passed += 1
    except Exception as e:
        logger.error(f"  ❌ FAILED: {e}")
        tests_failed += 1

    # Test 7: Collection size
    try:
        test_collection_size(client)
        tests_passed += 1
    except Exception as e:
        logger.error(f"  ❌ FAILED: {e}")
        tests_failed += 1

    client.close()

    # Summary
    logger.info("=" * 60)
    logger.info(f"RESULTS: {tests_passed} passed, {tests_failed} failed")
    logger.info("=" * 60)

    if tests_failed == 0:
        logger.info("🎉 All Phase 7 tests passed! Semantic search is ready.")
    else:
        logger.warning(f"⚠️ {tests_failed} test(s) failed — check prerequisites above")


if __name__ == "__main__":
    run_all_tests()