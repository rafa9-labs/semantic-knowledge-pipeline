# OpenCode Starter Prompt — DevKnowledge Project

Copy everything below the line into OpenCode to start a fully-contextualized session.

---

## PASTE THIS INTO OPENCODE:

Read `HANDOFF.md`, `DESIGN.md`, and `.opencode/rules.md` in that order. These files contain the full project state, product blueprint, and coding rules.

**Summary of where we are:**

We're building **DevKnowledge** — an AI-powered educational knowledge graph for ML/AI engineers. The tool teaches the exact tech stack used to build it ("eat your own dogfood" principle).

**Phases 1–8 are COMPLETE:**
- Phase 1: PostgreSQL + SQLAlchemy ORM (Docker)
- Phase 2: Playwright async web scraper (MDN)
- Phase 3: LangChain + Ollama (Gemma 4) triple extraction
- Phase 4: AI curriculum generation
- Phase 5: FastAPI REST API with Swagger UI
- Phase 6: Triple quality filter (6 rules, 24 tests passing)
- Phase 7: Weaviate vector DB + Ollama embeddings + semantic search API
- Phase 8: Design Blueprint (DESIGN.md — the master plan)

**Tech Stack:** Python, Playwright, Pydantic, PostgreSQL, SQLAlchemy, Ollama (Gemma 4 26B + nomic-embed-text), LangChain, Weaviate, FastAPI, Docker

**Our next task is Phase 9A: New Data Model.** Here's exactly what to build:

### Phase 9A — New Data Model + Seed Data

1. **Add 7 new SQLAlchemy tables to `database/models.py`:**
   - `domains` — top-level learning domains (Python Core, Databases, AI/ML Pipeline, APIs & Backend, DevOps, Tooling)
   - `topics` — learning topics within domains (Async Programming, Type Hints & Pydantic, etc.)
   - `concepts` — individual learnable concepts (async/await, Promise, embeddings, etc.) — the CORE entity
   - `concept_relationships` — typed edges between concepts (requires, enables, is_a, part_of, related_to, contrasts_with, built_on)
   - `examples` — code examples for concepts (scraped + LLM-generated)
   - `exercises` — practice problems with solutions, hints, test cases
   - `source_sections` — parsed article sections for citation

2. **Add `topic_id` foreign key** to existing `raw_articles` table

3. **Create `database/seed_data.py`** with seed data for 7 domains and ~25 topics (see DESIGN.md Section 2 for the exact domain/topic structure)

4. **Create a test script** to verify new tables create correctly and seed data inserts

**Exact table schemas with all columns, types, and constraints are in `DESIGN.md` Section 4.3.**

**Important rules from .opencode/rules.md:**
- Explain WHY before writing code using core technologies
- Pydantic models for ALL data validation
- Modular, object-oriented Python — no monolith scripts
- try/except error handling everywhere
- Descriptive comments for learning

After Phase 9A, the roadmap continues:
- Phase 9B: Multi-source scraping (6 new documentation scrapers)
- Phase 9C: Content enrichment (ELI5, examples, exercises via LLM)
- Phase 9D: RAG chatbot
- Phase 9E: Graph traversal & learning paths
- Phase 10: React frontend

Let's start with Phase 9A. Read the three files, confirm you understand the data model, and begin implementing.