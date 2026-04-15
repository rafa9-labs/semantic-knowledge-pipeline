# ============================================================
# scraper/mdn_scraper.py — MDN Web Docs Scraper
# ============================================================
# This scraper targets Mozilla Developer Network (MDN) documentation.
# MDN is one of the best resources for web development concepts,
# making it a perfect first data source for our knowledge graph.
#
# MDN PAGE STRUCTURE (what we're extracting from):
#   <main id="content"> ← Main content wrapper
#     <h1>Title</h1>    ← Article title
#     <p>Text...</p>    ← Body paragraphs
#     <pre><code>...</code></pre>  ← Code examples
#   </main>
#
# We use CSS selectors to target these elements in Playwright.
# ============================================================

import logging
from typing import Optional

from playwright.async_api import Page

from models.content import RawScrapedArticle
from scraper.base_scraper import BaseScraper

logger = logging.getLogger(__name__)


class MdnScraper(BaseScraper):
    """
    Scraper for Mozilla Developer Network (developer.mozilla.org).

    Inherits from BaseScraper:
      - ✅ Retry logic with exponential backoff
      - ✅ Rate limiting between requests
      - ✅ Browser lifecycle management
      - ✅ Pydantic validation

    Only implements:
      - _extract_content() — the MDN-specific CSS selectors and logic

    USAGE:
        scraper = MdnScraper()
        results = await scraper.scrape([
            "https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Statements/async_function",
            "https://developer.mozilla.org/en-US/docs/Web/API/Fetch_API",
        ])
    """

    # Override base class settings for MDN-specific values
    name: str = "MDN"
    rate_limit_delay: float = 2.0      # Be extra polite to MDN (2s between requests)
    max_retries: int = 3
    page_timeout_ms: int = 30_000      # 30 seconds

    async def _extract_content(
        self, page: Page, url: str
    ) -> Optional[RawScrapedArticle]:
        """
        Extract article content from an MDN documentation page.

        MDN-SPECIFIC SELECTORS:
          - "h1"              → The article title
          - "article"         → The main content container
          - ".notecard"       → MDN warning/note boxes (we skip these)

        IMPORTANT: This method is ASYNC because Playwright's locator methods
        (text_content(), inner_text()) return COROUTINES that must be awaited.
        The page is already loaded by the base class before this is called.

        Args:
            page: The loaded Playwright Page object.
            url: The URL being scraped.

        Returns:
            A validated RawScrapedArticle, or None if extraction fails.
        """
        # ----------------------------------------------------------
        # 1. EXTRACT TITLE
        # ----------------------------------------------------------
        # page.locator("h1") finds all <h1> elements on the page.
        # .first takes only the first match (there should be exactly one).
        # text_content() is ASYNC in Playwright — it returns a coroutine,
        # so we MUST await it to get the actual string value.
        #
        # FAILURE SCENARIO: If the page has no <h1>, this returns None.
        # We handle that below with the "if not title" check.
        title_element = page.locator("h1").first
        title = await title_element.text_content()

        if not title:
            logger.warning(f"[MDN] No title found on: {url}")
            return None

        # Strip whitespace (newlines, spaces) from the title.
        # Web pages often have extra whitespace in their HTML.
        title = title.strip()

        # ----------------------------------------------------------
        # 2. EXTRACT MAIN CONTENT
        # ----------------------------------------------------------
        # MDN wraps its main article content in an <article> element.
        # .inner_text() returns all visible text inside that element,
        # recursively including text from child elements.
        #
        # WHY inner_text() NOT text_content()?
        #   - text_content() includes hidden text (display:none, scripts)
        #   - inner_text() only returns VISIBLE text (what you'd see in browser)
        #   - For our purposes, we want the readable article text.
        # MDN uses <main> with id="content" — NOT <article>.
        # The page is rendered server-side but some JS hydration is needed.
        # We target the main content area which holds the actual documentation.
        content_element = page.locator("main#content").first
        raw_text = await content_element.inner_text()

        if not raw_text or len(raw_text.strip()) < 10:
            # ----------------------------------------------------------
            # FAILURE SCENARIO: Empty or very short content.
            # This could mean:
            #   - The page is a redirect/loading page
            #   - The page structure changed (MDN updated their HTML)
            #   - The page loaded but content is behind JavaScript we didn't wait for
            # We return None to skip this page.
            # ----------------------------------------------------------
            logger.warning(f"[MDN] Content too short on: {url}")
            return None

        raw_text = raw_text.strip()

        # ----------------------------------------------------------
        # 3. CREATE AND VALIDATE VIA PYDANTIC
        # ----------------------------------------------------------
        # RawScrapedArticle will validate:
        #   - title is non-empty string (min_length=1) ✅
        #   - url is a valid URL format ✅
        #   - raw_text has at least 10 characters ✅
        #   - timestamp is auto-generated in UTC ✅
        #
        # If any validation fails, Pydantic raises ValidationError,
        # which the base class catches and logs.
        return RawScrapedArticle(
            title=title,
            url=url,
            raw_text=raw_text,
            source_site="mdn",
        )