# ============================================================
# database/vector_store.py — Weaviate Vector Database Client
# ============================================================
# This module handles ALL interaction with Weaviate, our vector database.
# It follows the same pattern as database/connection.py for PostgreSQL:
#   - Encapsulate the connection logic in one place
#   - Provide clean methods for store/query operations
#   - Handle errors gracefully with retries
#
# WHAT IS A VECTOR DATABASE?
#   Traditional databases search by EXACT MATCH: "find rows WHERE subject = 'Promise'"
#   Vector databases search by MEANING: "find concepts SIMILAR TO 'Promise'"
#
#   They do this by storing MATHEMATICAL VECTORS (arrays of floats) alongside data.
#   Each vector represents the "meaning" of the text. Similar meanings → similar vectors.
#   Weaviate finds the "nearest neighbors" in vector space = most similar concepts.
#
# DATA FLOW:
#   PostgreSQL (triples) → embedder.py (generate vectors) → this module (store in Weaviate)
#   API request ("find similar to X") → embedder.py (vectorize query) → this module (search)
#
# WHY WEAVIATE?
#   - Fully local (Docker, no cloud dependency)
#   - Supports custom vectors (we generate our own via Ollama, not a paid API)
#   - Fast nearest-neighbor search using HNSW algorithm
#   - Metadata filtering (filter by confidence, source_url, etc.)
# ============================================================

import logging
import os
from typing import Optional

import weaviate
from weaviate.classes.config import Configure, Property, DataType
from weaviate.classes.query import Filter, MetadataQuery
from weaviate.util import generate_uuid5

logger = logging.getLogger(__name__)

# ----------------------------------------------------------
# COLLECTION NAME
# ----------------------------------------------------------
# In Weaviate, data is stored in "collections" (like tables in PostgreSQL).
# Each collection has a defined schema (properties + vector config).
# We use a single collection for all our knowledge triple embeddings.
COLLECTION_NAME = "KnowledgeTriple"


def get_weaviate_client() -> weaviate.WeaviateClient:
    """
    Create and return a connected Weaviate client.

    This is the CONNECTION FACTORY — same pattern as database/connection.py.
    Every function that needs Weaviate calls this to get a client.

    WHY CONNECT ON EACH CALL?
      Weaviate clients are lightweight. Creating a new one per operation is safe
      and avoids stale connection issues. The underlying HTTP connection pooling
      handles efficiency.

    Returns:
        weaviate.WeaviateClient: A connected client ready for operations.

    Raises:
        ConnectionError: If Weaviate is not running (Docker container down).
    """
    weaviate_url = os.getenv("WEAVIATE_URL", "http://localhost:8080")

    try:
        # Weaviate v4 client: connects via REST (port 8080) for schema ops
        # and gRPC (port 50051) for fast data ops.
        # additional_config lets us set timeouts for large batch operations.
        client = weaviate.connect_to_local(
            host=weaviate_url.replace("http://", "").replace("https://", "").split(":")[0],
            port=int(weaviate_url.split(":")[-1]) if ":" in weaviate_url else 8080,
        )
        logger.debug(f"Connected to Weaviate at {weaviate_url}")
        return client
    except Exception as e:
        logger.error(f"Failed to connect to Weaviate at {weaviate_url}: {e}")
        logger.error("Make sure Docker is running: docker compose up -d weaviate")
        raise ConnectionError(
            f"Cannot connect to Weaviate at {weaviate_url}. "
            "Run: docker compose up -d weaviate"
        ) from e


def ensure_collection_exists(client: weaviate.WeaviateClient) -> None:
    """
    Create the KnowledgeTriple collection in Weaviate if it doesn't exist.

    This is the Weaviate equivalent of SQLAlchemy's Base.metadata.create_all().
    We define the SCHEMA (properties and vector config) here.

    SCHEMA DESIGN:
        Properties (stored alongside the vector):
        - triple_id: The PostgreSQL ID (for joining back to SQL data)
        - subject: The triple's subject (e.g., "async function")
        - predicate: The relationship (e.g., "enables")
        - object_value: The object (e.g., "asynchronous behavior")
        - source_url: Where the triple came from
        - confidence: LLM confidence score (0.0-1.0)

        Vector config:
        - We use EXPLICIT vectors (none) — our embedder.py provides them
        - Vector dimensions must match the embedding model output (768 for nomic-embed-text)

    WHY CHECK IF EXISTS?
      Weaviate will error if you try to create a collection that already exists.
      This makes the function IDEMPOTENT — safe to call multiple times.
    """
    if client.collections.exists(COLLECTION_NAME):
        logger.debug(f"Collection '{COLLECTION_NAME}' already exists")
        return

    logger.info(f"Creating Weaviate collection '{COLLECTION_NAME}'...")

    # Define the collection schema
    client.collections.create(
        name=COLLECTION_NAME,
        description="Knowledge graph triples with semantic embeddings for similarity search",
        # Vectorizer: "none" means WE provide the vectors manually.
        # We don't use Weaviate's built-in vectorizers (OpenAI, Cohere, etc.)
        # because we generate our own embeddings locally via Ollama.
        vectorizer_config=Configure.Vectorizer.none(),
        # We could define vector_index_config for HNSW tuning, but defaults are fine
        # for our dataset size (< 10,000 triples).
        properties=[
            Property(
                name="triple_id",
                data_type=DataType.INT,
                description="PostgreSQL primary key for cross-referencing",
                skip_vectorization=True,  # Don't try to vectorize an integer!
            ),
            Property(
                name="subject",
                data_type=DataType.TEXT,
                description="The subject entity of the triple",
                skip_vectorization=True,
            ),
            Property(
                name="predicate",
                data_type=DataType.TEXT,
                description="The relationship between subject and object",
                skip_vectorization=True,
            ),
            Property(
                name="object_value",
                data_type=DataType.TEXT,
                description="The object entity of the triple",
                skip_vectorization=True,
            ),
            Property(
                name="source_url",
                data_type=DataType.TEXT,
                description="URL of the source article",
                skip_vectorization=True,
            ),
            Property(
                name="confidence",
                data_type=DataType.NUMBER,
                description="LLM confidence score (0.0-1.0)",
                skip_vectorization=True,
            ),
        ],
    )
    logger.info(f"Collection '{COLLECTION_NAME}' created successfully")


def store_triple_embedding(
    client: weaviate.WeaviateClient,
    triple_id: int,
    subject: str,
    predicate: str,
    object_value: str,
    source_url: str,
    confidence: float,
    vector: list[float],
) -> str:
    """
    Store a single knowledge triple with its embedding vector in Weaviate.

    This is called by our embedder pipeline after generating a vector via Ollama.

    WHY STORE METADATA ALONGSIDE THE VECTOR?
      When Weaviate returns search results, it includes the stored properties.
      This lets us show the user the actual triple data without a second PostgreSQL lookup.

    Args:
        client: Connected Weaviate client.
        triple_id: PostgreSQL row ID (for cross-referencing).
        subject: Triple subject (e.g., "async function").
        predicate: Triple predicate (e.g., "enables").
        object_value: Triple object (e.g., "asynchronous behavior").
        source_url: URL of the source article.
        confidence: LLM confidence score (0.0-1.0).
        vector: The embedding vector (768 floats from nomic-embed-text).

    Returns:
        str: The Weaviate UUID for the stored object.

    Raises:
        Exception: If the insert fails (logged but not re-raised in batch mode).
    """
    collection = client.collections.get(COLLECTION_NAME)

    # generate_uuid5 creates a DETERMINISTIC UUID from the data.
    # Same triple_id → same UUID → prevents duplicates if we re-run the pipeline.
    # Uses UUID v5 (SHA-1 hash of namespace + name) — consistent across runs.
    uuid = generate_uuid5(f"triple-{triple_id}")

    # Insert the object with its pre-computed vector
    collection.data.insert(
        properties={
            "triple_id": triple_id,
            "subject": subject,
            "predicate": predicate,
            "object_value": object_value,
            "source_url": source_url,
            "confidence": confidence,
        },
        vector=vector,      # The 768-dimensional embedding from Ollama
        uuid=uuid,          # Deterministic UUID for idempotency
    )

    logger.debug(f"Stored embedding for triple #{triple_id}: {subject} -[{predicate}]-> {object_value[:30]}")
    return uuid


def batch_store_triples(
    client: weaviate.WeaviateClient,
    triples: list[dict],
    vectors: list[list[float]],
) -> dict:
    """
    Store MULTIPLE triples with their embeddings in a single batch operation.

    WHY BATCH?
      Each individual insert is an HTTP request to Weaviate. For 15 triples,
      that's 15 HTTP requests. Batching sends them all at once — much faster.
      Weaviate's batch API is optimized for bulk inserts.

    Args:
        client: Connected Weaviate client.
        triples: List of dicts, each with keys:
            - triple_id, subject, predicate, object_value, source_url, confidence
        vectors: List of embedding vectors (one per triple, same order).

    Returns:
        dict: Summary {"stored": int, "errors": int, "total": int}
    """
    collection = client.collections.get(COLLECTION_NAME)

    stored = 0
    errors = 0

    for triple_data, vector in zip(triples, vectors):
        try:
            uuid = generate_uuid5(f"triple-{triple_data['triple_id']}")

            collection.data.insert(
                properties={
                    "triple_id": triple_data["triple_id"],
                    "subject": triple_data["subject"],
                    "predicate": triple_data["predicate"],
                    "object_value": triple_data["object_value"],
                    "source_url": triple_data["source_url"],
                    "confidence": triple_data["confidence"],
                },
                vector=vector,
                uuid=uuid,
            )
            stored += 1
        except Exception as e:
            logger.error(
                f"Failed to store triple #{triple_data.get('triple_id', '?')}: {e}"
            )
            errors += 1

    summary = {"stored": stored, "errors": errors, "total": len(triples)}
    logger.info(f"Batch store complete: {stored} stored, {errors} errors, {len(triples)} total")
    return summary


def semantic_search(
    client: weaviate.WeaviateClient,
    query_vector: list[float],
    limit: int = 10,
    min_confidence: Optional[float] = None,
) -> list[dict]:
    """
    Find knowledge triples SEMANTICALLY SIMILAR to a query vector.

    This is the CORE of our semantic search. Instead of exact keyword matching
    (LIKE '%async%'), we find concepts by MEANING:
      Query: "how does async/await work?"
      → Vectorized by Ollama
      → Weaviate finds nearest vectors
      → Returns: "await keyword enables asynchronous promise-based behavior"

    HOW IT WORKS (HNSW algorithm):
      Weaviate uses Hierarchical Navigable Small World graphs to find nearest
      neighbors. Think of it like a "skip list for vectors" — it creates layers
      of increasingly precise graphs to navigate to the closest matches quickly.
      For our dataset (< 10K triples), this is essentially instant.

    Args:
        client: Connected Weaviate client.
        query_vector: The embedding vector of the search query (from Ollama).
        limit: Maximum number of results to return (default 10).
        min_confidence: Optional filter — only return triples with confidence >= this value.

    Returns:
        list[dict]: Search results sorted by similarity (closest first).
            Each dict has: triple_id, subject, predicate, object_value,
            source_url, confidence, distance (lower = more similar).
    """
    collection = client.collections.get(COLLECTION_NAME)

    # Build optional filters
    # Weaviate filters work like SQL WHERE clauses but on the vector index
    filters = None
    if min_confidence is not None:
        filters = Filter.by_property("confidence").greater_or_equal(min_confidence)

    # Perform the vector search
    # near_vector: search for objects closest to this vector
    # distance: Weaviate returns the cosine DISTANCE (0 = identical, 2 = opposite)
    # We also request the distance score to show users how confident the match is
    response = collection.query.near_vector(
        near_vector=query_vector,
        limit=limit,
        filters=filters,
        return_metadata=MetadataQuery(distance=True),
    )

    # Parse the response into clean dicts
    results = []
    for obj in response.objects:
        results.append({
            "triple_id": obj.properties["triple_id"],
            "subject": obj.properties["subject"],
            "predicate": obj.properties["predicate"],
            "object_value": obj.properties["object_value"],
            "source_url": obj.properties["source_url"],
            "confidence": obj.properties["confidence"],
            # Distance: 0.0 = identical meaning, 2.0 = opposite meaning
            # We convert to similarity score (1 - distance) for intuition:
            # 1.0 = identical, 0.0 = unrelated
            "similarity": round(1.0 - obj.metadata.distance, 4) if obj.metadata.distance is not None else None,
        })

    logger.info(f"Semantic search returned {len(results)} results (limit={limit})")
    return results


def get_related_triples(
    client: weaviate.WeaviateClient,
    triple_id: int,
    vector: list[float],
    limit: int = 5,
) -> list[dict]:
    """
    Find knowledge triples related to a SPECIFIC triple by vector similarity.

    This is used in the API to enrich triple detail responses with "related concepts".
    For example, viewing the triple "await → enables → async behavior" might show
    related concepts: "Promise → represents → eventual completion", "fetch → returns → Promise".

    Args:
        client: Connected Weaviate client.
        triple_id: The PostgreSQL ID of the source triple (excluded from results).
        vector: The embedding vector of the source triple.
        limit: Max number of related triples to return.

    Returns:
        list[dict]: Related triples sorted by similarity (excluding the source triple).
    """
    collection = client.collections.get(COLLECTION_NAME)

    # Search for similar vectors, but EXCLUDE the source triple itself
    # (otherwise it would always be its own #1 match with distance ≈ 0.0)
    filters = Filter.by_property("triple_id").not_equal(triple_id)

    response = collection.query.near_vector(
        near_vector=vector,
        limit=limit,
        filters=filters,
        return_metadata=MetadataQuery(distance=True),
    )

    results = []
    for obj in response.objects:
        results.append({
            "triple_id": obj.properties["triple_id"],
            "subject": obj.properties["subject"],
            "predicate": obj.properties["predicate"],
            "object_value": obj.properties["object_value"],
            "source_url": obj.properties["source_url"],
            "confidence": obj.properties["confidence"],
            "similarity": round(1.0 - obj.metadata.distance, 4) if obj.metadata.distance is not None else None,
        })

    return results


def get_collection_size(client: weaviate.WeaviateClient) -> int:
    """
    Return the number of objects in the KnowledgeTriple collection.
    Useful for health checks and pipeline status reporting.
    """
    collection = client.collections.get(COLLECTION_NAME)
    try:
        # aggregate.over_all(total_count=True) returns the total number of objects
        response = collection.aggregate.over_all(total_count=True)
        return response.total_count
    except Exception:
        return 0