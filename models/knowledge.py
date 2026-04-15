# ============================================================
# models/knowledge.py — Knowledge Triple Schema
# ============================================================
# This is the SECOND data model in our pipeline. It represents
# a structured "knowledge triple" extracted from raw text by an LLM.
#
# DATA FLOW:
#   Raw Text → LLM (Gemma 4) → KnowledgeTriple (validated here) → PostgreSQL
#
# WHAT IS A KNOWLEDGE TRIPLE?
#   A knowledge triple is a FACT expressed as (subject, predicate, object):
#     ("async/await", "is_a", "JavaScript feature")
#     ("Promise", "enables", "asynchronous programming")
#     ("fetch()", "returns", "Promise object")
#
#   These triples become the NODES and EDGES of our knowledge graph:
#     - Subjects & Objects = Nodes (entities/concepts)
#     - Predicates = Edges (relationships between concepts)
#
# WHY PYDANTIC HERE?
#   LLMs are unpredictable. Sometimes they return garbage:
#     - Empty strings: subject="" ← useless
#     - Missing fields: only returns subject, no predicate
#     - Hallucinated confidence: confidence=99.0 ← should be 0.0-1.0
#   Pydantic catches ALL of these before they reach our database.
# ============================================================

from datetime import datetime, timezone
from typing import Optional

from pydantic import BaseModel, Field, HttpUrl


class KnowledgeTriple(BaseModel):
    """
    A single knowledge triple extracted from educational text.

    This is the FUNDAMENTAL UNIT of our knowledge graph.
    Every fact the LLM extracts must conform to this exact shape.

    Example valid input:
        triple = KnowledgeTriple(
            subject="async function",
            predicate="is_a",
            object="JavaScript declaration",
            source_url="https://developer.mozilla.org/en-US/docs/...",
            confidence=0.95,
        )
    """

    # --- Subject: The "thing" this triple is about ---
    # E.g., "async function", "Promise", "fetch API"
    # MUST be non-empty — a triple about "nothing" is meaningless.
    subject: str = Field(
        ...,
        min_length=1,
        max_length=500,
        description="The subject entity of the triple (the 'thing' being described)",
    )

    # --- Predicate: The relationship/verb ---
    # E.g., "is_a", "returns", "enables", "is_used_with"
    # This is the EDGE in our knowledge graph — HOW two concepts connect.
    predicate: str = Field(
        ...,
        min_length=1,
        max_length=200,
        description="The relationship between subject and object (the 'verb')",
    )

    # --- Object: What the subject relates to ---
    # E.g., "JavaScript feature", "Promise object", "asynchronous programming"
    object_: str = Field(
        ...,  # Note: "object" is a Python builtin, so we use "object_"
        alias="object",  # But in JSON/LLM output, it's still "object"
        min_length=1,
        max_length=500,
        description="The object entity of the triple (what the subject relates to)",
    )

    # --- Source URL: Where did this fact come from? ---
    # This lets us TRACE every triple back to the original article.
    # Critical for: verifying facts, re-processing if the LLM improves.
    source_url: HttpUrl = Field(
        ...,
        description="The URL of the article this triple was extracted from",
    )

    # --- Confidence: How sure is the LLM about this fact? ---
    # 0.0 = pure guess, 1.0 = absolutely certain.
    # We use this to FILTER low-confidence triples later.
    # ge=0.0 means "greater than or equal to 0.0"
    # le=1.0 means "less than or equal to 1.0"
    confidence: float = Field(
        default=1.0,
        ge=0.0,  # minimum value
        le=1.0,  # maximum value
        description="LLM's confidence score for this triple (0.0 to 1.0)",
    )

    # --- When was this triple extracted? ---
    # Useful for: tracking when the LLM ran, re-processing stale triples.
    extracted_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="UTC timestamp of when this triple was extracted by the LLM",
    )

    class Config:
        """
        Pydantic model configuration.

        - populate_by_name=True: Allows using either "object_" or "object"
          when creating an instance. This is needed because we aliased
          "object_" to "object" (since "object" is a Python builtin).
        - from_attributes=True: Allows creating from SQLAlchemy objects.
        """
        populate_by_name = True
        from_attributes = True
        json_schema_extra = {
            "example": {
                "subject": "async function",
                "predicate": "is_a",
                "object": "JavaScript declaration",
                "source_url": "https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Statements/async_function",
                "confidence": 0.95,
            }
        }


class TripleExtractionResult(BaseModel):
    """
    A BATCH of triples extracted from a single chunk of text.

    WHY A WRAPPER MODEL?
      The LLM doesn't return one triple — it returns a LIST.
      This model validates the ENTIRE list at once:
        - Ensures the "triples" field is actually a list
        - Validates each individual triple through KnowledgeTriple
        - Captures metadata about the extraction (model used, chunk info)

    FAILURE SCENARIO: If the LLM returns malformed JSON like
      {"triples": [{"subject": "", "predicate": "is_a"}]}
      Pydantic will reject it because subject="" violates min_length=1,
      and the "object" field is missing. This prevents garbage from
      entering our knowledge graph.
    """

    # The list of extracted triples — each one validated individually.
    triples: list[KnowledgeTriple] = Field(
        default_factory=list,
        description="List of knowledge triples extracted from the text",
    )

    # Which LLM model produced these triples? (for auditing)
    model_name: str = Field(
        default="gemma4:26b",
        description="The LLM model used for extraction",
    )

    # How many characters of text were processed (for tracking chunk sizes)
    chunk_chars: int = Field(
        default=0,
        ge=0,
        description="Number of characters in the source text chunk",
    )