# ============================================================
# database/seed_data.py — Domain & Topic Seed Data (Phase 9A)
# ============================================================
# This module provides functions to populate the `domains` and `topics`
# tables with the initial ML/AI Engineer learning track.
#
# WHY SEED DATA?
#   Our knowledge graph needs a structure BEFORE we have any content.
#   Domains and topics define the "skeleton" — the organizational hierarchy
#   that all scraped articles, extracted concepts, and exercises will hang off.
#
# IDEMPOTENT DESIGN:
#   These functions check if data already exists before inserting.
#   Running seed_domains_and_topics() multiple times is safe — it won't
#   create duplicates. This is critical because:
#     1. We might run the test script multiple times during development
#     2. In production, we don't want to accidentally duplicate data
#     3. CI/CD pipelines might re-run seeds on an existing database
#
# DATA SOURCE:
#   All domain/topic structure comes from DESIGN.md Section 2.
#   The source_urls for each topic come from DESIGN.md Section 6.
# ============================================================

from sqlalchemy.orm import Session

from database.models import Domain, Topic


# ----------------------------------------------------------
# SEED DATA: DOMAINS
# ----------------------------------------------------------
# Each domain is a top-level learning area.
# `sort_order` controls display order in the UI.
# `icon` is an emoji displayed next to the domain name.

SEED_DOMAINS = [
    {
        "name": "Python Core",
        "slug": "python-core",
        "description": (
            "Python language fundamentals — the building blocks every ML/AI engineer "
            "needs: async programming, type hints with Pydantic, object-oriented design, "
            "and robust error handling."
        ),
        "icon": "🐍",
        "sort_order": 1,
    },
    {
        "name": "Databases",
        "slug": "databases",
        "description": (
            "Data persistence and querying — from SQL fundamentals to advanced PostgreSQL "
            "features, SQLAlchemy ORM patterns, and modern vector databases for AI applications."
        ),
        "icon": "🗄️",
        "sort_order": 2,
    },
    {
        "name": "AI/ML Pipeline",
        "slug": "ai-ml-pipeline",
        "description": (
            "The modern AI/ML engineering stack — LLM fundamentals, local model management "
            "with Ollama, LangChain orchestration, embeddings, vector search, and RAG architecture."
        ),
        "icon": "🤖",
        "sort_order": 3,
    },
    {
        "name": "APIs & Backend",
        "slug": "apis-backend",
        "description": (
            "Building and designing REST APIs — FastAPI framework, endpoint design, "
            "Pydantic request/response schemas, CORS configuration, and middleware patterns."
        ),
        "icon": "🌐",
        "sort_order": 4,
    },
    {
        "name": "DevOps",
        "slug": "devops",
        "description": (
            "Infrastructure and deployment — Docker containers, multi-service orchestration "
            "with Docker Compose, and Git/GitHub collaboration workflows."
        ),
        "icon": "🐳",
        "sort_order": 5,
    },
    {
        "name": "Tooling",
        "slug": "tooling",
        "description": (
            "Developer tools and patterns — Playwright browser automation, web scraping "
            "strategies, and clean Python project architecture."
        ),
        "icon": "🔧",
        "sort_order": 6,
    },
]


# ----------------------------------------------------------
# SEED DATA: TOPICS
# ----------------------------------------------------------
# Each topic is keyed by its parent domain's slug.
# `source_urls` lists the documentation pages to scrape for this topic
# in Phase 9B (multi-source scraping).
# `difficulty` is one of: beginner, intermediate, advanced.

SEED_TOPICS = {
    "python-core": [
        {
            "name": "Async Programming",
            "slug": "async-programming",
            "description": (
                "Asynchronous programming in Python using async/await, asyncio event loop, "
                "coroutines, tasks, and concurrent execution patterns."
            ),
            "difficulty": "intermediate",
            "sort_order": 1,
            "source_urls": [
                "https://docs.python.org/3/library/asyncio.html",
                "https://docs.python.org/3/reference/compound_stmts.html#async",
                "https://docs.python.org/3/library/asyncio-task.html",
            ],
        },
        {
            "name": "Type Hints & Pydantic",
            "slug": "type-hints-pydantic",
            "description": (
                "Python type annotations, runtime validation with Pydantic, serialization, "
                "model composition, and custom validators."
            ),
            "difficulty": "intermediate",
            "sort_order": 2,
            "source_urls": [
                "https://docs.python.org/3/library/typing.html",
                "https://docs.pydantic.dev/latest/concepts/models/",
                "https://docs.pydantic.dev/latest/concepts/validators/",
            ],
        },
        {
            "name": "OOP & Design Patterns",
            "slug": "oop-design-patterns",
            "description": (
                "Object-oriented programming in Python — classes, inheritance, composition, "
                "dunder methods, and common design patterns."
            ),
            "difficulty": "intermediate",
            "sort_order": 3,
            "source_urls": [
                "https://docs.python.org/3/tutorial/classes.html",
                "https://docs.python.org/3/reference/datamodel.html",
            ],
        },
        {
            "name": "Error Handling",
            "slug": "error-handling",
            "description": (
                "Python exception handling — try/except/finally, custom exception classes, "
                "error propagation, logging, and defensive programming patterns."
            ),
            "difficulty": "beginner",
            "sort_order": 4,
            "source_urls": [
                "https://docs.python.org/3/tutorial/errors.html",
                "https://docs.python.org/3/library/exceptions.html",
                "https://docs.python.org/3/howto/logging.html",
            ],
        },
    ],
    "databases": [
        {
            "name": "SQL Fundamentals",
            "slug": "sql-fundamentals",
            "description": (
                "Core SQL concepts — SELECT, INSERT, UPDATE, DELETE, JOINs, aggregations, "
                "indexes, constraints, and query optimization basics."
            ),
            "difficulty": "beginner",
            "sort_order": 1,
            "source_urls": [
                "https://www.postgresql.org/docs/current/tutorial-sql.html",
                "https://www.postgresql.org/docs/current/queries.html",
            ],
        },
        {
            "name": "PostgreSQL",
            "slug": "postgresql",
            "description": (
                "PostgreSQL-specific features — JSONB columns, TIMESTAMPTZ, arrays, "
                "full-text search, performance tuning, and advanced indexing."
            ),
            "difficulty": "intermediate",
            "sort_order": 2,
            "source_urls": [
                "https://www.postgresql.org/docs/current/datatype-json.html",
                "https://www.postgresql.org/docs/current/functions-datetime.html",
                "https://www.postgresql.org/docs/current/indexes-types.html",
            ],
        },
        {
            "name": "SQLAlchemy ORM",
            "slug": "sqlalchemy-orm",
            "description": (
                "SQLAlchemy ORM patterns — model definitions, sessions, relationships, "
                "eager/lazy loading, migrations with Alembic, and query optimization."
            ),
            "difficulty": "intermediate",
            "sort_order": 3,
            "source_urls": [
                "https://docs.sqlalchemy.org/en/20/orm/quickstart.html",
                "https://docs.sqlalchemy.org/en/20/orm/session_basics.html",
                "https://docs.sqlalchemy.org/en/20/orm/relationships.html",
                "https://docs.sqlalchemy.org/en/20/core/metadata.html",
            ],
        },
        {
            "name": "Vector Databases",
            "slug": "vector-databases",
            "description": (
                "Vector databases for AI — Weaviate, embeddings storage, HNSW indexing, "
                "similarity search (cosine, dot product), and hybrid search patterns."
            ),
            "difficulty": "advanced",
            "sort_order": 4,
            "source_urls": [
                "https://weaviate.io/developers/weaviate/starter-guides/quickstart",
                "https://weaviate.io/developers/weaviate/concepts/vectorizer",
                "https://weaviate.io/developers/weaviate/concepts/search",
            ],
        },
    ],
    "ai-ml-pipeline": [
        {
            "name": "LLM Fundamentals",
            "slug": "llm-fundamentals",
            "description": (
                "Large Language Model basics — how LLMs work, prompting techniques, "
                "temperature and sampling, tokenization, context windows, and output parsing."
            ),
            "difficulty": "beginner",
            "sort_order": 1,
            "source_urls": [
                "https://python.langchain.com/docs/concepts/prompt_templates/",
                "https://python.langchain.com/docs/concepts/structured_output/",
            ],
        },
        {
            "name": "Ollama",
            "slug": "ollama",
            "description": (
                "Running LLMs locally with Ollama — model management, REST API, "
                "chat completions, embeddings, and model configuration."
            ),
            "difficulty": "beginner",
            "sort_order": 2,
            "source_urls": [
                "https://github.com/ollama/ollama/blob/main/docs/api.md",
                "https://github.com/ollama/ollama/blob/main/docs/modelfile.md",
            ],
        },
        {
            "name": "LangChain",
            "slug": "langchain",
            "description": (
                "LangChain framework — chains, prompt templates, output parsers, "
                "retrievers, retries, and LCEL (LangChain Expression Language)."
            ),
            "difficulty": "intermediate",
            "sort_order": 3,
            "source_urls": [
                "https://python.langchain.com/docs/concepts/chains/",
                "https://python.langchain.com/docs/concepts/output_parsers/",
                "https://python.langchain.com/docs/concepts/retrievers/",
                "https://python.langchain.com/docs/how_to/structured_output/",
            ],
        },
        {
            "name": "Embeddings & Vectors",
            "slug": "embeddings-vectors",
            "description": (
                "Text embeddings — what they are, how models like nomic-embed-text produce "
                "them, cosine similarity, vector dimensions, and practical applications."
            ),
            "difficulty": "intermediate",
            "sort_order": 4,
            "source_urls": [
                "https://weaviate.io/developers/weaviate/concepts/vectorizer",
                "https://python.langchain.com/docs/concepts/embedding_models/",
            ],
        },
        {
            "name": "RAG Architecture",
            "slug": "rag-architecture",
            "description": (
                "Retrieval-Augmented Generation — the retrieve → augment → generate pattern, "
                "document chunking, embedding stores, context window management, and citation."
            ),
            "difficulty": "advanced",
            "sort_order": 5,
            "source_urls": [
                "https://python.langchain.com/docs/concepts/rag/",
                "https://python.langchain.com/docs/tutorials/rag/",
                "https://weaviate.io/developers/weaviate/starter-guides/quickstart",
            ],
        },
    ],
    "apis-backend": [
        {
            "name": "FastAPI",
            "slug": "fastapi",
            "description": (
                "FastAPI web framework — route decorators, dependency injection, "
                "request/response models, middleware, and async endpoints."
            ),
            "difficulty": "intermediate",
            "sort_order": 1,
            "source_urls": [
                "https://fastapi.tiangolo.com/tutorial/first-steps/",
                "https://fastapi.tiangolo.com/tutorial/path-params/",
                "https://fastapi.tiangolo.com/tutorial/body/",
                "https://fastapi.tiangolo.com/tutorial/dependencies/",
                "https://fastapi.tiangolo.com/tutorial/middleware/",
            ],
        },
        {
            "name": "REST API Design",
            "slug": "rest-api-design",
            "description": (
                "REST API design principles — endpoint naming, HTTP methods, status codes, "
                "pagination patterns, versioning, and HATEOAS."
            ),
            "difficulty": "intermediate",
            "sort_order": 2,
            "source_urls": [
                "https://fastapi.tiangolo.com/tutorial/bigger-applications/",
                "https://fastapi.tiangolo.com/tutorial/response-model/",
            ],
        },
        {
            "name": "Pydantic Schemas",
            "slug": "pydantic-schemas",
            "description": (
                "Pydantic for API validation — request/response schemas, field validators, "
                "model serialization, configuration, and nested models."
            ),
            "difficulty": "intermediate",
            "sort_order": 3,
            "source_urls": [
                "https://docs.pydantic.dev/latest/concepts/models/",
                "https://docs.pydantic.dev/latest/concepts/fields/",
                "https://docs.pydantic.dev/latest/concepts/serialization/",
            ],
        },
        {
            "name": "CORS & Middleware",
            "slug": "cors-middleware",
            "description": (
                "Cross-Origin Resource Sharing and middleware — CORS configuration, "
                "security headers, request/response interceptors, and middleware chaining."
            ),
            "difficulty": "intermediate",
            "sort_order": 4,
            "source_urls": [
                "https://fastapi.tiangolo.com/tutorial/cors/",
                "https://fastapi.tiangolo.com/tutorial/middleware/",
                "https://fastapi.tiangolo.com/advanced/security/",
            ],
        },
    ],
    "devops": [
        {
            "name": "Docker Basics",
            "slug": "docker-basics",
            "description": (
                "Docker fundamentals — Dockerfile, images, containers, layers, "
                "volumes, networking, and the Docker CLI."
            ),
            "difficulty": "beginner",
            "sort_order": 1,
            "source_urls": [
                "https://docs.docker.com/get-started/docker-concepts/the-basics/",
                "https://docs.docker.com/reference/dockerfile/",
                "https://docs.docker.com/get-started/docker-concepts/building-images/",
            ],
        },
        {
            "name": "Docker Compose",
            "slug": "docker-compose",
            "description": (
                "Multi-service orchestration with Docker Compose — service definitions, "
                "networking, volumes, environment variables, and dependency management."
            ),
            "difficulty": "intermediate",
            "sort_order": 2,
            "source_urls": [
                "https://docs.docker.com/compose/",
                "https://docs.docker.com/compose/compose-file/",
                "https://docs.docker.com/compose/networking/",
            ],
        },
        {
            "name": "Git & GitHub",
            "slug": "git-github",
            "description": (
                "Version control with Git — branching strategies, pull requests, "
                "conventional commits, merge vs rebase, and GitHub collaboration."
            ),
            "difficulty": "beginner",
            "sort_order": 3,
            "source_urls": [
                "https://docs.github.com/en/get-started/using-git",
                "https://docs.github.com/en/pull-requests",
            ],
        },
    ],
    "tooling": [
        {
            "name": "Playwright",
            "slug": "playwright",
            "description": (
                "Playwright browser automation — headless browsing, async page interaction, "
                "CSS selectors, waiting strategies, and screenshot/PDF capture."
            ),
            "difficulty": "intermediate",
            "sort_order": 1,
            "source_urls": [
                "https://playwright.dev/python/docs/intro",
                "https://playwright.dev/python/docs/api/class-page",
                "https://playwright.dev/python/docs/locators",
            ],
        },
        {
            "name": "Web Scraping Patterns",
            "slug": "web-scraping-patterns",
            "description": (
                "Web scraping best practices — CSS/XPath selectors, pagination handling, "
                "rate limiting, retry strategies, and anti-bot evasion."
            ),
            "difficulty": "intermediate",
            "sort_order": 2,
            "source_urls": [
                "https://playwright.dev/python/docs/api/class-page#page-query-selector",
                "https://developer.mozilla.org/en-US/docs/Web/CSS/CSS_selectors",
            ],
        },
        {
            "name": "Project Architecture",
            "slug": "project-architecture",
            "description": (
                "Clean Python project structure — modular design, separation of concerns, "
                "package organization, configuration management, and dependency injection."
            ),
            "difficulty": "intermediate",
            "sort_order": 3,
            "source_urls": [
                "https://docs.python.org/3/tutorial/modules.html",
                "https://docs.python.org/3/reference/import.html",
            ],
        },
    ],
}


def seed_domains_and_topics(session: Session) -> dict:
    """
    Insert seed domains and topics if they don't already exist.

    IDEMPOTENT: Checks for existing data by slug before inserting.
    Returns a summary dict with counts of created and existing records.

    Args:
        session: An active SQLAlchemy session.

    Returns:
        dict: {"domains_created": int, "topics_created": int,
               "domains_existing": int, "topics_existing": int}
    """
    stats = {
        "domains_created": 0,
        "domains_existing": 0,
        "topics_created": 0,
        "topics_existing": 0,
    }

    domain_id_map = {}

    for domain_data in SEED_DOMAINS:
        existing = (
            session.query(Domain)
            .filter(Domain.slug == domain_data["slug"])
            .first()
        )
        if existing:
            stats["domains_existing"] += 1
            domain_id_map[domain_data["slug"]] = existing.id
        else:
            domain = Domain(**domain_data)
            session.add(domain)
            session.flush()
            stats["domains_created"] += 1
            domain_id_map[domain_data["slug"]] = domain.id

    for domain_slug, topics_list in SEED_TOPICS.items():
        domain_id = domain_id_map[domain_slug]
        for topic_data in topics_list:
            existing = (
                session.query(Topic)
                .filter(
                    Topic.domain_id == domain_id,
                    Topic.slug == topic_data["slug"],
                )
                .first()
            )
            if existing:
                stats["topics_existing"] += 1
            else:
                topic = Topic(domain_id=domain_id, **topic_data)
                session.add(topic)
                stats["topics_created"] += 1

    session.commit()
    return stats


if __name__ == "__main__":
    from database.connection import get_db_session

    with get_db_session() as session:
        result = seed_domains_and_topics(session)
        print(f"Domains: {result['domains_created']} created, "
              f"{result['domains_existing']} already existed")
        print(f"Topics: {result['topics_created']} created, "
              f"{result['topics_existing']} already existed")
