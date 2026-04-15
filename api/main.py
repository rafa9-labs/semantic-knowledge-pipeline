# ============================================================
# api/main.py — FastAPI Application Setup
# ============================================================
# This is the ENTRY POINT for the REST API.
# It creates the FastAPI app, configures middleware (CORS),
# and includes all route modules.
#
# Run: uvicorn api.main:app --reload --port 8000
#
# WHAT THIS FILE DOES:
#   1. Creates the FastAPI application instance
#   2. Adds CORS middleware (allows frontends to call our API)
#   3. Registers all route routers (curricula, knowledge)
#   4. Adds a health check endpoint
#   5. Configures Swagger UI metadata
#
# WHY uvicorn?
#   FastAPI is an ASGI framework — it needs an ASGI server to run.
#   Uvicorn is a lightning-fast ASGI server built on uvloops and httptools.
#   Think of it as the "web server" that listens for HTTP requests
#   and passes them to FastAPI for processing.
# ============================================================

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from database.connection import engine, Base
from api.routes import curricula, knowledge
from api.schemas.responses import HealthResponse

logger = logging.getLogger(__name__)

# ----------------------------------------------------------
# Create the FastAPI application
# ----------------------------------------------------------
# The title, description, and version appear in Swagger UI (/docs).
app = FastAPI(
    title="Semantic Knowledge Pipeline API",
    description=(
        "REST API for the AI-Powered Educational Knowledge Graph. "
        "Browse scraped articles, explore the knowledge graph, "
        "and generate AI curricula."
    ),
    version="0.1.0",
)

# ----------------------------------------------------------
# CORS Middleware
# ----------------------------------------------------------
# CORS = Cross-Origin Resource Sharing.
# By default, browsers BLOCK requests from one origin (e.g., localhost:3000)
# to another origin (e.g., localhost:8000). This is a security feature.
#
# We add CORSMiddleware to ALLOW frontends on different ports/origins
# to call our API. In production, we'd restrict `allow_origins` to
# specific domains instead of ["*"].
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],       # In production: ["https://your-frontend.com"]
    allow_credentials=True,
    allow_methods=["*"],       # Allow all HTTP methods (GET, POST, etc.)
    allow_headers=["*"],       # Allow all headers
)


# ----------------------------------------------------------
# Register route routers
# ----------------------------------------------------------
# Each router handles endpoints for one resource:
#   - curricula router: /api/curricula/*
#   - knowledge router: /api/articles, /api/triples
app.include_router(curricula.router)
app.include_router(knowledge.router)


# ----------------------------------------------------------
# Health Check Endpoint
# ----------------------------------------------------------
# A simple endpoint that returns "ok" — useful for:
#   - Monitoring (is the API alive?)
#   - Load balancers (route traffic only to healthy instances)
#   - CI/CD (wait for API to be ready before running tests)
@app.get("/api/", response_model=HealthResponse)
def health_check():
    """Health check — confirms the API is running."""
    return HealthResponse()


# ----------------------------------------------------------
# Startup event
# ----------------------------------------------------------
# When the API starts, ensure all database tables exist.
# This is like running `Base.metadata.create_all(engine)` in main.py.
@app.on_event("startup")
def startup():
    logger.info("API starting — ensuring database tables exist")
    Base.metadata.create_all(engine)
    logger.info("Database tables ready")