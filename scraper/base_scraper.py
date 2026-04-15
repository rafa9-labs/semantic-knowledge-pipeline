# ============================================================
# scraper/base_scraper.py — Abstract Base Scraper
# ============================================================
# This module defines the FOUNDATION that all our scrapers will build on.
# It handles the universal challenges of web scraping:
#   - Retrying failed requests (with exponential backoff)
#   - Rate limiting (don't overwhelm servers)
#   - Error logging (know what went wrong)
#   - Browser lifecycle (open/close Playwright)
#
# HOW INHERITANCE WORKS HERE:
#   BaseScraper is ABSTRACT — you never use it directly.
#   Instead, you create a subclass like MdnScraper that:
#     1. Inherits retry/error logic from BaseScraper
#     2. Implements _extract_content() for a specific website
#
#   Think of BaseScraper as the "chassis" of a car — it has the engine,
#   brakes, and steering. Each subclass adds the "body" (site-specific logic).
# ============================================================

import asyncio
import logging
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Optional

from playwright.async_api import async_playwright, Page, Browser, BrowserContext
from pydantic import ValidationError

from models.content import RawScrapedArticle

# ----------------------------------------------------------
# LOGGING SETUP
# ----------------------------------------------------------
# logging is Python's built-in logging system. We configure it to:
#   - Show timestamps, logger name, level (INFO/WARNING/ERROR), and message
#   - Output to the console (we could also log to files in production)
#
# Levels (least → most severe):
#   DEBUG    → Detailed diagnostic info (e.g., "Sending request to /api/foo")
#   INFO     → General progress (e.g., "Scraping page 3 of 10")
#   WARNING  → Something unexpected but recoverable (e.g., "Page loaded slowly")
#   ERROR    → Something failed (e.g., "Could not find article title")
#   CRITICAL → The whole pipeline might be broken
logger = logging.getLogger(__name__)


class BaseScraper(ABC):
    """
    Abstract base class for all web scrapers in this project.

    SUBCLASSES MUST IMPLEMENT:
        - _extract_content(page) → RawScrapedArticle
          This method contains the site-specific CSS selectors and extraction logic.

    SUBCLASSES MAY OVERRIDE:
        - name: A human-readable name for logging (e.g., "MDN Scraper")
        - rate_limit_delay: Seconds to wait between requests

    USAGE:
        class MdnScraper(BaseScraper):
            name = "MDN"
            rate_limit_delay = 2.0

            def _extract_content(self, page: Page) -> RawScrapedArticle:
                title = page.locator("h1").first.text_content()
                body = page.locator("article").first.inner_text()
                return RawScrapedArticle(title=title, url=page.url, raw_text=body)

        scraper = MdnScraper()
        results = await scraper.scrape(["https://developer.mozilla.org/..."])
    """

    # --- Configurable settings (override in subclasses) ---
    name: str = "BaseScraper"               # For logging: "[MDN Scraper] Scraping..."
    rate_limit_delay: float = 1.5           # Seconds between requests (be polite!)
    max_retries: int = 3                    # How many times to retry a failed page
    page_timeout_ms: int = 30_000           # 30 seconds — max wait for page load

    async def scrape(self, urls: list[str]) -> list[RawScrapedArticle]:
        """
        Main entry point: scrape a list of URLs and return validated articles.

        This method handles the FULL lifecycle:
          1. Launch Playwright browser (headless Chromium)
          2. For each URL: navigate → extract → validate → store result
          3. Retry failed pages with exponential backoff
          4. Close the browser when done

        Args:
            urls: List of URLs to scrape.

        Returns:
            List of successfully validated RawScrapedArticle objects.
            Failed URLs are logged but don't stop the whole process.
        """
        results: list[RawScrapedArticle] = []
        failed_urls: list[str] = []

        logger.info(f"[{self.name}] Starting scrape of {len(urls)} URLs")

        # ----------------------------------------------------------
        # PLAYWRIGHT LIFECYCLE
        # ----------------------------------------------------------
        # async_playwright() is an ASYNC CONTEXT MANAGER that:
        #   1. Starts the Playwright driver process
        #   2. Provides access to browser_type (Chromium, Firefox, WebKit)
        #   3. Cleans up the process when we exit the block
        #
        # We use "async with" so the browser process ALWAYS gets cleaned up,
        # even if an error occurs.
        async with async_playwright() as pw:
            # Launch headless Chromium.
            # headless=True means no visible browser window (runs in background).
            # In development, you can set headless=False to WATCH the browser
            # navigate — very useful for debugging CSS selectors.
            browser: Browser = await pw.chromium.launch(headless=True)

            # Create a BrowserContext — think of it as an "incognito window."
            # Each context has its own cookies, storage, etc.
            # We set a realistic user_agent so websites don't block us
            # for looking like a bot.
            context: BrowserContext = await browser.new_context(
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/136.0.0.0 Safari/537.36"
                )
            )

            try:
                for i, url in enumerate(urls):
                    logger.info(
                        f"[{self.name}] Scraping {i+1}/{len(urls)}: {url}"
                    )

                    # Attempt to scrape this URL with retry logic
                    article = await self._scrape_with_retry(context, url)

                    if article:
                        results.append(article)
                        logger.info(
                            f"[{self.name}] Success: '{article.title[:50]}...'"
                        )
                    else:
                        failed_urls.append(url)
                        logger.warning(
                            f"[{self.name}] Failed after retries: {url}"
                        )

                    # --------------------------------------------------
                    # RATE LIMITING
                    # --------------------------------------------------
                    # Don't send the next request immediately.
                    # This is both polite (don't overwhelm the server) and
                    # practical (avoid getting IP-banned).
                    # We only sleep if there are more URLs to process.
                    if i < len(urls) - 1:
                        await asyncio.sleep(self.rate_limit_delay)

            finally:
                # ALWAYS close browser resources, even on error.
                # If we don't, Chromium processes linger and consume memory.
                await context.close()
                await browser.close()

        # Summary log
        logger.info(
            f"[{self.name}] Done! Success: {len(results)}, "
            f"Failed: {len(failed_urls)}"
        )
        if failed_urls:
            logger.warning(f"[{self.name}] Failed URLs: {failed_urls}")

        return results

    async def _scrape_with_retry(
        self, context: BrowserContext, url: str
    ) -> Optional[RawScrapedArticle]:
        """
        Try to scrape a single URL, retrying on failure with exponential backoff.

        EXPONENTIAL BACKOFF EXPLAINED:
            When a request fails, we don't retry immediately. Instead, we wait
            increasingly longer between retries:
              Attempt 1: fail → wait 1s
              Attempt 2: fail → wait 2s
              Attempt 3: fail → wait 4s
              Attempt 4: give up

            This gives the server time to recover from temporary issues
            (overload, rate limiting, network blips) without hammering it.

        Args:
            context: Playwright browser context (shared across retries).
            url: The URL to scrape.

        Returns:
            A validated RawScrapedArticle, or None if all retries fail.
        """
        last_error: Optional[Exception] = None

        for attempt in range(1, self.max_retries + 1):
            try:
                # Open a new page (tab) in the browser context
                page: Page = await context.new_page()
                try:
                    # Navigate to the URL and wait for the page to load.
                    # wait_until="domcontentloaded" means we wait until the
                    # HTML is parsed, but images/styles may still be loading.
                    # This is faster than "load" (waits for everything) and
                    # usually sufficient for text extraction.
                    await page.goto(
                        url,
                        wait_until="domcontentloaded",
                        timeout=self.page_timeout_ms,
                    )

                    # Call the subclass's site-specific extraction logic
                    # NOTE: _extract_content is async because Playwright's
                    # locator methods (text_content, inner_text) return coroutines.
                    article = await self._extract_content(page, url)

                    # If extraction returned None, the subclass decided
                    # this page isn't worth scraping (e.g., a redirect page)
                    if article is None:
                        logger.warning(
                            f"[{self.name}] Extraction returned None for: {url}"
                        )
                        return None

                    # Article passed Pydantic validation — return it!
                    return article

                finally:
                    # ALWAYS close the page, even on error.
                    # Unclosed pages leak memory in the browser process.
                    await page.close()

            except ValidationError as e:
                # Pydantic validation failed — the data is structurally bad.
                # No point retrying — the same page will produce the same bad data.
                logger.error(
                    f"[{self.name}] Validation error for {url}: {e}"
                )
                return None

            except Exception as e:
                # Network error, timeout, element not found, etc.
                # These MIGHT work on retry (server might recover).
                last_error = e
                logger.warning(
                    f"[{self.name}] Attempt {attempt}/{self.max_retries} "
                    f"failed for {url}: {type(e).__name__}: {e}"
                )

                # Exponential backoff: 2^attempt seconds (1, 2, 4, 8, ...)
                # But only sleep if we're going to retry (not on last attempt)
                if attempt < self.max_retries:
                    backoff = 2 ** attempt  # 2, 4, 8...
                    logger.info(
                        f"[{self.name}] Retrying in {backoff}s..."
                    )
                    await asyncio.sleep(backoff)

        # All retries exhausted — give up on this URL
        logger.error(
            f"[{self.name}] All {self.max_retries} retries exhausted for {url}. "
            f"Last error: {last_error}"
        )
        return None

    @abstractmethod
    async def _extract_content(
        self, page: Page, url: str
    ) -> Optional[RawScrapedArticle]:
        """
        Site-specific content extraction. MUST be implemented by subclasses.

        This is where you define:
          1. Which CSS selectors to use for this specific website
          2. How to extract the title, body text, etc.
          3. Whether the page is worth keeping or should be skipped

        Args:
            page: The loaded Playwright Page object.
            url: The URL being scraped (useful for the RawScrapedArticle).

        Returns:
            A validated RawScrapedArticle, or None to skip this page.

        Example implementation:
            title = page.locator("h1").first.text_content()
            body = page.locator("article").first.inner_text()
            return RawScrapedArticle(
                title=title.strip(),
                url=url,
                raw_text=body.strip(),
                source_site="example_site",
            )
        """
        ...