# ============================================================
# api/routes/curricula.py — Curriculum Endpoints
# ============================================================
# These endpoints expose our AI-generated curricula via REST API.
#
# REST CONVENTION:
#   GET    /curricula          → List all curricula (summary)
#   GET    /curricula/{id}     → Get one curriculum (full detail)
#   POST   /curricula/generate → Generate a new curriculum
#
# WHY FastAPI ROUTERS?
#   Instead of putting ALL endpoints in one file, we split them
#   into "routers" — one per resource. This keeps the codebase
#   modular and each file focused on one concern.
# ============================================================

import logging

from fastapi import APIRouter, HTTPException

from database.connection import get_db_session
from database.models import CurriculumDB, ModuleDB, LessonDB, KnowledgeTripleDB, RawArticle
from pipeline.curriculum_agent import CurriculumAgent
from api.schemas.responses import (
    CurriculumSummaryResponse,
    CurriculumDetailResponse,
    CurriculumListResponse,
    ModuleResponse,
    LessonResponse,
    CurriculumGenerateRequest,
    CurriculumGenerateResponse,
)

logger = logging.getLogger(__name__)

# --- Create a FastAPI Router ---
# A Router is like a "mini-app" — we define routes here, then
# include them in the main app with app.include_router(router).
router = APIRouter(prefix="/api/curricula", tags=["Curricula"])


@router.get("", response_model=CurriculumListResponse)
def list_curricula():
    """
    List all generated curricula (summary view).

    Returns metadata for each curriculum WITHOUT the full module/lesson tree.
    This is fast — we only query the curricula table, not the nested data.
    """
    with get_db_session() as session:
        curricula = session.query(CurriculumDB).order_by(CurriculumDB.created_at.desc()).all()

        summaries = []
        for c in curricula:
            # Count modules and lessons without loading full relationships
            module_count = session.query(ModuleDB).filter_by(curriculum_id=c.id).count()
            lesson_count = (
                session.query(LessonDB)
                .join(ModuleDB)
                .filter(ModuleDB.curriculum_id == c.id)
                .count()
            )

            summaries.append(CurriculumSummaryResponse(
                id=c.id,
                title=c.title,
                description=c.description,
                topic=c.topic,
                target_audience=c.target_audience,
                difficulty=c.difficulty,
                model_name=c.model_name,
                module_count=module_count,
                lesson_count=lesson_count,
                created_at=c.created_at,
            ))

        return CurriculumListResponse(total=len(summaries), curricula=summaries)


@router.get("/{curriculum_id}", response_model=CurriculumDetailResponse)
def get_curriculum(curriculum_id: int):
    """
    Get a single curriculum with ALL modules and lessons.

    This loads the full hierarchical tree:
      Curriculum → Modules → Lessons

    If the curriculum doesn't exist, returns 404.
    """
    with get_db_session() as session:
        curriculum = session.query(CurriculumDB).filter_by(id=curriculum_id).first()

        if not curriculum:
            raise HTTPException(
                status_code=404,
                detail=f"Curriculum with id={curriculum_id} not found",
            )

        # Build the nested response manually from SQLAlchemy objects.
        # We sort modules and lessons by order_index so they display correctly.
        modules_response = []
        for mod in sorted(curriculum.modules, key=lambda m: m.order_index):
            lessons_response = [
                LessonResponse(
                    id=l.id,
                    title=l.title,
                    description=l.description,
                    order_index=l.order_index,
                    learning_objectives=l.learning_objectives,
                    prerequisites=l.prerequisites,
                    source_urls=l.source_urls,
                )
                for l in sorted(mod.lessons, key=lambda x: x.order_index)
            ]
            modules_response.append(ModuleResponse(
                id=mod.id,
                title=mod.title,
                description=mod.description,
                order_index=mod.order_index,
                lessons=lessons_response,
            ))

        return CurriculumDetailResponse(
            id=curriculum.id,
            title=curriculum.title,
            description=curriculum.description,
            topic=curriculum.topic,
            target_audience=curriculum.target_audience,
            difficulty=curriculum.difficulty,
            model_name=curriculum.model_name,
            created_at=curriculum.created_at,
            modules=modules_response,
        )


@router.post("/generate", response_model=CurriculumGenerateResponse)
def generate_curriculum(request: CurriculumGenerateRequest):
    """
    Generate a new curriculum using the AI agent.

    This endpoint:
      1. Reads ALL triples + articles from the database
      2. Sends them to the Curriculum Agent (Gemma 4 via Ollama)
      3. Validates the output with Pydantic
      4. Stores the result in PostgreSQL
      5. Returns the generated curriculum

    NOTE: This is a SYNCHRONOUS endpoint — the HTTP request blocks until
    the LLM finishes generating. For production, we'd make this async
    with a background task + polling. But for now, this works fine.

    FAILURE HANDLING:
      - If the LLM fails after retries → returns 500 with error message
      - If Pydantic validation fails → returns 500 with details
    """
    logger.info(f"Curriculum generation requested: topic='{request.topic}'")

    # Gather knowledge graph context from DB
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

    if not triples_data and not articles_data:
        raise HTTPException(
            status_code=422,
            detail="No knowledge graph data available. Run the pipeline first.",
        )

    # Initialize the AI agent and generate
    agent = CurriculumAgent(model_name="gemma4:26b", temperature=0.3, max_retries=3)

    curriculum = agent.generate_curriculum(
        topic=request.topic,
        triples=triples_data,
        articles=articles_data,
        target_audience=request.target_audience,
        difficulty=request.difficulty,
    )

    if not curriculum:
        raise HTTPException(
            status_code=500,
            detail="Curriculum generation failed after all retries. Check server logs.",
        )

    # Store the validated curriculum
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

        modules_response = []
        for mod in curriculum.modules:
            module_row = ModuleDB(
                title=mod.title,
                description=mod.description,
                order_index=mod.order_index,
                curriculum_id=curriculum_row.id,
            )
            session.add(module_row)
            session.flush()

            lessons_response = []
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
                lessons_response.append(LessonResponse(
                    id=lesson_row.id,
                    title=lesson.title,
                    description=lesson.description,
                    order_index=lesson.order_index,
                    learning_objectives=lesson.learning_objectives,
                    prerequisites=lesson.prerequisites,
                    source_urls=lesson.source_urls,
                ))

            modules_response.append(ModuleResponse(
                id=module_row.id,
                title=mod.title,
                description=mod.description,
                order_index=mod.order_index,
                lessons=lessons_response,
            ))

        session.commit()

        return CurriculumGenerateResponse(
            success=True,
            message=f"Generated curriculum with {len(curriculum.modules)} modules",
            curriculum=CurriculumDetailResponse(
                id=curriculum_row.id,
                title=curriculum.title,
                description=curriculum.description,
                topic=curriculum.topic,
                target_audience=curriculum.target_audience,
                difficulty=curriculum.difficulty,
                model_name=curriculum.model_name,
                created_at=curriculum_row.created_at,
                modules=modules_response,
            ),
        )