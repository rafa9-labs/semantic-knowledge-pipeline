# KodaStudy — AI-Powered Knowledge Graph Learning Platform

An end-to-end AI-powered pipeline that ingests technical documentation, extracts structured knowledge, generates 4-layer learning content (theory, ELI5, examples, exercises), and serves it through a modern web application.

**Product:** [kodastudy.com](https://kodastudy.com) — "Master any subject through AI-powered knowledge graphs"
**Stack:** Python, Playwright, Pydantic, PostgreSQL, SQLAlchemy, Ollama, LangChain, Weaviate, FastAPI, Next.js 15, Supabase, Docker

---

## What It Does

1. **Scrapes** educational content from 10 documentation sites using headless browsers
2. **Extracts** structured knowledge: concepts, typed relationships, ELI5 explanations
3. **Generates** code examples and practice exercises via local LLM
4. **Embeds** content into vectors for semantic search via Weaviate
5. **Serves** everything through a FastAPI REST API
6. **Presents** a 3-panel learning interface (sidebar + content + AI tutor) via Next.js

---

## Tech Stack

| Component | Technology | Purpose |
|-----------|-----------|---------|
| Scraping | `playwright` (async) | Headless browser for 10 documentation sites |
| Validation | `pydantic` | Data validation at every pipeline stage |
| Database | `postgresql` (Docker) | Relational storage for all content |
| ORM (backend) | `sqlalchemy` | Content tables: domains, topics, concepts, examples, exercises |
| ORM (frontend) | `prisma` | User tables: users, enrollments, progress, jobs |
| AI Orchestration | `langchain` | Prompt templates, LLM chaining, retries |
| LLM (dev) | `ollama` + Qwen 3.5 | Local AI for extraction, enrichment, curriculum |
| LLM (prod) | Gemini Flash / DeepSeek | Production API (~$0.10/1M tokens) |
| API | `fastapi` + `uvicorn` | REST API with auto-generated docs |
| Vector DB | `weaviate` (Docker) | Semantic search over knowledge triples |
| Embeddings | `ollama` + nomic-embed-text | 768D vectors for semantic similarity |
| Frontend | `Next.js 15` (App Router) | SSR + CSR, TailwindCSS, shadcn/ui, dark theme |
| Auth | `Supabase` | User accounts, JWT, SSO |
| Payments | `Stripe` | Subscription management |
| Deployment | `Vercel` + `Railway` + `Docker` | Frontend + backend + infra |

---

## Project Structure

```
semantic-knowledge-pipeline/
├── config/                        # LLM model configuration (brain/worker architecture)
├── database/                      # Database layer
│   ├── connection.py              # SQLAlchemy engine & session factory
│   ├── models.py                  # ORM models: 12+ tables
│   ├── seed_data.py               # 6 domains, 23 topics seed data
│   └── vector_store.py            # Weaviate client
│
├── models/                        # Pydantic validation models
│   ├── content.py                 # ScrapedContent
│   ├── knowledge.py               # KnowledgeTriple
│   ├── curriculum.py              # Curriculum/Module/Lesson
│   ├── scraped_page.py            # ScrapedPage, ScrapedSection
│   └── enrichment.py              # Concept, ELI5, Example, Exercise models
│
├── scraper/                       # 12 web scrapers
│   ├── base_scraper.py            # Playwright browser automation
│   ├── docs_scraper.py            # Generic configurable docs scraper
│   ├── mdn_scraper.py             # MDN Web Docs
│   ├── python_docs_scraper.py     # Python docs (Sphinx)
│   ├── fastapi_scraper.py         # FastAPI docs (MkDocs Material)
│   ├── sqlalchemy_scraper.py      # SQLAlchemy docs
│   ├── langchain_scraper.py       # LangChain docs
│   ├── docker_scraper.py          # Docker docs
│   ├── weaviate_scraper.py        # Weaviate docs
│   ├── postgresql_scraper.py      # PostgreSQL docs
│   ├── pydantic_scraper.py        # Pydantic docs
│   ├── playwright_docs_scraper.py # Playwright Python docs
│   └── github_scraper.py          # GitHub README/docs
│
├── pipeline/                      # Data processing layer
│   ├── text_chunker.py            # Splits articles into ~1000-char chunks
│   ├── triple_extractor.py        # LangChain + Ollama → triples
│   ├── triple_filter.py           # 6 hallucination quality filters
│   ├── curriculum_agent.py        # LangChain + Ollama → curricula
│   ├── embedder.py                # nomic-embed-text → 768D vectors
│   ├── section_parser.py          # HTML → heading-based sections
│   ├── multi_source_scraper.py    # Orchestrator: routes URLs, scrapes, stores
│   ├── concept_extractor.py       # LLM concept extraction per topic
│   ├── eli5_generator.py          # LLM ELI5 analogy generation
│   ├── relationship_extractor.py  # LLM typed relationship extraction
│   ├── example_generator.py       # LLM code example generation
│   ├── exercise_generator.py      # LLM exercise generation
│   └── json_utils.py              # Robust LLM JSON extraction with repair
│
├── api/                           # REST API layer
│   ├── main.py                    # FastAPI app + route registration
│   ├── routes/
│   │   ├── curricula.py           # Curricula CRUD
│   │   ├── knowledge.py           # Articles, triples
│   │   ├── search.py              # Semantic search
│   │   └── browse.py              # /api/knowledge/* browsing endpoints
│   └── schemas/
│       └── responses.py           # Pydantic response models
│
├── frontend/                      # KodaStudy — Next.js 15 application
│   ├── src/app/
│   │   ├── (public)/              # Landing, catalog, pricing, login, signup
│   │   ├── (dashboard)/           # 3-panel learning interface
│   │   │   ├── dashboard/         # Topic overview
│   │   │   ├── learn/             # Concept detail (4-tab), graph, path
│   │   │   ├── generate/          # On-demand curriculum generation
│   │   │   └── settings/          # Profile & subscription
│   │   └── api/                   # BFF proxy, Stripe webhooks
│   ├── src/components/
│   │   ├── layout/                # CurriculumSidebar, AiTutor
│   │   ├── learning/              # TheoryTab, Eli5Tab, ExamplesTab, ExercisesTab
│   │   ├── shared/                # PaywallGate
│   │   └── ui/                    # Button (shadcn)
│   ├── src/lib/                   # api.ts, auth.ts, db.ts, supabase-client.ts
│   └── prisma/                    # User/progress schema
│
├── alembic/                       # Database migrations
├── scripts/                       # Utility scripts
├── DESIGN.md                      # Product blueprint (master plan)
├── DESIGN_SAAS.md                 # SaaS architecture blueprint
├── ARCHITECTURE.md                # Technical deep-dive
├── HANDOFF.md                     # Session state handoff
└── TESTING_GUIDE.md               # How to run each test
```

---

## Implementation Roadmap

### Backend Pipeline (Phases 1–9E)

#### Phase 1: Database Foundation — *DONE*
- [x] Docker Compose for PostgreSQL 16
- [x] SQLAlchemy connection factory, ORM models (12+ tables)
- [x] Alembic migrations for version-controlled schema

#### Phase 2: Web Scraping — *DONE*
- [x] Playwright async headless browser
- [x] MDN-specific scraper with CSS selectors + error handling

#### Phase 3: Knowledge Extraction — *DONE*
- [x] Text chunker, LangChain + Ollama triple extractor
- [x] Pydantic validation, retry logic, deduplication

#### Phase 4: Curriculum Generation — *DONE*
- [x] AI curriculum agent, cascading saves to 3 tables

#### Phase 5: REST API — *DONE*
- [x] FastAPI + Uvicorn, Swagger UI at `/docs`

#### Phase 6: Triple Quality Filter — *DONE*
- [x] 6 rule-based hallucination filters, quality scoring, 24 unit tests

#### Phase 7: Vector Database & Semantic Search — *DONE*
- [x] Weaviate in Docker, nomic-embed-text embeddings, semantic search API

#### Phase 8: Design Blueprint — *DONE*
- [x] Product vision, MVP scope, 4 content layers, data model, API contracts

#### Phase 9A: New Data Model — *DONE*
- [x] 7 new tables: domains, topics, concepts, concept_relationships, examples, exercises, source_sections
- [x] 6 domains, 23 topics seed data

#### Phase 9B: Multi-Source Scraping — *DONE*
- [x] Generic DocsScraper + 10 site-specific scrapers
- [x] 52 articles, 1,155 sections across 23 topics

#### Phase 9C-1: Concept Extraction — *DONE*
- [x] 176 concepts extracted across 16 of 23 topics

#### Phase 9C-2: ELI5 + Relationships — *DONE*
- [x] 176 ELI5 explanations (100% coverage), 32 typed relationships

#### Phase 9C-3: Examples + Exercises — *CODE DONE, NEEDS REGENERATION*
- [x] ExampleGenerator + ExerciseGenerator pipelines
- [x] 426 examples, 252 exercises in database (old format)
- [ ] Run `python enrich_examples.py --force` for progressive examples (Getting Started/Real-World/Advanced)
- [ ] Run `python enrich_exercises.py --force` for 3 exercise types (predict_output/fix_bug/build_from_spec)

#### Phase 9C-4: Concept Enrichment — *DONE*
- [x] 176/176 concepts enriched with key_points (4-6 per concept) and common_mistakes (3-4 per concept)

#### Phase 9C-Q: Content Quality Overhaul — *DONE*
- [x] Rewritten ELI5 prompt: 4-6 sentences, structured analogy → mechanism → why → scenario
- [x] Rewritten example prompt: 3 progressive levels with when_to_use + difficulty_level
- [x] Rewritten exercise prompt: 3 types (predict_output, fix_bug, build_from_spec)
- [x] DB schema: new columns on examples (when_to_use, difficulty_level) and exercises (exercise_type, options, correct_answer, buggy_code, bug_explanation)
- [x] Frontend category color system (pastel/muted: sky/sage/amber/violet/teal)
- [x] Frontend: type-specific exercise rendering (MC quiz, fix-the-bug, build-from-spec)
- [x] 70+ automated tests in `test_pipeline_readiness.py`

#### Phase 9D: RAG Chatbot — *NEXT*
- [ ] Embed source_sections into Weaviate
- [ ] RAG pipeline: question → retrieve → LLM answer with citations
- [ ] `POST /api/chat` endpoint
- [ ] `POST /api/search/suggest` autocomplete

#### Phase 9E: Graph Traversal & Learning Paths — *PLANNED*
- [ ] BFS/DFS traversal over concept_relationships
- [ ] `GET /api/graph` and `GET /api/graph/path` endpoints
- [ ] Auto-generate prerequisite learning paths

---

### SaaS Product (Phases 11–13)

#### Phase 11A: Frontend Setup — *DONE*
- [x] Next.js 15 + TailwindCSS + shadcn/ui + dark theme
- [x] Supabase Auth, Prisma ORM, 3-panel CSS Grid layout

#### Phase 11B: Public Pages — *DONE*
- [x] Landing, catalog, pricing, topic preview, login/signup

#### Phase 11C: Dashboard + Learning Interface — *DONE*
- [x] CurriculumSidebar (live topic/concept tree)
- [x] 4-tab concept view: Theory, ELI5, Examples, Exercises
- [x] API proxy to FastAPI

#### Phase 11D: AI Tutor + Knowledge Graph — *PLANNED*
- [ ] Wire AiTutor to POST /api/chat (RAG)
- [ ] KnowledgeGraphView (interactive visualization)
- [ ] LearningPathView (prerequisite chains)

#### Phase 11E: Premium Features — *PLANNED*
- [ ] Stripe Checkout + webhook integration
- [ ] PaywallGate with real tier checking
- [ ] On-demand curriculum generation + GenerationTerminal

#### Phase 12: FastAPI Enhancements — *PLANNED*
- [ ] Auth middleware (Supabase JWT validation)
- [ ] Cloud LLM config (Ollama → Gemini/DeepSeek via env)
- [ ] Pagination, rate limiting, error standardization

#### Phase 13: Production Deployment — *PLANNED*
- [ ] Vercel (frontend) + Railway (backend)
- [ ] kodastudy.com domain + HTTPS
- [ ] Seed production database

---

## Quick Start

### Prerequisites
- Python 3.12+
- Docker Desktop (PostgreSQL + Weaviate)
- Ollama with Qwen 3.5 models pulled
- Node.js 20+ (for frontend)

### Backend Setup

```bash
# 1. Start infrastructure
docker compose up -d

# 2. Create virtual environment
python -m venv venv
venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt
playwright install chromium

# 4. Pull LLM models
ollama pull qwen3.5:27b
ollama pull nomic-embed-text

# 5. Run database migrations + seed data
alembic upgrade head
python database/seed_data.py

# 6. Run enrichment pipelines
python enrich_concepts.py
python enrich_eli5.py
python enrich_relationships.py
python enrich_examples.py
python enrich_exercises.py

# 7. Start the API
python -m uvicorn api.main:app --reload --port 8000
# Swagger UI: http://localhost:8000/docs
```

### Frontend Setup

```bash
cd frontend
npm install
npx prisma generate
npm run dev
# App: http://localhost:3000
```

---

## Documentation

| File | Description |
|------|-------------|
| [DESIGN.md](DESIGN.md) | Product blueprint: vision, data model, API contracts, content layers |
| [DESIGN_SAAS.md](DESIGN_SAAS.md) | SaaS architecture: Vercel + Railway + Supabase + Stripe |
| [ARCHITECTURE.md](ARCHITECTURE.md) | Technical deep-dive: how every technology works and why |
| [HANDOFF.md](HANDOFF.md) | Session state handoff for AI coding assistants |
| [TESTING_GUIDE.md](TESTING_GUIDE.md) | How to run and understand each test |
| [RUN_COMMANDS.md](RUN_COMMANDS.md) | Development commands reference |

---

## Data Flow

```
10 Doc Sites → Playwright (scrape) → Pydantic (validate) → PostgreSQL (store)
    → Section Parser (split) → LLM (extract concepts per topic)
    → LLM (generate ELI5, relationships, examples, exercises)
    → nomic-embed-text (embed) → Weaviate (vector store)
    → LLM (generate curriculum) → PostgreSQL (curricula + modules + lessons)
    → FastAPI (REST API + semantic search + knowledge browsing)
    → Next.js (3-panel learning interface + AI tutor)
```

---

## Current Stats

| Metric | Count |
|--------|-------|
| Documentation scrapers | 10 (+ MDN) |
| Source URLs mapped | 64 |
| Articles scraped | 52 |
| Sections parsed | 1,155 |
| Domains | 6 |
| Topics | 23 |
| Concepts extracted | 176 |
| ELI5 explanations | 176 |
| Typed relationships | 32 |
| Concepts enriched (key_points) | 176 |
| Concepts enriched (common_mistakes) | 176 |
| Code examples | 426 |
| Practice exercises | 252 |

---

## Immediate Next Steps

1. **Regenerate content:** `python enrich_eli5.py --force`, `python enrich_examples.py --force`, `python enrich_exercises.py --force`
2. **Phase 9D:** Build RAG chatbot (embed sections, `/api/chat`, `/api/search/suggest`)
3. **Phase 9E:** Graph traversal + learning paths
4. **Phase 11D:** Wire AI Tutor and build knowledge graph visualization

See [HANDOFF.md](HANDOFF.md) for full session state and [DESIGN_SAAS.md](DESIGN_SAAS.md) for SaaS launch plan.
