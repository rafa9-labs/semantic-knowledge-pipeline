# ============================================================
# scraper/sqlalchemy_scraper.py — SQLAlchemy Documentation Scraper
# ============================================================
# Scrapes docs.sqlalchemy.org (Sphinx-generated, similar to Python docs).
#
# HTML STRUCTURE:
#   <div class="document">            ← Main document wrapper
#     <div class="body" role="main">  ← Content area
#       <div class="section">         ← Each section
#         <h2>Title</h2>
#         <p>Content...</p>
#       </div>
#     </div>
#   </div>
#
# SELECTORS:
#   - content: "div.body[role='main']" or "div.document"
#   - title: "h1"
#   - remove: sidebar, navigation, footer elements
# ============================================================

from scraper.docs_scraper import DocsScraper


class SQLAlchemyScraper(DocsScraper):
    """Scraper for docs.sqlalchemy.org (Sphinx documentation)."""

    name: str = "SQLAlchemy"
    source_site: str = "sqlalchemy_docs"
    rate_limit_delay: float = 2.0

    content_selector: str = "div.body[role='main']"
    title_selector: str = "h1"
    wait_until: str = "networkidle"
    fallback_selectors: list[str] = [
        "div.body",
        "div.document",
        "div.section",
        "main",
        "article",
    ]
    remove_selectors: list[str] = [
        "div.sphinxsidebar",
        "div.sphinxsidebarwrapper",
        "div.related",
        "div.footer",
        "div.header",
        "div.top",
        "#docs-sidebar",
        "nav.docs-nav",
    ]
