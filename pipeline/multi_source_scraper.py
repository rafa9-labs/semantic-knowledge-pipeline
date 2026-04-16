# ============================================================
# pipeline/multi_source_scraper.py — Multi-Source Scraping Orchestrator
# ============================================================
# This module is the BRAINS of Phase 9B's multi-source scraping.
# It:
#   1. Reads all topics and their source_urls from the database
#   2. Groups URLs by domain (which scraper handles this site?)
#   3. Instantiates the correct scraper for each domain
#   4. Scrapes all URLs, stores articles with topic_id, and stores sections
#   5. Returns a summary of what was scraped
#
# WHY AN ORCHESTRATOR?
#   We have 7 different documentation sources, each with its own scraper.
#   We could manually run each scraper, but that's error-prone and tedious.
#   The orchestrator automates the full flow:
#     DB topics → URL routing → scraping → validation → storage → sections
#
# URL ROUTING:
#   The orchestrator maps domain substrings to scraper classes:
#     "docs.python.org"       → PythonDocsScraper
#     "fastapi.tiangolo.com"  → FastAPIScraper
#     "docs.sqlalchemy.org"   → SQLAlchemyScraper
#     "python.langchain.com"  → LangChainScraper
#     "docs.docker.com"       → DockerScraper
#     "weaviate.io"           → WeaviateScraper
#
# USAGE:
#   from pipeline.multi_source_scraper import MultiSourceScraper
#
#   orchestrator = MultiSourceScraper()
#   results = await orchestrator.scrape_all_topics()
#   print(results)
# ============================================================

import asyncio
import logging
from collections import defaultdict
from typing import Optional
from urllib.parse import urlparse

from sqlalchemy.orm import Session

from database.connection import get_db_session
from database.models import RawArticle, Topic
from models.scraped_page import ScrapedPage
from pipeline.section_parser import store_sections
from scraper.python_docs_scraper import PythonDocsScraper
from scraper.fastapi_scraper import FastAPIScraper
from scraper.sqlalchemy_scraper import SQLAlchemyScraper
from scraper.langchain_scraper import LangChainScraper
from scraper.docker_scraper import DockerScraper
from scraper.weaviate_scraper import WeaviateScraper
from scraper.postgresql_scraper import PostgreSQLScraper
from scraper.pydantic_scraper import PydanticScraper
from scraper.playwright_docs_scraper import PlaywrightDocsScraper
from scraper.github_scraper import GitHubScraper

logger = logging.getLogger(__name__)


# ----------------------------------------------------------
# URL -> SCRAPER ROUTING TABLE
# ----------------------------------------------------------
# Maps domain substrings to their scraper classes.
# The orchestrator checks each URL's domain against these patterns.
# First match wins (order matters if domains overlap).

SCRAPER_ROUTING: list[tuple[str, type]] = [
    ("docs.python.org", PythonDocsScraper),
    ("fastapi.tiangolo.com", FastAPIScraper),
    ("docs.sqlalchemy.org", SQLAlchemyScraper),
    ("python.langchain.com", LangChainScraper),
    ("docs.docker.com", DockerScraper),
    ("weaviate.io", WeaviateScraper),
    ("www.postgresql.org", PostgreSQLScraper),
    ("postgresql.org", PostgreSQLScraper),
    ("docs.pydantic.dev", PydanticScraper),
    ("playwright.dev", PlaywrightDocsScraper),
    ("github.com", GitHubScraper),
    ("docs.github.com", GitHubScraper),
    ("developer.mozilla.org", PlaywrightDocsScraper),
]


def get_scraper_for_url(url: str) -> Optional[type]:
    """
    Determine which scraper class handles a given URL.

    Checks the URL's domain against the routing table.
    Returns the first matching scraper class, or None.

    Args:
        url: The URL to route.

    Returns:
        A DocsScraper subclass, or None if no scraper matches.
    """
    parsed = urlparse(url)
    domain = parsed.netloc.lower()

    for domain_pattern, scraper_class in SCRAPER_ROUTING:
        if domain_pattern in domain:
            return scraper_class

    logger.warning(f"No scraper found for domain: {domain} (URL: {url})")
    return None


class MultiSourceScraper:
    """
    Orchestrates multi-source scraping across all documentation sites.

    Reads topics and source_urls from the database, routes each URL
    to the appropriate scraper, and stores the results.

    USAGE:
        orchestrator = MultiSourceScraper()
        results = await orchestrator.scrape_all_topics()
    """

    def __init__(self, max_concurrent_scrapers: int = 1):
        """
        Args:
            max_concurrent_scrapers: How many scrapers to run in parallel.
                Default 1 (sequential) for safety — we don't want to
                overwhelm documentation servers with too many concurrent
                requests. Increase only if you're confident about rate limits.
        """
        self.max_concurrent_scrapers = max_concurrent_scrapers

    def _read_topic_urls(self) -> list[tuple[int, str, list[str]]]:
        """
        Read all topics and their source_urls from the database.

        Returns:
            List of (topic_id, topic_slug, [source_urls]) tuples.
        """
        with get_db_session() as session:
            topics = session.query(Topic).all()
            result = []
            for topic in topics:
                if topic.source_urls and len(topic.source_urls) > 0:
                    result.append(
                        (topic.id, topic.slug, topic.source_urls)
                    )
            return result

    def _group_urls_by_scraper(
        self, topic_data: list[tuple[int, str, list[str]]]
    ) -> dict[str, list[tuple[str, int, str]]]:
        """
        Group URLs by which scraper handles them.

        Args:
            topic_data: List of (topic_id, topic_slug, [urls]) tuples.

        Returns:
            Dict mapping scraper class name to list of (url, topic_id, topic_slug).
        """
        grouped: dict[str, list[tuple[str, int, str]]] = defaultdict(list)

        for topic_id, topic_slug, urls in topic_data:
            for url in urls:
                scraper_class = get_scraper_for_url(url)
                if scraper_class:
                    key = scraper_class.__name__
                    grouped[key].append((url, topic_id, topic_slug))
                else:
                    logger.warning(
                        f"Skipping URL (no scraper): {url} "
                        f"(topic: {topic_slug})"
                    )

        return grouped

    async def _scrape_with_scraper(
        self,
        scraper_class: type,
        url_topic_pairs: list[tuple[str, int, str]],
    ) -> list[tuple[ScrapedPage, int]]:
        """
        Scrape a batch of URLs using a single scraper instance.

        Args:
            scraper_class: The DocsScraper subclass to use.
            url_topic_pairs: List of (url, topic_id, topic_slug).

        Returns:
            List of (ScrapedPage, topic_id) tuples for successful scrapes.
        """
        scraper = scraper_class()
        urls = [pair[0] for pair in url_topic_pairs]
        topic_ids = {pair[0]: pair[1] for pair in url_topic_pairs}

        scraped_pages = await scraper.scrape(urls)

        results = []
        for page in scraped_pages:
            page_url = str(page.url)
            topic_id = topic_ids.get(page_url)
            if topic_id is not None:
                results.append((page, topic_id))
            else:
                logger.warning(
                    f"[{scraper.name}] Scraped page URL not in expected set: "
                    f"{page_url}"
                )

        return results

    def _store_results(
        self, pages: list[tuple[ScrapedPage, int]]
    ) -> dict:
        """
        Store scraped pages in the database.

        For each page:
          1. Check if article already exists (by URL) — idempotent
          2. Create RawArticle row with topic_id
          3. Parse and store sections in source_sections

        Args:
            pages: List of (ScrapedPage, topic_id) tuples.

        Returns:
            Summary dict with counts.
        """
        stats = {
            "articles_stored": 0,
            "articles_skipped": 0,
            "articles_failed": 0,
            "sections_stored": 0,
        }

        for page, topic_id in pages:
            try:
                with get_db_session() as session:
                    existing = session.query(RawArticle).filter_by(
                        url=str(page.url)
                    ).first()

                    if existing:
                        logger.info(
                            f"  SKIPPED (duplicate): {page.title[:60]}"
                        )
                        stats["articles_skipped"] += 1
                        continue

                    article_dict = page.to_raw_article_dict()
                    article_row = RawArticle(
                        **article_dict,
                        topic_id=topic_id,
                    )
                    session.add(article_row)
                    session.flush()

                    if page.sections:
                        section_count = store_sections(
                            session, article_row.id, page.sections
                        )
                        stats["sections_stored"] += section_count

                    session.commit()
                    stats["articles_stored"] += 1
                    logger.info(
                        f"  STORED: {page.title[:60]} "
                        f"({len(page.sections)} sections)"
                    )

            except Exception as e:
                logger.error(
                    f"  FAILED: {page.title[:60]} — {e}"
                )
                stats["articles_failed"] += 1

        return stats

    async def scrape_all_topics(self) -> dict:
        """
        Main entry point: scrape all topics' source_urls.

        This is the full orchestrator flow:
          1. Read topics + source_urls from DB
          2. Group URLs by scraper
          3. Scrape each group
          4. Store results

        Returns:
            Summary dict with all counts.
        """
        logger.info("=" * 60)
        logger.info("MULTI-SOURCE SCRAPER — Starting")
        logger.info("=" * 60)

        # Step 1: Read topic URLs from DB
        topic_data = self._read_topic_urls()
        total_urls = sum(len(urls) for _, _, urls in topic_data)
        logger.info(
            f"Found {len(topic_data)} topics with {total_urls} total URLs"
        )

        if not topic_data:
            logger.warning("No topic URLs found in database")
            return {"error": "No topic URLs found"}

        # Step 2: Group URLs by scraper
        grouped = self._group_urls_by_scraper(topic_data)

        logger.info("URL distribution:")
        for scraper_name, url_list in grouped.items():
            logger.info(f"  {scraper_name}: {len(url_list)} URLs")

        # Step 3: Scrape each group
        all_pages: list[tuple[ScrapedPage, int]] = []

        for scraper_name, url_topic_pairs in grouped.items():
            scraper_class = None
            for _, cls in SCRAPER_ROUTING:
                if cls.__name__ == scraper_name:
                    scraper_class = cls
                    break

            if not scraper_class:
                continue

            logger.info(
                f"\n[{scraper_name}] Scraping {len(url_topic_pairs)} URLs..."
            )

            try:
                pages = await self._scrape_with_scraper(
                    scraper_class, url_topic_pairs
                )
                all_pages.extend(pages)
                logger.info(
                    f"[{scraper_name}] Success: {len(pages)}/{len(url_topic_pairs)}"
                )
            except Exception as e:
                logger.error(f"[{scraper_name}] Scraper failed: {e}")

        # Step 4: Store results
        logger.info(f"\nStoring {len(all_pages)} scraped pages...")
        stats = self._store_results(all_pages)

        logger.info("\n" + "=" * 60)
        logger.info("MULTI-SOURCE SCRAPER — Complete")
        logger.info(f"  Articles stored:  {stats['articles_stored']}")
        logger.info(f"  Articles skipped: {stats['articles_skipped']}")
        logger.info(f"  Articles failed:  {stats['articles_failed']}")
        logger.info(f"  Sections stored:  {stats['sections_stored']}")
        logger.info("=" * 60)

        return stats
