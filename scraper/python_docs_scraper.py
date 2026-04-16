# ============================================================
# scraper/python_docs_scraper.py — Python Official Documentation Scraper
# ============================================================
# Scrapes docs.python.org (Sphinx-generated documentation).
#
# HTML STRUCTURE:
#   <div class="body" role="main">   ← Main content wrapper
#     <div class="section" id="...">  ← Each section
#       <h2>Section Title</h2>         ← Section headings
#       <p>Content...</p>              ← Paragraphs
#     </div>
#   </div>
#
# SELECTORS:
#   - content: "div.body[role='main']" or fallback "div.section"
#   - title: "h1"
#   - remove: ".sphinxsidebar", ".related", "div.header" (nav elements)
# ============================================================

from scraper.docs_scraper import DocsScraper


class PythonDocsScraper(DocsScraper):
    """Scraper for docs.python.org (Sphinx documentation)."""

    name: str = "PythonDocs"
    source_site: str = "python_docs"
    rate_limit_delay: float = 2.0

    content_selector: str = "div.body[role='main']"
    title_selector: str = "h1"
    remove_selectors: list[str] = [
        ".sphinxsidebar",
        ".sphinxsidebarwrapper",
        "div.related",
        "div.header",
        "div.footer",
        ".toplink",
        "div.breadcrumbs",
        "div.sourcelink",
    ]
