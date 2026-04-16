# ============================================================
# scraper/postgresql_scraper.py — PostgreSQL Documentation Scraper
# ============================================================
# Scrapes www.postgresql.org/docs (PostgreSQL official docs).
#
# HTML STRUCTURE:
#   <div id="docContent">     <- Main content wrapper
#     <div class="chapter">   <- Chapter container
#       <h2 class="title">    <- Chapter title (NOT h1!)
#       <p>Content...</p>
#     </div>
#   </div>
#
# NOTE: PostgreSQL docs use h2 for chapter titles, not h1.
# ============================================================

from scraper.docs_scraper import DocsScraper


class PostgreSQLScraper(DocsScraper):
    """Scraper for www.postgresql.org/docs (PostgreSQL docs)."""

    name: str = "PostgreSQL"
    source_site: str = "postgresql_docs"
    rate_limit_delay: float = 2.0

    content_selector: str = "#docContent"
    title_selector: str = "h2.title"
    wait_until: str = "networkidle"
    fallback_selectors: list[str] = [
        "div.chapter",
        "div.book",
        "div.section",
        "main",
        "article",
    ]
    remove_selectors: list[str] = [
        "div.navheader",
        "div.navfooter",
        "div.toc",
        "footer",
        "nav",
        "div.docs-version",
        "#docSearchForm",
    ]
