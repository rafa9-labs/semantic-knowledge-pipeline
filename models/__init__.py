# ============================================================
# models/ — Pydantic Schemas for Data Validation
# ============================================================
# This package contains ALL Pydantic models that define the "shape"
# of data as it flows through our pipeline:
#
#   Scraper → RawScrapedArticle → Database
#   Database → ProcessedConcept → LLM Pipeline
#   LLM Pipeline → StructuredRelationship → Vector DB
#
# Every data transfer MUST pass through a model defined here.
# This is our single source of truth for data contracts.
#
# Example future files:
#   - content.py      → RawScrapedArticle (raw scraped data)
#   - concepts.py     → EducationalConcept (LLM-processed)
#   - relationships.py → ConceptRelationship (graph edges)
# ============================================================