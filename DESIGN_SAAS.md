# DESIGN_SAAS.md — DevKnowledge SaaS Architecture Blueprint

> **Created:** 2026-04-18
> **Domain:** kodastudy.com
> **Status:** Implementation blueprint for SaaS product launch

---

## 1. Product Definition

**Name:** KodaStudy
**Tagline:** "Master any subject through AI-powered knowledge graphs"
**URL:** kodastudy.com

### What Is KodaStudy?

A SaaS learning platform where users learn any subject through structured knowledge graphs,
simple explanations, interactive code examples, and AI tutoring. The platform generates
curricula on-demand using LLMs and presents content through a 3-panel learning interface.

### Target Users

- **Primary:** Junior-to-mid developers, CS students, self-taught programmers
- **Secondary:** Anyone wanting structured learning on academic/technical subjects
- **Use cases:**
  - "I need to learn FastAPI for my new job"
  - "Teach me Python async programming from scratch"
  - "I want to understand how vector databases work"
  - "Generate a curriculum for learning Rust"

---

## 2. Tech Stack

| Layer | Technology | Purpose | Cost |
|-------|-----------|---------|------|
| Frontend | Next.js 15 (App Router) | SSR, pages, auth UI | Free |
| Styling | TailwindCSS + shadcn/ui | Dark theme, components | Free |
| Auth | Supabase Auth | User accounts, JWT, SSO | Free tier |
| Database | Supabase PostgreSQL (shared) | Users, progress, content | Free tier |
| ORM (Next.js) | Prisma | User/progress model access | Free |
| ORM (FastAPI) | SQLAlchemy (existing) | Content/pipeline access | Free |
| Vector DB | pgvector on Supabase | Semantic search | Free |
| Backend API | FastAPI (existing, enhanced) | LLM, scraping, knowledge graph | — |
| LLM (dev) | Ollama + Qwen 3.5 (local) | Development | $0 |
| LLM (prod) | Gemini Flash / DeepSeek API | Production | ~$0.10/1M tokens |
| Payments | Stripe | Subscriptions | 2.9% + $0.30/tx |
| Frontend hosting | Vercel | Next.js deployment | Free tier |
| Backend hosting | Railway | FastAPI + background jobs | ~$5/mo |

---

## 3. Architecture

```
kodastudy.com
│
├── Vercel (Next.js 15)
│   ├── Public pages (SSR): landing, pricing, catalog
│   ├── Dashboard pages (CSR): 3-panel learning interface
│   ├── Supabase Auth: login, signup, session management
│   ├── Stripe: checkout, webhook, subscription management
│   └── API Routes: proxy to FastAPI, Stripe webhooks
│
├── Railway (FastAPI)
│   ├── /api/knowledge/*   — topics, concepts, examples, exercises
│   ├── /api/chat           — RAG AI tutor with citations
│   ├── /api/graph/*        — knowledge graph traversal, learning paths
│   ├── /api/generate/*     — on-demand curriculum generation
│   ├── /ws/jobs/{id}       — WebSocket progress streaming
│   └── Existing pipeline   — scraping, extraction, enrichment
│
└── Supabase (PostgreSQL + Auth)
    ├── Existing tables: domains, topics, concepts, relationships, examples, exercises
    ├── New tables: users, enrollments, progress, generation_jobs
    └── pgvector: semantic search embeddings
```

### Data Flow

```
User Action          Next.js              FastAPI              Database
─────────────────────────────────────────────────────────────────────────
Browse catalog   →   SSR page         →   GET /api/knowledge/topics  →  PostgreSQL
Learn concept    →   Client render    →   GET /api/knowledge/concept →  PostgreSQL
Ask AI tutor     →   API route proxy  →   POST /api/chat            →  Weaviate + LLM
Generate topic   →   API route proxy  →   POST /api/generate        →  Background job
Track progress   →   Prisma direct    →   —                        →  PostgreSQL
Subscribe        →   Stripe Checkout  →   —                        →  Stripe → DB
```

---

## 4. Subscription Tiers

### Free Tier
- Browse all topics and concepts
- Theory content (scraped documentation)
- ELI5 explanations
- View (not interact) knowledge graph
- First 2 concepts of every topic are fully accessible

### Premium Tier ($9.99/month or $79.99/year)
- All free features, plus:
- Full code examples (3+ per concept)
- Interactive exercises with test runner
- AI Tutor chat with citations
- Interactive knowledge graph exploration
- Learning path generation (prerequisite chains)
- On-demand curriculum generation ("Teach me X")
- Progress tracking across all topics

### Paywall Implementation
- `PaywallGate` React component wraps premium content
- Free users see blurred content with upgrade CTA
- FastAPI validates premium status via Supabase JWT
- Premium endpoints return 402 Payment Required for free users

---

## 5. UI Architecture — The 3-Panel Layout

### 5.1 CSS Grid App Shell

```
┌──────────────────────────────────────────────────────────────────┐
│  layout.tsx — h-screen grid grid-cols-[280px_1fr_350px]        │
│                                                                  │
│  ┌──────────┬──────────────────────────┬──────────────┐        │
│  │ 280px    │ 1fr (flexible)          │ 350px        │        │
│  │          │                          │              │        │
│  │ LEFT     │ CENTER (MainCanvas)      │ RIGHT        │        │
│  │          │                          │ (AiTutor)    │        │
│  │ Curric.  │  Tab: Theory | ELI5 |   │              │        │
│  │ Sidebar  │       Examples | Exercise│  Chat msgs   │        │
│  │          │                          │  ...         │        │
│  │ ▸ Topic  │  Content area            │  ...         │        │
│  │   ✓ C1   │  (changes per tab)       │              │        │
│  │   ● C2   │                          │  Input box   │        │
│  │   ○ C3   │  [Graph View] toggle     │              │        │
│  └──────────┴──────────────────────────┴──────────────┘        │
└──────────────────────────────────────────────────────────────────┘
```

### 5.2 Component Architecture

**Server Components (RSC):** Fetch data from Supabase/PostgreSQL directly.
- `CurriculumSidebar` — loads topic hierarchy, wraps client `<CollapsibleTree />`
- Topic layout pages — prefetch topic data

**Client Components:** Interactive, stateful.
- `MainCanvas` — tab router, URL-driven content switching
- `AiTutor` — chat interface, Vercel AI SDK `useChat` hook
- `GenerationTerminal` — WebSocket progress, terminal aesthetic
- `TheoryTab`, `Eli5Tab`, `ExamplesTab`, `ExercisesTab`
- `KnowledgeGraphView` — react-force-graph
- `LearningPathView` — prerequisite chain visualization

### 5.3 State Flow

```
Left sidebar click
  → router.push('/learn/{topic}/{concept}')
  → Center MainCanvas loads concept data
  → conceptId passed to AiTutor via context
  → AiTutor sends chat with concept context
  → FastAPI RAG returns answer with citations
```

---

## 6. Next.js App Router Structure

```
frontend/
├── app/
│   ├── (public)/
│   │   ├── layout.tsx                 # Minimal layout (no sidebar)
│   │   ├── page.tsx                   # Landing page
│   │   ├── pricing/page.tsx           # Pricing tiers
│   │   ├── catalog/page.tsx           # Browse all topics
│   │   ├── topic/[slug]/page.tsx      # Topic preview
│   │   ├── login/page.tsx             # Supabase Auth login
│   │   └── signup/page.tsx            # Supabase Auth signup
│   │
│   ├── (dashboard)/
│   │   ├── layout.tsx                 # ★ 3-panel App Shell
│   │   ├── dashboard/page.tsx         # Overview: enrolled topics, progress
│   │   ├── learn/[topicSlug]/
│   │   │   ├── layout.tsx             # Loads topic data (RSC)
│   │   │   ├── page.tsx               # Topic overview
│   │   │   ├── concept/[conceptSlug]/page.tsx  # ★ 4-tab concept view
│   │   │   ├── graph/page.tsx         # Knowledge graph explorer
│   │   │   └── path/page.tsx          # Learning path
│   │   ├── generate/
│   │   │   ├── page.tsx               # "What do you want to learn?" form
│   │   │   └── [jobId]/page.tsx       # ★ Generation terminal (WebSocket)
│   │   └── settings/page.tsx          # Profile, subscription
│   │
│   └── api/
│       ├── auth/[...nextauth]/route.ts
│       ├── stripe/
│       │   ├── checkout/route.ts
│       │   └── webhook/route.ts
│       └── proxy/[...path]/route.ts   # BFF proxy to FastAPI
│
├── components/
│   ├── layout/
│   │   ├── CurriculumSidebar.tsx
│   │   ├── MainCanvas.tsx
│   │   ├── AiTutor.tsx
│   │   └── GenerationTerminal.tsx
│   ├── learning/
│   │   ├── TheoryTab.tsx
│   │   ├── Eli5Tab.tsx
│   │   ├── ExamplesTab.tsx
│   │   ├── ExercisesTab.tsx
│   │   ├── KnowledgeGraphView.tsx
│   │   └── LearningPathView.tsx
│   ├── chat/
│   │   ├── ChatMessage.tsx
│   │   ├── CitationBadge.tsx
│   │   └── ChatInput.tsx
│   └── shared/
│       ├── ProgressBar.tsx
│       ├── TimeEstimate.tsx
│       ├── PaywallGate.tsx
│       └── SubscriptionBadge.tsx
│
├── lib/
│   ├── auth.ts
│   ├── stripe.ts
│   ├── api.ts
│   └── ws.ts
│
├── prisma/
│   └── schema.prisma
│
└── tailwind.config.ts
```

---

## 7. Database Schema Additions

### New Tables (Prisma-managed, same PostgreSQL)

```prisma
model User {
  id            String    @id @default(cuid())
  email         String    @unique
  name          String?
  image         String?
  tier          Tier      @default(FREE)
  stripeCustomerId String? @unique
  stripePriceId String?
  createdAt     DateTime  @default(now())
  updatedAt     DateTime  @updatedAt
  enrollments   Enrollment[]
  generationJobs GenerationJob[]
}

enum Tier {
  FREE
  PREMIUM
}

model Enrollment {
  id          String    @id @default(cuid())
  userId      String
  topicId     Int       // FK to existing topics table
  user        User      @relation(fields: [userId], references: [id])
  progress    Progress[]
  createdAt   DateTime  @default(now())

  @@unique([userId, topicId])
}

model Progress {
  id            String         @id @default(cuid())
  enrollmentId  String
  conceptId     Int            // FK to existing concepts table
  enrollment    Enrollment     @relation(fields: [enrollmentId], references: [id])
  status        ProgressStatus @default(NOT_STARTED)
  completedAt   DateTime?

  @@unique([enrollmentId, conceptId])
}

enum ProgressStatus {
  NOT_STARTED
  IN_PROGRESS
  COMPLETED
}

model GenerationJob {
  id            String         @id @default(cuid())
  userId        String
  user          User           @relation(fields: [userId], references: [id])
  topicName     String
  status        JobStatus      @default(PENDING)
  resultTopicId Int?
  steps         Json           // [{step, progress, message}]
  error         String?
  createdAt     DateTime       @default(now())
  completedAt   DateTime?
}

enum JobStatus {
  PENDING
  SCRAPING
  EXTRACTING
  ENRICHING
  GENERATING
  COMPLETE
  FAILED
}
```

### Existing Tables (SQLAlchemy-managed, untouched)

`domains`, `topics`, `concepts`, `concept_relationships`, `examples`, `exercises`, `source_sections`, `raw_articles`

Both Prisma and SQLAlchemy connect to the same PostgreSQL database. Prisma reads/writes user tables, SQLAlchemy reads/writes content tables.

---

## 8. On-Demand Generation Flow

```
1. User submits: "Teach me Rust Programming"
2. Next.js → POST /api/proxy/generate { topic: "Rust Programming" }
3. FastAPI creates GenerationJob → returns { job_id: "abc123" }
4. Next.js navigates to /generate/abc123
5. GenerationTerminal mounts → opens WebSocket ws://api.kodastudy.com/ws/jobs/abc123
6. FastAPI background task:
   a. Scrape Rust sources         → { step: "scraping", progress: 15 }
   b. Extract concepts via LLM    → { step: "extracting", progress: 35 }
   c. Generate ELI5s              → { step: "enriching", progress: 55 }
   d. Extract relationships       → { step: "enriching", progress: 65 }
   e. Generate examples           → { step: "generating", progress: 80 }
   f. Generate exercises          → { step: "generating", progress: 95 }
   g. Done                        → { status: "complete", topic_slug: "rust-programming" }
7. GenerationTerminal → router.push('/learn/rust-programming')
```

**Estimated generation time:** 20-45 minutes per topic.

---

## 9. API Contracts

### FastAPI Endpoints (existing + new)

```
# Knowledge browsing
GET    /api/knowledge/domains              → [{id, name, slug, topic_count}]
GET    /api/knowledge/topics               → [{id, name, slug, concept_count}]
GET    /api/knowledge/topics/{slug}        → {topic, concepts: [...]}
GET    /api/knowledge/concepts/{slug}      → {concept, examples, exercises, relationships}
GET    /api/knowledge/concepts/{id}/examples   → [{title, code, language, explanation}]
GET    /api/knowledge/concepts/{id}/exercises  → [{title, starter_code, solution, hints}]

# AI Tutor (Premium)
POST   /api/chat                           → {answer, citations: [{triple, source_url}]}
POST   /api/search                         → {results: [{concept, score, snippet}]}

# Knowledge Graph
GET    /api/graph/{topic_slug}             → {nodes: [...], edges: [...]}
GET    /api/graph/path?from=X&to=Y         → {path: [concept1, concept2, ...]}

# On-demand Generation (Premium)
POST   /api/generate/curriculum            → {job_id, status}
GET    /ws/jobs/{job_id}                   → WebSocket: progress streaming
```

### Next.js API Routes (BFF)

```
POST   /api/stripe/checkout                → {checkout_url}
POST   /api/stripe/webhook                 → Stripe event handler
GET    /api/proxy/[...path]                → Proxy to FastAPI (adds auth header)
```

---

## 10. Implementation Phases

### Phase 11A: Project Setup (1 session)
- Initialize Next.js 15 project in `frontend/`
- Configure TailwindCSS + shadcn/ui + dark theme
- Set up Supabase project + Auth
- Configure Prisma with shared PostgreSQL
- Create the App Shell layout (3-panel CSS Grid)
- Basic route structure + navigation

### Phase 11B: Public Pages (1 session)
- Landing page (hero, features, CTA)
- Pricing page (free vs premium tiers)
- Catalog page (browse all topics from FastAPI)
- Topic preview page
- Auth pages (login/signup via Supabase)

### Phase 11C: Dashboard + Learning Interface (2 sessions)
- Dashboard overview (enrolled topics, progress rings)
- CurriculumSidebar component (left panel, collapsible tree)
- MainCanvas component (center panel, tab router)
- TheoryTab (markdown renderer with syntax highlighting)
- Eli5Tab (simple explanation display)
- ExamplesTab (code examples) — wrapped in PaywallGate
- ExercisesTab (code editor with Monaco) — wrapped in PaywallGate
- Progress tracking (checkmarks, progress bar)

### Phase 11D: AI Tutor + Knowledge Graph (2 sessions)
- AiTutor component (right panel, Vercel AI SDK)
- CitationBadge (show source triples + original URLs)
- KnowledgeGraphView (react-force-graph)
- LearningPathView (prerequisite chain)
- Wire to FastAPI /api/chat endpoint

### Phase 11E: Premium Features (1 session)
- Stripe Checkout integration
- Stripe Webhook handler (subscription events)
- PaywallGate component (blur + upgrade CTA)
- Subscription management page
- On-demand generation form
- GenerationTerminal component (WebSocket progress)

### Phase 12: FastAPI Enhancements (2 sessions)
- Auth middleware (validate Supabase JWT)
- Build /api/knowledge/* endpoints (browse, concept detail)
- Build /api/chat (RAG tutor) — Phase 9D
- Build /api/graph + /api/graph/path — Phase 9E
- Build /api/generate/* (on-demand curriculum)
- Build /ws/jobs/{id} (WebSocket progress)
- Swap Ollama → cloud LLM via config

### Phase 13: Production Deployment (1 session)
- Dockerfile for FastAPI backend
- Deploy Next.js to Vercel
- Deploy FastAPI to Railway
- Configure kodastudy.com domain on Vercel
- Configure api.kodastudy.com on Railway
- HTTPS + environment secrets
- Seed production database with pre-built content
- Monitor first user flow

---

## 11. Content Expansion Strategy

### Pre-Built Library (Launch Content)

| Domain | Topics | Status |
|--------|--------|--------|
| Python Core | 4 topics | ✅ 176 concepts already extracted |
| Databases | 4 topics | ✅ Partially populated |
| AI/ML Pipeline | 5 topics | ✅ Partially populated |
| APIs & Backend | 4 topics | ✅ Partially populated |
| DevOps | 3 topics | ✅ Partially populated |
| Tooling | 3 topics | ✅ Partially populated |

### Post-Launch Expansion (Premium Generation)

- History: World History, Art History, Science History
- Languages: Spanish, French, Japanese (grammar + vocabulary)
- Sciences: Physics, Chemistry, Biology
- Mathematics: Calculus, Linear Algebra, Statistics
- Business: Economics, Marketing, Finance

Each new domain = run the pipeline with new source URLs.

---

## 12. Success Metrics

### Launch Criteria
1. ✅ 100+ concepts with theory + ELI5
2. 🔜 3+ examples per concept (80%+ coverage — currently 141/176)
3. 🔜 2+ exercises per concept (currently 72/176)
4. 🔜 User accounts + auth working
5. 🔜 Premium subscription flow (Stripe)
6. 🔜 AI Tutor chat with citations
7. 🔜 Knowledge graph visualization
8. 🔜 Public website at kodastudy.com

### Growth Targets (6 months)
- 500+ registered users
- 50+ premium subscribers
- 20+ topic domains
- 1000+ concepts
