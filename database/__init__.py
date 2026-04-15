# ============================================================
# database/ — SQLAlchemy ORM & Connection Module
# ============================================================
# This package handles ALL database interactions:
#   - Defining SQLAlchemy table models (ORM = Object Relational Mapping)
#   - Managing connection pools (so we don't open/close a connection per query)
#   - CRUD operations (Create, Read, Update, Delete)
#
# Example future files:
#   - connection.py   → Engine + session factory (async ready)
#   - models.py       → SQLAlchemy ORM models (maps Python classes → DB tables)
#   - crud.py         → Insert/query functions for our data
# ============================================================