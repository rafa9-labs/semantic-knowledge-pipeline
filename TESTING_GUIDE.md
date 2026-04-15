# 🧪 Semantic Knowledge Pipeline — Testing Guide

## How This Project Works (The Big Picture)

```
┌─────────────┐     ┌──────────────┐     ┌──────────────┐     ┌─────────────┐
│  PHASE 1    │     │   PHASE 2    │     │   PHASE 3    │     │   PHASE 4   │
│  SCRAPE     │ ──► │  EXTRACT     │ ──► │  GENERATE    │ ──► │  REST API   │
│             │     │              │     │              │     │             │
│ Playwright  │     │ Gemma 4 LLM  │     │ Curriculum   │     │ FastAPI     │
│ scrapes MDN │     │ extracts     │     │ Agent builds │     │ serves JSON │
│ web pages   │     │ knowledge    │     │ structured   │     │ endpoints   │
│             │     │ triples      │     │ curricula    │     │             │
└─────────────┘     └──────────────┘     └──────────────┘     └─────────────┘
      │                    │                    │                    │
      ▼                    ▼                    ▼                    ▼
  6 Articles          15 Triples          2 Curricula         6 Endpoints
  in PostgreSQL       in PostgreSQL       in PostgreSQL        via HTTP
```

### What each phase does:

1. **Scrape (Phase 1):** A browser (Playwright) visits MDN web pages, reads the content, validates it with Pydantic models, and stores it in PostgreSQL.

2. **Extract (Phase 2):** We send each article's text to a local AI model (Gemma 4 via Ollama). The AI reads the text and extracts "knowledge triples" — facts in the format `subject → predicate → object`. Example: `"await keyword → enables → asynchronous behavior"`.

3. **Generate (Phase 3):** We send ALL triples + articles to the AI and ask it to design a structured curriculum with modules and lessons. The AI outputs JSON that we validate with Pydantic and store in PostgreSQL.

4. **API (Phase 4):** FastAPI serves all this data as REST endpoints so any frontend can display it.

---

## Prerequisites

Before testing, make sure these are running:

| Service | How to Check | How to Start |
|---------|-------------|-------------|
| **PostgreSQL** | `docker ps` shows `postgres` container | `docker-compose up -d postgres` |
| **Ollama + Gemma 4** | `curl http://localhost:11434/api/tags` | `ollama serve` then `ollama pull gemma4:26b` |
| **Python venv** | `pip list` shows installed packages | `python -m venv venv` then `pip install -r requirements.txt` |

---

## Step-by-Step Testing

### STEP 1: Start the Database

```bash
# Start PostgreSQL in Docker
docker-compose up -d postgres

# Verify it's running (should show "postgres" container)
docker ps
```

**What happens:** Docker starts a PostgreSQL database server on port 5432. All our data (articles, triples, curricula) lives here.

---

### STEP 2: Run the Pipeline (Scrape → Extract → Generate)

```bash
# Activate the virtual environment
venv\Scripts\activate

# Run the full pipeline
python main.py
```

**What happens (this takes 5-15 minutes):**
1. Playwright opens a headless browser, visits 5 MDN pages, extracts the text
2. Each article is validated by Pydantic (`ScrapedContent` model) and stored in PostgreSQL
3. Each article is split into chunks and sent to Gemma 4 for triple extraction
4. Triples are validated by Pydantic (`KnowledgeTriple` model) and stored
5. All data is sent to the Curriculum Agent which generates a structured curriculum
6. The curriculum is validated by Pydantic (`Curriculum` model with nested `Module` and `Lesson`) and stored

**You'll see output like:**
```
🚀 Semantic Knowledge Pipeline
============================================================
[Phase 1] Scraping 5 URLs...
  ✓ async function — 7716 chars
  ✓ Using the Fetch API — 14405 chars
  ...
[Phase 2] Extracting knowledge triples...
  Extracting from: async function (chunk 1/2)
  ...
[Phase 3] Generating curriculum...
  ✓ Generated: Mastering Async JavaScript (3 modules, 6 lessons)
```

---

### STEP 3: Start the REST API

```bash
# In a NEW terminal (keep this running)
venv\Scripts\uvicorn api.main:app --reload --port 8000
```

**What happens:**
- Uvicorn starts an HTTP server on port 8000
- FastAPI loads all routes, connects to PostgreSQL, and ensures tables exist
- `--reload` means the server auto-restarts when you edit code

**You'll see:**
```
INFO: Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
INFO: Application startup complete.
```

---

### STEP 4: Test with Swagger UI (Easiest!)

Open your browser and go to:
```
http://127.0.0.1:8000/docs
```

**Swagger UI** is an interactive API documentation page that FastAPI auto-generates. You can:
1. See every endpoint with its description
2. Click **"Try it out"** on any endpoint
3. Click **"Execute"** to run the request
4. See the JSON response right in the browser

#### Try these in order:

**4a. Health Check**
- Expand `GET /api/` → Try it out → Execute
- You should see: `{"status": "ok", "service": "Semantic Knowledge Pipeline API", "version": "0.1.0"}`

**4b. List Articles**
- Expand `GET /api/articles` → Try it out → Execute
- You should see 6 articles with titles like "Promise", "async function", etc.

**4c. List Knowledge Triples**
- Expand `GET /api/triples` → Try it out → Execute
- You should see 15 knowledge triples (subject → predicate → object)
- Try adding `subject=await` in the filter field — should return 3 results

**4d. List Curricula**
- Expand `GET /api/curricula` → Try it out → Execute
- You should see 2 curricula with module/lesson counts

**4e. Get Curriculum Detail**
- Expand `GET /api/curricula/{curriculum_id}` → Try it out → Enter `2` → Execute
- You should see the FULL curriculum: 3 modules, each with 2 lessons, learning objectives, prerequisites, source URLs

**4f. Generate a New Curriculum** (requires Ollama running)
- Expand `POST /api/curricula/generate` → Try it out
- Edit the request body:
```json
{
  "topic": "JavaScript Promises",
  "target_audience": "Beginner developers",
  "difficulty": "beginner"
}
```
- Click Execute — this takes 1-3 minutes (LLM is thinking)
- You should get back a brand new curriculum with modules and lessons

---

### STEP 5: Test with curl (Command Line)

If you prefer the terminal over the browser:

```bash
# Health check
curl.exe -s http://127.0.0.1:8000/api/

# List articles
curl.exe -s http://127.0.0.1:8000/api/articles

# List all triples
curl.exe -s http://127.0.0.1:8000/api/triples

# Filter triples by subject
curl.exe -s "http://127.0.0.1:8000/api/triples?subject=await"

# List curricula
curl.exe -s http://127.0.0.1:8000/api/curricula

# Get curriculum #2 with full detail
curl.exe -s http://127.0.0.1:8000/api/curricula/2

# Test 404 (should return error)
curl.exe -s http://127.0.0.1:8000/api/curricula/999

# Generate a new curriculum (takes 1-3 min)
curl.exe -s -X POST http://127.0.0.1:8000/api/curricula/generate -H "Content-Type: application/json" -d "{\"topic\":\"JavaScript Promises\",\"target_audience\":\"Beginners\",\"difficulty\":\"beginner\"}"
```

---

### STEP 6: Inspect the Database Directly

Connect to PostgreSQL to see the raw data:

```bash
# Connect to the database
docker exec -it semantic-knowledge-pipeline-postgres-1 psql -U forex_admin -d forex_ml

# See all articles
SELECT id, title, source_site, LENGTH(raw_text) as text_len FROM raw_articles;

# See all knowledge triples
SELECT id, subject, predicate, object_value, confidence FROM knowledge_triples;

# See all curricula
SELECT id, title, topic, difficulty, model_name FROM curricula;

# See modules for curriculum #2
SELECT id, title, order_index FROM modules WHERE curriculum_id = 2 ORDER BY order_index;

# See lessons for module #4
SELECT id, title, order_index, learning_objectives FROM lessons WHERE module_id = 4 ORDER BY order_index;

# Exit
\q
```

---

## Project File Structure (What Each File Does)

```
semantic-knowledge-pipeline/
│
├── .clinerules                  # AI coding assistant rules
├── .env                         # Secrets (DB password, API keys) — NEVER commit this
├── docker-compose.yml           # PostgreSQL database config
├── requirements.txt             # Python dependencies
├── main.py                      # Run the full pipeline (scrape → extract → generate)
│
├── models/                      # Pydantic data validation models
│   ├── content.py               #   ScrapedContent — validates scraped web data
│   ├── knowledge.py             #   KnowledgeTriple — validates extracted facts
│   └── curriculum.py            #   Curriculum, Module, Lesson — validates AI output
│
├── scraper/                     # Web scraping (Phase 1)
│   ├── base_scraper.py          #   BaseScraper — shared browser/session logic
│   └── mdn_scraper.py           #   MDNScraper — scrapes Mozilla Developer Network
│
├── pipeline/                    # AI processing (Phases 2 & 3)
│   ├── text_chunker.py          #   Splits long articles into smaller pieces for the LLM
│   ├── triple_extractor.py      #   Sends text to Gemma 4 → gets knowledge triples
│   └── curriculum_agent.py      #   Sends triples → gets structured curriculum
│
├── database/                    # PostgreSQL storage
│   ├── connection.py            #   SQLAlchemy engine + session factory
│   └── models.py                #   SQLAlchemy ORM tables (articles, triples, curricula)
│
└── api/                         # REST API (Phase 4)
    ├── main.py                  #   FastAPI app setup + CORS + startup
    ├── routes/
    │   ├── curricula.py         #   GET /curricula, GET /curricula/{id}, POST /generate
    │   └── knowledge.py         #   GET /articles, GET /triples (with filters)
    └── schemas/
        └── responses.py         #   Pydantic response models (API output format)
```

---

## Common Issues

| Problem | Solution |
|---------|----------|
| `Connection refused` on port 8000 | Run `venv\Scripts\uvicorn api.main:app --reload --port 8000` |
| `Connection refused` on port 5432 | Run `docker-compose up -d postgres` |
| `model "gemma4:26b" not found` | Run `ollama pull gemma4:26b` |
| `No module named 'fastapi'` | Run `pip install -r requirements.txt` |
| `curl` not working in PowerShell | Use `curl.exe` instead of `curl` |
| Empty database | Run `python main.py` to populate data |