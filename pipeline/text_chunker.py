# ============================================================
# pipeline/text_chunker.py — Split Long Text into Chunks
# ============================================================
# WHY DO WE NEED CHUNKING?
#   LLMs have a TOKEN LIMIT — they can only process so much text at once.
#   Even though Gemma 4 supports 128K tokens, we still chunk because:
#     1. Smaller chunks = more focused, accurate extractions
#     2. If the LLM fails on one chunk, we don't lose ALL the work
#     3. We can track which chunk produced which triples
#
# HOW CHUNKING WORKS:
#   Input: "AAA. BBB. CCC. DDD. EEE." (5000 chars)
#   Chunk size: 2000 chars, overlap: 200 chars
#   Output:
#     Chunk 1: "AAA. BBB." (chars 0-2000)
#     Chunk 2: "BBB. CCC." (chars 1800-3800)  ← overlap with chunk 1
#     Chunk 3: "DDD. EEE." (chars 3600-5000)  ← overlap with chunk 2
#
#   The OVERLAP ensures we don't cut a sentence in half and lose context.
#   If we cut at "The Promise object is" and "used for async operations",
#   the overlap catches the full sentence in at least one chunk.
#
# TECH CHOICE:
#   We use a simple character-based approach (not LangChain's text splitters)
#   because our articles are relatively short and we want full control.
#   For larger corpora, LangChain's RecursiveCharacterTextSplitter is better.
# ============================================================

import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)


# ----------------------------------------------------------
# Data Class: Represents a single chunk of text
# ----------------------------------------------------------
# @dataclass is a lightweight alternative to Pydantic models.
# We use it here (instead of Pydantic) because chunks are INTERNAL
# to the pipeline — they don't cross module boundaries or get stored
# in the database. Pydantic is reserved for data that LEAVES this module.
@dataclass
class TextChunk:
    """
    A chunk of text split from a larger article.

    Attributes:
        text: The actual text content of this chunk.
        chunk_index: Which chunk number this is (0, 1, 2, ...).
        start_char: Character offset where this chunk starts in the original text.
        total_chunks: Total number of chunks the article was split into.
    """
    text: str
    chunk_index: int
    start_char: int
    total_chunks: int


def chunk_text(
    text: str,
    chunk_size: int = 4000,
    overlap: int = 400,
    min_chunk_size: int = 200,
) -> list[TextChunk]:
    """
    Split a long text into overlapping chunks.

    This is a SLIDING WINDOW approach:
    - We slide a window of `chunk_size` characters across the text
    - Each step moves forward by `chunk_size - overlap` characters
    - The overlap ensures sentences split at boundaries are captured

    Args:
        text: The full article text to split.
        chunk_size: Maximum characters per chunk (default 4000 ≈ ~1000 tokens).
        overlap: How many characters to overlap between chunks (default 400).
        min_chunk_size: If the last chunk is smaller than this, merge it with
            the previous chunk. This prevents tiny useless chunks like "the end."

    Returns:
        List of TextChunk objects, each with metadata about position.

    Example:
        >>> chunks = chunk_text("Hello world " * 1000, chunk_size=100, overlap=20)
        >>> len(chunks)
        11
        >>> chunks[0].text[:50]
        'Hello world Hello world Hello world Hello world Hello wor'
    """
    # ----------------------------------------------------------
    # Edge case: Text is already small enough — no chunking needed
    # ----------------------------------------------------------
    if len(text) <= chunk_size:
        return [TextChunk(
            text=text,
            chunk_index=0,
            start_char=0,
            total_chunks=1,
        )]

    chunks: list[TextChunk] = []
    start = 0
    step = chunk_size - overlap  # How far to slide each time

    while start < len(text):
        end = start + chunk_size

        # ----------------------------------------------------------
        # Extract the chunk and try to break at a sentence boundary
        # ----------------------------------------------------------
        chunk = text[start:end]

        # If this isn't the last chunk, try to break at the last period/newline
        # to avoid cutting mid-sentence. We look for the LAST punctuation mark
        # in the last 20% of the chunk (to avoid breaking too early).
        if end < len(text):
            # Search for sentence-ending punctuation in the last 20% of chunk
            search_start = len(chunk) - int(chunk_size * 0.2)
            # Find the last ".", "!", "?", or newline in that region
            last_period = max(
                chunk.rfind(".", search_start),
                chunk.rfind("!", search_start),
                chunk.rfind("?", search_start),
                chunk.rfind("\n", search_start),
            )
            # If we found a good break point, trim the chunk there
            if last_period > search_start:
                chunk = chunk[: last_period + 1]  # Include the punctuation

        chunks.append(TextChunk(
            text=chunk,
            chunk_index=len(chunks),
            start_char=start,
            total_chunks=-1,  # Will update after all chunks are created
        ))

        # Move the window forward
        start += step

    # ----------------------------------------------------------
    # Merge the last chunk if it's too small
    # ----------------------------------------------------------
    # FAILURE SCENARIO: If the last chunk is only 50 chars like "end of article.",
    # the LLM can't extract meaningful triples from it. We merge it with the
    # previous chunk to avoid wasting an API call.
    if len(chunks) > 1 and len(chunks[-1].text) < min_chunk_size:
        logger.debug(
            f"Last chunk too small ({len(chunks[-1].text)} chars), merging with previous"
        )
        # Merge into the previous chunk
        chunks[-2].text += " " + chunks[-1].text
        chunks.pop()  # Remove the tiny last chunk

    # Update total_chunks count on all chunks
    total = len(chunks)
    for c in chunks:
        c.total_chunks = total

    logger.info(f"Split text ({len(text)} chars) into {total} chunks")
    return chunks