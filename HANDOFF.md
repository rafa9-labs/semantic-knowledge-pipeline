# HANDOFF.md — Session State for AI Coding Assistant

> **Created:** 2026-04-16, after completing Phase 8 (Design Blueprint)
> **Updated:** 2026-04-19, after content quality overhaul + color system + concept enrichment
> **Purpose:** Gives a new AI coding session full context of project state, decisions, and next steps.

---

## Quick Start — Read These Files in Order

1. **This file** (`HANDOFF.md`) — Current state, what's done, what's next
2. **`.opencode/rules.md`** — Coding standards and teaching protocol
3. **`DESIGN.md`** — Product blueprint (Phase 8 output, the master plan)
4. **`DESIGN_SAAS.md`** — SaaS architecture blueprint (Vercel + Railway + Supabase + Stripe)
5. **`ARCHITECTURE.md`** — Deep technical explanations of every component
6. **`README.md`** — Project overview, roadmap, and setup instructions

---

## Project Identity

**Name:** KodaStudy (formerly DevKnowledge)
**Tagline:** "Master any subject through AI-powered knowledge graphs"
**URL:** kodastudy.com
**Purpose:** An AI-powered SaaS learning platform where ML/AI engineers learn the modern data/AI tech stack through knowledge graphs, simple explanations, code examples, and exercises.
**Principle:** "Eat your own dogfood" — teaches the exact stack used to build it.
**Stack:** Python, Playwright, Pydantic, PostgreSQL, SQLAlchemy, Ollama (Qwen 3.5), LangChain, Weaviate, FastAPI, Next.js 15, Supabase, Docker

---

## Current State: Content Quality Overhaul Done, Regeneration Pending

### Backend Pipeline — ALL DONE through concept enrichment

| Phase | Status | Key Output |
|-------|--------|------------|
| 1: Database Foundation | ✅ DONE | PostgreSQL + Docker, SQLAlchemy, Alembic migrations |
| 2: Web Scraping | ✅ DONE | Playwright headless browser, MDN scraper |
| 3: Knowledge Extraction | ✅ DONE | LangChain + Ollama triple extractor, Pydantic validation |
| 4: Curriculum Generation | ✅ DONE | AI curriculum agent, cascading saves |
| 5: REST API | ✅ DONE | FastAPI + Uvicorn, Swagger UI |
| 6: Triple Quality Filter | ✅ DONE | 6 hallucination filters, 24 unit tests |
| 7: Vector DB & Search | ✅ DONE | Weaviate, nomic-embed-text embeddings, semantic search |
| 8: Design Blueprint | ✅ DONE | DESIGN.md — product vision, data model, API contracts |
| 9A: New Data Model | ✅ DONE | 7 new tables, 6 domains, 23 topics seed data |
| 9B: Multi-Source Scraping | ✅ DONE | 10 scrapers, 52 articles, 1,155 sections |
| 9C-1: Concept Extraction | ✅ DONE | 176 concepts across 16 topics |
| 9C-2: ELI5 + Relationships | ✅ DONE | 176 ELI5s, 32 typed relationships |
| 9C-3: Examples + Exercises | ✅ CODE DONE | 426 examples, 252 exercises (old format — need --force regenerate) |
| 9C-4: Concept Enrichment | ✅ DONE | 176/176 key_points + common_mistakes populated |
| 9C-Q: Quality Overhaul | ✅ DONE | Rewritten prompts (progressive examples, 3 exercise types, richer ELI5), category color system, DB schema upgrade |
| 9D: RAG Chatbot | 🔜 NEXT | Embed sections, RAG pipeline, POST /api/chat |
| 9E: Graph & Paths | 🔜 PLANNED | BFS/DFS, learning path generation |

### SaaS Product — Phases 11A–11C DONE

| Phase | Status | Key Output |
|-------|--------|------------|
| 11A: Frontend Setup | ✅ DONE | Next.js 15, TailwindCSS, shadcn/ui, Supabase Auth, Prisma |
| 11B: Public Pages | ✅ DONE | Landing, catalog, pricing, login/signup |
| 11C: Dashboard + Learning | ✅ DONE | 3-panel layout, 4-tab concept view (Theory/ELI5/Examples/Exercises) |
| 11D: AI Tutor + Graph | 🔜 PLANNED | Wire AiTutor, KnowledgeGraphView, LearningPathView |
| 11E: Premium Features | 🔜 PLANNED | Stripe, PaywallGate, on-demand generation |
| 12: FastAPI Enhancements | 🔜 PLANNED | Auth middleware, cloud LLM, pagination |
| 13: Production Deploy | 🔜 PLANNED | Vercel + Railway, kodastudy.com |

### Browse API — DONE
- `GET /api/knowledge/domains` — list all domains with topic counts
- `GET /api/knowledge/topics` — list all topics with concept counts
- `GET /api/knowledge/topics/{slug}` — topic detail with concepts
- `GET /api/knowledge/concepts/slug/{topic_slug}/{concept_slug}` — full concept detail (examples, exercises, relationships)
- `GET /api/knowledge/concepts/{id}` — concept detail by ID

### Known Issues
- **7 topics have 0 concepts**: 3 have no articles (LLM Fundamentals, LangChain, Git & GitHub), 2 have too little content (<200 chars), SQL Fundamentals times out, Playwright has only 2 concepts
- **Large topics timeout**: Topics with 10+ concepts timeout during relationship extraction. Fix: batch into sub-groups of ~6
- **browse.py responses**: Uses `return dict, status_code` tuples instead of `HTTPException` for error cases
- **AiTutor is a shell**: UI exists but no chat logic (blocked on Phase 9D)
- **Graph/Path pages are placeholders**: Static text, no visualization
- **Stripe integration is stubs**: Returns static JSON

---

## Next Steps

### Before Next Session: Regenerate Content (requires Ollama, ~4-5 hrs)

The DB currently has OLD-format examples (426, no when_to_use/difficulty_level) and OLD-format exercises (252, all build_from_spec). The new generators need to run with `--force`:

```bash
python enrich_eli5.py --force           # ~30 min: regenerate 176 ELI5s (richer 4-6 sentence format)
python enrich_examples.py --force       # ~1-2 hrs: 176 concepts x 3 progressive examples
python enrich_exercises.py --force      # ~2-3 hrs: 176 concepts x 3 typed exercises (predict_output + fix_bug + build_from_spec)
```

**WARNING:** `--force` will ADD new examples/exercises alongside existing ones. To replace cleanly, delete old ones first:
```python
from database.connection import SessionLocal
from database.models import Example, Exercise
with SessionLocal() as s:
    s.query(Example).delete(); s.query(Exercise).delete(); s.commit()
```

### Next Phase: 9D — RAG Chatbot

### What to Build:
1. Embed raw article sections (not just triples) into Weaviate
2. RAG pipeline: user question → retrieve relevant sections → LLM answers with sources
3. `POST /api/chat` endpoint
4. `POST /api/search/suggest` autocomplete endpoint

### See DESIGN.md Section 5.5 for API contracts, Section 9 Phase 9D for details

---

## Pre-Requisite: Live Run of Phase 9C-3

Before starting 9D, run the enrichment generators to populate examples and exercises:

```bash
# Requires Ollama running with model pulled
ollama pull qwen3.5:27b    # or whatever LLM_BRAIN_MODEL is set to
ollama pull qwen3.5:9b     # or whatever LLM_WORKER_MODEL is set to

python enrich_examples.py       # Generate 2-3 examples per concept (~1-2 hrs)
python enrich_exercises.py      # Generate 1-2 exercises per concept (~1-2 hrs)
python test_phase9c3.py         # Verify (7 test categories)
```

---

## Infrastructure Setup

### Required Services
```bash
docker compose up -d          # PostgreSQL (5432) + Weaviate (8080)
ollama pull qwen3.5:27b       # Brain model (extraction, relationships)
ollama pull qwen3.5:9b        # Worker model (ELI5, examples, exercises)
ollama pull nomic-embed-text  # Embedding model
```

### Run the Pipeline
```bash
python main.py                # Original pipeline: scrape → extract → filter → embed → curriculum
python scrape_all.py          # Multi-source scraper (Phase 9B)
python enrich_concepts.py     # Concept extraction (Phase 9C-1)
python enrich_eli5.py         # ELI5 generation (Phase 9C-2)
python enrich_relationships.py # Relationship extraction (Phase 9C-2)
python enrich_examples.py     # Example generation (Phase 9C-3)
python enrich_exercises.py    # Exercise generation (Phase 9C-3)
```

### Run the API
```bash
uvicorn api.main:app --reload --port 8000
# Swagger UI: http://localhost:8000/docs
```

### Run the Frontend
```bash
cd frontend
npm install
npx prisma generate
npm run dev
# App: http://localhost:3000
```

---

## Model Configuration (Fast-Slow Architecture)

The pipeline uses two models configured via `.env`:

| Role | Env Var | Default | Purpose |
|------|---------|---------|---------|
| Brain | `LLM_BRAIN_MODEL` | `qwen3.5:27b` | Concept extraction, relationships (needs reasoning) |
| Worker | `LLM_WORKER_MODEL` | `qwen3.5:9b` | ELI5, examples, exercises (needs speed) |

See `config/models.py` for the configuration and `config/__init__.py`.

---

## Key Design Decisions

1. **Concepts vs Triples:** Triples are raw (subject, predicate, object) strings. Concepts are first-class entities with IDs, categories, explanations. Concept relationships are typed edges between concept IDs.

2. **4 Content Layers:** Every concept has Theory (scraped), ELI5 (LLM-generated), Examples (scraped + generated), Exercises (LLM-generated).

3. **7 Relationship Types:** requires, enables, is_a, part_of, related_to, contrasts_with, built_on

4. **$0 Dev Cost:** Everything local — Ollama, Docker, PostgreSQL, Weaviate. No cloud.

5. **SaaS Architecture:** Vercel (Next.js) + Railway (FastAPI) + Supabase (Auth + PostgreSQL) + Stripe (payments). See DESIGN_SAAS.md.

6. **Dual ORM:** SQLAlchemy manages content tables (backend). Prisma manages user tables (frontend). Same PostgreSQL database.

---

## File Map — What Every File Does

```
CONFIGURATION:
  .opencode/rules.md    — AI coding assistant rules & teaching protocol
  .env                  — DB credentials, model names, Supabase keys
  config/__init__.py    — Package init
  config/models.py      — LLM model configuration (brain/worker architecture)
  opencode.json         — OpenCode configuration
  docker-compose.yml    — PostgreSQL 16 + Weaviate services
  requirements.txt      — Python dependencies

DATABASE LAYER (database/):
  connection.py     — SQLAlchemy engine, session factory, Base class
  models.py         — ORM tables: RawArticle, KnowledgeTripleDB, Domain, Topic, Concept,
                      ConceptRelationship, Example, Exercise, SourceSection
  seed_data.py      — Seed data: 6 domains, 23 topics
  vector_store.py   — Weaviate client: store/search/health check

PYDANTIC MODELS (models/):
  content.py        — ScrapedContent, RawScrapedArticle
  scraped_page.py   — ScrapedPage, ScrapedSection
  knowledge.py      — KnowledgeTriple, TripleExtraction
  curriculum.py     — Curriculum, Module, Lesson
  enrichment.py     — ExtractedConcept, ConceptExtractionResult, ExtractedRelationship,
                      GeneratedExample, GeneratedExercise, ExampleGenerationResult,
                      ExerciseGenerationResult

SCRAPERS (scraper/):
  base_scraper.py              — BaseScraper: Playwright browser, fetch_page(), extract_links()
  docs_scraper.py              — DocsScraper: generic configurable docs scraper
  mdn_scraper.py               — MDNScraper
  python_docs_scraper.py       — Python docs
  fastapi_scraper.py           — FastAPI docs
  sqlalchemy_scraper.py        — SQLAlchemy docs
  langchain_scraper.py         — LangChain docs
  docker_scraper.py            — Docker docs
  weaviate_scraper.py          — Weaviate docs
  postgresql_scraper.py        — PostgreSQL docs
  pydantic_scraper.py          — Pydantic docs
  playwright_docs_scraper.py   — Playwright Python docs
  github_scraper.py            — GitHub README/docs

PIPELINE (pipeline/):
  text_chunker.py              — Splits articles into ~1000-char overlapping chunks
  triple_extractor.py          — LangChain + Ollama → (subject, predicate, object) triples
  triple_filter.py             — 6 quality filters + scoring (0.0-1.0)
  curriculum_agent.py          — LangChain + Ollama → structured curricula
  embedder.py                  — nomic-embed-text → 768D vectors for semantic search
  section_parser.py            — HTML → heading-based sections → source_sections table
  multi_source_scraper.py      — Orchestrator: routes URLs, scrapes, stores
  concept_extractor.py         — LLM concept extraction per topic with slug dedup
  eli5_generator.py            — LLM ELI5 analogy generation per concept
  relationship_extractor.py    — LLM typed relationship extraction per topic
  example_generator.py         — LLM code example generation per concept
  exercise_generator.py        — LLM exercise generation per concept
  json_utils.py                — Robust LLM JSON extraction with repair fallback

API (api/):
  main.py                      — FastAPI app, CORS, route registration, startup event
  routes/curricula.py          — GET/POST curricula endpoints
  routes/knowledge.py          — GET articles, GET triples endpoints
  routes/search.py             — POST semantic search, GET health
  routes/browse.py             — GET /api/knowledge/* browsing endpoints
  schemas/responses.py         — Pydantic response models

FRONTEND (frontend/):
  src/app/(public)/            — Landing, catalog, pricing, topic preview, login, signup
  src/app/(dashboard)/         — 3-panel learning interface
    dashboard/                 — Topic overview with concept counts
    learn/[topicSlug]/         — Topic detail, concept detail (4-tab), graph, path
    generate/                  — On-demand curriculum generation (placeholder)
    settings/                  — Profile & subscription (placeholder)
  src/app/api/                 — BFF proxy to FastAPI, Stripe stubs
  src/components/layout/       — CurriculumSidebar, AiTutor (shell)
  src/components/learning/     — TheoryTab, Eli5Tab, ExamplesTab, ExercisesTab
  src/components/shared/       — PaywallGate (pass-through)
  src/components/ui/           — Button (shadcn)
  src/lib/                     — api.ts, auth.ts, db.ts, supabase-client.ts, utils.ts
  prisma/schema.prisma         — User, Enrollment, Progress, GenerationJob models

ENTRY POINTS:
  main.py                      — Original full pipeline orchestrator
  scrape_all.py                — Multi-source scraper entry point
  enrich_concepts.py           — Concept extraction (--topic, --dry-run)
  enrich_eli5.py               — ELI5 generation (--concept, --force)
  enrich_relationships.py      — Relationship extraction (--topic, --dry-run)
  enrich_examples.py           — Example generation (--concept, --force, --limit, --dry-run)
  enrich_exercises.py          — Exercise generation (--concept, --force, --limit, --dry-run)

TESTS:
  test_triple_filter.py        — 24 unit tests for quality filter
  test_scraper.py              — Scraper integration test
  test_db_setup.py             — Database connection test
  test_curriculum.py           — Curriculum generation test
  test_embeddings.py           — Embedding & vector store tests
  test_phase9a.py              — Phase 9A verification (7 categories)
  test_phase9b.py              — Phase 9B verification (6 categories)
  test_phase9c1.py             — Phase 9C-1 verification (6 categories)
  test_phase9c2.py             — Phase 9C-2 verification (7 categories)
  test_phase9c3.py             — Phase 9C-3 verification (7 categories)

DOCUMENTATION:
  README.md                    — Project overview and unified roadmap
  DESIGN.md                    — Product blueprint (THE master plan)
  DESIGN_SAAS.md               — SaaS architecture (kodastudy.com launch plan)
  ARCHITECTURE.md              — Deep technical explanations
  TESTING_GUIDE.md             — How to run each test
  HANDOFF.md                   — THIS FILE — session state handoff
  RUN_COMMANDS.md              — Development commands reference
```

---

## Full Phase Roadmap

```
BACKEND PIPELINE:
  ✅ Phase 1:  Database Foundation
  ✅ Phase 2:  Web Scraping (Playwright + MDN)
  ✅ Phase 3:  Knowledge Extraction (LLM triples)
  ✅ Phase 4:  Curriculum Generation (LLM curricula)
  ✅ Phase 5:  REST API (FastAPI)
  ✅ Phase 6:  Triple Quality Filter
  ✅ Phase 7:  Vector Database & Semantic Search (Weaviate)
  ✅ Phase 8:  Design Blueprint
  ✅ Phase 9A: New Data Model (7 tables, Alembic, seed data)
  ✅ Phase 9B: Multi-Source Scraping (10 scrapers, 52 articles)
  ✅ Phase 9C-1: Concept Extraction (176 concepts)
  ✅ Phase 9C-2: ELI5 + Relationships (176 ELI5s, 32 edges)
  ✅ Phase 9C-3: Examples + Exercises (426 examples, 252 exercises — need --force regenerate for new format)
  ✅ Phase 9C-4: Concept Enrichment (176/176 key_points + common_mistakes)
  ✅ Phase 9C-Q: Quality Overhaul (rewritten prompts, 3 exercise types, color system, DB schema upgrade)
  🔜 Phase 9D: RAG Chatbot
  🔜 Phase 9E: Graph Traversal & Learning Paths

SAAS PRODUCT:
  ✅ Phase 11A: Frontend Setup (Next.js 15, Tailwind, shadcn, Supabase, Prisma)
  ✅ Phase 11B: Public Pages (landing, catalog, pricing, auth)
  ✅ Phase 11C: Dashboard + Learning Interface (3-panel, 4-tab concept view)
  🔜 Phase 11D: AI Tutor + Knowledge Graph Visualization
  🔜 Phase 11E: Premium Features (Stripe, paywall, generation)
  🔜 Phase 12:  FastAPI Enhancements (auth middleware, cloud LLM)
  🔜 Phase 13:  Production Deployment (kodastudy.com)
```

---

## Session-by-Session Plan (Next Steps)

| Session | Phase | Task |
|---------|-------|------|
| DONE | 9C-4 | `enrich_key_points.py` — 176/176 enriched, 0 failed |
| Next | 9C-Q | `enrich_eli5.py --force` + `enrich_examples.py --force` + `enrich_exercises.py --force` (~4-5 hrs with Ollama) |
| +1 | 9D | RAG chatbot: embed sections, `/api/chat`, `/api/search/suggest` |
| +2 | 9E | Graph traversal: BFS/DFS, `/api/graph`, `/api/graph/path` |
| +3 | 11D | Frontend: wire AiTutor, build KnowledgeGraphView + LearningPathView |
| +4 | 11E | Stripe integration, PaywallGate, on-demand generation |
| +5 | 12 | FastAPI auth middleware, cloud LLM swap, pagination |
| +6 | 13 | Deploy: Vercel + Railway, kodastudy.com, seed production |
