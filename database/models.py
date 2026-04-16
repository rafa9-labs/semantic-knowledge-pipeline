# ============================================================
# database/models.py — SQLAlchemy ORM Table Definitions
# ============================================================
# This file defines our DATABASE TABLES as Python classes.
# Each class = one table in PostgreSQL.
# Each class attribute = one column in that table.
#
# WHY ORM INSTEAD OF RAW SQL?
#   1. IDE autocomplete — your editor knows the column names
#   2. Type safety — you can't accidentally insert a string into an int column
#   3. Migration tools — Alembic can auto-generate schema migrations from these
#   4. Database-agnostic — the same code works on PostgreSQL, MySQL, SQLite
#
# IMPORTANT DISTINCTION:
#   - Pydantic models (models/content.py) = DATA VALIDATION (what shape is valid?)
#   - SQLAlchemy models (this file) = DATA STORAGE (what table does it live in?)
#
#   They look similar but serve different purposes:
#     Scraper → Pydantic (validates) → SQLAlchemy (stores) → PostgreSQL
# ============================================================

import enum
from datetime import datetime, timezone

from sqlalchemy import (
    CheckConstraint,
    Column,
    Enum,
    Float,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
    DateTime,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.connection import Base


# ============================================================
# RELATIONSHIP TYPE ENUM (Phase 9A)
# ============================================================
# WHY AN ENUM + CHECK CONSTRAINT?
#   We want to enforce that relationship_type is one of exactly 7 valid values.
#   - The Python Enum gives us IDE autocomplete, runtime validation, and
#     prevents typos like "requries" instead of "requires".
#   - The PostgreSQL CHECK constraint adds a second layer of defense:
#     even if someone connects to the DB directly and bypasses our Python code,
#     they can't insert invalid values.
#
# THE 7 RELATIONSHIP TYPES:
#   - requires:   You must know A before B (async requires understanding of functions)
#   - enables:    Knowing A unlocks B (understanding Promises enables async/await)
#   - is_a:       A is a type/subtype of B (Docker Compose is_a orchestration tool)
#   - part_of:    A is a component of B (routing is_part_of FastAPI)
#   - related_to: General connection (Promises related_to callbacks)
#   - contrasts_with: A and B are alternatives/opposing (sync contrasts_with async)
#   - built_on:   A is built on top of B (FastAPI built_on Starlette)
# ============================================================

class RelationshipType(str, enum.Enum):
    requires = "requires"
    enables = "enables"
    is_a = "is_a"
    part_of = "part_of"
    related_to = "related_to"
    contrasts_with = "contrasts_with"
    built_on = "built_on"


class RawArticle(Base):
    """
    SQLAlchemy ORM model for the `raw_articles` table.

    This table stores the raw output from our web scrapers.
    Each row = one scraped article/page.

    RELATIONSHIP TO PYDANTIC:
        Our Pydantic model `RawScrapedArticle` validates incoming data.
        This SQLAlchemy model stores that validated data in PostgreSQL.
        They share similar field names, but serve different purposes:
          - Pydantic: runtime validation + serialization
          - SQLAlchemy: persistent storage + querying

    Example:
        # After validating with Pydantic:
        validated = RawScrapedArticle(title="Python Async", ...)

        # Store using SQLAlchemy:
        db_row = RawArticle(
            title=validated.title,
            url=str(validated.url),
            raw_text=validated.raw_text,
            source_site=validated.source_site,
        )
        session.add(db_row)
        session.commit()
    """

    # ----------------------------------------------------------
    # TABLE NAME
    # ----------------------------------------------------------
    # This tells SQLAlchemy which PostgreSQL table to map to.
    # If the table doesn't exist, create_all() will create it.
    __tablename__ = "raw_articles"

    # ----------------------------------------------------------
    # COLUMNS (each attribute = one database column)
    # ----------------------------------------------------------

    # --- Primary Key ---
    # Every table needs a PRIMARY KEY — a unique identifier for each row.
    # We use autoincrement so PostgreSQL assigns id=1, id=2, id=3, etc.
    # Mapped[int] + mapped_column is the SQLAlchemy 2.0 style (type-safe).
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # --- Title ---
    # String(500) maps to VARCHAR(500) in PostgreSQL.
    # nullable=False means this column CANNOT be empty (Postgres enforces this).
    # This mirrors our Pydantic constraint: title must have min_length=1.
    title: Mapped[str] = mapped_column(String(500), nullable=False)

    # --- URL ---
    # String(2048) — URLs can be long, 2048 is a safe max length.
    # nullable=False — every article must have a source URL.
    # We also add a UNIQUE constraint — we don't want to scrape the same
    # article twice. If we try to insert a duplicate URL, PostgreSQL rejects it.
    # NOTE: Pydantic's HttpUrl type serializes to a string, so we store it as String.
    url: Mapped[str] = mapped_column(String(2048), nullable=False, unique=True)

    # --- Raw Text Content ---
    # Text() maps to the TEXT type in PostgreSQL — unlimited length.
    # This is where the full article body goes (can be thousands of words).
    # We use Text instead of String because we don't want a length limit.
    raw_text: Mapped[str] = mapped_column(Text, nullable=False)

    # --- Source Website ---
    # String(100) — e.g., "mdn", "python_docs", "wikipedia"
    # nullable=True — this is optional (mirrors Pydantic's Optional[str])
    source_site: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # --- Scraped At Timestamp ---
    # DateTime with timezone=True maps to TIMESTAMPTZ in PostgreSQL.
    # This stores the EXACT moment we scraped the article (with timezone info).
    # We default to UTC now — matching our Pydantic default_factory.
    # server_default tells PostgreSQL to set this if not provided in the INSERT.
    scraped_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    # --- Topic Foreign Key (Phase 9A) ---
    # Links this article to a learning topic in our domain structure.
    # nullable=True so existing articles (scraped before Phase 9A) still work.
    # When set, this lets us know WHICH topic an article belongs to, enabling
    # queries like "show me all articles about Async Programming".
    topic_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("topics.id", ondelete="SET NULL"),
        nullable=True,
    )

    # SQLAlchemy relationship: access the parent topic via article.topic
    topic: Mapped["Topic | None"] = relationship("Topic", back_populates="articles")

    def __repr__(self) -> str:
        """
        String representation for debugging.
        When you print(db_row) or see it in logs, you get a readable summary
        instead of `<RawArticle object at 0x7f3a...>`.
        """
        return (
            f"<RawArticle(id={self.id}, title='{self.title[:50]}...', "
            f"source='{self.source_site}')>"
        )


class KnowledgeTripleDB(Base):
    """
    SQLAlchemy ORM model for the `knowledge_triples` table.

    This table stores structured knowledge triples extracted from raw articles
    by our LLM (Gemma 4). Each triple is a (subject, predicate, object) fact.

    RELATIONSHIP TO OTHER TABLES:
        - source_url links back to RawArticle.url (logical foreign key)
        - Each raw article can produce MANY triples (one-to-many)

    RELATIONSHIP TO PYDANTIC:
        - Our Pydantic model `KnowledgeTriple` validates incoming LLM output
        - This SQLAlchemy model stores that validated data in PostgreSQL
        - They share similar field names but serve different purposes:
          - Pydantic: runtime validation + serialization
          - SQLAlchemy: persistent storage + querying

    Example:
        # After LLM extraction + Pydantic validation:
        validated = KnowledgeTriple(
            subject="async function",
            predicate="is_a",
            object="JavaScript declaration,
            source_url="https://...",
            confidence=0.95,
        )

        # Store using SQLAlchemy:
        db_row = KnowledgeTripleDB(
            subject=validated.subject,
            predicate=validated.predicate,
            object=validated.object_,
            source_url=str(validated.source_url),
            confidence=validated.confidence,
        )
        session.add(db_row)
        session.commit()
    """

    __tablename__ = "knowledge_triples"

    # --- Primary Key ---
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # --- Subject: The entity/concept this fact is about ---
    # E.g., "async function", "Promise", "fetch API"
    subject: Mapped[str] = mapped_column(String(500), nullable=False, index=True)
    # index=True adds a database INDEX on this column, making queries like
    # "find all triples about 'async function'" much faster.

    # --- Predicate: The relationship between subject and object ---
    # E.g., "is_a", "returns", "enables", "is_used_with"
    predicate: Mapped[str] = mapped_column(String(200), nullable=False, index=True)

    # --- Object: What the subject relates to ---
    # E.g., "JavaScript feature", "Promise object"
    # Note: We name the column "object_value" to avoid conflicts with
    # Python's builtin "object". In the database it's just a regular column.
    object_value: Mapped[str] = mapped_column(String(500), nullable=False, index=True)

    # --- Source URL: Which article did this come from? ---
    # This is a LOGICAL foreign key to RawArticle.url (not a formal FK constraint
    # because we want flexibility — triples can exist even if the source article
    # is deleted from the raw_articles table).
    source_url: Mapped[str] = mapped_column(String(2048), nullable=False)

    # --- Confidence: How sure is the LLM about this fact? ---
    # Stored as a float (0.0 to 1.0). We can filter later:
    #   "only show triples with confidence > 0.8"
    confidence: Mapped[float] = mapped_column(nullable=False, default=1.0)

    # --- When was this triple extracted? ---
    extracted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    def __repr__(self) -> str:
        return (
            f"<KnowledgeTriple(id={self.id}, "
            f"'{self.subject}' -[{self.predicate}]-> '{self.object_value[:30]}', "
            f"conf={self.confidence})>"
        )


# ============================================================
# CURRICULUM TABLES (Phase 3)
# ============================================================
# These 3 tables store AI-generated curricula.
# HIERARCHY: Curriculum → Module → Lesson (one-to-many at each level)
# The `order_index` columns let us display modules/lessons in the
# correct learning sequence.

class CurriculumDB(Base):
    """
    Stores a generated curriculum (the top-level course).

    RELATIONSHIPS:
        - Has many Modules (one-to-many via curriculum_id FK)
        - Each curriculum covers ONE topic (e.g., "Async JavaScript")
    """
    __tablename__ = "curricula"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    topic: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    target_audience: Mapped[str] = mapped_column(String(200), nullable=False, default="Developers")
    difficulty: Mapped[str] = mapped_column(String(20), nullable=False, default="intermediate")
    model_name: Mapped[str] = mapped_column(String(100), nullable=False, default="gemma4:26b")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    # SQLAlchemy relationship: access modules via curriculum.modules
    modules: Mapped[list["ModuleDB"]] = relationship(
        "ModuleDB", back_populates="curriculum",
        cascade="all, delete-orphan",  # Delete modules if curriculum is deleted
        order_by="ModuleDB.order_index",
    )

    def __repr__(self) -> str:
        return f"<Curriculum(id={self.id}, title='{self.title}', topic='{self.topic}')>"


class ModuleDB(Base):
    """
    Stores a module (chapter) within a curriculum.

    RELATIONSHIPS:
        - Belongs to one Curriculum (many-to-one via curriculum_id)
        - Has many Lessons (one-to-many via module_id FK)
    """
    __tablename__ = "modules"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    order_index: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    curriculum_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("curricula.id", ondelete="CASCADE"), nullable=False,
    )

    curriculum: Mapped["CurriculumDB"] = relationship("CurriculumDB", back_populates="modules")
    lessons: Mapped[list["LessonDB"]] = relationship(
        "LessonDB", back_populates="module",
        cascade="all, delete-orphan",
        order_by="LessonDB.order_index",
    )

    def __repr__(self) -> str:
        return f"<Module(id={self.id}, title='{self.title}', order={self.order_index})>"


class LessonDB(Base):
    """
    Stores a single lesson within a module.

    RELATIONSHIPS:
        - Belongs to one Module (many-to-one via module_id)

    JSON COLUMNS:
        - learning_objectives: list of strings (what the learner will achieve)
        - prerequisites: list of strings (what to know before starting)
        - source_urls: list of URLs (where the content came from)
    We use JSON type because these are variable-length lists that don't
    need their own table — they're always fetched with the lesson.
    """
    __tablename__ = "lessons"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    order_index: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    learning_objectives: Mapped[str] = mapped_column(JSON, nullable=False)
    prerequisites: Mapped[str] = mapped_column(JSON, nullable=False, default=list)
    source_urls: Mapped[str] = mapped_column(JSON, nullable=False, default=list)
    module_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("modules.id", ondelete="CASCADE"), nullable=False,
    )

    module: Mapped["ModuleDB"] = relationship("ModuleDB", back_populates="lessons")

    def __repr__(self) -> str:
        return f"<Lesson(id={self.id}, title='{self.title}', order={self.order_index})>"


# ============================================================
# PHASE 9A: KNOWLEDGE GRAPH DATA MODEL
# ============================================================
# These 7 new tables form the core of our educational knowledge graph.
# HIERARCHY: Domain → Topic → Concept → (Examples, Exercises, Relationships)
#
# The concept_relationships table is the actual GRAPH — typed edges
# between concept nodes that enable prerequisite chains, learning paths,
# and "related concepts" navigation.
#
# WHY THIS STRUCTURE?
#   - Domains = broad areas (Python Core, Databases, AI/ML Pipeline)
#   - Topics = focused subjects within a domain (Async Programming, SQLAlchemy ORM)
#   - Concepts = individual learnable units (async/await, Promise, embeddings)
#   - Relationships = typed connections (requires, enables, part_of, etc.)
#   - Examples/Exercises = content layers for each concept
#   - Source Sections = parsed article sections for citation
# ============================================================


class Domain(Base):
    """
    Top-level learning domain.

    Each domain represents a broad technology area (e.g., Python Core, Databases,
    AI/ML Pipeline). Domains contain multiple Topics, which in turn contain Concepts.

    Example domains:
      - "Python Core" — Python language fundamentals
      - "Databases" — SQL, PostgreSQL, SQLAlchemy, Vector DBs
      - "AI/ML Pipeline" — LLMs, embeddings, RAG, LangChain
    """
    __tablename__ = "domains"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    slug: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    icon: Mapped[str | None] = mapped_column(String(50), nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    topics: Mapped[list["Topic"]] = relationship(
        "Topic", back_populates="domain",
        cascade="all, delete-orphan",
        order_by="Topic.sort_order",
    )

    def __repr__(self) -> str:
        return f"<Domain(id={self.id}, name='{self.name}', slug='{self.slug}')>"


class Topic(Base):
    """
    Learning topic within a domain.

    A Topic groups related Concepts together. For example, the "Python Core"
    domain has topics like "Async Programming", "Type Hints & Pydantic", etc.

    The `source_urls` JSONB column stores a list of documentation URLs to scrape
    for this topic. This drives the multi-source scraping in Phase 9B.
    """
    __tablename__ = "topics"
    __table_args__ = (
        UniqueConstraint("domain_id", "slug", name="uq_topics_domain_slug"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    domain_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("domains.id", ondelete="CASCADE"), nullable=False,
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    slug: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    difficulty: Mapped[str] = mapped_column(
        String(20), nullable=False, default="intermediate",
    )
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    source_urls: Mapped[dict] = mapped_column(JSON, nullable=False, default=list)

    domain: Mapped["Domain"] = relationship("Domain", back_populates="topics")
    concepts: Mapped[list["Concept"]] = relationship(
        "Concept", back_populates="topic",
        cascade="all, delete-orphan",
        order_by="Concept.slug",
    )
    articles: Mapped[list["RawArticle"]] = relationship(
        "RawArticle", back_populates="topic",
    )

    def __repr__(self) -> str:
        return f"<Topic(id={self.id}, name='{self.name}', domain_id={self.domain_id})>"


class Concept(Base):
    """
    Individual learnable concept — the CORE entity of the knowledge graph.

    A concept is a single thing a learner needs to understand: a language feature,
    a framework, a tool, a design pattern, or an abstract idea.

    4 CONTENT LAYERS:
      - theory_text: Formal explanation (scraped from documentation)
      - simple_explanation: ELI5 analogy (generated by our LLM)
      - examples: Code snippets (scraped + generated)
      - exercises: Practice problems (generated by our LLM)

    CATEGORY determines the concept's nature:
      - language_feature: Built-in language capability (async/await, decorators)
      - framework: Part of a framework/library (FastAPI routes, Pydantic models)
      - tool: Standalone tool (Ollama, Docker, Weaviate)
      - pattern: Design pattern or approach (RAG, semantic search)
      - concept: Abstract idea (embeddings, cosine similarity)
    """
    __tablename__ = "concepts"
    __table_args__ = (
        UniqueConstraint("topic_id", "slug", name="uq_concepts_topic_slug"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    topic_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("topics.id", ondelete="CASCADE"), nullable=False,
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    slug: Mapped[str] = mapped_column(String(200), nullable=False)
    category: Mapped[str] = mapped_column(String(50), nullable=False)
    difficulty: Mapped[int] = mapped_column(Integer, nullable=False, default=3)
    theory_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    simple_explanation: Mapped[str | None] = mapped_column(Text, nullable=True)
    simple_explanation_source: Mapped[str | None] = mapped_column(
        String(50), nullable=True,
    )
    key_points: Mapped[dict] = mapped_column(JSON, nullable=False, default=list)
    common_mistakes: Mapped[dict] = mapped_column(JSON, nullable=False, default=list)
    related_concepts_cache: Mapped[dict | None] = mapped_column(
        JSON, nullable=True,
    )

    topic: Mapped["Topic"] = relationship("Topic", back_populates="concepts")
    examples: Mapped[list["Example"]] = relationship(
        "Example", back_populates="concept",
        cascade="all, delete-orphan",
        order_by="Example.sort_order",
    )
    exercises: Mapped[list["Exercise"]] = relationship(
        "Exercise", back_populates="concept",
        cascade="all, delete-orphan",
        order_by="Exercise.sort_order",
    )

    # For concept_relationships, we need two relationships:
    # outgoing: this concept is the "from" side
    # incoming: this concept is the "to" side
    outgoing_relationships: Mapped[list["ConceptRelationship"]] = relationship(
        "ConceptRelationship",
        back_populates="from_concept",
        foreign_keys="ConceptRelationship.from_concept_id",
        cascade="all, delete-orphan",
    )
    incoming_relationships: Mapped[list["ConceptRelationship"]] = relationship(
        "ConceptRelationship",
        back_populates="to_concept",
        foreign_keys="ConceptRelationship.to_concept_id",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return (
            f"<Concept(id={self.id}, name='{self.name}', "
            f"category='{self.category}', difficulty={self.difficulty})>"
        )


class ConceptRelationship(Base):
    """
    Typed edge between two concepts — the knowledge graph's edges.

    This is where the "graph" in "knowledge graph" lives. Each row is a directed
    edge from one concept to another with a specific relationship type.

    The 7 relationship types are defined in the RelationshipType enum and enforced
    by both a Python Enum and a PostgreSQL CHECK constraint (defense in depth).

    Example edges:
      - async/await --[requires]--> functions
      - Promises --[enables]--> async/await
      - Docker Compose --[is_a]--> orchestration tool
      - routing --[part_of]--> FastAPI
      - FastAPI --[built_on]--> Starlette
    """
    __tablename__ = "concept_relationships"
    __table_args__ = (
        UniqueConstraint(
            "from_concept_id", "to_concept_id", "relationship_type",
            name="uq_concept_relationships_edge",
        ),
        CheckConstraint(
            "relationship_type IN ('requires', 'enables', 'is_a', 'part_of', "
            "'related_to', 'contrasts_with', 'built_on')",
            name="ck_concept_relationships_type",
        ),
        CheckConstraint(
            "strength >= 0.0 AND strength <= 1.0",
            name="ck_concept_relationships_strength",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    from_concept_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("concepts.id", ondelete="CASCADE"), nullable=False,
    )
    to_concept_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("concepts.id", ondelete="CASCADE"), nullable=False,
    )
    relationship_type: Mapped[str] = mapped_column(
        String(50), nullable=False,
    )
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    strength: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    source: Mapped[str | None] = mapped_column(String(50), nullable=True)

    from_concept: Mapped["Concept"] = relationship(
        "Concept", back_populates="outgoing_relationships",
        foreign_keys=[from_concept_id],
    )
    to_concept: Mapped["Concept"] = relationship(
        "Concept", back_populates="incoming_relationships",
        foreign_keys=[to_concept_id],
    )

    def __repr__(self) -> str:
        return (
            f"<ConceptRelationship(id={self.id}, "
            f"from={self.from_concept_id}, to={self.to_concept_id}, "
            f"type='{self.relationship_type}')>"
        )


class Example(Base):
    """
    Code example for a concept.

    Examples can come from three sources:
      - scraped: Parsed from official documentation code blocks
      - generated: Created by our LLM (Gemma 4) to illustrate a concept
      - manual: Hand-written by a contributor

    Each example has a title, the code itself, the programming language,
    and optional line-by-line explanation.
    """
    __tablename__ = "examples"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    concept_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("concepts.id", ondelete="CASCADE"), nullable=False,
    )
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    code: Mapped[str] = mapped_column(Text, nullable=False)
    language: Mapped[str] = mapped_column(String(30), nullable=False)
    explanation: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    source_type: Mapped[str] = mapped_column(
        String(20), nullable=False, default="generated",
    )
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    concept: Mapped["Concept"] = relationship("Concept", back_populates="examples")

    def __repr__(self) -> str:
        return f"<Example(id={self.id}, title='{self.title}', lang='{self.language}')>"


class Exercise(Base):
    """
    Practice problem for a concept.

    Exercises are generated by our LLM and include:
      - starter_code: Template the learner starts from (with TODOs)
      - solution_code: The correct solution (hidden until requested)
      - hints: Progressive hints that guide without giving away the answer
      - test_cases: Input/output pairs for auto-grading
      - learning_objectives: What this exercise tests

    Difficulty is on a 1-5 scale matching the concept difficulty.
    """
    __tablename__ = "exercises"
    __table_args__ = (
        CheckConstraint(
            "difficulty >= 1 AND difficulty <= 5",
            name="ck_exercises_difficulty",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    concept_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("concepts.id", ondelete="CASCADE"), nullable=False,
    )
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    difficulty: Mapped[int] = mapped_column(Integer, nullable=False, default=3)
    language: Mapped[str] = mapped_column(String(30), nullable=False)
    starter_code: Mapped[str | None] = mapped_column(Text, nullable=True)
    solution_code: Mapped[str] = mapped_column(Text, nullable=False)
    hints: Mapped[dict] = mapped_column(JSON, nullable=False, default=list)
    test_cases: Mapped[dict] = mapped_column(JSON, nullable=False, default=list)
    learning_objectives: Mapped[dict] = mapped_column(
        JSON, nullable=False, default=list,
    )
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    concept: Mapped["Concept"] = relationship("Concept", back_populates="exercises")

    def __repr__(self) -> str:
        return f"<Exercise(id={self.id}, title='{self.title}', difficulty={self.difficulty})>"


class SourceSection(Base):
    """
    Parsed article section for citation.

    When we scrape a documentation page, we split it into sections (by headings).
    Each section is stored here so we can:
      - Cite the exact section when answering questions (RAG)
      - Link sections to the concepts they describe
      - Provide "read more" links to specific parts of an article

    The concept_ids JSONB column stores a list of concept IDs that are
    referenced in this section (populated during content enrichment).
    """
    __tablename__ = "source_sections"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    article_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("raw_articles.id", ondelete="CASCADE"), nullable=False,
    )
    heading: Mapped[str | None] = mapped_column(String(500), nullable=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    heading_level: Mapped[int | None] = mapped_column(Integer, nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    concept_ids: Mapped[dict] = mapped_column(JSON, nullable=False, default=list)

    def __repr__(self) -> str:
        return (
            f"<SourceSection(id={self.id}, heading='{self.heading}', "
            f"article_id={self.article_id})>"
        )
