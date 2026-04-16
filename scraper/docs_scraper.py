# ============================================================
# scraper/docs_scraper.py — Generic Documentation Site Scraper
# ============================================================
# This is the BASE CLASS for all documentation site scrapers in Phase 9B.
# It inherits from BaseScraper (retry logic, rate limiting, browser lifecycle)
# and adds documentation-specific functionality:
#
#   1. Configurable CSS selectors (each site sets its own)
#   2. Extracts both plain text AND raw HTML
#   3. Parses HTML into sections by headings
#   4. Returns ScrapedPage (richer than RawScrapedArticle)
#
# HOW TO ADD A NEW DOCUMENTATION SOURCE:
#   1. Create a new file: scraper/your_site_scraper.py
#   2. Subclass DocsScraper
#   3. Set these class attributes:
#        - name: "YourSite" (for logging)
#        - source_site: "your_site" (stored in DB)
#        - content_selector: CSS selector for main content area
#        - title_selector: CSS selector for page title
#        - remove_selectors: list of CSS selectors to remove (nav, sidebar, etc.)
#   4. Optionally override _extract_content() for special cases
#
# CSS SELECTOR EXAMPLES:
#   - "article"           → matches <article> element
#   - "div.md-content"    → matches <div class="md-content">
#   - "main#content"      → matches <main id="content">
#   - ".body[role=main]"  → matches <div class="body" role="main">
#
# WHY GENERIC INSTEAD OF SEPARATE SCRAPERS?
#   Most documentation sites (Sphinx, MkDocs, Docusaurus, Mintlify) share
#   the same structure: a main content area with headings and paragraphs.
#   The only difference is WHICH CSS class/id wraps that content.
#   A generic scraper with configurable selectors avoids duplicating
#   200+ lines of retry/error/rate-limit logic for each site.
# ============================================================

import logging
from typing import Optional

from playwright.async_api import Page

from models.scraped_page import ScrapedPage, ScrapedSection
from scraper.base_scraper import BaseScraper

logger = logging.getLogger(__name__)


class DocsScraper(BaseScraper):
    """
    Generic documentation site scraper with configurable CSS selectors.

    Subclasses set class attributes to configure site-specific behavior.
    The base class handles the full scraping lifecycle.

    REQUIRED CLASS ATTRIBUTES (set in subclass):
        - content_selector: CSS selector for the main content container
        - title_selector: CSS selector for the page title (usually h1)
        - source_site: String identifier for the source (e.g., "python_docs")

    OPTIONAL CLASS ATTRIBUTES:
        - remove_selectors: List of CSS selectors to remove before extraction
          (navigation, sidebars, footers, cookie banners, etc.)
        - rate_limit_delay: Seconds between requests (default 2.0)
    """

    # --- Subclasses MUST set these ---
    content_selector: str = "article"
    title_selector: str = "h1"
    source_site: str = "unknown"
    remove_selectors: list[str] = []
    # Fallback selectors tried if the primary content_selector times out
    fallback_selectors: list[str] = []
    # Wait strategy: "domcontentloaded" (fast) or "networkidle" (for JS-heavy sites)
    wait_until: str = "domcontentloaded"

    async def _scrape_with_retry(self, context, url):
        """
        Override to use configurable wait_until strategy.
        Falls back to alternative content selectors if the primary one fails.
        """
        from playwright.async_api import Page as PlaywrightPage
        from pydantic import ValidationError as PydanticValidationError

        last_error = None

        for attempt in range(1, self.max_retries + 1):
            try:
                page: PlaywrightPage = await context.new_page()
                try:
                    await page.goto(
                        url,
                        wait_until=self.wait_until,
                        timeout=self.page_timeout_ms,
                    )

                    # Try primary selector, then fallbacks
                    article = await self._extract_content(page, url)

                    if article is None and self.fallback_selectors:
                        original = self.content_selector
                        for fallback in self.fallback_selectors:
                            logger.info(
                                f"[{self.name}] Trying fallback selector: {fallback}"
                            )
                            self.content_selector = fallback
                            article = await self._extract_content(page, url)
                            if article is not None:
                                break
                        self.content_selector = original

                    return article

                finally:
                    await page.close()

            except PydanticValidationError as e:
                logger.error(f"[{self.name}] Validation error for {url}: {e}")
                return None
            except Exception as e:
                last_error = e
                logger.warning(
                    f"[{self.name}] Attempt {attempt}/{self.max_retries} "
                    f"failed for {url}: {type(e).__name__}: {e}"
                )
                if attempt < self.max_retries:
                    backoff = 2 ** attempt
                    logger.info(f"[{self.name}] Retrying in {backoff}s...")
                    import asyncio
                    await asyncio.sleep(backoff)

        logger.error(
            f"[{self.name}] All {self.max_retries} retries exhausted for {url}. "
            f"Last error: {last_error}"
        )
        return None

    async def _extract_content(
        self, page: Page, url: str
    ) -> Optional[ScrapedPage]:
        """
        Extract content from a documentation page using configured selectors.

        This method:
          1. Removes unwanted elements (nav, sidebar, ads)
          2. Extracts the title
          3. Extracts the main content as both text AND HTML
          4. Parses the HTML into sections by headings
          5. Returns a validated ScrapedPage

        Args:
            page: The loaded Playwright Page object.
            url: The URL being scraped.

        Returns:
            A validated ScrapedPage, or None if extraction fails.
        """
        # ----------------------------------------------------------
        # 1. REMOVE UNWANTED ELEMENTS
        # ----------------------------------------------------------
        # Many docs sites have navigation, sidebars, cookie banners,
        # and "edit on GitHub" links mixed into the content area.
        # We remove these BEFORE extracting text to get cleaner content.
        for selector in self.remove_selectors:
            try:
                await page.evaluate(
                    f"""document.querySelectorAll('{selector}')
                        .forEach(el => el.remove())"""
                )
            except Exception as e:
                logger.debug(
                    f"[{self.name}] Could not remove '{selector}': {e}"
                )

        # ----------------------------------------------------------
        # 2. EXTRACT TITLE
        # ----------------------------------------------------------
        title = None
        try:
            title_el = page.locator(self.title_selector).first
            title = await title_el.text_content(timeout=5000)
        except Exception as e:
            logger.debug(f"[{self.name}] Title extraction with '{self.title_selector}' failed: {e}")
            # Try common fallback title selectors
            for fb_title in ["h1", "h2", "title"]:
                try:
                    title = await page.locator(fb_title).first.text_content(timeout=3000)
                    if title and title.strip():
                        break
                except Exception:
                    continue
                title = None

        if not title or not title.strip():
            # Last resort: use the page's <title> tag
            try:
                title = await page.title()
            except Exception:
                pass

        if not title or not title.strip():
            logger.warning(f"[{self.name}] No title found on: {url}")
            return None

        title = title.strip()

        # ----------------------------------------------------------
        # 3. EXTRACT CONTENT (text + HTML)
        # ----------------------------------------------------------
        content_el = page.locator(self.content_selector).first

        try:
            raw_text = await content_el.inner_text(timeout=10000)
        except Exception as e:
            logger.debug(f"[{self.name}] Text extraction with '{self.content_selector}' failed: {e}")
            return None

        if not raw_text or len(raw_text.strip()) < 10:
            logger.warning(
                f"[{self.name}] Content too short on: {url}"
            )
            return None

        raw_text = raw_text.strip()

        try:
            raw_html = await content_el.inner_html(timeout=5000)
        except Exception as e:
            logger.warning(
                f"[{self.name}] HTML extraction failed, using text: {e}"
            )
            raw_html = f"<p>{raw_text}</p>"

        # ----------------------------------------------------------
        # 4. PARSE SECTIONS FROM HTML
        # ----------------------------------------------------------
        sections = await self._parse_sections_from_page(page)

        # ----------------------------------------------------------
        # 5. CREATE AND VALIDATE VIA PYDANTIC
        # ----------------------------------------------------------
        try:
            return ScrapedPage(
                title=title,
                url=url,
                raw_text=raw_text,
                raw_html=raw_html,
                source_site=self.source_site,
                sections=sections,
            )
        except Exception as e:
            logger.error(f"[{self.name}] Validation error: {e}")
            return None

    async def _parse_sections_from_page(self, page: Page) -> list[ScrapedSection]:
        """
        Parse the content area into sections by extracting heading elements
        and the content between them using JavaScript evaluation in the browser.

        This runs inside the browser context, so we have full DOM access
        to walk the tree and split by heading tags.
        """
        js_code = """
        (contentSelector) => {
            const container = document.querySelector(contentSelector);
            if (!container) return [];

            const sections = [];
            let currentSection = null;
            let sortOrder = 0;

            const allElements = container.querySelectorAll(
                'h1, h2, h3, h4, h5, h6, p, pre, ul, ol, dl, table, div.section, div[id]'
            );

            for (const el of allElements) {
                const tagName = el.tagName.toLowerCase();
                const headingMatch = tagName.match(/^h(\\d)$/);

                if (headingMatch) {
                    if (currentSection && currentSection.content.trim()) {
                        sections.push(currentSection);
                    }
                    currentSection = {
                        heading: el.textContent.trim(),
                        heading_level: parseInt(headingMatch[1]),
                        content: '',
                        sort_order: sortOrder++
                    };
                } else if (currentSection !== null) {
                    const text = el.textContent.trim();
                    if (text) {
                        currentSection.content += text + '\\n\\n';
                    }
                }
            }

            if (currentSection && currentSection.content.trim()) {
                sections.push(currentSection);
            }

            return sections;
        }
        """

        try:
            result = await page.evaluate(js_code, self.content_selector)
            sections = []
            for s in result:
                try:
                    sections.append(ScrapedSection(
                        heading=s.get("heading"),
                        content=s["content"].strip(),
                        heading_level=s.get("heading_level"),
                        sort_order=s.get("sort_order", 0),
                    ))
                except Exception:
                    continue
            return sections
        except Exception as e:
            logger.debug(f"[{self.name}] Section parsing failed: {e}")
            return []
