# ============================================================
# test_curriculum.py — Test Curriculum Generation (standalone)
# ============================================================
# This script tests ONLY the curriculum generation step.
# It reads existing data from the database (triples + articles)
# and generates a curriculum without re-scraping or re-extracting.
#
# Run: python test_curriculum.py
# ============================================================

import logging

from database.connection import engine, Base, get_db_session
from database.models import (
    RawArticle, KnowledgeTripleDB,
    CurriculumDB, ModuleDB, LessonDB,
)
from pipeline.curriculum_agent import CurriculumAgent

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


def main():
    # Ensure new tables exist
    Base.metadata.create_all(engine)

    # Read existing knowledge graph data
    with get_db_session() as session:
        triples = session.query(KnowledgeTripleDB).all()
        articles = session.query(RawArticle).all()

        triples_data = [
            {
                "subject": t.subject,
                "predicate": t.predicate,
                "object_value": t.object_value,
                "confidence": t.confidence,
            }
            for t in triples
        ]
        articles_data = [
            {
                "title": a.title,
                "url": a.url,
                "raw_text": a.raw_text,
            }
            for a in articles
        ]

    print(f"📚 Knowledge Graph: {len(triples_data)} triples, {len(articles_data)} articles\n")

    # Generate curriculum
    agent = CurriculumAgent(model_name="gemma4:26b", temperature=0.3, max_retries=3)

    curriculum = agent.generate_curriculum(
        topic="Async JavaScript",
        triples=triples_data,
        articles=articles_data,
        target_audience="Junior to mid-level JavaScript developers",
        difficulty="intermediate",
    )

    if not curriculum:
        print("❌ Curriculum generation failed!")
        return

    print(f"\n✅ Generated: '{curriculum.title}'")
    print(f"   {curriculum.description}\n")

    # Store in database
    with get_db_session() as session:
        curriculum_row = CurriculumDB(
            title=curriculum.title,
            description=curriculum.description,
            topic=curriculum.topic,
            target_audience=curriculum.target_audience,
            difficulty=curriculum.difficulty,
            model_name=curriculum.model_name,
        )
        session.add(curriculum_row)
        session.flush()

        for mod in curriculum.modules:
            module_row = ModuleDB(
                title=mod.title,
                description=mod.description,
                order_index=mod.order_index,
                curriculum_id=curriculum_row.id,
            )
            session.add(module_row)
            session.flush()

            for lesson in mod.lessons:
                lesson_row = LessonDB(
                    title=lesson.title,
                    description=lesson.description,
                    order_index=lesson.order_index,
                    learning_objectives=lesson.learning_objectives,
                    prerequisites=lesson.prerequisites,
                    source_urls=lesson.source_urls,
                    module_id=module_row.id,
                )
                session.add(lesson_row)

        session.commit()
        print("💾 Stored in database!\n")

    # Pretty print
    print("=" * 60)
    print(f"📖 {curriculum.title}")
    print(f"   Topic: {curriculum.topic} | Difficulty: {curriculum.difficulty}")
    print(f"   Audience: {curriculum.target_audience}")
    print()
    for mod in sorted(curriculum.modules, key=lambda x: x.order_index):
        print(f"  📂 Module {mod.order_index}: {mod.title}")
        print(f"     {mod.description}")
        for lesson in sorted(mod.lessons, key=lambda x: x.order_index):
            print(f"     📄 Lesson {lesson.order_index}: {lesson.title}")
            print(f"        {lesson.description}")
            print(f"        Objectives:")
            for obj in lesson.learning_objectives:
                print(f"          ✅ {obj}")
            if lesson.prerequisites:
                print(f"        Prerequisites:")
                for pre in lesson.prerequisites:
                    print(f"          🔗 {pre}")
            print()
    print("=" * 60)


if __name__ == "__main__":
    main()