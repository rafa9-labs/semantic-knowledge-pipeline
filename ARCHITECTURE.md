# 🏗️ Semantic Knowledge Pipeline — Architecture Deep Dive

## Table of Contents
1. [The Big Picture: What Are We Building?](#the-big-picture)
2. [How Data Flows Through the System](#how-data-flows)
3. [Technology Stack Explained](#technology-stack)
4. [How Each Phase Works (Code Walkthrough)](#phase-walkthrough)
5. [The Knowledge Graph Concept](#knowledge-graph)
6. [Why This Stack? (Alternatives Considered)](#why-this-stack)

---

<a id="the-big-picture"></a>
## 1. The Big Picture: What Are We Building?

We're building an **AI-Powered Educational Knowledge Graph** — a system that:

1. **Scrapes** educational content from the web (MDN, documentation sites)
2. **Extracts** knowledge as structured facts (triples: subject → predicate → object)
3. **Generates** structured curricula from those facts using AI
4. **Serves** everything through a REST API

Think of it as an automated curriculum designer: you give it a topic, and it reads documentation, understands the concepts, figures out how they relate to each other, and creates a step-by-step learning path.

### The Key Insight: Knowledge Graphs

A **knowledge graph** is a way of storing information as a network of connected facts. Instead of storing "JavaScript async/await is used to handle promises" as plain text, we store it as:

```
"async/await" ──handles──▶ "Promises"
```

This structured format lets us:
- **Query** specific relationships ("What does await enable?")
- **Find connections** ("What concepts depend on Promises?")
- **Build learning paths** ("To learn async/await, you first need to understand Promises")

---

<a id="how-data-flows"></a>
## 2. How Data Flows Through the System

```
                    ┌─────────────────────────────────────────────┐
                    │           THE PIPELINE (main.py)            │
                    │                                             │
  Raw URLs    ──▶   │  Phase 1: SCRAPE                           │
  (MDN docs)       │  ┌──────────┐    ┌──────────┐    ┌───────┐ │
                    │  │Playwright│───▶│ Pydantic │───▶│PostgrSQL│ │
                    │  │(browser) │    │(validate)│    │ (save) │ │
                    │  └──────────┘    └──────────┘    └───────┘ │
                    │        │                                  │
                    │        ▼ raw text                         │
                    │  Phase 2: EXTRACT                         │
                    │  ┌──────────┐    ┌──────────┐    ┌──────┐│
                    │  │Chunker   │───▶│ Gemma 4  │───▶│Filter││
                    │  │(split)   │    │(LLM)     │    │(clean)││
                    │  └──────────┘    └──────────┘    └──────┘│
                    │        │                                  │
                    │        ▼ clean triples + articles         │
                    │  Phase 3: GENERATE                        │
                    │  ┌──────────┐    ┌──────────┐    ┌───────┐ │
                    │  │Curriculum│───▶│ Pydantic │───▶│PostgrSQL│ │
                    │  │Agent     │    │(validate)│    │(save)  │ │
                    │  └──────────┘    └──────────┘    └───────┘ │
                    └─────────────────────────────────────────────┘
                                      │
                                      ▼
                    ┌─────────────────────────────────────────────┐
                    │           THE API (api/main.py)             │
                    │                                             │
                    │  ┌──────────┐    ┌──────────────────────┐  │
                    │  │ FastAPI  │───▶│ JSON HTTP responses  │  │
                    │  │ +Uvicorn │    │ /api/curricula       │  │
                    │  └──────────┘    │ /api/articles        │  │
                    │                  │ /api/triples         │  │
                    │                  └──────────────────────┘  │
                    └─────────────────────────────────────────────┘
```

---

<a id="technology-stack"></a>
## 3. Technology Stack Explained

### 🐳 Docker — "The Shipping Container for Software"

**What it is:** Docker packages software into isolated, reproducible environments called **containers**. Think of it like a shipping container — it doesn't matter what's inside, any ship (computer) can transport it.

**Why we use it:** We need PostgreSQL (a database server). Instead of installing PostgreSQL directly on your Windows machine (which involves installers, configuration, system services), we run it in a Docker container. One command: `docker-compose up -d` and the database is ready.

**Our setup (`docker-compose.yml`):**
```yaml
services:
  postgres:
    image: postgres:16          # Use PostgreSQL version 16
    ports:
      - "5432:5432"             # Expose on localhost:5432
    environment:
      POSTGRES_USER: forex_admin
      POSTGRES_PASSWORD: changeme_secure_password
      POSTGRES_DB: forex_ml
    volumes:
      - postgres_data:/var/lib/postgresql/data  # Persist data
```

**What this means:**
- `image: postgres:16` — Download the official PostgreSQL 16 image from Docker Hub
- `ports: "5432:5432"` — Map container port 5432 to your machine's port 5432
- `volumes:` — Store database files on your machine so data survives container restarts
- `environment:` — Set credentials (these match our `.env` file)

**Without Docker**, you'd need to:
1. Download the PostgreSQL installer for Windows
2. Run the installer, configure ports and users
3. Set up the Windows service
4. Configure authentication
5. Pray it works

**With Docker**: `docker-compose up -d`. Done.

---

### 🎭 Playwright — "The Robot Browser"

**What it is:** Playwright is a browser automation library. It opens a real browser (Chromium) programmatically, navigates to web pages, and extracts content — just like a human would, but automated.

**Why we use it:** MDN's documentation pages use JavaScript rendering. A simple `requests.get(url)` would only get the raw HTML before JavaScript runs. Playwright waits for the page to fully render, then extracts the visible text.

**How it works in our project:**
```
1. Launch a headless Chromium browser (no GUI, runs in background)
2. Navigate to https://developer.mozilla.org/en-US/docs/Web/JavaScript/...
3. Wait for the page to fully load (JavaScript executed, CSS applied)
4. Extract the main article text using CSS selectors
5. Return the clean text content
```

**Our code (`scraper/base_scraper.py`):**
```python
# asyncplaywright is the async version — it doesn't block while waiting
# for pages to load. We can scrape multiple pages concurrently.
async with async_playwright() as p:
    browser = await p.chromium.launch(headless=True)
    page = await browser.new_page()
    await page.goto(url)
    text = await page.locator("article").inner_text()
```

**Why `headless=True`?** No visible browser window opens. The browser runs invisibly in memory — faster, uses less resources, works on servers without displays.

**Why async?** Web scraping is I/O-bound — most time is spent waiting for network responses. With async, while one page is loading, we can start loading another. This is **concurrency without threads** — much more efficient.

---

### 🛡️ Pydantic — "The Data Bouncer"

**What it is:** Pydantic is a data validation library. It enforces that data matches a strict schema — types, constraints, required fields. If data doesn't match, it raises a clear error.

**Why we use it:** Data flows through our pipeline in stages: scraper → LLM → database → API. At EVERY stage, Pydantic acts as a checkpoint that validates the data is correct before passing it on. This prevents garbage from propagating.

**Real example from our project (`models/content.py`):**
```python
class ScrapedContent(BaseModel):
    title: str                          # MUST be a string
    url: HttpUrl                        # MUST be a valid URL (https://...)
    raw_text: str                       # MUST be a string
    source_site: str                    # MUST be a string
    
    @validator('raw_text')
    def text_must_not_be_empty(cls, v):
        if len(v.strip()) < 50:         # MUST have at least 50 chars
            raise ValueError("Scraped text too short — page may have failed to load")
        return v
```

**What happens if we pass bad data:**
```python
# This works ✅
ScrapedContent(title="Promise", url="https://mdn.org/Promise", raw_text="Long text...", source_site="mdn")

# This fails ❌ — invalid URL
ScrapedContent(title="Promise", url="not-a-url", raw_text="Long text...", source_site="mdn")
# → ValidationError: url – invalid or missing URL scheme

# This fails ❌ — text too short (page probably didn't load)
ScrapedContent(title="Promise", url="https://mdn.org/Promise", raw_text="Hi", source_site="mdn")
# → ValidationError: text must have at least 50 characters
```

**We use Pydantic at 4 points in our pipeline:**
1. **After scraping** — validate scraped data is real content, not error pages
2. **After LLM extraction** — validate the AI didn't hallucinate garbage triples
3. **After curriculum generation** — validate the AI produced a valid curriculum structure
4. **API responses** — validate the JSON we send to users matches our documented schema

---

### 🐘 PostgreSQL — "The Data Vault"

**What it is:** PostgreSQL is a powerful, open-source relational database. It stores structured data in **tables** (like spreadsheets) with **relationships** between them.

**Why we use it:** We have structured, relational data:
- Articles have triples extracted from them
- Curricula have modules, modules have lessons
- Lessons reference source articles

PostgreSQL handles these relationships natively with **foreign keys** and **SQL joins**.

**Our database schema:**
```
┌──────────────┐       ┌──────────────────┐
│ raw_articles │       │ knowledge_triples│
├──────────────┤       ├──────────────────┤
│ id (PK)      │◀──────│ source_url       │
│ title        │       │ id (PK)          │
│ url          │       │ subject          │
│ raw_text     │       │ predicate        │
│ source_site  │       │ object_value     │
│ scraped_at   │       │ confidence       │
└──────────────┘       └──────────────────┘

┌──────────────┐       ┌──────────────┐       ┌──────────────┐
│ curricula    │       │ modules      │       │ lessons      │
├──────────────┤       ├──────────────┤       ├──────────────┤
│ id (PK)      │◀──────│ curriculum_id│◀──────│ module_id    │
│ title        │       │ id (PK)      │       │ id (PK)      │
│ topic        │       │ title        │       │ title        │
│ difficulty   │       │ order_index  │       │ objectives   │
│ model_name   │       └──────────────┘       │ prereqs      │
└──────────────┘                              │ source_urls  │
                                              └──────────────┘
```

**Why not just use JSON files?**
- **Querying**: "Find all triples about 'await'" — SQL: `SELECT * FROM knowledge_triples WHERE subject ILIKE '%await%'`
- **Relationships**: "Get all lessons for curriculum #2" — SQL joins handle this
- **Durability**: If the server crashes, PostgreSQL recovers data. JSON files can corrupt.
- **Concurrency**: Multiple API requests can read/write simultaneously safely

---

### 🔧 SQLAlchemy — "The Python-SQL Translator"

**What it is:** SQLAlchemy is an ORM (Object-Relational Mapper). It lets you define database tables as Python classes and query them using Python methods instead of writing raw SQL strings.

**Why we use it:** Writing raw SQL is error-prone (typos, SQL injection, different SQL dialects). SQLAlchemy gives us:
- **Python classes** for database tables
- **Python methods** for queries
- **Automatic SQL generation** — works with PostgreSQL, MySQL, SQLite, etc.

**Example — defining a table (`database/models.py`):**
```python
class RawArticle(Base):
    __tablename__ = 'raw_articles'    # The SQL table name
    
    id = Column(Integer, primary_key=True)       # id INTEGER PRIMARY KEY
    title = Column(String, nullable=False)        # title VARCHAR NOT NULL
    url = Column(String, nullable=False, unique=True)  # url VARCHAR UNIQUE
    raw_text = Column(Text, nullable=False)       # raw_text TEXT NOT NULL
    source_site = Column(String)                  # source_site VARCHAR
    scraped_at = Column(DateTime, default=datetime.utcnow)  # auto-timestamp
```

**Example — querying (instead of raw SQL):**
```python
# Raw SQL way (dangerous — SQL injection risk):
cursor.execute("SELECT * FROM raw_articles WHERE source_site = '" + site + "'")

# SQLAlchemy way (safe — parameterized automatically):
articles = session.query(RawArticle).filter_by(source_site="mdn").all()
```

**The `relationship()` feature:**
```python
class CurriculumDB(Base):
    modules = relationship("ModuleDB", back_populates="curriculum", cascade="all, delete")

# Now you can do:
curriculum.modules    # → Returns all modules for this curriculum
module.curriculum     # → Returns the parent curriculum
```

SQLAlchemy automatically handles the SQL JOINs behind the scenes.

---

### 🧠 LangChain — "The LLM Orchestrator"

**What it is:** LangChain is a framework for building applications powered by Large Language Models (LLMs). It provides a universal interface to talk to ANY LLM — OpenAI, Ollama, Anthropic, etc.

**Why we use it:** We need to send text to an LLM and get structured JSON back. Without LangChain, we'd need to:
1. Format the prompt manually
2. Make the HTTP request to the LLM API
3. Parse the JSON response
4. Handle errors, retries, rate limits

LangChain handles all of this with a clean, consistent interface.

**How we use it — Triple Extraction (`pipeline/triple_extractor.py`):**
```python
from langchain_ollama import OllamaLLM
from langchain_core.prompts import PromptTemplate

# Step 1: Connect to our local LLM
llm = OllamaLLM(model="gemma4:26b", temperature=0.1)

# Step 2: Define a prompt template with variables
prompt = PromptTemplate.from_template("""
Extract knowledge triples from this text.
Text: {article_text}
Format: JSON array of {subject, predicate, object} objects.
""")

# Step 3: Create a chain (prompt → LLM → output)
chain = prompt | llm

# Step 4: Run the chain
result = chain.invoke({"article_text": "The await keyword can only be used inside async functions..."})
# → [{"subject": "await keyword", "predicate": "is_only_valid_in", "object": "async functions"}]
```

**The key concept: `prompt | llm` (the pipe operator)**

LangChain uses Python's pipe operator to create **chains**:
```
prompt | llm | parser
  │       │      │
  │       │      └─ Parse the LLM's text output into Python objects
  │       └─ Send the formatted prompt to the LLM
  └─ Fill in the template variables
```

This is why it's called "Lang**Chain**" — you chain components together.

---

### 🦙 Ollama — "The Local AI Server"

**What it is:** Ollama runs large language models (LLMs) locally on your machine. Think of it as "ChatGPT, but running on your own hardware, with no API costs."

**Why we use it:** 
- **Free** — no API costs (OpenAI would charge ~$0.01-0.05 per pipeline run)
- **Private** — no data leaves your machine
- **Fast** — no network latency to external APIs
- **Offline** — works without internet

**Our model: `gemma4:26b`**
- Made by Google
- "26b" = 26 billion parameters (the size of the neural network)
- Runs locally via Ollama
- Good at following structured output instructions (JSON)

**How Ollama fits in:**
```
Our Python code
    │
    ▼
LangChain (formats prompt, handles response)
    │
    ▼
Ollama Python client (HTTP request to localhost:11434)
    │
    ▼
Ollama server (manages the model, GPU/CPU allocation)
    │
    ▼
Gemma 4 26B (the actual neural network, ~16GB of RAM)
    │
    ▼
Generated text (our knowledge triples or curriculum)
```

---

### ⚡ FastAPI — "The API Framework"

**What it is:** FastAPI is a modern Python web framework for building REST APIs. It's called "Fast" because it's one of the fastest Python frameworks (built on Starlette and Pydantic).

**Why we use it:**
- **Auto-documentation** — creates Swagger UI (/docs) automatically from your code
- **Type validation** — uses Pydantic to validate incoming requests and outgoing responses
- **Async support** — handles thousands of concurrent requests efficiently
- **Developer experience** — excellent error messages, autocomplete in IDEs

**How a FastAPI endpoint works:**
```python
@router.get("/api/triples", response_model=TripleListResponse)
def list_triples(
    skip: int = Query(0, ge=0),        # URL parameter: ?skip=0 (must be ≥ 0)
    limit: int = Query(100, ge=1, le=500),  # URL parameter: ?limit=100 (1-500)
    subject: str = Query(None),         # Optional filter: ?subject=await
):
    # 1. FastAPI validates the query parameters (types, constraints)
    # 2. We query the database
    # 3. We return a Pydantic model
    # 4. FastAPI validates the response matches TripleListResponse
    # 5. FastAPI serializes to JSON and sends HTTP response
    return TripleListResponse(total=15, triples=[...])
```

**What FastAPI does automatically:**
1. **Request validation**: If someone sends `?skip=abc`, FastAPI returns `422 Unprocessable Entity` with a clear error: "skip must be an integer"
2. **Response validation**: If our code returns bad data, FastAPI catches it before sending to the user
3. **Documentation**: The `response_model=TripleListResponse` tells FastAPI to generate a schema in Swagger UI
4. **Serialization**: Pydantic models are automatically converted to JSON

---

### 🚀 Uvicorn — "The HTTP Server"

**What it is:** Uvicorn is an **ASGI** (Asynchronous Server Gateway Interface) server. It's the program that actually listens for HTTP requests and passes them to FastAPI.

**Why it's needed:** FastAPI is a framework, not a server. It defines HOW to handle requests, but it needs a server to actually receive them. Uvicorn is that server.

**Analogy:**
- **FastAPI** = the restaurant kitchen (prepares the food)
- **Uvicorn** = the waiter (receives orders, delivers food)
- **HTTP request** = a customer's order
- **HTTP response** = the prepared dish

**Why ASGI, not WSGI?**
- **WSGI** (old): One request at a time (Flask, Django)
- **ASGI** (new): Thousands of concurrent requests via async/await (FastAPI, Starlette)

Our API is synchronous right now, but ASGI means we can add async endpoints later without changing the server.

---

### 🔗 REST API — "The Communication Protocol"

**What it is:** REST (Representational State Transfer) is a convention for how web APIs should work. It maps HTTP methods to database operations:

| HTTP Method | URL Pattern | Action | Database Equivalent |
|-------------|-------------|--------|---------------------|
| `GET` | `/api/curricula` | List all | `SELECT * FROM curricula` |
| `GET` | `/api/curricula/2` | Get one | `SELECT * FROM curricula WHERE id=2` |
| `POST` | `/api/curricula/generate` | Create one | `INSERT INTO curricula ...` |
| `PUT` | `/api/curricula/2` | Update one | `UPDATE curricula SET ... WHERE id=2` |
| `DELETE` | `/api/curricula/2` | Delete one | `DELETE FROM curricula WHERE id=2` |

**HTTP Status Codes we use:**
- `200 OK` — Success, here's your data
- `404 Not Found` — That curriculum doesn't exist
- `422 Unprocessable Entity` — Your request had invalid parameters
- `500 Internal Server Error` — Something broke on our server (LLM failure, etc.)

---

<a id="phase-walkthrough"></a>
## 4. How Each Phase Works (Code Walkthrough)

### Phase 1: Scraping (`main.py` → `scraper/`)

```python
# What happens when you run: python main.py

# 1. Define URLs to scrape
urls = [
    "https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Statements/async_function",
    "https://developer.mozilla.org/en-US/docs/Web/API/Fetch_API/Using_Fetch",
    "https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Promise",
    "https://developer.mozilla.org/en-US/docs/Web/JavaScript/Guide/Using_promises",
    "https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Statements/for...of",
]

# 2. Create scraper and run
scraper = MDNScraper()
results = scraper.scrape_urls(urls)    # ← Opens browser, visits each URL

# 3. Each result is validated by Pydantic
for result in results:
    validated = ScrapedContent(**result)   # ← Pydantic checks it's valid
    store_in_database(validated)           # ← SQLAlchemy saves to PostgreSQL
```

**What Playwright does step-by-step:**
```
1. Downloads and launches Chromium browser (headless=True, no window)
2. Opens a new page
3. Navigates to the MDN URL
4. Waits for the page to fully load (JavaScript executes, content renders)
5. Finds the <article> element using a CSS selector
6. Extracts the innerText (visible text content)
7. Returns: {"title": "async function", "url": "...", "raw_text": "...", "source_site": "mdn"}
8. Closes the page (memory cleanup)
```

---

### Phase 2: Knowledge Extraction (`pipeline/triple_extractor.py`)

This is where the AI reads each article and extracts structured facts.

```
Input:  "The await keyword can only be used inside async functions..."
                │
                ▼
        ┌───────────────┐
        │  Text Chunker  │   Splits 7716-char article into smaller pieces
        │  (1000 chars)  │   (LLMs have context limits — can't read everything at once)
        └───────┬───────┘
                │ chunk 1, chunk 2, ...
                ▼
        ┌───────────────┐
        │   LangChain   │   Formats each chunk into a prompt:
        │   Prompt      │   "Extract knowledge triples from: {chunk}"
        └───────┬───────┘
                │ formatted prompt
                ▼
        ┌───────────────┐
        │   Ollama      │   Sends prompt to Gemma 4 (running locally)
        │   + Gemma 4   │   The LLM reads the text and outputs JSON triples
        └───────┬───────┘
                │ raw JSON string
                ▼
        ┌───────────────┐
        │   Pydantic    │   Validates each triple:
        │   Knowledge   │     - subject: str (not empty)
        │   Triple      │     - predicate: str (not empty)
        │               │     - object: str (not empty)
        │               │     - confidence: 0.0 to 1.0
        └───────┬───────┘
                │ validated triples
                ▼
        ┌───────────────┐
        │  PostgreSQL   │   Stores: "await keyword" → "is_only_valid_in" → "async functions"
        └───────────────┘
```

**Why we chunk the text:** LLMs have a maximum input size (context window). Gemma 4 26B can read ~128K tokens, but performance degrades with very long inputs. Chunking into ~1000-character pieces gives the LLM focused, manageable sections.

---

### Phase 2.5: Triple Quality Filtering (`pipeline/triple_filter.py`)

After extraction, we run all triples through a **rule-based quality filter** before saving to the database. This catches hallucinations that Pydantic can't (Pydantic validates structure, not semantics).

**The Problem:** The LLM sometimes produces garbage triples from MDN navigation menus, code syntax, or table-of-contents:
```
(":", ":", ":")           ← punctuation, not concepts
(":", ":", ",")           ← same issue
("async function", "is_a", "async function") ← circular
("a", "is_a", "thing")    ← too short to be meaningful
```

**The Solution:** 6 independent rule-based filters (no LLM needed — fast & free):

```
Raw triples from LLM
        │
        ▼
  ┌─────────────────┐
  │ Rule 1: Punct   │ ← Reject ":" "," "()" as field values
  │ Rule 2: Alpha   │ ← Require ≥2 alphabetic chars per field
  │ Rule 3: Words   │ ← Require ≥1 real word in subject/object
  │ Rule 4: Circular│ ← Reject if subject ≈ object (Jaccard similarity)
  │ Rule 5: Predicate│ ← Predicate must be a real word, not a symbol
  │ Rule 6: Artifacts│ ← Catch code syntax, all-short-fields, etc.
  └────────┬────────┘
           │
     ┌─────┴─────┐
     │            │
  ACCEPTED     REJECTED (logged with reason)
     │
     ▼
  Quality Score (0.0-1.0) assigned to each surviving triple
     │
     ▼
  PostgreSQL (only clean, high-quality triples)
```

**Why not use the LLM to filter?**
- **Speed**: regex checks take microseconds; LLM calls take seconds
- **Cost**: free vs. LLM API costs
- **Reliability**: deterministic rules can't hallucinate

**DB Cleanup Tool:** `scripts/cleanup_triples.py` retroactively applies these filters to existing triples in the database (dry-run by default, `--live` to actually delete).

---

### Phase 3: Curriculum Generation (`pipeline/curriculum_agent.py`)

This is where the AI designs a learning path.

```
Input:  15 knowledge triples + 6 articles
                │
                ▼
        ┌───────────────┐
        │   LangChain   │   Formats a detailed prompt:
        │   Prompt      │   "Design a curriculum about {topic}.
        │               │    Here are the knowledge triples: {triples}
        │               │    Here are the articles: {articles}
        │               │    Target audience: {audience}
        │               │    Difficulty: {difficulty}
        │               │    Output as JSON with modules and lessons."
        └───────┬───────┘
                │
                ▼
        ┌───────────────┐
        │   Ollama      │   Gemma 4 generates a complete curriculum:
        │   + Gemma 4   │
        │   (26B model) │   {
        └───────┬───────┘     "title": "Mastering Async JavaScript",
                │              "modules": [
                ▼                { "title": "The Foundation: Promises",
        ┌───────────────┐         "lessons": [
        │   Pydantic    │           { "title": "Introduction to Promises",
        │   Curriculum  │             "objectives": [...],
        │   Model       │             "prerequisites": [] }
        │               │         ]
        │   Validates:  │       },
        │   - 1-5 mods  │       { "title": "Modern Syntax: Async/Await", ... },
        │   - 1-5 lessns│       { "title": "Practical Implementation", ... }
        │   - objectives│     ]
        │   - prereqs   │   }
        │   - sources   │
        └───────┬───────┘
                │ validated curriculum
                ▼
        ┌───────────────────────────────────┐
        │   PostgreSQL (3 tables)            │
        │   curricula: 1 row (the curriculum)│
        │   modules:   3 rows (the modules)  │
        │   lessons:   6 rows (the lessons)  │
        └───────────────────────────────────┘
```

**The Pydantic validation is critical here.** The LLM might:
- Generate 10 modules (too many!) → Pydantic rejects: `max_length=5`
- Forget to include prerequisites → Pydantic rejects: `required field`
- Add a lesson with no source URL → Pydantic rejects: `min_length=1`

If validation fails, the agent **retries** (up to 3 times) with a different prompt asking the LLM to fix its mistakes.

---

<a id="knowledge-graph"></a>
## 5. The Knowledge Graph Concept

### What is a Knowledge Triple?

A triple is the atomic unit of a knowledge graph — a single fact expressed as three parts:

```
Subject  ──Predicate──▶  Object
(what)      (how)        (to what)
```

**Examples from our database:**
| Subject | Predicate | Object |
|---------|-----------|--------|
| await keyword | enables | asynchronous, promise-based behavior |
| async function | returns | a new Promise |
| await keyword | is_only_valid_in | async function body |
| fetch() | performs | HTTP requests |
| Promise | represents | eventual completion or failure |

### Why Triples Are Powerful

From these simple triples, we can derive a **learning dependency graph**:

```
Promise ──────────────────────────────────┐
  │                                        │
  ▼                                        │
"async function returns a Promise"         │
  │                                        │
  ▼                                        │
await keyword (needs async function) ──────┘
  │
  ▼
fetch() + await (practical usage)
```

This tells us: "To learn about await, you first need to understand Promises and async functions." That's exactly how the AI builds the curriculum!

---

<a id="why-this-stack"></a>
## 6. Why This Stack? (Alternatives Considered)

| Our Choice | Alternative | Why We Chose Ours |
|------------|------------|-------------------|
| **Playwright** | BeautifulSoup, Scrapy | MDN uses JS rendering; Playwright waits for full page load |
| **Pydantic** | Manual validation, Marshmallow | FastAPI uses it natively; best Python validation library |
| **PostgreSQL** | SQLite, MongoDB | We have relational data; PostgreSQL is production-grade |
| **SQLAlchemy** | Raw SQL, Django ORM | Most flexible ORM; works with any database |
| **LangChain** | Raw HTTP requests | Handles prompts, parsing, retries, model switching |
| **Ollama/Gemma** | OpenAI API | Free, private, offline, no rate limits |
| **FastAPI** | Flask, Django | Auto-docs, async, Pydantic integration, fastest Python framework |
| **Docker** | Local install | One command setup; reproducible across machines |

### Cost Analysis

| Component | Cost |
|-----------|------|
| PostgreSQL (Docker) | Free (open source) |
| Ollama + Gemma 4 26B | Free (local, no API calls) |
| Playwright | Free (open source) |
| All Python libraries | Free (open source) |
| **Total** | **$0** |

The equivalent using OpenAI's API would cost ~$0.05-0.50 per pipeline run, depending on article count and curriculum complexity.

---

## Summary: The Complete Flow in Plain English

1. **Docker** starts our PostgreSQL database — a structured storage system for all our data
2. **Playwright** opens a hidden browser, visits MDN documentation pages, and copies the text content
3. **Pydantic** checks that the scraped text is real content (not empty or error pages)
4. **SQLAlchemy** saves the validated articles to **PostgreSQL** tables
5. The articles are split into chunks (the **Text Chunker**) because the AI can't read everything at once
6. **LangChain** formats each chunk into a prompt and sends it to **Ollama**, which runs **Gemma 4** (our local AI)
7. The AI reads each chunk and outputs knowledge triples — structured facts like `"await" → "enables" → "async behavior"`
8. **Pydantic** validates each triple is well-formed (structure)
9. **TripleFilter** removes hallucinations and garbage (semantics) — punctuation-only triples, circular triples, and other LLM artifacts are caught by 6 rule-based filters
10. Only clean, high-quality triples are saved to **PostgreSQL**
11. All triples + articles are sent back to the AI via **LangChain** with a curriculum design prompt
10. The AI generates a complete curriculum with modules and lessons
11. **Pydantic** validates the curriculum structure (correct number of modules, required fields, etc.)
12. **SQLAlchemy** saves the curriculum to **PostgreSQL** (3 tables: curricula, modules, lessons)
13. **FastAPI** + **Uvicorn** start a web server that serves all this data as JSON REST endpoints
14. **Swagger UI** auto-generates an interactive documentation page where anyone can explore the API
15. Any frontend (React, Streamlit, mobile app) can call our API to display the data

**Total cost: $0. Total cloud dependencies: 0. Everything runs on your machine.**