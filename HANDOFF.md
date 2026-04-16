# 🔄 HANDOFF.md — Session State for AI Coding Assistant

> **Created:** 2026-04-16, after completing Phase 8 (Design Blueprint)
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

## Current State: 7 Phases Complete, Starting Phase 9A

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

---

## Next Phase: 9A — New Data Model

### What to Build:
1. Add new SQLAlchemy tables to `database/models.py`:
   - `domains` — top-level learning domains (Python Core, Databases, AI/ML, etc.)
   - `topics` — learning topics within domains
   - `concepts` — individual learnable concepts (the core entity)
   - `concept_relationships` — typed edges between concepts (the knowledge graph)
   - `examples` — code examples for concepts
   - `exercises` — practice problems for concepts
   - `source_sections` — parsed article sections for citation
2. Add `topic_id` FK to existing `raw_articles` table
3. Create `database/seed_data.py` with initial domain/topic data
4. Create test script to verify new tables

### Exact table schemas are in DESIGN.md Section 4.3

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
  models.py         — ORM tables: RawArticle, KnowledgeTripleDB, CurriculumDB, ModuleDB, LessonDB
  vector_store.py   — Weaviate client: store/search/health check

PYDANTIC MODELS (models/):
  content.py        — ScrapedContent, RawScrapedArticle (scraper validation)
  knowledge.py      — KnowledgeTriple, TripleExtraction (LLM output validation)
  curriculum.py     — Curriculum, Module, Lesson (AI curriculum validation)

SCRAPERS (scraper/):
  base_scraper.py   — BaseScraper: Playwright browser, fetch_page(), extract_links()
  mdn_scraper.py    — MDNScraper: MDN-specific CSS selectors, URL patterns

PIPELINE (pipeline/):
  text_chunker.py       — Splits articles into ~1000-char overlapping chunks
  triple_extractor.py   — LangChain + Ollama → extracts (subject, predicate, object) triples
  triple_filter.py      — 6 quality filters + scoring (0.0–1.0)
  curriculum_agent.py   — LangChain + Ollama → generates structured curricula
  embedder.py           — Ollama nomic-embed-text → 768D vectors for semantic search

API (api/):
  main.py               — FastAPI app, CORS, route registration, startup event
  routes/curricula.py   — GET/POST curricula endpoints
  routes/knowledge.py   — GET articles, GET triples endpoints
  routes/search.py      — POST semantic search, GET health
  schemas/responses.py  — Pydantic response models

SCRIPTS & TESTS:
  main.py               — Full pipeline orchestrator (5 steps)
  test_db_setup.py      — Database connection test
  test_scraper.py       — Scraper integration test
  test_curriculum.py    — Curriculum generation test
  test_triple_filter.py — 24 unit tests for quality filter
  test_embeddings.py    — Embedding & vector store tests
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
🔜 Phase 9A: New Data Model + Seed Data
   Phase 9B: Multi-Source Scraping (6 new scrapers)
   Phase 9C: Content Enrichment (ELI5, examples, exercises)
   Phase 9D: RAG Chatbot
   Phase 9E: Graph Traversal & Learning Paths
   Phase 10: React Frontend