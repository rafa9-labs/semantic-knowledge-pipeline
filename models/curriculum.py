# ============================================================
# models/curriculum.py — Curriculum, Module & Lesson Schemas
# ============================================================
# These Pydantic models define the shape of a GENERATED CURRICULUM.
#
# DATA FLOW:
#   Knowledge Graph (triples) + Raw Articles
#     → LLM (Gemma 4) generates curriculum
#     → These Pydantic models validate the output
#     → SQLAlchemy stores in PostgreSQL
#
# HIERARCHY:
#   Curriculum (the whole course)
#     └── Module (a group of related lessons)
#           └── Lesson (a single teachable unit)
#
# WHY PYDANTIC HERE?
#   The LLM might return:
#     - A lesson with no title (useless)
#     - A module with lessons out of order
#     - Missing learning objectives
#   Pydantic catches all of these before storage.
# ============================================================

from datetime import datetime, timezone
from typing import Optional

from pydantic import BaseModel, Field


class Lesson(BaseModel):
    """
    A single teachable lesson within a module.

    This is the SMALLEST unit of learning. Each lesson covers ONE concept
    and has clear objectives so the learner knows what they'll achieve.

    Example:
        Lesson(
            title="What are Promises",
            description="Learn what Promise objects are, their three states,
                        and why they replaced callbacks.",
            learning_objectives=[
                "Explain what a Promise is",
                "Identify the three Promise states",
                "Convert a callback to a Promise"
            ],
            prerequisites=["Basic JavaScript functions"],
            order_index=1,
            source_urls=["https://developer.mozilla.org/.../Promise"],
        )
    """
    title: str = Field(
        ...,
        min_length=1,
        max_length=300,
        description="Clear, specific lesson title",
    )
    description: str = Field(
        ...,
        min_length=10,
        max_length=2000,
        description="What this lesson covers and why it matters",
    )
    learning_objectives: list[str] = Field(
        ...,
        min_length=1,
        max_length=10,
        description="What the learner will be able to DO after this lesson",
    )
    prerequisites: list[str] = Field(
        default_factory=list,
        max_length=10,
        description="Concepts the learner should know before starting",
    )
    order_index: int = Field(
        ...,
        ge=0,
        description="Position within the module (0 = first lesson)",
    )
    source_urls: list[str] = Field(
        default_factory=list,
        description="URLs of source material used to compose this lesson",
    )

    class Config:
        json_schema_extra = {
            "example": {
                "title": "What are Promises",
                "description": "Learn what Promise objects are and their three states.",
                "learning_objectives": [
                    "Explain what a Promise is",
                    "Identify the three Promise states",
                ],
                "prerequisites": ["Basic JavaScript functions"],
                "order_index": 0,
                "source_urls": [
                    "https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Promise"
                ],
            }
        }


class Module(BaseModel):
    """
    A group of related lessons within a curriculum.

    Modules organize lessons into LOGICAL GROUPINGS. Think of them as
    "chapters" in a book — each covers a broader theme.

    Example:
        Module(
            title="Promise Fundamentals",
            description="Understanding the basics of JavaScript Promises",
            order_index=0,
            lessons=[...],  # 2-5 Lesson objects
        )
    """
    title: str = Field(
        ...,
        min_length=1,
        max_length=300,
        description="Module title describing the theme",
    )
    description: str = Field(
        ...,
        min_length=10,
        max_length=1000,
        description="What this module covers and why it's important",
    )
    order_index: int = Field(
        ...,
        ge=0,
        description="Position within the curriculum (0 = first module)",
    )
    lessons: list[Lesson] = Field(
        ...,
        min_length=1,
        max_length=10,
        description="The lessons in this module (1-10 per module)",
    )

    class Config:
        json_schema_extra = {
            "example": {
                "title": "Promise Fundamentals",
                "description": "Understanding the basics of JavaScript Promises",
                "order_index": 0,
                "lessons": [],
            }
        }


class Curriculum(BaseModel):
    """
    A complete generated curriculum for a topic.

    This is the TOP-LEVEL object — a full learning path from beginner
    to competent in a specific topic. It contains modules, which contain
    lessons, creating a structured hierarchy.

    Example:
        Curriculum(
            title="Modern Async JavaScript",
            description="Master asynchronous JavaScript from callbacks to async/await",
            topic="Async JavaScript",
            target_audience="Junior to mid-level developers",
            difficulty="intermediate",
            modules=[...],  # 3-6 Module objects
        )
    """
    title: str = Field(
        ...,
        min_length=1,
        max_length=300,
        description="Curriculum title",
    )
    description: str = Field(
        ...,
        min_length=10,
        max_length=2000,
        description="What this curriculum covers and who it's for",
    )
    topic: str = Field(
        ...,
        min_length=1,
        max_length=200,
        description="The main topic/subject area",
    )
    target_audience: str = Field(
        default="Developers",
        max_length=200,
        description="Who this curriculum is designed for",
    )
    difficulty: str = Field(
        default="intermediate",
        pattern="^(beginner|intermediate|advanced)$",
        description="Difficulty level: beginner, intermediate, or advanced",
    )
    modules: list[Module] = Field(
        ...,
        min_length=1,
        max_length=10,
        description="The modules in this curriculum (1-10)",
    )
    model_name: str = Field(
        default="gemma4:26b",
        description="The LLM model that generated this curriculum",
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="When this curriculum was generated",
    )

    class Config:
        json_schema_extra = {
            "example": {
                "title": "Modern Async JavaScript",
                "description": "Master asynchronous JavaScript programming",
                "topic": "Async JavaScript",
                "target_audience": "Junior developers",
                "difficulty": "intermediate",
                "modules": [],
            }
        }