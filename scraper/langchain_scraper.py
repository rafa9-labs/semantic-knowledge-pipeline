# ============================================================
# scraper/langchain_scraper.py — LangChain Documentation Scraper
# ============================================================
# Scrapes python.langchain.com (Mintlify documentation platform).
#
# HTML STRUCTURE:
#   Mintlify uses a custom framework with:
#   - <article> or main content div for the docs body
#   - <h1> for page title
#   - Sections with headings h2-h4
#
# SELECTORS:
#   - content: "article" or fallback selectors
#   - title: "h1"
#   - remove: nav, sidebar, footer, cookie banners
# ============================================================

from scraper.docs_scraper import DocsScraper


class LangChainScraper(DocsScraper):
    """Scraper for python.langchain.com (Mintlify docs)."""

    name: str = "LangChain"
    source_site: str = "langchain_docs"
    rate_limit_delay: float = 2.5

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
        "[data-testid='assistant-popup']",
        ".theme-selector",
        ".feedback-section",
    ]
