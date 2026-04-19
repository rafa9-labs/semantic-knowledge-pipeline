# Semantic Knowledge Pipeline — Run Commands & Expected Output

## Prerequisites

### 1. Start Docker Services

```bash
docker compose up -d
```

**Expected output:**
```
[+] Running 4/4
 ✔ Network skp_default          Created
 ✔ Container skp-db             Started  (healthy)
 ✔ Container skp-weaviate       Started  (healthy)
 ✔ Container skp-pgadmin        Started
```

**Verify:**
```bash
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
```
All 4 containers should show `Up` and `healthy` status.

### 2. Ollama Models Required

```bash
# Worker model (JSON output tasks — 6.1 GB)
ollama pull qwen3.5:9b

# Brain model (reasoning tasks — 16.2 GB)
ollama pull qwen3.5:27b

# Embedding model (0.3 GB)
ollama pull nomic-embed-text
```

**Verify:**
```bash
ollama list
```
Should show: `qwen3.5:9b`, `qwen3.5:27b`, `nomic-embed-text`

### 3. Python Environment

```bash
# Activate virtual environment
.\venv\Scripts\Activate.ps1
```

---

## Phase Tests

### Test Phase 9C-3 (Examples + Exercises)

```bash
python test_phase9c3.py
```

**Expected output (7/7 PASS):**
```
============================================================
PHASE 9C-3: EXAMPLES + EXERCISES — VERIFICATION
============================================================

--- Test 1: ExampleGenerator Initialization ---
  OK: ExampleGenerator initialized (model=qwen3.5:9b)

--- Test 2: ExerciseGenerator Initialization ---
  OK: ExerciseGenerator initialized (model=qwen3.5:9b)

--- Test 3: GeneratedExample Validation ---
  OK: Valid example accepted
  OK: Invalid language rejected
  OK: Short title rejected
  OK: Short code rejected
  OK: All example validation tests passed

--- Test 4: GeneratedExercise Validation ---
  OK: Valid exercise accepted
  OK: Invalid difficulty rejected
  OK: Short description rejected
  OK: All exercise validation tests passed

--- Test 5: Database State ---
  Total concepts: 176
  ...

--- Test 6: Single Concept Example Generation (requires Ollama) ---
  Concept: <concept_name>
  Examples generated: 3
    [python] <title>
    ...

--- Test 7: Single Concept Exercise Generation (requires Ollama) ---
  ...

============================================================
RESULTS SUMMARY
============================================================
  PASS: ExampleGenerator Init
  PASS: ExerciseGenerator Init
  PASS: Example Validation
  PASS: Exercise Validation
  PASS: Database State
  PASS: Single Example Gen
  PASS: Single Exercise Gen

  7/7 tests passed
============================================================
```

**Run time:** ~1-3 minutes (tests 6-7 each make one LLM call).

### Test Phase 9C-2 (ELI5 + Relationships)

```bash
python test_phase9c2.py
```

**Expected:** 7/7 tests passed. Run time: ~1-3 minutes.

### Test Phase 9C-1 (Concept Extraction)

```bash
python test_phase9c1.py
```

### Test Phase 9B (Embeddings)

```bash
python test_phase9b.py
```

---

## Enrichment Pipeline Commands

### Dry Run (Preview, No LLM Calls)

```bash
python enrich_examples.py --dry-run
python enrich_exercises.py --dry-run
```

**Expected output:**
```
[DRY RUN] Would process 176 concepts:
  - emulate_media (api, difficulty 3)
  - Conditional Execution (fundamentals, difficulty 2)
  ...
```

### Smoke Test (5 Concepts, ~3-5 Minutes)

```bash
python enrich_examples.py --limit 5
python enrich_exercises.py --limit 5
```

**Expected output (examples):**
```
Generating examples for all eligible concepts...
05:29:04 [INFO] Generated 3/3 valid examples for 'Conditional Execution' (attempt 1)
05:29:04 [INFO] [2/5] 'Conditional Execution': 3 examples OK
...

============================================================
EXAMPLE GENERATION RESULTS
============================================================
  Total concepts in DB:    176
  Concepts processed:      5
  Examples generated:      9
  Concepts completed:      3
  Concepts failed:         2
  Skipped (already had):   171
============================================================
```

**Note:** Some failures (JSON parse errors) are expected. The retry mechanism handles most cases. Success rate is typically 60-80%.

### Single Concept

```bash
python enrich_examples.py --concept 42
python enrich_exercises.py --concept 42
```

**Expected:** Generates 2-3 examples or 1-2 exercises for one concept, takes ~10-20 seconds.

### Full Batch Generation

```bash
python enrich_examples.py              # ~45-90 min for 176 concepts
python enrich_exercises.py             # ~50-100 min for 176 concepts
```

**Expected output (examples, end of run):**
```
============================================================
EXAMPLE GENERATION COMPLETE
============================================================
Examples generated: 350+
Concepts completed: 120+
Concepts failed:    30-50
Skipped (already had): 0
============================================================
```

**Note:** Run is idempotent — re-running skips concepts that already have content.

### Force Regenerate All

```bash
python enrich_examples.py --force
python enrich_exercises.py --force
```

Regenerates examples/exercises for ALL concepts, including those that already have them.

### ELI5 Generation (Phase 9C-2)

```bash
python enrich_eli5.py                  # Generate for concepts missing ELI5
python enrich_eli5.py --force          # Regenerate ALL ELI5s
python enrich_eli5.py --concept 42     # Single concept
```

### Relationship Extraction (Phase 9C-2)

```bash
python enrich_relationships.py                 # Extract for all topics
python enrich_relationships.py --topic 3       # Single topic
python enrich_relationships.py --dry-run       # Preview only
```

### Concept Extraction (Phase 9C-1)

```bash
python enrich_concepts.py               # Extract for all topics
python enrich_concepts.py --topic 3     # Single topic
python enrich_concepts.py --dry-run     # Preview only
```

---

## Scraping Commands

### Scrape All Sources

```bash
python scrape_all.py
```

**Expected:** Scrapes 16+ documentation sources (Python docs, FastAPI, SQLAlchemy, Pydantic, Docker, Weaviate, LangChain, Playwright, etc.). Run time: 5-30 minutes depending on sources.

---

## Database Commands

### Run Migrations

```bash
alembic upgrade head
```

### Seed Initial Data

```bash
python database/seed_data.py
```

### Check Database State

```bash
python -c "
from database.connection import SessionLocal
from database.models import Topic, Concept, ConceptRelationship, Example, Exercise

with SessionLocal() as s:
    print(f'Topics:                    {s.query(Topic).count()}')
    print(f'Concepts:                  {s.query(Concept).count()}')
    print(f'Concepts with ELI5:        {s.query(Concept).filter(Concept.simple_explanation.isnot(None)).count()}')
    print(f'Relationships:             {s.query(ConceptRelationship).count()}')
    print(f'Examples:                  {s.query(Example).count()}')
    print(f'Exercises:                 {s.query(Exercise).count()}')
"
```

**Expected output:**
```
Topics:                    23
Concepts:                  176
Concepts with ELI5:        176
Relationships:             32
Examples:                  <varies>
Exercises:                 <varies>
```

### pgAdmin Web UI

Open `http://localhost:5050` in browser.
- **Login:** admin@skp.dev / admin
- **Add server:** Host: `db`, Port: `5432`, User: `skp_admin`, Password: `skp_dev_password`, DB: `knowledge_graph`

---

## API Server

### Start API

```bash
python main.py
# or
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
```

### Test Endpoints

```bash
# Health check
curl http://localhost:8000/health

# List topics
curl http://localhost:8000/api/topics

# Search concepts
curl "http://localhost:8000/api/search?q=async"
```

---

## Docker Management

```bash
# Start all services
docker compose up -d

# Stop all services
docker compose down

# Stop and remove volumes (DESTROYS database data!)
docker compose down -v

# View logs
docker compose logs -f db          # PostgreSQL logs
docker compose logs -f weaviate    # Weaviate logs

# Restart a single service
docker compose restart db
```

---

## Ollama Management

```bash
# List installed models
ollama list

# Pull a model
ollama pull qwen3.5:9b

# Remove a model
ollama rm <model_name>

# Check running models (GPU usage)
ollama ps
```

---

## Architecture Overview

```
Fast-Slow LLM Architecture (RTX 3090, 24GB VRAM):

  BRAIN (reasoning)              WORKER (JSON output)
  qwen3.5:27b (17GB)             qwen3.5:9b (6.1GB)
  ~35 tok/s                      ~80 tok/s
  ┌──────────────────┐           ┌──────────────────┐
  │ Concept Extractor │           │ ELI5 Generator   │
  │ Relationship Ext. │           │ Example Generator │
  └──────────────────┘           │ Exercise Generator│
                                 └──────────────────┘

  Config: .env
    LLM_BRAIN_MODEL=qwen3.5:27b
    LLM_WORKER_MODEL=qwen3.5:9b

  Embedding: nomic-embed-text (0.3GB, 768 dimensions)
```

```
Data Pipeline Flow:

  Scraping → Parsing → Concepts → ELI5s → Relationships → Examples → Exercises
  (Phase 8) (Phase 8) (9C-1)    (9C-2)  (9C-2)          (9C-3)    (9C-3)
                                     ↓
                               PostgreSQL + Weaviate
                                     ↓
                                  FastAPI
```

---

## Current Database State (as of latest run)

| Table | Count | Status |
|-------|-------|--------|
| Topics | 23 | 17 with concepts, 6 empty |
| Concepts | 176 | All have ELI5 explanations |
| Relationships | 32 | Typed edges across topics |
| Examples | 9+ | Generated via Qwen 3.5 9B |
| Exercises | 2+ | Generated via Qwen 3.5 9B |
