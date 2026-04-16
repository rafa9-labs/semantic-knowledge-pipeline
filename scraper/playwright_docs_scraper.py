# ============================================================
# scraper/playwright_docs_scraper.py — Playwright Documentation Scraper
# ============================================================
# Scrapes playwright.dev/python/docs (Playwright Python docs).
# Uses a modern docs platform with standard article structure.
# ============================================================

from scraper.docs_scraper import DocsScraper


class PlaywrightDocsScraper(DocsScraper):
    """Scraper for playwright.dev/python/docs (Playwright Python docs)."""

    name: str = "Playwright"
    source_site: str = "playwright_docs"
    rate_limit_delay: float = 2.0

    content_selector: str = "article"
    title_selector: str = "h1"
    wait_until: str = "networkidle"
    fallback_selectors: list[str] = [
        "main",
        "[role='main']",
        "div.md-content",
    ]
    remove_selectors: list[str] = [
        "nav",
        "header",
        "footer",
        "aside",
        ".sidebar",
        "div.toc",
    ]
