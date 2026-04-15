"""
Quick test script to verify the full database pipeline:
  Pydantic Validation → SQLAlchemy ORM → PostgreSQL Storage

Run: python test_db_setup.py
"""

from database.connection import engine, Base, get_db_session
from database.models import RawArticle
from models.content import RawScrapedArticle

# Step 1: Create the table in PostgreSQL
print("Creating table...")
Base.metadata.create_all(engine)
print("Table 'raw_articles' created!")

# Step 2: Validate data with Pydantic
validated = RawScrapedArticle(
    title="Python AsyncIO Documentation",
    url="https://docs.python.org/3/library/asyncio.html",
    raw_text=(
        "Asyncio is a library to write concurrent code using the "
        "async/await syntax. It is used as a foundation for multiple "
        "Python asynchronous frameworks."
    ),
    source_site="python_docs",
)
print(f"Pydantic validated: {validated.title}")

# Step 3: Insert into PostgreSQL via SQLAlchemy
with get_db_session() as session:
    row = RawArticle(
        title=validated.title,
        url=str(validated.url),
        raw_text=validated.raw_text,
        source_site=validated.source_site,
    )
    session.add(row)
    session.commit()
    session.refresh(row)
    print(f"DB inserted: {row}")

# Step 4: Read it back to verify
with get_db_session() as session:
    all_rows = session.query(RawArticle).all()
    print(f"\nTotal articles in DB: {len(all_rows)}")
    for r in all_rows:
        print(f"  [{r.id}] {r.title} ({r.source_site})")

print("\nFull pipeline test PASSED!")