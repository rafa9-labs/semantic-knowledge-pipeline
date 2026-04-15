# ============================================================
# pipeline/triple_extractor.py — LLM Knowledge Triple Extractor
# ============================================================
# This is the CORE AI module of our pipeline. It takes raw text,
# sends it to a local LLM (Gemma 4 via Ollama), and extracts
# structured knowledge triples.
#
# HOW LANGCHAIN WORKS HERE:
#   1. We define a PROMPT TEMPLATE — instructions telling the LLM
#      exactly what format to return (JSON with subject/predicate/object)
#   2. LangChain sends the prompt + text to Ollama (local Gemma 4)
#   3. The LLM responds with structured JSON
#   4. We parse and validate that JSON through our Pydantic model
#
# WHY LANGCHAIN (instead of calling Ollama directly)?
#   - LangChain is LLM-AGNOSTIC: swap Ollama for OpenAI by changing 1 line
#   - Built-in prompt templating with variable substitution
#   - Structured output parsing (JSON validation)
#   - Retry logic and error handling
#
# ERROR HANDLING STRATEGY:
#   LLMs are NON-DETERMINISTIC — they might return:
#     - Malformed JSON (missing brackets, bad escaping)
#     - Wrong structure (array instead of object)
#     - Empty responses (model gave up or hit a limit)
#   We handle ALL of these with try/except + retry + Pydantic validation.
# ============================================================

import json
import logging
import re
from typing import Optional

from langchain_ollama import ChatOllama
from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import ValidationError

from models.knowledge import KnowledgeTriple, TripleExtractionResult
from pipeline.text_chunker import TextChunk

logger = logging.getLogger(__name__)


# ----------------------------------------------------------
# SYSTEM PROMPT — The LLM's "job description"
# ----------------------------------------------------------
# The system prompt tells the LLM WHAT role to play and HOW to respond.
# This is CRITICAL for consistent, structured output.
#
# We ask the LLM to return STRICT JSON because:
#   - JSON is parseable by Python's json.loads()
#   - We can validate it with Pydantic
#   - No ambiguity about format
#
# We give EXAMPLES in the prompt because LLMs perform MUCH better
# when shown the expected output format (few-shot prompting).
SYSTEM_PROMPT = """You are a knowledge graph construction assistant. Your job is to extract knowledge triples from educational text about programming and computer science.

A knowledge triple is a fact expressed as: (subject, predicate, object)
- subject: A concept, technology, or entity (e.g., "async function", "Promise")
- predicate: The relationship (e.g., "is_a", "returns", "enables", "is_used_for")
- object: What the subject relates to (e.g., "JavaScript feature", "Promise object")

RULES:
1. Extract ONLY factual, explicit knowledge from the text — do NOT hallucinate.
2. Each triple must have a clear subject-predicate-object relationship.
3. Use snake_case for predicates (e.g., "is_a", "returns", "enables").
4. Keep subjects and objects concise but specific.
5. Assign a confidence score (0.0-1.0) to each triple.
6. Return ONLY triples you are confident about (confidence >= 0.5).
7. Extract AT LEAST 3 triples and AT MOST 15 triples from the text.

You MUST respond with ONLY valid JSON in this exact format (no markdown, no extra text):
{
  "triples": [
    {"subject": "...", "predicate": "...", "object": "...", "confidence": 0.9},
    {"subject": "...", "predicate": "...", "object": "...", "confidence": 0.8}
  ]
}

EXAMPLES:
Text: "The async function declaration creates a new async function. The await keyword can be used inside async functions."
Output:
{
  "triples": [
    {"subject": "async function", "predicate": "is_a", "object": "function declaration", "confidence": 0.95},
    {"subject": "await keyword", "predicate": "is_used_in", "object": "async function", "confidence": 0.95},
    {"subject": "async function", "predicate": "creates", "object": "asynchronous function", "confidence": 0.9}
  ]
}
"""


class TripleExtractor:
    """
    Extracts knowledge triples from text using a local LLM (Gemma 4 via Ollama).

    This class encapsulates ALL LLM interaction logic:
      - Configuring the Ollama connection
      - Building prompts
      - Calling the LLM
      - Parsing and validating responses
      - Retrying on failure

    USAGE:
        extractor = TripleExtractor()
        result = await extractor.extract(
            text="The Promise object represents the eventual completion...",
            source_url="https://developer.mozilla.org/...",
        )
        for triple in result.triples:
            print(f"{triple.subject} -[{triple.predicate}]-> {triple.object_}")
    """

    def __init__(
        self,
        model_name: str = "gemma4:26b",
        base_url: str = "http://localhost:11434",
        temperature: float = 0.1,
        num_ctx: int = 32768,
        max_retries: int = 3,
    ):
        """
        Initialize the TripleExtractor.

        Args:
            model_name: The Ollama model tag to use (default: "gemma4:26b").
            base_url: Where Ollama is running (default: localhost:11434).
            temperature: Controls randomness. 0.0 = deterministic, 1.0 = creative.
                We use 0.1 (nearly deterministic) because we want FACTUAL extraction,
                not creative writing. Lower temperature = more consistent output.
            num_ctx: Context window size in TOKENS. 32768 tokens ≈ ~24,000 words.
                This is the maximum input + output the model can process at once.
            max_retries: How many times to retry on LLM failure.
        """
        self.model_name = model_name
        self.max_retries = max_retries

        # ----------------------------------------------------------
        # INITIALIZE LANGCHAIN + OLLAMA
        # ----------------------------------------------------------
        # ChatOllama is LangChain's adapter for Ollama's chat API.
        # It handles: HTTP connection, request formatting, response parsing.
        # Behind the scenes, it sends POST requests to http://localhost:11434/api/chat
        #
        # WHY THESE SETTINGS:
        #   - temperature=0.1: Nearly deterministic for factual extraction
        #   - num_ctx=32768: Large context window to fit our articles
        #   - format="json": Tells Ollama to enforce JSON output (structured mode)
        self.llm = ChatOllama(
            model=model_name,
            base_url=base_url,
            temperature=temperature,
            num_ctx=num_ctx,
            format="json",  # Force JSON output from Ollama
        )

        logger.info(
            f"TripleExtractor initialized: model={model_name}, "
            f"ctx={num_ctx}, temp={temperature}"
        )

    async def extract(
        self,
        text: str,
        source_url: str,
    ) -> TripleExtractionResult:
        """
        Extract knowledge triples from a piece of text.

        This is the main entry point. It:
          1. Builds the prompt with the text
          2. Calls the LLM
          3. Parses the JSON response
          4. Validates each triple through Pydantic
          5. Returns a TripleExtractionResult

        Args:
            text: The raw text to extract triples from.
            source_url: The URL of the source article (attached to each triple).

        Returns:
            TripleExtractionResult with validated triples, or empty result on failure.
        """
        # Build the messages for the LLM
        # SystemMessage = the LLM's role/instructions
        # HumanMessage = the actual text we want it to process
        messages = [
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(content=f"Extract knowledge triples from this text:\n\n{text}"),
        ]

        # ----------------------------------------------------------
        # CALL LLM WITH RETRY LOGIC
        # ----------------------------------------------------------
        # LLMs can fail for many reasons:
        #   - Ollama server not running (ConnectionError)
        #   - Model not found (the user hasn't pulled it)
        #   - Timeout (model is too slow, out of memory)
        #   - Malformed JSON response (model didn't follow instructions)
        # We retry up to max_retries times before giving up.
        last_error: Optional[str] = None

        for attempt in range(1, self.max_retries + 1):
            try:
                logger.info(
                    f"Calling LLM (attempt {attempt}/{self.max_retries}, "
                    f"text: {len(text)} chars)"
                )

                # ----------------------------------------------------------
                # THE ACTUAL LLM CALL
                # ----------------------------------------------------------
                # self.llm.ainvoke() sends the messages to Ollama asynchronously.
                # "ainvoke" = async invoke — it returns a coroutine we await.
                # The LLM processes our prompt and returns an AIMessage.
                response = await self.llm.ainvoke(messages)

                # response.content is the raw text the LLM returned.
                # It should be JSON (because we set format="json" above).
                raw_response = response.content
                logger.debug(f"LLM response ({len(raw_response)} chars): {raw_response[:200]}")

                # ----------------------------------------------------------
                # PARSE JSON RESPONSE
                # ----------------------------------------------------------
                # The LLM might wrap JSON in markdown code blocks like:
                #   ```json\n{"triples": [...]}\n```
                # We strip those with regex before parsing.
                cleaned = self._clean_json_response(raw_response)
                parsed = json.loads(cleaned)

                # ----------------------------------------------------------
                # VALIDATE WITH PYDANTIC
                # ----------------------------------------------------------
                # Each triple goes through our KnowledgeTriple Pydantic model.
                # This catches: empty strings, missing fields, bad confidence values.
                # We also attach the source_url to each triple here.
                triples: list[KnowledgeTriple] = []
                for raw_triple in parsed.get("triples", []):
                    try:
                        # Add source_url to each triple (not from LLM, from us)
                        raw_triple["source_url"] = source_url
                        triple = KnowledgeTriple(**raw_triple)
                        triples.append(triple)
                    except ValidationError as ve:
                        # Log but SKIP invalid triples — don't fail the whole batch
                        logger.warning(f"Skipping invalid triple: {ve}")
                        continue

                logger.info(
                    f"Extracted {len(triples)} valid triples "
                    f"(attempt {attempt})"
                )

                return TripleExtractionResult(
                    triples=triples,
                    model_name=self.model_name,
                    chunk_chars=len(text),
                )

            except json.JSONDecodeError as e:
                # LLM returned something that's not valid JSON
                last_error = f"JSON parse error: {e}"
                logger.warning(
                    f"Attempt {attempt}/{self.max_retries} failed: {last_error}"
                )
            except ConnectionError as e:
                # Ollama server is not running or not reachable
                last_error = f"Connection error (is Ollama running?): {e}"
                logger.warning(
                    f"Attempt {attempt}/{self.max_retries} failed: {last_error}"
                )
            except Exception as e:
                # Catch-all for unexpected errors (timeout, OOM, etc.)
                last_error = f"Unexpected error: {type(e).__name__}: {e}"
                logger.warning(
                    f"Attempt {attempt}/{self.max_retries} failed: {last_error}"
                )

        # All retries exhausted
        logger.error(
            f"All {self.max_retries} retries exhausted. Last error: {last_error}"
        )
        # Return EMPTY result (not an exception) so the pipeline can continue
        # with other articles even if this one failed.
        return TripleExtractionResult(
            triples=[],
            model_name=self.model_name,
            chunk_chars=len(text),
        )

    async def extract_from_chunks(
        self,
        chunks: list[TextChunk],
        source_url: str,
    ) -> TripleExtractionResult:
        """
        Extract triples from multiple chunks of a single article.

        WHY CHUNK-BY-CHUNK?
          Each chunk is processed independently by the LLM.
          This is more reliable than sending the entire article at once
          because the LLM can focus on each section.

        DEDUPLICATION:
          Because chunks overlap, the LLM might extract the same triple
          from two adjacent chunks. We deduplicate by (subject, predicate, object).

        Args:
            chunks: List of TextChunk objects to process.
            source_url: URL of the source article.

        Returns:
            Combined TripleExtractionResult from all chunks.
        """
        all_triples: list[KnowledgeTriple] = []

        for i, chunk in enumerate(chunks):
            logger.info(
                f"Processing chunk {i + 1}/{len(chunks)} "
                f"({len(chunk.text)} chars)"
            )

            result = await self.extract(
                text=chunk.text,
                source_url=source_url,
            )
            all_triples.extend(result.triples)

        # ----------------------------------------------------------
        # DEDUPLICATE TRIPLES
        # ----------------------------------------------------------
        # Because of chunk overlap, we might get duplicate triples.
        # We deduplicate by (subject, predicate, object_) combination.
        # We keep the one with the HIGHEST confidence score.
        seen: dict[tuple[str, str, str], KnowledgeTriple] = {}
        for triple in all_triples:
            key = (
                triple.subject.lower().strip(),
                triple.predicate.lower().strip(),
                triple.object_.lower().strip(),
            )
            if key not in seen or triple.confidence > seen[key].confidence:
                seen[key] = triple

        deduplicated = list(seen.values())
        logger.info(
            f"Deduplicated: {len(all_triples)} → {len(deduplicated)} triples"
        )

        return TripleExtractionResult(
            triples=deduplicated,
            model_name=self.model_name,
            chunk_chars=sum(c.total_chunks * len(c.text) for c in chunks) if chunks else 0,
        )

    @staticmethod
    def _clean_json_response(text: str) -> str:
        """
        Clean LLM response to extract valid JSON.

        LLMs sometimes wrap JSON in markdown code blocks:
          ```json
          {"triples": [...]}
          ```
        Or add extra text before/after the JSON.

        This method strips all that away, leaving only the JSON object.

        Args:
            text: Raw LLM response text.

        Returns:
            Cleaned JSON string ready for json.loads().
        """
        # Strip markdown code blocks: ```json ... ``` or ``` ... ```
        text = re.sub(r"```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```", "", text)

        # Find the JSON object (first { to last })
        start = text.find("{")
        end = text.rfind("}") + 1
        if start >= 0 and end > start:
            return text[start:end]

        # If no JSON object found, return as-is (will fail in json.loads)
        return text.strip()