# ============================================================
# test_phase9b.py — Phase 9B Verification Test Script
# ============================================================
# Tests the Phase 9B multi-source scraping architecture WITHOUT
# doing live scraping (that requires internet and takes minutes).
#
# WHAT IT TESTS:
#   1. All scraper classes instantiate correctly
#   2. URL routing maps URLs to the correct scrapers
#   3. CSS selectors are configured for each scraper
#   4. ScrapedPage Pydantic model validates correctly
#   5. Section parser stores and retrieves sections
#   6. Topic URLs from DB are routed correctly
#   7. MultiSourceScraper orchestrator initializes
#
# HOW TO RUN:
#   python test_phase9b.py
#
# PREREQUISITES:
#   - Docker Compose running (PostgreSQL up)
#   - Phase 9A complete (tables + seed data)
# ============================================================

import sys
from pydantic import ValidationError

from database.connection import get_db_session
from database.models import RawArticle, SourceSection, Topic
from models.scraped_page import ScrapedPage, ScrapedSection
from pipeline.multi_source_scraper import (
    get_scraper_for_url,
    SCRAPER_ROUTING,
    MultiSourceScraper,
)
from pipeline.section_parser import store_sections, get_sections_for_article
from scraper.docs_scraper import DocsScraper
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


def test_scraper_classes():
    """Verify all scraper classes instantiate with correct config."""
    print("\n--- Scraper Class Tests ---")

    scrapers = [
        (PythonDocsScraper, "PythonDocs", "python_docs"),
        (FastAPIScraper, "FastAPI", "fastapi"),
        (SQLAlchemyScraper, "SQLAlchemy", "sqlalchemy_docs"),
        (LangChainScraper, "LangChain", "langchain_docs"),
        (DockerScraper, "Docker", "docker_docs"),
        (WeaviateScraper, "Weaviate", "weaviate_docs"),
        (PostgreSQLScraper, "PostgreSQL", "postgresql_docs"),
        (PydanticScraper, "Pydantic", "pydantic_docs"),
        (PlaywrightDocsScraper, "Playwright", "playwright_docs"),
        (GitHubScraper, "GitHub", "github_docs"),
    ]

    all_ok = True
    for cls, expected_name, expected_source in scrapers:
        scraper = cls()
        checks = [
            (scraper.name == expected_name, f"name={scraper.name}"),
            (scraper.source_site == expected_source, f"source_site={scraper.source_site}"),
            (len(scraper.content_selector) > 0, f"content_selector={scraper.content_selector}"),
            (len(scraper.title_selector) > 0, f"title_selector={scraper.title_selector}"),
            (scraper.rate_limit_delay >= 1.0, f"rate_limit={scraper.rate_limit_delay}s"),
        ]

        for ok, detail in checks:
            status = "OK" if ok else "FAIL"
            print(f"  [{status}] {cls.__name__}: {detail}")
            if not ok:
                all_ok = False

    return all_ok


def test_url_routing():
    """Verify URL routing maps URLs to correct scrapers."""
    print("\n--- URL Routing Tests ---")

    test_cases = [
        ("https://docs.python.org/3/library/asyncio.html", PythonDocsScraper),
        ("https://fastapi.tiangolo.com/tutorial/first-steps/", FastAPIScraper),
        ("https://docs.sqlalchemy.org/en/20/orm/quickstart.html", SQLAlchemyScraper),
        ("https://python.langchain.com/docs/concepts/chains/", LangChainScraper),
        ("https://docs.docker.com/get-started/introduction/", DockerScraper),
        ("https://weaviate.io/developers/weaviate/quickstart", WeaviateScraper),
    ]

    all_ok = True
    for url, expected_class in test_cases:
        result = get_scraper_for_url(url)
        if result == expected_class:
            print(f"  [OK] {url}")
            print(f"       -> {result.__name__}")
        else:
            actual = result.__name__ if result else "None"
            print(f"  [FAIL] {url}")
            print(f"         Expected: {expected_class.__name__}, Got: {actual}")
            all_ok = False

    # Test unknown domain
    unknown = get_scraper_for_url("https://example.com/docs")
    if unknown is None:
        print(f"  [OK] Unknown domain returns None")
    else:
        print(f"  [FAIL] Unknown domain should return None")
        all_ok = False

    return all_ok


def test_scraped_page_model():
    """Verify ScrapedPage Pydantic model validates correctly."""
    print("\n--- ScrapedPage Model Tests ---")

    # Valid page
    try:
        page = ScrapedPage(
            title="asyncio — Asynchronous I/O",
            url="https://docs.python.org/3/library/asyncio.html",
            raw_text="asyncio is a library to write concurrent code using the async/await syntax. It is used as a foundation for multiple Python asynchronous frameworks.",
            raw_html="<div><h2>Coroutines</h2><p>Coroutines declared with async def syntax.</p></div>",
            source_site="python_docs",
            sections=[
                ScrapedSection(
                    heading="Coroutines",
                    content="Coroutines declared with async def syntax.",
                    heading_level=2,
                    sort_order=0,
                ),
            ],
        )
        print(f"  [OK] Valid ScrapedPage created: '{page.title}'")
    except ValidationError as e:
        print(f"  [FAIL] Valid page rejected: {e}")
        return False

    # Test to_raw_article_dict conversion
    article_dict = page.to_raw_article_dict()
    assert "raw_html" not in article_dict
    assert "sections" not in article_dict
    assert article_dict["title"] == page.title
    print(f"  [OK] to_raw_article_dict() strips HTML/sections")

    # Invalid page (empty raw_text)
    try:
        ScrapedPage(
            title="Bad",
            url="https://example.com",
            raw_text="short",
            raw_html="<p>short</p>",
        )
        print(f"  [FAIL] Short raw_text should be rejected")
        return False
    except ValidationError:
        print(f"  [OK] Short raw_text correctly rejected")

    # Invalid section (content too short)
    try:
        ScrapedSection(heading="", content="", heading_level=2)
        print(f"  [FAIL] Empty section content should be rejected")
        return False
    except ValidationError:
        print(f"  [OK] Empty section content correctly rejected")

    return True


def test_section_parser():
    """Verify section parser stores and retrieves sections."""
    print("\n--- Section Parser Tests ---")

    with get_db_session() as session:
        # Find or create a test article
        test_article = session.query(RawArticle).first()
        if not test_article:
            print("  [SKIP] No articles in DB (need Phase 2 data)")
            return True

        test_sections = [
            ScrapedSection(
                heading="Test Section Alpha",
                content="This is the first test section content for Phase 9B verification.",
                heading_level=2,
                sort_order=0,
            ),
            ScrapedSection(
                heading="Test Section Beta",
                content="This is the second test section content for Phase 9B verification.",
                heading_level=3,
                sort_order=1,
            ),
        ]

        count = store_sections(session, test_article.id, test_sections)
        session.commit()

        if count == 2:
            print(f"  [OK] Stored {count} sections for article_id={test_article.id}")
        else:
            print(f"  [FAIL] Expected 2 sections, got {count}")
            return False

        retrieved = get_sections_for_article(session, test_article.id)
        if len(retrieved) >= 2:
            headings = [s["heading"] for s in retrieved if s["heading"]]
            print(f"  [OK] Retrieved {len(retrieved)} sections: {headings}")
        else:
            print(f"  [FAIL] Retrieved {len(retrieved)} sections (expected >=2)")
            return False

        # Test idempotency: store again should replace, not duplicate
        count2 = store_sections(session, test_article.id, test_sections)
        session.commit()
        retrieved2 = get_sections_for_article(session, test_article.id)
        if len(retrieved2) == 2:
            print(f"  [OK] Idempotent: re-stored still {len(retrieved2)} sections")
        else:
            print(f"  [FAIL] Idempotency broken: {len(retrieved2)} sections after re-store")
            return False

    return True


def test_topic_urls_in_db():
    """Verify topics have source_urls that map to known scrapers."""
    print("\n--- Topic URL Routing Tests ---")

    with get_db_session() as session:
        topics = session.query(Topic).all()
        if not topics:
            print("  [FAIL] No topics found (run test_phase9a.py first)")
            return False

        routable = 0
        unroutable = 0
        for topic in topics:
            for url in topic.source_urls:
                scraper = get_scraper_for_url(url)
                if scraper:
                    routable += 1
                else:
                    unroutable += 1
                    print(f"  [WARN] Unroutable URL in topic '{topic.slug}': {url}")

        print(f"  [OK] {routable} URLs routable across {len(topics)} topics")
        if unroutable > 0:
            print(f"  [WARN] {unroutable} URLs could not be routed to a scraper")

    return unroutable == 0


def test_orchestrator_init():
    """Verify MultiSourceScraper initializes correctly."""
    print("\n--- Orchestrator Tests ---")

    orchestrator = MultiSourceScraper()
    print(f"  [OK] MultiSourceScraper initialized")

    topic_data = orchestrator._read_topic_urls()
    if topic_data:
        print(f"  [OK] Read {len(topic_data)} topics with URLs from DB")
        total_urls = sum(len(urls) for _, _, urls in topic_data)
        print(f"  [OK] Total source URLs: {total_urls}")
    else:
        print(f"  [FAIL] No topic URLs found (run test_phase9a.py)")
        return False

    grouped = orchestrator._group_urls_by_scraper(topic_data)
    print(f"  [OK] URLs grouped into {len(grouped)} scraper buckets:")
    for name, urls in grouped.items():
        print(f"       {name}: {len(urls)} URLs")

    return True


def main():
    print("=" * 60)
    print("PHASE 9B — MULTI-SOURCE SCRAPER VERIFICATION")
    print("=" * 60)

    results = []

    print("\n[Step 1] Testing scraper classes...")
    results.append(("Scraper Classes", test_scraper_classes()))

    print("\n[Step 2] Testing URL routing...")
    results.append(("URL Routing", test_url_routing()))

    print("\n[Step 3] Testing ScrapedPage model...")
    results.append(("ScrapedPage Model", test_scraped_page_model()))

    print("\n[Step 4] Testing section parser...")
    results.append(("Section Parser", test_section_parser()))

    print("\n[Step 5] Testing topic URL routing from DB...")
    results.append(("Topic URL Routing", test_topic_urls_in_db()))

    print("\n[Step 6] Testing orchestrator initialization...")
    results.append(("Orchestrator", test_orchestrator_init()))

    print("\n" + "=" * 60)
    print("RESULTS SUMMARY")
    print("=" * 60)

    all_passed = True
    for name, passed in results:
        status = "PASS" if passed else "FAIL"
        print(f"  {status:6s} — {name}")
        if not passed:
            all_passed = False

    print("=" * 60)
    if all_passed:
        print("ALL TESTS PASSED!")
        print("\nNext step: Run `python scrape_all.py` to perform live scraping.")
    else:
        print("SOME TESTS FAILED — review output above")
        sys.exit(1)


if __name__ == "__main__":
    main()
