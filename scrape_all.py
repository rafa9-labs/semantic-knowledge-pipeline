# ============================================================
# scrape_all.py — Multi-Source Documentation Scraper Entry Point
# ============================================================
# This script runs the Phase 9B multi-source scraping pipeline.
# It reads all topics and source_urls from the database, scrapes
# each URL using the appropriate documentation scraper, stores the
# articles with topic_id, and parses them into sections.
#
# HOW TO RUN:
#   python scrape_all.py
#
# WHAT IT DOES:
#   1. Reads topics from DB (6 domains, ~23 topics, ~70 URLs)
#   2. Routes each URL to the right scraper (Python/FastAPI/SQLAlchemy/etc.)
#   3. Scrapes all URLs using Playwright headless browser
#   4. Stores articles in raw_articles (with topic_id set)
#   5. Parses and stores sections in source_sections
#
# PREREQUISITES:
#   - Docker Compose running (PostgreSQL up)
#   - Phase 9A tables + seed data loaded (run test_phase9a.py first)
#   - Internet connection (scraping live docs sites)
#
# ESTIMATED TIME:
#   ~70 URLs × 2s rate limit = ~2.5 minutes
# ============================================================

import asyncio
import logging

from pipeline.multi_source_scraper import MultiSourceScraper

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


async def main():
    logger.info("=" * 60)
    logger.info("PHASE 9B — MULTI-SOURCE DOCUMENTATION SCRAPER")
    logger.info("=" * 60)

    orchestrator = MultiSourceScraper()
    results = await orchestrator.scrape_all_topics()

    if "error" in results:
        logger.error(f"Pipeline error: {results['error']}")
        logger.error("Did you run test_phase9a.py first to seed topics?")
        return

    print("\n" + "=" * 60)
    print("RESULTS SUMMARY")
    print("=" * 60)
    print(f"  Articles stored:  {results.get('articles_stored', 0)}")
    print(f"  Articles skipped: {results.get('articles_skipped', 0)}")
    print(f"  Articles failed:  {results.get('articles_failed', 0)}")
    print(f"  Sections stored:  {results.get('sections_stored', 0)}")
    print("=" * 60)

    if results.get("articles_failed", 0) > 0:
        print("\nSome articles failed. Check the logs above for details.")
        print("Common causes: network issues, site structure changes, timeouts.")


if __name__ == "__main__":
    asyncio.run(main())
