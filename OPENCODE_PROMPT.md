# OpenCode Starter Prompt — DevKnowledge Project

Copy everything below the line into OpenCode to start a fully-contextualized session.

---

## PASTE THIS INTO OPENCODE:

Read `HANDOFF.md`, `DESIGN.md`, and `.opencode/rules.md` in that order. These files contain the full project state, product blueprint, and coding rules.

**Summary of where we are:**

We're building **DevKnowledge** — an AI-powered educational knowledge graph for ML/AI engineers. The tool teaches the exact tech stack used to build it ("eat your own dogfood" principle).

**Phases 1–9B are COMPLETE:**
- Phase 1: PostgreSQL + SQLAlchemy ORM (Docker)
- Phase 2: Playwright async web scraper (MDN)
- Phase 3: LangChain + Ollama (Gemma 4) triple extraction
- Phase 4: AI curriculum generation
- Phase 5: FastAPI REST API with Swagger UI
- Phase 6: Triple quality filter (6 rules, 24 tests passing)
- Phase 7: Weaviate vector DB + Ollama embeddings + semantic search API
- Phase 8: Design Blueprint (DESIGN.md — the master plan)
- Phase 9A: New data model (7 tables, Alembic, seed data: 6 domains, 23 topics)
- Phase 9B: Multi-source scraping (10 scrapers, 64 URLs, section parser)

**Tech Stack:** Python, Playwright, Pydantic, PostgreSQL, SQLAlchemy, Ollama (Gemma 4 26B + nomic-embed-text), LangChain, Weaviate, FastAPI, Docker

**Our next task is Phase 9C: Content Enrichment.** Here's exactly what to build:

### Phase 9C — Content Enrichment (LLM-powered)

1. **Concept extraction pipeline** (`pipeline/concept_extractor.py`)
   - Identify concepts from scraped articles using LLM
   - Deduplicate by name/slug within each topic
   - Store in `concepts` table with category and difficulty

2. **ELI5 generation pipeline** (`pipeline/eli5_generator.py`)
   - Generate simple explanations for each concept using Gemma 4
   - Store in `concepts.simple_explanation`

3. **Relationship extraction pipeline** (`pipeline/relationship_extractor.py`)
   - Extract typed relationships between concepts using LLM
   - Store in `concept_relationships` with RelationshipType validation

4. **Example extraction + generation** (`pipeline/example_extractor.py`)
   - Parse code blocks from scraped HTML
   - Generate additional examples via LLM
   - Store in `examples` table

5. **Exercise generation pipeline** (`pipeline/exercise_generator.py`)
   - Generate practice problems with solutions and test cases
   - Store in `exercises` table

**Important rules from .opencode/rules.md:**
- Explain WHY before writing code using core technologies
- Pydantic models for ALL data validation
- Modular, object-oriented Python — no monolith scripts
- try/except error handling everywhere
- Descriptive comments for learning

After Phase 9C, the roadmap continues:
- Phase 9D: RAG Chatbot
- Phase 9E: Graph traversal & learning paths
- Phase 10: React frontend

Let's start with Phase 9C. Read the three files, confirm you understand the enrichment pipeline, and begin implementing.