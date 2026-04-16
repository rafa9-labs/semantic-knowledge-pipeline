# ============================================================
# scraper/github_scraper.py — GitHub/Markdown Documentation Scraper
# ============================================================
# Scrapes GitHub README files and GitHub Pages documentation.
# Also handles docs.github.com (GitHub's own docs).
# GitHub renders markdown as HTML with .markdown-body class.
#
# HTML STRUCTURE:
#   GitHub README: <article class="markdown-body">...</article>
#   GitHub Docs:   <article>...</article>
# ============================================================

from scraper.docs_scraper import DocsScraper


class GitHubScraper(DocsScraper):
    """Scraper for GitHub pages (README files, GitHub docs)."""

    name: str = "GitHub"
    source_site: str = "github_docs"
    rate_limit_delay: float = 2.5

    content_selector: str = "article.markdown-body"
    title_selector: str = "h1"
    wait_until: str = "networkidle"
    fallback_selectors: list[str] = [
        "article",
        "main",
        "[role='main']",
        "div.markdown-body",
    ]
    remove_selectors: list[str] = [
        "nav",
        "header",
        "footer",
        ".Box-header",
        ".file-navigation",
        ".js-sticky",
        "div[role='navigation']",
    ]

    async def _extract_content(self, page, url):
        """
        Override to handle GitHub's two different layouts:
          - Raw README files use article.markdown-body
          - GitHub Docs pages use a different structure
        """
        markdown_body = page.locator("article.markdown-body")
        if await markdown_body.count() == 0:
            self.content_selector = "article"
        else:
            self.content_selector = "article.markdown-body"

        return await super()._extract_content(page, url)
