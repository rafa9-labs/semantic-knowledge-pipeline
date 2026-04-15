# 🧠 Semantic Knowledge Pipeline

An end-to-end AI-powered pipeline that ingests technical documentation, extracts structured knowledge as triples, generates learning curricula, and serves everything through a REST API.

**Total cost: $0. Total cloud dependencies: 0. Everything runs locally.**

---

## 🎯 What It Does

1. **Scrapes** educational content from MDN Web Docs using a headless browser
2. **Extracts** knowledge triples (subject → predicate → object) using a local LLM
3. **Filters** hallucinations and garbage using 6 rule-based quality filters
4. **Generates** structured learning curricula with modules and lessons via AI
5. **Serves** all data through a FastAPI REST API with Swagger UI

---

## 🏗️ Tech Stack

| Component | Technology | Purpose |
|-----------|-----------|---------|
| Scraping | `playwright` (async) | Headless browser for JS-rendered pages |
| Validation | `pydantic` | Data validation at every pipeline stage |
| Database | `postgresql` (Docker) | Relational storage for articles, triples, curricula |
| ORM | `sqlalchemy` | Python-SQL translation, query building |
| AI Orchestration | `langchain` | Prompt templates, LLM chaining, retries |
| LLM | `ollama` + Gemma 4 26B | Local AI for extraction & curriculum generation |
| API | `fastapi` + `uvicorn` | REST API with auto-generated docs |
| Deployment | `docker` + `docker-compose` | One-command infrastructure setup |
| Quality | Rule-based filters | Hallucination detection, garbage triple removal |

---

## 📁 Project Structure

```
semantic-knowledge-pipeline/
├── .clinerules                  # AI coding assistant rules
├── .env                         # Environment variables (DB creds, model name)
├── docker-compose.yml           # PostgreSQL in Docker
├── main.py                      # Main pipeline orchestrator
├── requirements.txt             # Python dependencies
│
├── database/                    # Database layer
│   ├── connection.py            # SQLAlchemy engine & session factory
│   └── models.py                # ORM models (tables) for PostgreSQL
│
├── models/                      # Pydantic validation models
│   ├── content.py               # ScrapedContent — validates scraped data
│   ├── knowledge.py             # KnowledgeTriple — validates LLM-extracted triples
│   └── curriculum.py            # Curriculum/Module/Lesson — validates AI curricula
│
├── scraper/                     # Web scraping layer
│   ├── base_scraper.py          # BaseScraper with Playwright browser automation
│   └── mdn_scraper.py           # MDN-specific scraper (CSS selectors, URL handling)
│
├── pipeline/                    # Data processing layer
│   ├── text_chunker.py          # Splits articles into ~1000-char chunks for LLM
│   ├── triple_extractor.py      # LangChain + Ollama → extracts triples from text
│   ├── triple_filter.py         # 6 rule-based filters for hallucination detection
│   └── curriculum_agent.py      # LangChain + Ollama → generates curricula
│
├── api/                         # REST API layer
│   ├── main.py                  # FastAPI app + route registration
│   ├── routes/
│   │   ├── curricula.py         # GET /api/curricula, POST /api/curricula/generate
│   │   └── knowledge.py         # GET /api/triples, GET /api/articles
│   └── schemas/
│       └── responses.py         # Pydantic response models for API
│
├── scripts/                     # Utility scripts
│   └── cleanup_triples.py       # DB cleanup tool (dry-run / live mode)
│
├── test_triple_filter.py        # 24 unit tests for quality filter
├── test_scraper.py              # Scraper integration test
├── test_db_setup.py             # Database connection test
├── test_curriculum.py           # Curriculum generation test
│
├── ARCHITECTURE.md              # Deep-dive: how every technology works & why
└── TESTING_GUIDE.md             # How to run each test
```

---

## ✅ Implementation Roadmap

### Phase 1: Database Foundation — *DONE*
- [x] Docker Compose for PostgreSQL 16
- [x] SQLAlchemy connection factory (`database/connection.py`)
- [x] ORM models: `raw_articles`, `knowledge_triples`, `curricula`, `modules`, `lessons`
- [x] Auto-create tables on startup

### Phase 2: Web Scraping — *DONE*
- [x] Playwright async headless browser (`scraper/base_scraper.py`)
- [x] MDN-specific scraper with CSS selectors (`scraper/mdn_scraper.py`)
- [x] Pydantic `ScrapedContent` model with min-length validation
- [x] Error handling: timeouts, missing elements, retry logic

### Phase 3: Knowledge Extraction — *DONE*
- [x] Text chunker: splits articles into ~1000-char overlapping chunks
- [x] LangChain + Ollama integration (Gemma 4 26B)
- [x] Structured JSON prompt with few-shot examples
- [x] Pydantic `KnowledgeTriple` model with confidence scoring
- [x] Retry logic (3 attempts) for LLM failures
- [x] Deduplication by (subject, predicate, object)

### Phase 4: Curriculum Generation — *DONE*
- [x] AI curriculum agent using LangChain (`pipeline/curriculum_agent.py`)
- [x] Pydantic `Curriculum`, `Module`, `Lesson` models with constraints
- [x] Retry with error feedback on validation failure
- [x] Cascading saves to 3 tables (curricula → modules → lessons)

### Phase 5: REST API — *DONE*
- [x] FastAPI application with Uvicorn (`api/main.py`)
- [x] Curricula endpoints: list, get, generate
- [x] Knowledge endpoints: list triples, list articles
- [x] Pydantic response schemas for all endpoints
- [x] Swagger UI auto-documentation at `/docs`

### Phase 6: Triple Quality Filter — *DONE*
- [x] 6 rule-based hallucination filters (`pipeline/triple_filter.py`)
  - Punctuation detection, alpha length, real words, circularity, predicate quality, artifact detection
- [x] Quality scoring (0.0–1.0) for ranking triples
- [x] Integrated into extraction pipeline (runs after dedup)
- [x] Improved extraction prompt with anti-hallucination rules
- [x] DB cleanup script with dry-run mode (`scripts/cleanup_triples.py`)
- [x] 24 unit tests — all passing

### Phase 7: Vector Database & Semantic Search — *TODO*
- [ ] Set up Pinecone or Weaviate (vector database)
- [ ] Generate embeddings for knowledge triples using Ollama
- [ ] Store embeddings in vector DB with metadata
- [ ] Implement semantic search endpoint: "find concepts similar to X"
- [ ] Add "related concepts" to API responses using vector similarity

### Phase 8: Polished Frontend UI — *TODO*
- [ ] Choose framework (Streamlit for speed, React for polish)
- [ ] Knowledge graph visualization (interactive node-link diagram)
- [ ] Curriculum browser with module/lesson drill-down
- [ ] Search interface for triples and articles
- [ ] Pipeline status dashboard (scrape → extract → filter → generate)

---

## 🚀 Quick Start

### Prerequisites
- Python 3.12+
- Docker Desktop (for PostgreSQL)
- Ollama (for local LLM) with Gemma 4 26B pulled

### Setup

```bash
# 1. Start PostgreSQL
docker-compose up -d

# 2. Create virtual environment
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # Linux/Mac

# 3. Install dependencies
pip install -r requirements.txt

# 4. Install Playwright browsers
playwright install chromium

# 5. Pull the LLM model
ollama pull gemma4:26b

# 6. Run the full pipeline
python main.py

# 7. Start the API
python -m uvicorn api.main:app --reload --port 8000
# → Swagger UI: http://localhost:8000/docs
```

### Useful Commands

```bash
# Run all tests
python -m pytest test_triple_filter.py -v

# Clean garbage triples from database (dry run)
python scripts/cleanup_triples.py

# Actually delete bad triples
python scripts/cleanup_triples.py --live
```

---

## 📖 Documentation

- **[ARCHITECTURE.md](ARCHITECTURE.md)** — Deep-dive into every technology: what it does, why we chose it, how it works in this project
- **[TESTING_GUIDE.md](TESTING_GUIDE.md)** — How to run and understand each test

---

## 🔄 Data Flow Summary

```
MDN URLs → Playwright (scrape) → Pydantic (validate) → PostgreSQL (store)
    → Text Chunker (split) → Gemma 4 via LangChain (extract triples)
    → TripleFilter (remove garbage) → PostgreSQL (clean triples)
    → Gemma 4 via LangChain (generate curriculum) → Pydantic (validate)
    → PostgreSQL (curricula + modules + lessons)
    → FastAPI (serve as JSON REST API)
```

---

## 📋 Next Steps (for new chat)

The pipeline is fully functional from scraping through API. The remaining work is:

1. **Phase 7: Vector Database** — Add Pinecone or Weaviate for semantic search over triples. Generate embeddings with Ollama, store in vector DB, create `/api/search` endpoint.

2. **Phase 8: Frontend UI** — Build a visual interface. Streamlit is fastest for a data-oriented UI; React gives the most polish. Start with a knowledge graph visualization.

See `.clinerules` for the coding standards and tech stack constraints to follow.