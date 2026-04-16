# 🔄 HANDOFF.md — Session State for AI Coding Assistant

> **Created:** 2026-04-16, after completing Phase 8 (Design Blueprint)
> **Updated:** 2026-04-16, after completing Phase 9A + Phase 9B
> **Purpose:** Gives a new AI coding session full context of project state, decisions, and next steps.

---

## Quick Start — Read These Files in Order

1. **This file** (`HANDOFF.md`) — Current state, what's done, what's next
2. **`.clinerules`** or **`.opencode/rules.md`** — Coding standards and teaching protocol
3. **`DESIGN.md`** — Product blueprint (Phase 8 output, the master plan)
4. **`ARCHITECTURE.md`** — Deep technical explanations of every component
5. **`README.md`** — Project overview and setup instructions

---

## Project Identity

**Name:** DevKnowledge — AI-Powered Educational Knowledge Graph
**Purpose:** An AI-powered learning platform where ML/AI engineers learn the modern data/AI
tech stack through knowledge graphs, simple explanations, code examples, and exercises.
**Principle:** "Eat your own dogfood" — teaches the exact stack used to build it.
**Stack:** Python, Playwright, Pydantic, PostgreSQL, SQLAlchemy, Ollama, LangChain, Weaviate, FastAPI, Docker

---

## Current State: 9 Phases Complete (9A+9B), Starting Phase 9C

### ✅ Phase 1: Database Foundation — DONE
- Docker Compose for PostgreSQL 16
- SQLAlchemy connection factory (`database/connection.py`)
- ORM models: `raw_articles`, `knowledge_triples`, `curricula`, `modules`, `lessons`

### ✅ Phase 2: Web Scraping — DONE
- Playwright async headless browser (`scraper/base_scraper.py`)
- MDN-specific scraper (`scraper/mdn_scraper.py`)
- Pydantic `ScrapedContent` validation model

### ✅ Phase 3: Knowledge Extraction — DONE
- Text chunker (`pipeline/text_chunker.py`)
- LangChain + Ollama (Gemma 4 26B) triple extractor (`pipeline/triple_extractor.py`)
- Pydantic `KnowledgeTriple` model with confidence scoring

### ✅ Phase 4: Curriculum Generation — DONE
- AI curriculum agent (`pipeline/curriculum_agent.py`)
- Pydantic `Curriculum`, `Module`, `Lesson` models

### ✅ Phase 5: REST API — DONE
- FastAPI + Uvicorn (`api/main.py`)
- Endpoints: curricula, knowledge (articles, triples), health check
- Swagger UI at `/docs`

### ✅ Phase 6: Triple Quality Filter — DONE
- 6 rule-based hallucination filters (`pipeline/triple_filter.py`)
- Quality scoring (0.0–1.0)
- 24 unit tests passing

### ✅ Phase 7: Vector Database & Semantic Search — DONE
- Weaviate in Docker (`docker-compose.yml`)
- Ollama nomic-embed-text embeddings (`pipeline/embedder.py`)
- Semantic search API (`api/routes/search.py`)
- Integration tests (`test_embeddings.py`)

### ✅ Phase 8: Design Blueprint — DONE
- Product vision defined: ML/AI Engineer learning tool
- MVP scope: 7 domains covering the project's own tech stack
- 4 content layers: Theory, ELI5, Examples, Exercises
- Complete data model with 7 new tables
- API contracts for React frontend
- Written to `DESIGN.md`

### ✅ Phase 9A: New Data Model — DONE
- 7 new SQLAlchemy tables: domains, topics, concepts, concept_relationships, examples, exercises, source_sections
- RelationshipType enum (7 types) with Python Enum + PostgreSQL CHECK constraints
- topic_id FK added to raw_articles (nullable for backwards compat)
- Alembic initialized for version-controlled schema migrations
- Seed data: 6 domains, 23 topics with source_urls
- Test script: 7 verification categories, all passing

### ✅ Phase 9B: Multi-Source Scraping — DONE
- Generic DocsScraper base class with configurable CSS selectors
- 10 site-specific scrapers: Python, FastAPI, SQLAlchemy, LangChain, Docker, Weaviate, PostgreSQL, Pydantic, Playwright, GitHub
- ScrapedPage Pydantic model (extends RawScrapedArticle with raw_html + sections)
- Section parser: splits articles into heading-based sections -> source_sections table
- MultiSourceScraper orchestrator: reads topics from DB, routes URLs, scrapes, stores
- 64 source URLs across 23 topics, all routable to correct scrapers
- scrape_all.py entry point for live scraping

---

## Next Phase: 9C — Content Enrichment

### What to Build:
1. Concept extraction: identify and deduplicate concepts from scraped articles
2. ELI5 generation: LLM prompt that generates simple explanations
3. Relationship extraction: LLM identifies typed relationships between concepts
4. Example extraction: parse code blocks from articles + LLM generates new ones
5. Exercise generation: LLM creates exercises with solutions and test cases
6. Wire everything into pipeline as new steps

### See DESIGN.md Section 7 for the enrichment pipeline flow

---

## File Map — What Every File Does

```
CONFIGURATION:
  .clinerules / .opencode/rules.md   — AI coding assistant rules & teaching protocol
  .env                               — DB credentials, model names, API keys
  docker-compose.yml                  — PostgreSQL 16 + Weaviate services
  requirements.txt                    — Python dependencies

DATABASE LAYER (database/):
  connection.py     — SQLAlchemy engine, session factory, Base class
  models.py         — ORM tables: RawArticle, KnowledgeTripleDB, + Phase 9A tables
  seed_data.py      — Seed data: 6 domains, 23 topics (Phase 9A)
  vector_store.py   — Weaviate client: store/search/health check

PYDANTIC MODELS (models/):
  content.py        — ScrapedContent, RawScrapedArticle (scraper validation)
  scraped_page.py   — ScrapedPage, ScrapedSection (Phase 9B enriched scraping)
  knowledge.py      — KnowledgeTriple, TripleExtraction (LLM output validation)
  curriculum.py     — Curriculum, Module, Lesson (AI curriculum validation)

SCRAPERS (scraper/):
  base_scraper.py         — BaseScraper: Playwright browser, fetch_page(), extract_links()
  docs_scraper.py         — DocsScraper: generic configurable docs scraper (Phase 9B)
  mdn_scraper.py          — MDNScraper: MDN-specific CSS selectors
  python_docs_scraper.py  — Python docs (Sphinx) scraper
  fastapi_scraper.py      — FastAPI docs (MkDocs Material) scraper
  sqlalchemy_scraper.py   — SQLAlchemy docs (Sphinx) scraper
  langchain_scraper.py    — LangChain docs (Mintlify) scraper
  docker_scraper.py       — Docker docs scraper
  weaviate_scraper.py     — Weaviate docs scraper
  postgresql_scraper.py   — PostgreSQL docs (Sphinx) scraper
  pydantic_scraper.py     — Pydantic docs scraper
  playwright_docs_scraper.py — Playwright Python docs scraper
  github_scraper.py       — GitHub README/docs scraper

PIPELINE (pipeline/):
  text_chunker.py          — Splits articles into ~1000-char overlapping chunks
  triple_extractor.py      — LangChain + Ollama -> extracts (subject, predicate, object) triples
  triple_filter.py         — 6 quality filters + scoring (0.0-1.0)
  curriculum_agent.py      — LangChain + Ollama -> generates structured curricula
  embedder.py              — Ollama nomic-embed-text -> 768D vectors for semantic search
  section_parser.py        — Parses HTML sections -> source_sections table (Phase 9B)
  multi_source_scraper.py  — Orchestrator: routes URLs, scrapes, stores (Phase 9B)

API (api/):
  main.py               — FastAPI app, CORS, route registration, startup event
  routes/curricula.py   — GET/POST curricula endpoints
  routes/knowledge.py   — GET articles, GET triples endpoints
  routes/search.py      — POST semantic search, GET health
  schemas/responses.py  — Pydantic response models

SCRIPTS & TESTS:
  main.py               — Full pipeline orchestrator (5 steps)
  scrape_all.py          — Multi-source scraper entry point (Phase 9B)
  test_db_setup.py       — Database connection test
  test_scraper.py        — Scraper integration test
  test_curriculum.py     — Curriculum generation test
  test_triple_filter.py  — 24 unit tests for quality filter
  test_embeddings.py     — Embedding & vector store tests
  test_phase9a.py        — Phase 9A verification (7 test categories)
  test_phase9b.py        — Phase 9B verification (6 test categories)
  scripts/cleanup_triples.py — DB cleanup tool (dry-run/live)

DOCUMENTATION:
  DESIGN.md          — Product blueprint (THE master plan for future work)
  ARCHITECTURE.md    — Deep technical explanations of every component
  README.md          — Project overview, setup, roadmap
  TESTING_GUIDE.md   — How to run each test
  HANDOFF.md         — THIS FILE — session state handoff
```

---

## Infrastructure Setup

### Required Services
```bash
docker compose up -d          # Starts PostgreSQL (port 5432) + Weaviate (port 8080)
ollama pull gemma4:26b        # LLM for extraction/curriculum
ollama pull nomic-embed-text  # Embedding model for semantic search
```

### Run the Pipeline
```bash
python main.py                # Full pipeline: scrape → extract → filter → embed → curriculum
```

### Run the API
```bash
uvicorn api.main:app --reload --port 8000
# Swagger UI: http://localhost:8000/docs
```

---

## Key Design Decisions (from DESIGN.md)

1. **Concepts vs Triples:** Triples are raw (subject, predicate, object) strings. Concepts
   are first-class entities with IDs, categories, explanations. Concept relationships are
   typed edges between concept IDs. Migration path: triples → concept relationships.

2. **4 Content Layers:** Every concept has Theory (scraped), ELI5 (LLM-generated),
   Examples (scraped + generated), Exercises (LLM-generated).

3. **7 Relationship Types:** requires, enables, is_a, part_of, related_to, contrasts_with, built_on

4. **$0 Cost:** Everything local — Ollama, Docker, PostgreSQL, Weaviate. No cloud.

5. **MVP Scope:** Only the ML/AI engineer tech stack. Scale to other domains later.

---

## MCP Servers Available (Cline Configuration)

These MCP tools are configured and available:
- **filesystem** — File read/write at `C:\Users\rafa\Projects`
- **github** — GitHub API (repos, issues, PRs, files)
- **context7** — Library documentation lookup
- **sequential-thinking** — Step-by-step reasoning
- **brave-search** — Web search
- **puppeteer** — Browser automation
- **postgres** — Direct PostgreSQL queries on `forex_ml` database
- **fetch** — HTTP requests (HTML, Markdown, JSON, YouTube transcripts)

---

## Full Phase Roadmap

```
✅ Phase 1:  Database Foundation
✅ Phase 2:  Web Scraping (Playwright + MDN)
✅ Phase 3:  Knowledge Extraction (LLM triples)
✅ Phase 4:  Curriculum Generation (LLM curricula)
✅ Phase 5:  REST API (FastAPI)
✅ Phase 6:  Triple Quality Filter
✅ Phase 7:  Vector Database & Semantic Search (Weaviate)
✅ Phase 8:  Design Blueprint (DESIGN.md)
✅ Phase 9A: New Data Model + Seed Data
✅ Phase 9B: Multi-Source Scraping (10 scrapers, 64 URLs)
🔜 Phase 9C: Content Enrichment (ELI5, examples, exercises)
   Phase 9D: RAG Chatbot
   Phase 9E: Graph Traversal & Learning Paths
   Phase 10: React Frontend