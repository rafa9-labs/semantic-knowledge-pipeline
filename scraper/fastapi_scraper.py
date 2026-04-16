# ============================================================
# scraper/fastapi_scraper.py — FastAPI Documentation Scraper
# ============================================================
# Scrapes fastapi.tiangolo.com (MkDocs Material theme).
#
# HTML STRUCTURE:
#   <article class="md-content__inner">  ← Main content
#     <h1 id="...">Title</h1>             ← Page title
#     <p>Content...</p>                   ← Paragraphs
#   </article>
#
# SELECTORS:
#   - content: "div.md-content" or "article.md-content__inner"
#   - title: "h1"
#   - remove: "nav", "footer", ".md-header", ".md-sidebar"
# ============================================================

from scraper.docs_scraper import DocsScraper


class FastAPIScraper(DocsScraper):
    """Scraper for fastapi.tiangolo.com (MkDocs Material)."""

    name: str = "FastAPI"
    source_site: str = "fastapi"
    rate_limit_delay: float = 2.0

    content_selector: str = "div.md-content"
    title_selector: str = "h1"
    remove_selectors: list[str] = [
        "header.md-header",
        "nav.md-nav",
        "div.md-sidebar",
        "footer.md-footer",
        "div.md-banner",
        ".md-skip",
        "div.announce-wrapper",
        ".sponsor-badge",
        ".sponsor-image",
        "a.announce-link",
    ]
