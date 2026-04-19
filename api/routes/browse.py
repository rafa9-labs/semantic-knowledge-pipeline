import logging
from fastapi import APIRouter
from sqlalchemy import func
from database.connection import get_db_session
from database.models import Domain, Topic, Concept, Example, Exercise

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/knowledge", tags=["Knowledge Browsing"])


@router.get("/domains")
def list_domains():
    with get_db_session() as session:
        domains = session.query(Domain).order_by(Domain.sort_order).all()
        result = []
        for d in domains:
            topic_count = session.query(func.count(Topic.id)).filter(Topic.domain_id == d.id).scalar()
            result.append({
                "id": d.id,
                "name": d.name,
                "slug": d.slug,
                "description": d.description,
                "icon": d.icon,
                "topic_count": topic_count,
            })
        return result


@router.get("/topics")
def list_topics():
    with get_db_session() as session:
        topics = session.query(Topic).order_by(Topic.sort_order).all()
        result = []
        for t in topics:
            concept_count = session.query(func.count(Concept.id)).filter(Concept.topic_id == t.id).scalar()
            domain = session.query(Domain).filter(Domain.id == t.domain_id).first()
            result.append({
                "id": t.id,
                "name": t.name,
                "slug": t.slug,
                "description": t.description,
                "difficulty": t.difficulty,
                "concept_count": concept_count,
                "domain_name": domain.name if domain else None,
                "domain_slug": domain.slug if domain else None,
            })
        return result


@router.get("/topics/{slug}")
def get_topic(slug: str):
    with get_db_session() as session:
        topic = session.query(Topic).filter(Topic.slug == slug).first()
        if not topic:
            return {"error": "Topic not found"}, 404
        domain = session.query(Domain).filter(Domain.id == topic.domain_id).first()
        concepts = session.query(Concept).filter(Concept.topic_id == topic.id).order_by(Concept.slug).all()
        return {
            "id": topic.id,
            "name": topic.name,
            "slug": topic.slug,
            "description": topic.description,
            "difficulty": topic.difficulty,
            "domain_name": domain.name if domain else None,
            "domain_slug": domain.slug if domain else None,
            "concepts": [
                {
                    "id": c.id,
                    "name": c.name,
                    "slug": c.slug,
                    "category": c.category,
                    "difficulty": c.difficulty,
                    "has_eli5": c.simple_explanation is not None,
                    "has_theory": c.theory_text is not None,
                }
                for c in concepts
            ],
        }


@router.get("/concepts/slug/{topic_slug}/{concept_slug}")
def get_concept_by_slug(topic_slug: str, concept_slug: str):
    with get_db_session() as session:
        topic = session.query(Topic).filter(Topic.slug == topic_slug).first()
        if not topic:
            return {"error": "Topic not found"}, 404
        concept = session.query(Concept).filter(
            Concept.topic_id == topic.id,
            Concept.slug == concept_slug,
        ).first()
        if not concept:
            return {"error": "Concept not found"}, 404
        examples = session.query(Example).filter(Example.concept_id == concept.id).order_by(Example.sort_order).all()
        exercises = session.query(Exercise).filter(Exercise.concept_id == concept.id).order_by(Exercise.sort_order).all()

        from_concepts = []
        for r in concept.outgoing_relationships:
            fc = session.query(Concept).filter(Concept.id == r.to_concept_id).first()
            if fc:
                from_concepts.append({"id": fc.id, "name": fc.name, "slug": fc.slug, "type": r.relationship_type})

        to_concepts = []
        for r in concept.incoming_relationships:
            tc = session.query(Concept).filter(Concept.id == r.from_concept_id).first()
            if tc:
                to_concepts.append({"id": tc.id, "name": tc.name, "slug": tc.slug, "type": r.relationship_type})

        return {
            "id": concept.id,
            "name": concept.name,
            "slug": concept.slug,
            "category": concept.category,
            "difficulty": concept.difficulty,
            "theory_text": concept.theory_text,
            "simple_explanation": concept.simple_explanation,
            "key_points": concept.key_points,
            "common_mistakes": concept.common_mistakes,
            "topic_name": topic.name,
            "topic_slug": topic.slug,
            "examples": [
                {
                    "id": e.id,
                    "title": e.title,
                    "description": e.description,
                    "code": e.code,
                    "language": e.language,
                    "explanation": e.explanation,
                    "source_type": e.source_type,
                }
                for e in examples
            ],
            "exercises": [
                {
                    "id": ex.id,
                    "title": ex.title,
                    "description": ex.description,
                    "difficulty": ex.difficulty,
                    "language": ex.language,
                    "starter_code": ex.starter_code,
                    "solution_code": ex.solution_code,
                    "hints": ex.hints,
                    "learning_objectives": ex.learning_objectives,
                }
                for ex in exercises
            ],
            "relationships": {
                "outgoing": from_concepts,
                "incoming": to_concepts,
            },
        }


@router.get("/concepts/{concept_id}")
def get_concept(concept_id: int):
    with get_db_session() as session:
        concept = session.query(Concept).filter(Concept.id == concept_id).first()
        if not concept:
            return {"error": "Concept not found"}, 404
        topic = session.query(Topic).filter(Topic.id == concept.topic_id).first()
        examples = session.query(Example).filter(Example.concept_id == concept.id).order_by(Example.sort_order).all()
        exercises = session.query(Exercise).filter(Exercise.concept_id == concept.id).order_by(Exercise.sort_order).all()

        from_concepts = []
        for r in concept.outgoing_relationships:
            fc = session.query(Concept).filter(Concept.id == r.to_concept_id).first()
            if fc:
                from_concepts.append({"id": fc.id, "name": fc.name, "slug": fc.slug, "type": r.relationship_type})

        to_concepts = []
        for r in concept.incoming_relationships:
            tc = session.query(Concept).filter(Concept.id == r.from_concept_id).first()
            if tc:
                to_concepts.append({"id": tc.id, "name": tc.name, "slug": tc.slug, "type": r.relationship_type})

        return {
            "id": concept.id,
            "name": concept.name,
            "slug": concept.slug,
            "category": concept.category,
            "difficulty": concept.difficulty,
            "theory_text": concept.theory_text,
            "simple_explanation": concept.simple_explanation,
            "key_points": concept.key_points,
            "common_mistakes": concept.common_mistakes,
            "topic_name": topic.name if topic else None,
            "topic_slug": topic.slug if topic else None,
            "examples": [
                {
                    "id": e.id,
                    "title": e.title,
                    "description": e.description,
                    "code": e.code,
                    "language": e.language,
                    "explanation": e.explanation,
                    "source_type": e.source_type,
                }
                for e in examples
            ],
            "exercises": [
                {
                    "id": ex.id,
                    "title": ex.title,
                    "description": ex.description,
                    "difficulty": ex.difficulty,
                    "language": ex.language,
                    "starter_code": ex.starter_code,
                    "hints": ex.hints,
                    "learning_objectives": ex.learning_objectives,
                }
                for ex in exercises
            ],
            "relationships": {
                "outgoing": from_concepts,
                "incoming": to_concepts,
            },
        }
