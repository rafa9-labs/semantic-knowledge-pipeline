from database.connection import engine, get_db_session
from database.models import KnowledgeTripleDB

with get_db_session() as session:
    rows = session.query(KnowledgeTripleDB).all()
    print(f"Total triples: {len(rows)}")
    for r in rows:
        print(f"  {r.subject} -[{r.predicate}]-> {r.object_value} (conf={r.confidence})")