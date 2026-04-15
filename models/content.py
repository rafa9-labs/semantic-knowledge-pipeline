# ============================================================
# models/content.py — Raw Scraped Article Schema
# ============================================================
# This is the FIRST data model in our pipeline. It represents
# the raw output of a web scraper before any AI processing.
#
# DATA FLOW:
#   Playwright Scraper → RawScrapedArticle (validated here) → PostgreSQL
#
# PYDANTIC'S ROLE:
#   Pydantic is a data validation library that enforces types and
#   constraints at RUNTIME. If a scraper passes a string where an
#   integer is expected, Pydantic raises a ValidationError BEFORE
#   the data reaches our database. This is our first line of defense
#   against corrupt data.
# ============================================================

from datetime import datetime, timezone
from typing import Optional

from pydantic import BaseModel, Field, HttpUrl


class RawScrapedArticle(BaseModel):
    """
    Represents a single article/documentation page scraped from the web.

    This model is the ENTRY POINT of our data pipeline. Every piece of
    content we scrape MUST conform to this schema. If it doesn't, the
    scraper has a bug — and Pydantic will tell us exactly what's wrong.

    Example valid input:
        article = RawScrapedArticle(
            title="Python Async/Await Guide",
            url="https://docs.python.org/3/library/asyncio.html",
            raw_text="Asynchronous programming in Python...",
            source_site="python_docs",
            timestamp=datetime.now(timezone.utc)  # auto-filled if omitted
        )
    """

    # --- Title of the scraped page ---
    # Field constraint: must be a non-empty string (min_length=1).
    # If a scraper returns title="" or title=None, Pydantic raises ValidationError.
    # This prevents empty titles from silently entering our database.
    title: str = Field(
        ...,  # "..." means this field is REQUIRED (no default value)
        min_length=1,
        max_length=500,
        description="The title/heading of the scraped article",
    )

    # --- URL of the scraped page ---
    # HttpUrl is a SPECIAL Pydantic type that validates the string is a real URL.
    # It checks for: valid scheme (http/https), valid domain, no spaces, etc.
    # Example: "not a url" → ValidationError, "https://example.com" → passes
    # We also store it as a string in the database (HttpUrl serializes to str).
    url: HttpUrl = Field(
        ...,
        description="The full URL where this article was scraped from",
    )

    # --- Raw text content of the page ---
    # This is the UNPROCESSED text — no AI, no structuring, just what we scraped.
    # min_length=10 is a sanity check: if we got less than 10 chars of text,
    # the page probably didn't load, or we hit a paywall, or the scraper broke.
    # We'll catch this early instead of storing garbage data.
    raw_text: str = Field(
        ...,
        min_length=10,
        description="The raw text content extracted from the page (unprocessed)",
    )

    # --- Source website identifier ---
    # Optional field — not every scraper needs to specify this, but it helps
    # us track WHERE each article came from (e.g., "mdn", "python_docs", "wiki").
    # This is useful for filtering in queries: "show me only MDN articles."
    source_site: Optional[str] = Field(
        default=None,
        max_length=100,
        description="Identifier for the source website (e.g., 'mdn', 'python_docs')",
    )

    # --- When this article was scraped ---
    # We default to UTC NOW if not provided. Using UTC (not local time) is
    # critical in data engineering — it avoids timezone confusion when your
    # app runs across different servers/regions.
    # datetime.now(timezone.utc) gives us an AWARE datetime (has timezone info).
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="UTC timestamp of when this article was scraped",
    )

    class Config:
        """
        Pydantic V2 model configuration.

        - from_attributes=True: Allows creating this model from objects with
          attributes (e.g., a SQLAlchemy ORM object). This bridges our DB layer
          to our validation layer seamlessly.

        - json_schema_extra: Provides an example for documentation generation
          (useful for FastAPI later — it auto-generates API docs from this).
        """
        from_attributes = True
        json_schema_extra = {
            "example": {
                "title": "Python Async/Await Guide",
                "url": "https://docs.python.org/3/library/asyncio.html",
                "raw_text": "Asynchronous programming is a type of parallel programming...",
                "source_site": "python_docs",
                "timestamp": "2026-04-14T18:00:00Z",
            }
        }