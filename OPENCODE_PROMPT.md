# OpenCode Starter Prompt — DevKnowledge Project

Copy everything below the line into OpenCode to start a fully-contextualized session.

---

## PASTE THIS INTO OPENCODE:

Read `HANDOFF.md`, `DESIGN.md`, and `.opencode/rules.md` in that order. These files contain the full project state, product blueprint, and coding rules.

**Summary of where we are:**

We're building **DevKnowledge** — an AI-powered educational knowledge graph for ML/AI engineers. The tool teaches the exact tech stack used to build it ("eat your own dogfood" principle).

**Phases 1–9C-1 are COMPLETE:**
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
- Phase 9C-1: Concept extraction (176 concepts across 16 of 23 topics)

**Tech Stack:** Python, Playwright, Pydantic, PostgreSQL, SQLAlchemy, Ollama (Gemma 4 26B + nomic-embed-text), LangChain, Weaviate, FastAPI, Docker

**Our next task is Phase 9C-2: ELI5 + Relationship Extraction.** Here's exactly what to build:

### Phase 9C-2 — ELI5 + Relationships

1. **ELI5 generator** (`pipeline/eli5_generator.py`)
   - For each concept in the DB, generate a simple analogy-based explanation
   - ~176 LLM calls (1 per concept), sequential with progress logging
   - Store in `concepts.simple_explanation` column
   - Use creative temperature (~0.7) for diverse analogies

2. **Relationship extractor** (`pipeline/relationship_extractor.py`)
   - For each topic, send its concepts to the LLM and ask for typed relationships
   - ~16 LLM calls (1 per topic that has concepts)
   - Validate relationship_type against the 7 valid types (requires, enables, is_a, etc.)
   - Match concept names to concept IDs, store in `concept_relationships` table
   - Use ExtractedRelationship model from `models/enrichment.py` (already built)

**Key reference files:**
- `pipeline/concept_extractor.py` — Same LangChain + Ollama pattern to follow
- `models/enrichment.py` — ExtractedRelationship model already defined
- `database/models.py` — Concept, ConceptRelationship, RelationshipType

**Important rules from .opencode/rules.md:**
- Explain WHY before writing code using core technologies
- Pydantic models for ALL data validation
- Modular, object-oriented Python — no monolith scripts
- try/except error handling everywhere
- Descriptive comments for learning

After Phase 9C-2, the roadmap continues:
- Phase 9C-3: Examples + Exercises
- Phase 9D: RAG Chatbot
- Phase 9E: Graph traversal & learning paths
- Phase 10: React frontend

Let's start with Phase 9C-2. Read the three files, confirm you understand the enrichment pipeline, and begin implementing.
