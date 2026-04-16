# ============================================================
# scraper/docker_scraper.py — Docker Documentation Scraper
# ============================================================
# Scrapes docs.docker.com (custom documentation platform).
#
# HTML STRUCTURE:
#   <main> or <article>                ← Main content area
#   <h1>                               ← Page title
#   Sections with standard heading tags
#
# SELECTORS:
#   - content: "main" or "article"
#   - title: "h1"
#   - remove: nav, sidebar, footer, breadcrumbs
# ============================================================

from scraper.docs_scraper import DocsScraper


class DockerScraper(DocsScraper):
    """Scraper for docs.docker.com (Docker docs)."""

    name: str = "Docker"
    source_site: str = "docker_docs"
    rate_limit_delay: float = 2.0

    content_selector: str = "main"
    title_selector: str = "h1"
    remove_selectors: list[str] = [
        "nav",
        "header",
        "footer",
        "aside",
        ".breadcrumb",
        ".sidebar",
        "[aria-label=' breadcrumbs']",
        ".feedback",
    ]
