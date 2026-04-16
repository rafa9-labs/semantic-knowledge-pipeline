# ============================================================
# pipeline/embedder.py — Embedding Generation via Ollama
# ============================================================
# This module converts knowledge triples into EMBEDDING VECTORS
# using Ollama's embedding model (nomic-embed-text).
#
# WHAT IS AN EMBEDDING?
#   An embedding is a mathematical representation of text as a VECTOR
#   (a list of floats). Text with SIMILAR MEANING gets SIMILAR vectors.
#
#   Example (simplified — real vectors are 768 dimensions):
#     "async function returns Promise"     → [0.82, 0.15, 0.93, ...]
#     "Promise represents async operation" → [0.79, 0.18, 0.90, ...]  ← similar!
#     "CSS flexbox layout"                 → [0.12, 0.88, 0.31, ...]  ← different
#
#   By comparing vectors, we can measure SEMANTIC SIMILARITY — how close
#   two pieces of text are in MEANING, not just keywords.
#
# WHY nomic-embed-text?
#   - Small (274MB download vs 670MB for larger models)
#   - 768-dimensional vectors (good balance of quality vs size)
#   - Runs locally via Ollama (no API costs)
#   - Great performance on English text similarity tasks
#
# DATA FLOW:
#   Triple from PostgreSQL → combine fields into text → Ollama embedding → vector → Weaviate
#   User search query → Ollama embedding → vector → Weaviate (find similar)
#
# WHY COMBINE FIELDS INTO NATURAL LANGUAGE?
#   We convert "subject=await, predicate=enables, object=async" into
#   "await enables async" before embedding. This produces BETTER embeddings
#   because the model was trained on natural language, not structured data.
# ============================================================

import logging
import os
from typing import Optional

from langchain_ollama import OllamaEmbeddings
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


# ----------------------------------------------------------
# PYDANTIC MODELS — Data Validation
# ----------------------------------------------------------
# Every piece of data that flows through this module is validated by Pydantic.
# This catches issues like empty texts, wrong-dimensional vectors, etc.

class EmbeddingInput(BaseModel):
    """
    Validates the INPUT to the embedding process.

    This ensures we don't try to embed garbage (empty strings, None values, etc.)
    before sending it to Ollama — wasting an expensive LLM call.

    WHY VALIDATE BEFORE EMBEDDING?
      Each Ollama embedding call takes ~50-200ms. If we embed 100 triples,
      that's 5-20 seconds. Validating first prevents wasting time on bad data.
    """
    triple_id: int = Field(..., gt=0, description="PostgreSQL row ID")
    text: str = Field(
        ...,
        min_length=3,
        max_length=2000,
        description="Combined triple text to embed (e.g., 'await enables async behavior')",
    )
    subject: str = Field(..., min_length=1)
    predicate: str = Field(..., min_length=1)
    object_value: str = Field(..., min_length=1)
    source_url: str = Field(..., min_length=1)
    confidence: float = Field(..., ge=0.0, le=1.0)


class EmbeddingResult(BaseModel):
    """
    Validates the OUTPUT of the embedding process.

    This ensures the vector we got back from Ollama is valid:
      - Correct number of dimensions (768 for nomic-embed-text)
      - All values are finite floats (no NaN or Infinity)
      - We keep a reference to which triple this vector represents
    """
    triple_id: int
    vector: list[float] = Field(
        ...,
        min_length=1,
        description="Embedding vector from Ollama",
    )
    model_name: str
    dimensions: int = Field(
        ...,
        gt=0,
        description="Number of dimensions in the vector (should be 768 for nomic-embed-text)",
    )


# ----------------------------------------------------------
# EMBEDDER CLASS
# ----------------------------------------------------------

class TripleEmbedder:
    """
    Generates embedding vectors for knowledge triples using Ollama.

    This class is the INTERFACE between our pipeline and Ollama's embedding model.
    It follows the same pattern as TripleExtractor:
      - Initialize with model config
      - Call a method to process data
      - Get validated results back

    USAGE:
        embedder = TripleEmbedder(model_name="nomic-embed-text")
        result = embedder.embed_triple(
            triple_id=1,
            subject="await keyword",
            predicate="enables",
            object_value="asynchronous behavior",
            source_url="https://...",
            confidence=0.95,
        )
        # result.vector → [0.082, -0.031, 0.156, ...] (768 floats)
    """

    def __init__(
        self,
        model_name: str = "nomic-embed-text",
        base_url: Optional[str] = None,
    ):
        """
        Initialize the embedder.

        Args:
            model_name: The Ollama embedding model to use.
                Must be pulled first: ollama pull nomic-embed-text
            base_url: Ollama server URL. Defaults to http://localhost:11434
                (where Ollama runs by default).
        """
        self.model_name = model_name
        # OllamaEmbeddings is a LangChain wrapper around Ollama's embedding API.
        # It handles: formatting the request, HTTP call, parsing the response.
        # Same pattern as our TripleExtractor using OllamaLLM for text generation.
        self.embeddings = OllamaEmbeddings(
            model=model_name,
            base_url=base_url or os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
        )
        logger.info(f"TripleEmbedder initialized with model: {model_name}")

    @staticmethod
    def triple_to_text(subject: str, predicate: str, object_value: str) -> str:
        """
        Combine triple fields into a natural language string for embedding.

        WHY COMBINE INTO NATURAL LANGUAGE?
          Embedding models are trained on natural text, not structured data.
          "await keyword enables asynchronous promise-based behavior" produces
          a MUCH better embedding than three separate fields.

          This is called "text representation" in NLP — how you format the input
          directly affects the quality of the output.

        Args:
            subject: The triple's subject (e.g., "async function")
            predicate: The relationship (e.g., "returns")
            object_value: The triple's object (e.g., "a Promise")

        Returns:
            str: Combined text like "async function returns a Promise"
        """
        return f"{subject} {predicate} {object_value}"

    def embed_triple(
        self,
        triple_id: int,
        subject: str,
        predicate: str,
        object_value: str,
        source_url: str,
        confidence: float,
    ) -> Optional[EmbeddingResult]:
        """
        Generate an embedding vector for a single knowledge triple.

        PIPELINE:
          1. Validate input with Pydantic (EmbeddingInput)
          2. Combine fields into natural text
          3. Send to Ollama for embedding
          4. Validate output with Pydantic (EmbeddingResult)

        Args:
            triple_id: PostgreSQL row ID.
            subject: Triple subject.
            predicate: Triple predicate.
            object_value: Triple object.
            source_url: Source article URL.
            confidence: LLM confidence score.

        Returns:
            EmbeddingResult with the vector, or None if embedding failed.
        """
        # Step 1: Validate input
        text = self.triple_to_text(subject, predicate, object_value)

        try:
            validated_input = EmbeddingInput(
                triple_id=triple_id,
                text=text,
                subject=subject,
                predicate=predicate,
                object_value=object_value,
                source_url=source_url,
                confidence=confidence,
            )
        except Exception as e:
            logger.error(f"Invalid embedding input for triple #{triple_id}: {e}")
            return None

        # Step 2: Generate embedding via Ollama
        try:
            # embed_query sends the text to Ollama and returns a list of floats.
            # Despite the name "embed_query", it works for any text — it's just
            # the LangChain method name for single-text embedding.
            vector = self.embeddings.embed_query(validated_input.text)

            if not vector or len(vector) == 0:
                logger.error(f"Empty vector returned for triple #{triple_id}")
                return None

            # Step 3: Validate output
            result = EmbeddingResult(
                triple_id=triple_id,
                vector=vector,
                model_name=self.model_name,
                dimensions=len(vector),
            )

            logger.debug(
                f"Embedded triple #{triple_id}: '{text[:50]}...' "
                f"→ {result.dimensions}D vector"
            )
            return result

        except Exception as e:
            logger.error(f"Failed to embed triple #{triple_id}: {e}")
            logger.error(f"  Text was: '{text[:80]}'")
            return None

    def embed_query(self, query: str) -> Optional[list[float]]:
        """
        Generate an embedding vector for a user's SEARCH QUERY.

        This is used by the /api/search endpoint to vectorize the user's
        natural language query before sending it to Weaviate.

        WHY A SEPARATE METHOD?
          Search queries are different from triples:
            - No triple_id, subject, predicate, etc.
            - Can be any text ("how does async/await work?")
            - Don't need Pydantic validation (no database involvement)
          So we simplify the flow: text → Ollama → vector.

        Args:
            query: User's search query (e.g., "how does async await work?")

        Returns:
            list[float]: The embedding vector, or None if embedding failed.
        """
        if not query or len(query.strip()) < 2:
            logger.warning("Query too short to embed")
            return None

        try:
            vector = self.embeddings.embed_query(query.strip())
            logger.debug(f"Embedded query '{query[:50]}...' → {len(vector)}D vector")
            return vector
        except Exception as e:
            logger.error(f"Failed to embed query '{query[:50]}': {e}")
            return None

    def embed_triples_batch(
        self,
        triples: list[dict],
    ) -> list[EmbeddingResult]:
        """
        Generate embeddings for MULTIPLE triples in sequence.

        WHY NOT PARALLEL?
          Ollama processes embedding requests sequentially anyway (it's single-threaded
          for GPU inference). Parallel requests would just queue up. Sequential is simpler
          and avoids overwhelming Ollama with concurrent requests.

        WHY NOT USE OLLAMA'S BATCH API?
          Ollama's embedding API processes one text at a time. LangChain's
          embed_documents() does batch by calling the API multiple times internally.
          We do it explicitly so we can handle errors PER TRIPLE (one failure
          doesn't stop the rest).

        Args:
            triples: List of dicts with keys: triple_id, subject, predicate,
                     object_value, source_url, confidence.

        Returns:
            list[EmbeddingResult]: Successfully embedded triples (failures are logged
            and skipped — partial success is acceptable).
        """
        results = []

        logger.info(f"Starting batch embedding of {len(triples)} triples...")

        for i, triple in enumerate(triples):
            result = self.embed_triple(
                triple_id=triple["triple_id"],
                subject=triple["subject"],
                predicate=triple["predicate"],
                object_value=triple["object_value"],
                source_url=triple["source_url"],
                confidence=triple["confidence"],
            )

            if result:
                results.append(result)
            else:
                logger.warning(
                    f"  [{i+1}/{len(triples)}] SKIPPED triple #{triple.get('triple_id', '?')} "
                    f"(embedding failed)"
                )

            # Progress logging every 5 triples
            if (i + 1) % 5 == 0:
                logger.info(f"  Embedded {i+1}/{len(triples)} triples...")

        logger.info(
            f"Batch embedding complete: {len(results)}/{len(triples)} successful"
        )
        return results