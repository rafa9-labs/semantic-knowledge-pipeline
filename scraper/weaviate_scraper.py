# ============================================================
# scraper/weaviate_scraper.py — Weaviate Documentation Scraper
# ============================================================
# Scrapes weaviate.io/developers/weaviate (Weaviate developer docs).
#
# HTML STRUCTURE:
#   Similar to Mintlify/Docusaurus — modern docs platform with:
#   - <article> or main content div
#   - <h1> for page title
#   - Standard heading hierarchy
#
# SELECTORS:
#   - content: "article" or "main"
#   - title: "h1"
#   - remove: nav, sidebar, footer
# ============================================================

from scraper.docs_scraper import DocsScraper


class WeaviateScraper(DocsScraper):
    """Scraper for weaviate.io/developers/weaviate (Weaviate docs)."""

    name: str = "Weaviate"
    source_site: str = "weaviate_docs"
    rate_limit_delay: float = 2.0

    content_selector: str = "article"
    title_selector: str = "h1"
    wait_until: str = "networkidle"
    fallback_selectors: list[str] = [
        "main",
        "[role='main']",
        "div.md-content",
        "div.content",
    ]
    remove_selectors: list[str] = [
        "nav",
        "header",
        "footer",
        "aside",
        ".sidebar",
        ".cookie-banner",
        ".feedback",
        ".edit-page",
    ]
