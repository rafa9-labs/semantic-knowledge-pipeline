# ============================================================
# api/routes/search.py — Semantic Search Endpoint
# ============================================================
# This module provides the SEMANTIC SEARCH API endpoint.
# Unlike traditional search (exact keyword matching), semantic search
# finds concepts by MEANING using vector similarity.
#
# HOW IT WORKS:
#   1. User sends a query: "how does async/await work?"
#   2. We embed the query using Ollama → 768-dimensional vector
#   3. We send the vector to Weaviate → finds nearest vectors
#   4. Weaviate returns the most semantically similar triples
#   5. We enrich with PostgreSQL data and return as JSON
#
# EXAMPLE:
#   POST /api/search
#   Body: {"query": "how does async/await work?", "limit": 5}
#
#   Response: { "results": [
#     { "subject": "await keyword", "predicate": "enables",
#       "object_value": "asynchronous promise-based behavior",
#       "similarity": 0.87 },
#     ...
#   ]}
#
# WHY POST INSTEAD OF GET?
#   Search queries can be long and contain special characters.
#   POST body is cleaner than URL-encoding a complex query into GET params.
#   However, GET /api/search?q=... would also be valid for simpler cases.
# ============================================================

import logging
import os
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from database.vector_store import (
    get_weaviate_client,
    semantic_search,
    get_collection_size,
    ensure_collection_exists,
)
from pipeline.embedder import TripleEmbedder

logger = logging.getLogger(__name__)

# Create a FastAPI router for search endpoints
# Routers let us split endpoints across files, then register them all in api/main.py
router = APIRouter(prefix="/api", tags=["search"])


# ----------------------------------------------------------
# REQUEST / RESPONSE SCHEMAS (Pydantic)
# ----------------------------------------------------------
# These define the EXACT shape of data the API accepts and returns.
# FastAPI auto-generates Swagger docs from these models.

class SearchRequest(BaseModel):
    """
    The body of a semantic search request.

    The user provides a natural language query, and we find
    the most semantically similar knowledge triples.

    EXAMPLE:
        {"query": "how does Promise work?", "limit": 5, "min_confidence": 0.5}
    """
    query: str = Field(
        ...,
        min_length=2,
        max_length=500,
        description="Natural language search query (e.g., 'how does async/await work?')",
    )
    limit: int = Field(
        default=10,
        ge=1,
        le=50,
        description="Maximum number of results to return",
    )
    min_confidence: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Only return triples with confidence >= this value",
    )


class SearchResultItem(BaseModel):
    """
    A single search result — one knowledge triple with its similarity score.
    """
    triple_id: int
    subject: str
    predicate: str
    object_value: str
    source_url: str
    confidence: float
    similarity: float = Field(
        description="Similarity score (1.0 = identical meaning, 0.0 = unrelated)"
    )


class SearchResponse(BaseModel):
    """
    The complete search response with all results and metadata.
    """
    query: str
    total_results: int
    results: list[SearchResultItem]
    vector_db_size: int = Field(
        description="Total number of vectors in the Weaviate collection"
    )


class SearchHealthResponse(BaseModel):
    """Health/status check for the search service."""
    weaviate_connected: bool
    vector_count: int
    embedding_model: str


# ----------------------------------------------------------
# ENDPOINTS
# ----------------------------------------------------------

@router.post("/search", response_model=SearchResponse)
def search_knowledge(request: SearchRequest):
    """
    Semantic search over the knowledge graph.

    Finds knowledge triples that are SEMANTICALLY SIMILAR to the query,
    not just keyword matches. Uses vector embeddings from Ollama and
    Weaviate's HNSW index for fast similarity search.

    **Flow:**
    1. Embed the query using Ollama's nomic-embed-text model
    2. Search Weaviate for the nearest vectors
    3. Return results sorted by similarity (highest first)
    """
    logger.info(f"Semantic search: '{request.query[:50]}' (limit={request.limit})")

    # Step 1: Embed the query
    try:
        embedder = TripleEmbedder(
            model_name=os.getenv("EMBEDDING_MODEL", "nomic-embed-text"),
        )
        query_vector = embedder.embed_query(request.query)
    except Exception as e:
        logger.error(f"Failed to embed query: {e}")
        raise HTTPException(
            status_code=503,
            detail=f"Embedding service unavailable. Is Ollama running? Error: {str(e)}",
        )

    if query_vector is None:
        raise HTTPException(
            status_code=400,
            detail="Failed to generate embedding for query. Query may be too short.",
        )

    # Step 2: Search Weaviate
    try:
        client = get_weaviate_client()
    except ConnectionError as e:
        raise HTTPException(
            status_code=503,
            detail=f"Vector database unavailable. Is Weaviate running? Error: {str(e)}",
        )

    try:
        # Ensure the collection exists (idempotent)
        ensure_collection_exists(client)

        # Perform the semantic search
        results = semantic_search(
            client,
            query_vector=query_vector,
            limit=request.limit,
            min_confidence=request.min_confidence,
        )

        # Get collection size for metadata
        vec_count = get_collection_size(client)

        # Build response
        search_results = [
            SearchResultItem(**r) for r in results
        ]

        return SearchResponse(
            query=request.query,
            total_results=len(search_results),
            results=search_results,
            vector_db_size=vec_count,
        )

    except Exception as e:
        logger.error(f"Search failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Search failed: {str(e)}",
        )
    finally:
        client.close()


@router.get("/search/health", response_model=SearchHealthResponse)
def search_health():
    """
    Health check for the semantic search service.

    Returns whether Weaviate is connected and how many vectors are stored.
    Useful for monitoring and debugging.
    """
    embedding_model = os.getenv("EMBEDDING_MODEL", "nomic-embed-text")

    try:
        client = get_weaviate_client()
        vec_count = get_collection_size(client)
        client.close()
        return SearchHealthResponse(
            weaviate_connected=True,
            vector_count=vec_count,
            embedding_model=embedding_model,
        )
    except Exception:
        return SearchHealthResponse(
            weaviate_connected=False,
            vector_count=0,
            embedding_model=embedding_model,
        )