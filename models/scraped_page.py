# ============================================================
# models/scraped_page.py — Extended Pydantic Model for Documentation Scraping
# ============================================================
# This model extends RawScrapedArticle with additional fields needed
# by the multi-source documentation scrapers in Phase 9B.
#
# WHY A SEPARATE MODEL (not modify RawScrapedArticle)?
#   - Backwards compatibility: MdnScraper and the existing pipeline
#     still use RawScrapedArticle. We don't want to change 6+ files.
#   - Single Responsibility: RawScrapedArticle = basic scraped content.
#     ScrapedPage = enriched content with HTML and section metadata.
#   - The pipeline converts ScrapedPage → RawArticle (SQLAlchemy) by
#     extracting only the fields RawArticle needs.
#
# DATA FLOW:
#   DocsScraper → ScrapedPage (validated) → RawArticle (stored) + SourceSections (parsed)
# ============================================================

from datetime import datetime, timezone
from typing import Optional

from pydantic import BaseModel, Field, HttpUrl

from models.content import RawScrapedArticle


class ScrapedSection(BaseModel):
    """
    A single section parsed from an article's HTML by heading tags.

    Sections are the building blocks of the source_sections table.
    Each section represents content between two heading elements (h1-h6).

    Example:
        ScrapedSection(
            heading="Coroutines and Tasks",
            content="Coroutines declared with async def syntax...",
            heading_level=2,
            sort_order=3,
        )
    """
    heading: Optional[str] = Field(
        default=None,
        max_length=500,
        description="Section heading text (from h1-h6 tag)",
    )
    content: str = Field(
        ...,
        min_length=1,
        description="Section body text",
    )
    heading_level: Optional[int] = Field(
        default=None,
        ge=1,
        le=6,
        description="HTML heading level (1=h1, 2=h2, etc.)",
    )
    sort_order: int = Field(
        default=0,
        description="Position of this section within the article",
    )


class ScrapedPage(BaseModel):
    """
    Enriched scraped page with raw HTML and parsed sections.

    This model wraps all data extracted from a documentation page:
      - The standard article fields (title, url, raw_text, source_site)
      - The raw HTML (needed for section parsing)
      - Pre-parsed sections (heading → content pairs)

    The pipeline uses this to:
      1. Store article in raw_articles table (using article fields)
      2. Store sections in source_sections table (using sections list)
    """
    title: str = Field(
        ...,
        min_length=1,
        max_length=500,
        description="The title/heading of the scraped article",
    )
    url: HttpUrl = Field(
        ...,
        description="The full URL where this article was scraped from",
    )
    raw_text: str = Field(
        ...,
        min_length=10,
        description="The plain text content extracted from the page",
    )
    raw_html: str = Field(
        ...,
        min_length=10,
        description="The raw HTML of the main content area (for section parsing)",
    )
    source_site: Optional[str] = Field(
        default=None,
        max_length=100,
        description="Identifier for the source website (e.g., 'python_docs', 'fastapi')",
    )
    sections: list[ScrapedSection] = Field(
        default_factory=list,
        description="Parsed sections from the article HTML",
    )
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="UTC timestamp of when this page was scraped",
    )

    def to_raw_article_dict(self) -> dict:
        """
        Convert to a dict suitable for creating a RawArticle SQLAlchemy object.

        Strips fields not needed by raw_articles (raw_html, sections).
        """
        return {
            "title": self.title,
            "url": str(self.url),
            "raw_text": self.raw_text,
            "source_site": self.source_site,
        }

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "title": "asyncio — Asynchronous I/O",
                "url": "https://docs.python.org/3/library/asyncio.html",
                "raw_text": "asyncio is a library to write concurrent code...",
                "raw_html": "<div class='section'><h2>Coroutines</h2><p>...</p></div>",
                "source_site": "python_docs",
                "sections": [
                    {
                        "heading": "Coroutines",
                        "content": "Coroutines declared with async def syntax...",
                        "heading_level": 2,
                        "sort_order": 0,
                    }
                ],
            }
        }
