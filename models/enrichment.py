# ============================================================
# models/enrichment.py — Pydantic Models for Content Enrichment
# ============================================================
# These models validate the OUTPUT of our LLM enrichment pipeline.
# When Gemma 4 extracts concepts, generates ELI5 explanations, or
# identifies relationships, Pydantic ensures the data is well-formed
# BEFORE it reaches our PostgreSQL database.
#
# DATA FLOW:
#   Scraped Articles → LLM (Gemma 4) → Pydantic Validation → PostgreSQL
#
# WHY SEPARATE MODELS FOR ENRICHMENT?
#   The enrichment pipeline has different data shapes than scraping:
#     - Concepts: need name, slug, category, difficulty
#     - Relationships: need two concept IDs + a typed edge
#     - Each has different validation rules
#   Keeping them separate makes each model focused and testable.
#
# VALID CATEGORIES (matching Concept.category in database/models.py):
#   - language_feature: Built-in language capability (async/await, decorators)
#   - framework: Part of a framework/library (FastAPI routes, Pydantic models)
#   - tool: Standalone tool (Ollama, Docker, Weaviate)
#   - pattern: Design pattern or approach (RAG, semantic search)
#   - concept: Abstract idea (embeddings, cosine similarity)
# ============================================================

from datetime import datetime, timezone
from typing import Optional

from pydantic import BaseModel, Field, field_validator


VALID_CATEGORIES = {
    "language_feature",
    "framework",
    "tool",
    "pattern",
    "concept",
}

VALID_RELATIONSHIP_TYPES = {
    "requires",
    "enables",
    "is_a",
    "part_of",
    "related_to",
    "contrasts_with",
    "built_on",
}


class ExtractedConcept(BaseModel):
    """
    A single concept identified by the LLM from scraped documentation.

    This is what the LLM returns when we ask "what concepts are in this text?".
    Pydantic validates that:
      - name is non-empty and reasonable length
      - category is one of the 5 valid values
      - difficulty is 1-5
      - description is provided (not just a name with no context)

    Example valid input:
        concept = ExtractedConcept(
            name="async/await",
            category="language_feature",
            difficulty=3,
            description="Python's syntax for writing asynchronous code..."
        )
    """

    name: str = Field(
        ...,
        min_length=2,
        max_length=200,
        description="Human-readable concept name (e.g., 'async/await', 'Pydantic models')",
    )

    category: str = Field(
        ...,
        description="One of: language_feature, framework, tool, pattern, concept",
    )

    difficulty: int = Field(
        default=3,
        ge=1,
        le=5,
        description="Learning difficulty from 1 (beginner) to 5 (expert)",
    )

    description: str = Field(
        ...,
        min_length=10,
        max_length=2000,
        description="Brief explanation of what this concept is and why it matters",
    )

    @field_validator("category")
    @classmethod
    def validate_category(cls, v: str) -> str:
        """Ensure the category is one of our 5 valid values."""
        v = v.strip().lower()
        if v not in VALID_CATEGORIES:
            raise ValueError(
                f"Invalid category '{v}'. Must be one of: {sorted(VALID_CATEGORIES)}"
            )
        return v

    @field_validator("name")
    @classmethod
    def clean_name(cls, v: str) -> str:
        """Strip whitespace and normalize the concept name."""
        return v.strip()

    class Config:
        json_schema_extra = {
            "example": {
                "name": "async/await",
                "category": "language_feature",
                "difficulty": 3,
                "description": "Python's syntax for writing asynchronous code using async def and await keywords, built on top of the asyncio event loop.",
            }
        }


class ConceptExtractionResult(BaseModel):
    """
    A batch of concepts extracted from all articles for a single topic.

    The LLM processes all articles for one topic and returns a list of concepts.
    This wrapper model validates the ENTIRE list at once.

    WHY A WRAPPER?
      - The LLM returns {"concepts": [...]} not just a bare list
      - We can attach metadata (topic, model, article count)
      - Pydantic validates each concept individually AND the list as a whole
    """

    concepts: list[ExtractedConcept] = Field(
        default_factory=list,
        description="List of concepts extracted from the topic's articles",
    )

    topic_name: str = Field(
        default="",
        description="The topic these concepts belong to",
    )

    model_name: str = Field(
        default="gemma4:26b",
        description="The LLM model used for extraction",
    )

    total_article_chars: int = Field(
        default=0,
        ge=0,
        description="Total characters of article text processed for this topic",
    )

    class Config:
        json_schema_extra = {
            "example": {
                "concepts": [
                    {
                        "name": "async/await",
                        "category": "language_feature",
                        "difficulty": 3,
                        "description": "Python's async syntax...",
                    }
                ],
                "topic_name": "async-programming",
                "model_name": "gemma4:26b",
                "total_article_chars": 15000,
            }
        }


class ExtractedRelationship(BaseModel):
    """
    A typed relationship between two concepts, extracted by the LLM.

    This represents an edge in our knowledge graph. The LLM identifies
    how concepts connect: "async/await REQUIRES understanding of functions",
    "FastAPI is BUILT_ON Starlette", etc.

    The concept names are FREE TEXT from the LLM — we match them to actual
    concept IDs in the database after extraction.
    """

    from_concept: str = Field(
        ...,
        min_length=2,
        max_length=200,
        description="Name of the source concept",
    )

    to_concept: str = Field(
        ...,
        min_length=2,
        max_length=200,
        description="Name of the target concept",
    )

    relationship_type: str = Field(
        ...,
        description="One of: requires, enables, is_a, part_of, related_to, contrasts_with, built_on",
    )

    description: Optional[str] = Field(
        default=None,
        max_length=1000,
        description="Optional explanation of why this relationship exists",
    )

    strength: float = Field(
        default=0.8,
        ge=0.0,
        le=1.0,
        description="How strong/important this relationship is (0.0-1.0)",
    )

    @field_validator("relationship_type")
    @classmethod
    def validate_relationship_type(cls, v: str) -> str:
        """Ensure the relationship type is one of our 7 valid values."""
        v = v.strip().lower()
        if v not in VALID_RELATIONSHIP_TYPES:
            raise ValueError(
                f"Invalid relationship_type '{v}'. Must be one of: {sorted(VALID_RELATIONSHIP_TYPES)}"
            )
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "from_concept": "async/await",
                "to_concept": "coroutines",
                "relationship_type": "requires",
                "description": "You need to understand coroutines before async/await makes sense",
                "strength": 0.95,
            }
        }


class RelationshipExtractionResult(BaseModel):
    """
    A batch of relationships extracted from concepts within a topic.
    """

    relationships: list[ExtractedRelationship] = Field(
        default_factory=list,
        description="List of typed relationships between concepts",
    )

    topic_name: str = Field(
        default="",
        description="The topic these relationships belong to",
    )

    model_name: str = Field(
        default="gemma4:26b",
        description="The LLM model used for extraction",
    )


# ============================================================
# PHASE 9C-3: EXAMPLE & EXERCISE MODELS
# ============================================================

VALID_LANGUAGES = {
    "python",
    "sql",
    "bash",
    "yaml",
    "json",
    "dockerfile",
    "javascript",
    "typescript",
    "html",
    "css",
    "rust",
    "go",
    "java",
    "c",
    "cpp",
    "csharp",
    "ruby",
    "php",
    "swift",
    "kotlin",
    "markdown",
    "text",
}


class GeneratedExample(BaseModel):
    """
    A single code example for a concept, produced by our LLM.

    The LLM generates examples with a title, the code itself, the language,
    and an optional line-by-line explanation. Pydantic validates structure
    before we insert into the `examples` table.

    Example:
        GeneratedExample(
            title="Creating a basic async function",
            code="async def fetch(url):\\n    ...",
            language="python",
            explanation="Line 1: async def declares a coroutine function..."
        )
    """

    title: str = Field(
        ...,
        min_length=5,
        max_length=300,
        description="Short title describing what this example demonstrates",
    )

    code: str = Field(
        ...,
        min_length=10,
        max_length=10000,
        description="The actual code snippet",
    )

    language: str = Field(
        ...,
        description="Programming language (python, sql, bash, yaml, json, dockerfile, etc.)",
    )

    explanation: Optional[str] = Field(
        default=None,
        max_length=5000,
        description="Line-by-line annotation of the code",
    )

    @field_validator("language")
    @classmethod
    def validate_language(cls, v: str) -> str:
        v = v.strip().lower()
        if v not in VALID_LANGUAGES:
            raise ValueError(
                f"Invalid language '{v}'. Must be one of: {sorted(VALID_LANGUAGES)}"
            )
        return v

    @field_validator("title")
    @classmethod
    def clean_title(cls, v: str) -> str:
        return v.strip()

    class Config:
        json_schema_extra = {
            "example": {
                "title": "Creating a basic async function",
                "code": "import asyncio\n\nasync def greet(name: str) -> str:\n    await asyncio.sleep(1)\n    return f'Hello, {name}!'",
                "language": "python",
                "explanation": "Line 1: Import asyncio for async primitives. Line 3: async def declares a coroutine. Line 4: await pauses execution without blocking.",
            }
        }


class ExampleGenerationResult(BaseModel):
    """
    A batch of examples generated for a single concept.
    """

    examples: list[GeneratedExample] = Field(
        default_factory=list,
        description="List of code examples for the concept",
    )

    concept_name: str = Field(
        default="",
        description="The concept these examples are for",
    )

    model_name: str = Field(
        default="gemma4:26b",
        description="The LLM model used for generation",
    )


class GeneratedExercise(BaseModel):
    """
    A single practice exercise for a concept, produced by our LLM.

    Each exercise includes:
      - title + description: What to build
      - starter_code: Template with TODOs for the learner
      - solution_code: The correct answer (hidden until requested)
      - hints: Progressive hints (3 levels: gentle nudge → big hint → near-answer)
      - test_cases: Input/output pairs for auto-grading
      - learning_objectives: What this exercise tests

    Example:
        GeneratedExercise(
            title="Build a Concurrent URL Fetcher",
            description="Write an async function that fetches 3 URLs concurrently...",
            difficulty=3,
            language="python",
            starter_code="async def fetch_many(urls):\\n    # TODO\\n    pass",
            solution_code="async def fetch_many(urls):\\n    tasks = [fetch_one(u) for u in urls]\\n    return await asyncio.gather(*tasks)",
            hints=["Use a list comprehension", "Pass coroutines to asyncio.gather()"],
            test_cases=[{"input": "3 URLs", "expected": "list of 3 responses"}],
            learning_objectives=["Use asyncio.gather for concurrency"]
        )
    """

    title: str = Field(
        ...,
        min_length=5,
        max_length=300,
        description="Short title of the exercise",
    )

    description: str = Field(
        ...,
        min_length=20,
        max_length=3000,
        description="What the learner needs to build or achieve",
    )

    difficulty: int = Field(
        default=3,
        ge=1,
        le=5,
        description="Exercise difficulty (1-5, matching concept difficulty)",
    )

    language: str = Field(
        ...,
        description="Programming language for the exercise",
    )

    starter_code: Optional[str] = Field(
        default=None,
        max_length=5000,
        description="Template code with TODOs that the learner starts from",
    )

    solution_code: str = Field(
        ...,
        min_length=5,
        max_length=10000,
        description="The correct solution (hidden until requested)",
    )

    hints: list[str] = Field(
        default_factory=list,
        description="Progressive hints (3 levels: gentle → specific → near-answer)",
    )

    test_cases: list[dict] = Field(
        default_factory=list,
        description="Input/output pairs for auto-grading: [{\"input\": ..., \"expected\": ...}]",
    )

    learning_objectives: list[str] = Field(
        default_factory=list,
        description="What this exercise tests",
    )

    @field_validator("language")
    @classmethod
    def validate_language(cls, v: str) -> str:
        v = v.strip().lower()
        if v not in VALID_LANGUAGES:
            raise ValueError(
                f"Invalid language '{v}'. Must be one of: {sorted(VALID_LANGUAGES)}"
            )
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "title": "Build a Concurrent URL Fetcher",
                "description": "Write an async function that fetches 3 URLs concurrently using asyncio.gather(). Return results in the same order as input URLs.",
                "difficulty": 3,
                "language": "python",
                "starter_code": "import asyncio\n\nasync def fetch_many(urls: list[str]) -> list[str]:\n    # TODO: Fetch all URLs concurrently\n    pass",
                "solution_code": "import asyncio\n\nasync def fetch_many(urls: list[str]) -> list[str]:\n    tasks = [fetch_one(url) for url in urls]\n    return await asyncio.gather(*tasks)",
                "hints": [
                    "Create a list of coroutines using a list comprehension",
                    "Pass the coroutines to asyncio.gather()",
                ],
                "test_cases": [
                    {"input": "3 URLs", "expected": "list of 3 responses"},
                ],
                "learning_objectives": [
                    "Use asyncio.gather for concurrent execution",
                ],
            }
        }


class ExerciseGenerationResult(BaseModel):
    """
    A batch of exercises generated for a single concept.
    """

    exercises: list[GeneratedExercise] = Field(
        default_factory=list,
        description="List of practice exercises for the concept",
    )

    concept_name: str = Field(
        default="",
        description="The concept these exercises are for",
    )

    model_name: str = Field(
        default="gemma4:26b",
        description="The LLM model used for generation",
    )
