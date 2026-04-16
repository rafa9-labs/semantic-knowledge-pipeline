# ============================================================
# scraper/pydantic_scraper.py — Pydantic Documentation Scraper
# ============================================================
# Scrapes docs.pydantic.dev (Pydantic V2 documentation).
# Uses MkDocs Material or similar modern docs framework.
# ============================================================

from scraper.docs_scraper import DocsScraper


class PydanticScraper(DocsScraper):
    """Scraper for docs.pydantic.dev (Pydantic docs)."""

    name: str = "Pydantic"
    source_site: str = "pydantic_docs"
    rate_limit_delay: float = 2.0

    content_selector: str = "article"
    title_selector: str = "h1"
    wait_until: str = "networkidle"
    fallback_selectors: list[str] = [
        "div.md-content",
        "main",
        "[role='main']",
    ]
    remove_selectors: list[str] = [
        "nav",
        "header",
        "footer",
        "aside",
        ".sidebar",
        ".feedback",
    ]
