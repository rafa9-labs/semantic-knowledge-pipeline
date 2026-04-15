# ============================================================
# pipeline/curriculum_agent.py — AI Curriculum Generation Agent
# ============================================================
# This is the BRAIN of the curriculum generation feature.
#
# WHAT IT DOES:
#   1. Queries our knowledge graph (triples + articles from PostgreSQL)
#   2. Builds a context string with relevant concepts and relationships
#   3. Sends this to our local LLM (Gemma 4 via Ollama)
#   4. Parses the LLM response into a structured Curriculum (Pydantic)
#   5. Returns a validated Curriculum object ready for storage
#
# WHY AN "AGENT" AND NOT JUST A FUNCTION?
#   This module doesn't just call the LLM once — it:
#     - Gathers context from MULTIPLE database sources
#     - Makes INTELLIGENT decisions about what to include
#     - Handles failures (retry logic, fallback behavior)
#     - Validates its own output before returning
#   These are characteristics of an "agent" pattern.
#
# DATA FLOW:
#   PostgreSQL (triples + articles)
#     → Context Builder (gathers relevant data)
#     → LangChain Prompt Template (formats instructions)
#     → Ollama LLM (Gemma 4 generates curriculum)
#     → JSON Parser (cleans response)
#     → Pydantic Validator (ensures correct structure)
#     → Curriculum object (returned to caller)
# ============================================================

import json
import logging
import re
from typing import Optional

from langchain_ollama import ChatOllama
from langchain_core.messages import HumanMessage, SystemMessage

from models.curriculum import Curriculum, Module, Lesson

# Configure logging — this lets us trace exactly what the agent does
logger = logging.getLogger(__name__)


class CurriculumAgent:
    """
    AI Agent that generates structured curricula from knowledge graph data.

    USAGE:
        agent = CurriculumAgent(model_name="gemma4:26b")
        curriculum = agent.generate_curriculum(
            topic="Async JavaScript",
            triples=[...],       # From knowledge_triples table
            articles=[...],      # From raw_articles table
            target_audience="Junior developers",
            difficulty="intermediate",
        )
        # curriculum is a validated Pydantic Curriculum object

    FAILURE HANDLING:
        - If LLM returns invalid JSON → retry up to max_retries times
        - If Pydantic validation fails → log the error and retry
        - If all retries fail → raise RuntimeError with details
    """

    def __init__(
        self,
        model_name: str = "gemma4:26b",
        temperature: float = 0.3,
        max_retries: int = 3,
    ):
        """
        Initialize the Curriculum Agent.

        Args:
            model_name: Ollama model to use (must be pulled via `ollama pull`)
            temperature: 0.0 = deterministic, 1.0 = creative.
                We use 0.3 — slightly creative for varied curricula,
                but not so high that it hallucinates random lessons.
            max_retries: How many times to retry if LLM output is invalid.
        """
        self.model_name = model_name
        self.max_retries = max_retries

        # --- WHY LangChain? ---
        # LangChain provides a UNIVERSAL interface to LLMs.
        # We can swap Gemma for any other model by changing this one line.
        # It also handles: prompt templating, structured output, error handling.
        logger.info(f"Initializing CurriculumAgent with model: {model_name}")
        self.llm = ChatOllama(
            model=model_name,
            temperature=temperature,
            # 32K context window — curricula need space for all the context
            num_ctx=32768,
        )

    def _build_system_prompt(self) -> str:
        """
        Build the SYSTEM prompt — instructions that tell the LLM HOW to behave.

        The system prompt is the LLM's "job description". It defines:
          - What role the LLM plays (curriculum designer)
          - What output format we expect (strict JSON schema)
          - What rules to follow (practical, job-focused lessons)
        """
        return """You are an expert curriculum designer for software engineering education.

Your task is to create a structured, practical curriculum based on the knowledge graph data provided.

## RULES:
1. Create 2-5 modules, each with 1-4 lessons
2. Order lessons from FUNDAMENTALS → ADVANCED (prerequisites first)
3. Focus on PRACTICAL, job-ready skills (not theory-heavy)
4. Use the knowledge triples to determine prerequisite ordering
5. Use the source articles to ground the curriculum in real documentation

## CRITICAL: EVERY LESSON MUST HAVE THESE EXACT FIELDS:
- "title" (string)
- "description" (string, at least 10 characters)
- "learning_objectives" (array of strings, AT LEAST 1 item) — THIS IS REQUIRED, DO NOT OMIT
- "prerequisites" (array of strings, can be empty [])
- "order_index" (integer, starting from 0)
- "source_urls" (array of strings, can be empty [])

## OUTPUT FORMAT:
Return ONLY valid JSON matching this EXACT structure (no markdown, no code fences):

{
  "title": "string",
  "description": "string",
  "topic": "string",
  "target_audience": "string",
  "difficulty": "beginner or intermediate or advanced",
  "modules": [
    {
      "title": "string",
      "description": "string",
      "order_index": 0,
      "lessons": [
        {
          "title": "string",
          "description": "string",
          "learning_objectives": ["string", "string"],
          "prerequisites": ["string"],
          "order_index": 0,
          "source_urls": ["string"]
        }
      ]
    }
  ]
}

REMEMBER: "learning_objectives" is a REQUIRED field in EVERY lesson. Do NOT skip it.

Return ONLY the JSON object. No markdown code fences. No explanation before or after."""

    def _build_context(
        self,
        topic: str,
        triples: list[dict],
        articles: list[dict],
        target_audience: str,
        difficulty: str,
    ) -> str:
        """
        Build the USER prompt — the specific data the LLM needs to work with.

        This gathers ALL relevant context:
          - Knowledge triples (concept relationships)
          - Source articles (raw content to draw from)
          - User preferences (audience, difficulty)

        Args:
            topic: What the curriculum should cover
            triples: List of knowledge triples from DB (as dicts)
            articles: List of source articles from DB (as dicts)
            target_audience: Who the curriculum is for
            difficulty: beginner, intermediate, or advanced
        """
        # --- Format Knowledge Triples ---
        # Convert triples into a readable format the LLM can reason about.
        # Example: "async function -[returns]-> a new Promise (confidence: 0.95)"
        triples_text = ""
        if triples:
            triples_text = "## KNOWLEDGE TRIPLES (concept relationships):\n"
            for t in triples:
                subj = t.get("subject", "")
                pred = t.get("predicate", "")
                obj = t.get("object_value", "")
                conf = t.get("confidence", 0)
                triples_text += f"- {subj} -[{pred}]-> {obj} (confidence: {conf})\n"
        else:
            triples_text = "## KNOWLEDGE TRIPLES: None available.\n"

        # --- Format Source Articles ---
        # Give the LLM article titles + first 500 chars so it knows
        # what source material is available (full text would be too long).
        articles_text = ""
        if articles:
            articles_text = "## SOURCE ARTICLES available:\n"
            for a in articles:
                title = a.get("title", "Untitled")
                url = a.get("url", "")
                # Truncate content — we just need a summary for context
                content = a.get("raw_text", "")[:500]
                articles_text += f"### {title}\nURL: {url}\nExcerpt: {content}...\n\n"
        else:
            articles_text = "## SOURCE ARTICLES: None available.\n"

        # --- Combine everything into the user prompt ---
        return f"""Create a curriculum on the topic: "{topic}"

Target audience: {target_audience}
Difficulty level: {difficulty}

{triples_text}

{articles_text}

Generate a complete, structured curriculum now. Remember: return ONLY valid JSON."""

    def _parse_json_response(self, response_text: str) -> dict:
        """
        Parse the LLM response into a Python dict.

        FAILURE SCENARIOS WE HANDLE:
          1. LLM wraps JSON in ```json ... ``` code fences → strip them
          2. LLM adds explanatory text before/after JSON → extract JSON
          3. LLM returns invalid JSON → raise ValueError (triggers retry)

        Args:
            response_text: Raw text output from the LLM

        Returns:
            Parsed dict ready for Pydantic validation

        Raises:
            ValueError if no valid JSON can be extracted
        """
        text = response_text.strip()

        # --- Strip markdown code fences ---
        # LLMs often wrap JSON in ```json ... ``` even when told not to.
        # This regex finds and extracts just the JSON content.
        fence_pattern = r"```(?:json)?\s*\n?(.*?)\n?\s*```"
        fence_match = re.search(fence_pattern, text, re.DOTALL)
        if fence_match:
            text = fence_match.group(1).strip()

        # --- Try to find JSON object boundaries ---
        # If there's text before/after the JSON, find the { ... } block.
        first_brace = text.find("{")
        last_brace = text.rfind("}")
        if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
            text = text[first_brace : last_brace + 1]

        # --- Parse the cleaned JSON ---
        try:
            return json.loads(text)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON from LLM: {e}\nText preview: {text[:200]}")

    def _repair_lessons(self, parsed: dict) -> None:
        """
        Repair common LLM mistakes in the parsed JSON (in-place).

        WHY THIS EXISTS:
            Even with clear prompts, LLMs (especially smaller ones like Gemma)
            CONSISTENTLY omit certain fields. Rather than wasting retries,
            we fix the most common issues programmatically:
              - Missing learning_objectives → derive from title/description
              - Missing prerequisites → default to empty list
              - Missing source_urls → default to empty list
              - Missing order_index → assign sequential index

        Args:
            parsed: The parsed JSON dict (modified in-place)
        """
        modules = parsed.get("modules", [])
        for mod in modules:
            lessons = mod.get("lessons", [])
            for i, lesson in enumerate(lessons):
                # Fix missing learning_objectives
                # If omitted, generate a sensible default from the title
                if "learning_objectives" not in lesson or not lesson["learning_objectives"]:
                    title = lesson.get("title", "this topic")
                    lesson["learning_objectives"] = [
                        f"Understand the key concepts of {title}",
                        f"Apply {title} in practical scenarios",
                    ]
                    logger.debug(f"Repaired missing learning_objectives for: {title}")

                # Fix missing prerequisites
                if "prerequisites" not in lesson:
                    lesson["prerequisites"] = []

                # Fix missing source_urls
                if "source_urls" not in lesson:
                    lesson["source_urls"] = []

                # Fix missing order_index
                if "order_index" not in lesson:
                    lesson["order_index"] = i

                # Fix missing description
                if "description" not in lesson or len(lesson.get("description", "")) < 10:
                    title = lesson.get("title", "")
                    lesson["description"] = f"Learn about {title} and how to apply it in practice."

    def generate_curriculum(
        self,
        topic: str,
        triples: list[dict],
        articles: list[dict],
        target_audience: str = "Junior developers",
        difficulty: str = "intermediate",
    ) -> Optional[Curriculum]:
        """
        Generate a complete curriculum from knowledge graph data.

        This is the main entry point. It:
          1. Builds context from triples + articles
          2. Sends to LLM with system instructions
          3. Parses JSON response
          4. Validates with Pydantic
          5. Retries on failure

        Args:
            topic: The subject to create a curriculum for
            triples: Knowledge triples from DB (as dicts)
            articles: Source articles from DB (as dicts)
            target_audience: Who the curriculum is for
            difficulty: beginner, intermediate, or advanced

        Returns:
            A validated Curriculum Pydantic object, or None if all retries fail
        """
        logger.info(
            f"Generating curriculum for '{topic}' "
            f"(audience={target_audience}, difficulty={difficulty})"
        )
        logger.info(f"Context: {len(triples)} triples, {len(articles)} articles")

        # Build the prompts
        system_prompt = self._build_system_prompt()
        user_prompt = self._build_context(
            topic, triples, articles, target_audience, difficulty
        )

        # --- Retry Loop ---
        # The LLM might return invalid JSON or fail Pydantic validation.
        # We retry up to max_retries times before giving up.
        for attempt in range(1, self.max_retries + 1):
            logger.info(f"Calling LLM (attempt {attempt}/{self.max_retries})")

            try:
                # Send messages to LLM via LangChain
                messages = [
                    SystemMessage(content=system_prompt),
                    HumanMessage(content=user_prompt),
                ]
                response = self.llm.invoke(messages)
                raw_text = response.content

                # Parse the JSON response
                parsed = self._parse_json_response(raw_text)

                # --- Repair common LLM mistakes ---
                # LLMs sometimes omit required fields. Rather than failing
                # immediately, we try to FIX the most common issues:
                #   - Missing learning_objectives → add a default
                #   - Missing prerequisites → add empty list
                #   - Missing source_urls → add empty list
                self._repair_lessons(parsed)

                # Validate with Pydantic — this is our safety net!
                # If the LLM returned garbage (missing fields, wrong types),
                # Pydantic will raise ValidationError and we'll retry.
                curriculum = Curriculum(**parsed)

                logger.info(
                    f"Generated curriculum: '{curriculum.title}' with "
                    f"{len(curriculum.modules)} modules"
                )
                for mod in curriculum.modules:
                    logger.info(
                        f"  Module {mod.order_index}: {mod.title} "
                        f"({len(mod.lessons)} lessons)"
                    )

                return curriculum

            except ValueError as e:
                # JSON parsing failed — log and retry
                logger.warning(f"Attempt {attempt} failed (JSON parse): {e}")

            except Exception as e:
                # Pydantic validation failed or other error — log and retry
                logger.warning(f"Attempt {attempt} failed (validation): {e}")

        # All retries exhausted
        logger.error(
            f"Failed to generate curriculum after {self.max_retries} attempts"
        )
        return None