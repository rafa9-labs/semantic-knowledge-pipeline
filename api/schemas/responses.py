# ============================================================
# api/schemas/responses.py — Pydantic Response Models
# ============================================================
# These define EXACTLY what JSON the API returns.
#
# WHY SEPARATE PYDANTIC MODELS FOR API RESPONSES?
#   Our database models (database/models.py) define HOW data is STORED.
#   These response models define HOW data is PRESENTED to the API consumer.
#   They are NOT the same!
#     - DB models have internal fields (like foreign keys) we don't want to expose
#     - API responses may combine data from multiple tables
#     - API responses may exclude sensitive fields
#     - FastAPI auto-generates Swagger docs from these models
#
# FASTAPI MAGIC:
#   When a route returns one of these models, FastAPI:
#     1. Validates the data matches the schema
#     2. Serializes to JSON
#     3. Shows the schema in /docs (Swagger UI)
# ============================================================

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


# ============================================================
# ARTICLE RESPONSES
# ============================================================

class ArticleResponse(BaseModel):
    """A single scraped article returned by the API."""
    id: int
    title: str
    url: str
    source_site: Optional[str] = None
    # We DON'T include raw_text in the list endpoint — too much data!
    # Use a separate detail endpoint if you need the full text.
    text_length: int = Field(description="Character count of the raw text")
    scraped_at: datetime

    class Config:
        from_attributes = True  # Allows reading from SQLAlchemy objects


class ArticleListResponse(BaseModel):
    """Paginated list of articles."""
    total: int
    articles: list[ArticleResponse]


# ============================================================
# KNOWLEDGE TRIPLE RESPONSES
# ============================================================

class TripleResponse(BaseModel):
    """A single knowledge graph triple (subject → predicate → object)."""
    id: int
    subject: str
    predicate: str
    object_value: str
    source_url: str
    confidence: float
    extracted_at: datetime

    class Config:
        from_attributes = True


class TripleListResponse(BaseModel):
    """Paginated list of knowledge triples."""
    total: int
    triples: list[TripleResponse]


# ============================================================
# CURRICULUM RESPONSES
# ============================================================

class LessonResponse(BaseModel):
    """A single lesson within a module."""
    id: int
    title: str
    description: str
    order_index: int
    learning_objectives: list[str]
    prerequisites: list[str]
    source_urls: list[str]

    class Config:
        from_attributes = True


class ModuleResponse(BaseModel):
    """A single module within a curriculum, including its lessons."""
    id: int
    title: str
    description: str
    order_index: int
    lessons: list[LessonResponse] = []

    class Config:
        from_attributes = True


class CurriculumSummaryResponse(BaseModel):
    """
    Summary of a curriculum (used in list endpoints).
    Does NOT include modules/lessons — just the top-level metadata.
    """
    id: int
    title: str
    description: str
    topic: str
    target_audience: str
    difficulty: str
    model_name: str
    module_count: int = Field(description="Number of modules in this curriculum")
    lesson_count: int = Field(description="Total lessons across all modules")
    created_at: datetime

    class Config:
        from_attributes = True


class CurriculumDetailResponse(BaseModel):
    """
    Full curriculum with all modules and lessons.
    Used when fetching a single curriculum by ID.
    """
    id: int
    title: str
    description: str
    topic: str
    target_audience: str
    difficulty: str
    model_name: str
    created_at: datetime
    modules: list[ModuleResponse]

    class Config:
        from_attributes = True


class CurriculumListResponse(BaseModel):
    """List of curriculum summaries."""
    total: int
    curricula: list[CurriculumSummaryResponse]


# ============================================================
# GENERATION REQUEST/RESPONSE
# ============================================================

class CurriculumGenerateRequest(BaseModel):
    """
    Request body for generating a new curriculum.

    This is what the client SENDS to POST /api/curricula/generate.
    Pydantic validates the incoming request data.
    """
    topic: str = Field(
        ...,
        min_length=1,
        max_length=200,
        description="The subject to create a curriculum for",
    )
    target_audience: str = Field(
        default="Junior developers",
        max_length=200,
        description="Who the curriculum is for",
    )
    difficulty: str = Field(
        default="intermediate",
        pattern="^(beginner|intermediate|advanced)$",
        description="Difficulty level",
    )


class CurriculumGenerateResponse(BaseModel):
    """Response after triggering curriculum generation."""
    success: bool
    message: str
    curriculum: Optional[CurriculumDetailResponse] = None


# ============================================================
# HEALTH CHECK
# ============================================================

class HealthResponse(BaseModel):
    """Health check response."""
    status: str = "ok"
    service: str = "Semantic Knowledge Pipeline API"
    version: str = "0.1.0"