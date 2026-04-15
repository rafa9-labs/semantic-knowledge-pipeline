# ============================================================
# scraper/ — Playwright Scraping Module
# ============================================================
# This package will contain our async web scrapers powered by Playwright.
# Each scraper targets a specific documentation site and outputs
# validated Pydantic models (RawScrapedArticle instances).
#
# Example future files:
#   - base_scraper.py    → Abstract base class with shared retry/error logic
#   - mdn_scraper.py     → Scrapes Mozilla Developer Network docs
#   - python_docs_scraper.py → Scrapes Python official docs
# ============================================================