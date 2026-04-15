# ============================================================
# api/routes/knowledge.py — Knowledge Graph & Article Endpoints
# ============================================================
# These endpoints expose our raw scraped articles and extracted
# knowledge triples (the "knowledge graph").
#
# ENDPOINTS:
#   GET /api/articles   → List all scraped articles
#   GET /api/triples    → List all knowledge graph triples
#
# These are READ-ONLY endpoints — data is created by the pipeline,
# not by API users. This is the "query" side of CQRS (Command Query
# Responsibility Segregation) — a pattern where writes (pipeline)
# and reads (API) are separated.
# ============================================================

from fastapi import APIRouter, Query

from database.connection import get_db_session
from database.models import RawArticle, KnowledgeTripleDB
from api.schemas.responses import (
    ArticleResponse,
    ArticleListResponse,
    TripleResponse,
    TripleListResponse,
)

router = APIRouter(prefix="/api", tags=["Knowledge Graph"])


@router.get("/articles", response_model=ArticleListResponse)
def list_articles(
    skip: int = Query(0, ge=0, description="Number of articles to skip (pagination)"),
    limit: int = Query(50, ge=1, le=100, description="Max articles to return"),
):
    """
    List all scraped articles (without full text).

    Returns a paginated list of articles with metadata.
    We exclude raw_text to keep responses small — the full text
    can be thousands of characters per article.
    """
    with get_db_session() as session:
        query = session.query(RawArticle).order_by(RawArticle.scraped_at.desc())
        total = query.count()
        articles = query.offset(skip).limit(limit).all()

        article_responses = [
            ArticleResponse(
                id=a.id,
                title=a.title,
                url=a.url,
                source_site=a.source_site,
                text_length=len(a.raw_text) if a.raw_text else 0,
                scraped_at=a.scraped_at,
            )
            for a in articles
        ]

        return ArticleListResponse(total=total, articles=article_responses)


@router.get("/triples", response_model=TripleListResponse)
def list_triples(
    skip: int = Query(0, ge=0, description="Number of triples to skip (pagination)"),
    limit: int = Query(100, ge=1, le=500, description="Max triples to return"),
    subject: str = Query(None, description="Filter by subject (partial match)"),
    predicate: str = Query(None, description="Filter by predicate (partial match)"),
):
    """
    List knowledge graph triples with optional filtering.

    KNOWLEDGE GRAPH NAVIGATION:
      - Without filters: returns all triples
      - With subject filter: finds all facts about a concept
      - With predicate filter: finds all relationships of a type

    Example queries:
      GET /api/triples?subject=Promise
      GET /api/triples?predicate=returns
      GET /api/triples?subject=async&predicate=is_a
    """
    with get_db_session() as session:
        query = session.query(KnowledgeTripleDB)

        # --- Apply filters ---
        # ilike = case-insensitive partial match (SQL LIKE with % wildcards)
        if subject:
            query = query.filter(KnowledgeTripleDB.subject.ilike(f"%{subject}%"))
        if predicate:
            query = query.filter(KnowledgeTripleDB.predicate.ilike(f"%{predicate}%"))

        total = query.count()
        triples = (
            query.order_by(KnowledgeTripleDB.extracted_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )

        triple_responses = [
            TripleResponse(
                id=t.id,
                subject=t.subject,
                predicate=t.predicate,
                object_value=t.object_value,
                source_url=t.source_url,
                confidence=t.confidence,
                extracted_at=t.extracted_at,
            )
            for t in triples
        ]

        return TripleListResponse(total=total, triples=triple_responses)