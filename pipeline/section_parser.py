# ============================================================
# pipeline/section_parser.py — HTML Section Parser for Source Sections
# ============================================================
# This module parses raw HTML content into structured sections by
# splitting on heading tags (h1-h6). The output goes directly into
# the source_sections table.
#
# WHY A STANDALONE PARSER (not inside DocsScraper)?
#   1. Separation of concerns: scraping vs. parsing
#   2. Reusability: can parse HTML from any source (scraped, uploaded, etc.)
#   3. Testability: can unit test parsing without running a browser
#   4. The DocsScraper does inline section parsing for convenience, but
#      this standalone parser handles the DB storage step.
#
# HOW IT WORKS:
#   The DocsScraper already parses sections via JavaScript in the browser.
#   This module takes those ScrapedSection objects and persists them to
#   the source_sections table with the correct article_id FK.
# ============================================================

import logging
from typing import Optional

from sqlalchemy.orm import Session

from database.models import SourceSection, RawArticle
from models.scraped_page import ScrapedSection

logger = logging.getLogger(__name__)


def store_sections(
    session: Session,
    article_id: int,
    sections: list[ScrapedSection],
) -> int:
    """
    Store parsed sections in the source_sections table.

    IDEMPOTENT: Deletes existing sections for this article before re-inserting.
    This ensures re-scraping the same article doesn't create duplicates.

    Args:
        session: Active SQLAlchemy session.
        article_id: The ID of the parent article in raw_articles.
        sections: List of ScrapedSection objects to store.

    Returns:
        Number of sections stored.
    """
    if not sections:
        logger.debug(f"No sections to store for article_id={article_id}")
        return 0

    session.query(SourceSection).filter(
        SourceSection.article_id == article_id
    ).delete()

    stored = 0
    for section in sections:
        if not section.content or len(section.content.strip()) < 5:
            continue

        row = SourceSection(
            article_id=article_id,
            heading=section.heading,
            content=section.content.strip(),
            heading_level=section.heading_level,
            sort_order=section.sort_order,
            concept_ids=[],
        )
        session.add(row)
        stored += 1

    session.flush()
    logger.info(
        f"Stored {stored} sections for article_id={article_id}"
    )
    return stored


def get_sections_for_article(
    session: Session, article_id: int
) -> list[dict]:
    """
    Retrieve all sections for a given article, ordered by sort_order.

    Args:
        session: Active SQLAlchemy session.
        article_id: The article to retrieve sections for.

    Returns:
        List of dicts with section data.
    """
    rows = (
        session.query(SourceSection)
        .filter(SourceSection.article_id == article_id)
        .order_by(SourceSection.sort_order)
        .all()
    )
    return [
        {
            "id": r.id,
            "heading": r.heading,
            "content": r.content[:200] + "..." if len(r.content) > 200 else r.content,
            "heading_level": r.heading_level,
            "sort_order": r.sort_order,
        }
        for r in rows
    ]
