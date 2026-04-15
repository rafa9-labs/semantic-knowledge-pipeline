"""
Test script for the MDN scraper.
Scrapes real MDN pages and stores them in PostgreSQL.

Run: python test_scraper.py
"""

import asyncio
import logging

from scraper.mdn_scraper import MdnScraper
from database.connection import engine, Base, get_db_session
from database.models import RawArticle

# Configure logging so we can see what the scraper is doing
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)


async def main():
    # Step 1: Ensure database table exists
    print("Ensuring database table exists...")
    Base.metadata.create_all(engine)

    # Step 2: Scrape some MDN pages
    urls = [
        "https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Statements/async_function",
        "https://developer.mozilla.org/en-US/docs/Web/API/Fetch_API/Using_Fetch",
    ]

    print(f"\nScraping {len(urls)} MDN pages...")
    scraper = MdnScraper()
    articles = await scraper.scrape(urls)

    # Step 3: Store results in PostgreSQL
    print(f"\nStoring {len(articles)} articles in PostgreSQL...")
    with get_db_session() as session:
        for article in articles:
            # Check if URL already exists (avoid duplicates)
            existing = session.query(RawArticle).filter_by(url=str(article.url)).first()
            if existing:
                print(f"  SKIPPED (already exists): {article.title[:50]}...")
                continue

            row = RawArticle(
                title=article.title,
                url=str(article.url),
                raw_text=article.raw_text,
                source_site=article.source_site,
            )
            session.add(row)
            print(f"  STORED: {article.title[:60]}...")

        session.commit()

    # Step 4: Show what's in the database
    with get_db_session() as session:
        all_rows = session.query(RawArticle).all()
        print(f"\nTotal articles in database: {len(all_rows)}")
        for r in all_rows:
            text_preview = r.raw_text[:80].replace("\n", " ")
            print(f"  [{r.id}] {r.title}")
            print(f"       Source: {r.source_site} | Text: {text_preview}...")


if __name__ == "__main__":
    asyncio.run(main())