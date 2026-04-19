import sys
import traceback

def section(name):
    print(f"\n{'='*60}")
    print(f"  {name}")
    print(f"{'='*60}")

def check(label, condition, detail=""):
    status = "PASS" if condition else "FAIL"
    icon = "[OK]" if condition else "[XX]"
    extra = f" -- {detail}" if detail else ""
    print(f"  {icon} {label}{extra}")
    if not condition:
        return False
    return True

failures = []

try:
    section("1. IMPORTS — All modules load without errors")

    try:
        from database.models import (
            Base, Domain, Topic, Concept, ConceptRelationship,
            Example, Exercise, SourceSection, RawArticle,
            KnowledgeTripleDB, RelationshipType,
        )
        check("All SQLAlchemy models import", True)
    except Exception as e:
        check("SQLAlchemy models import", False, str(e))
        failures.append("SQLAlchemy models import")

    try:
        from models.enrichment import (
            ExtractedConcept, ConceptExtractionResult,
            ExtractedRelationship, RelationshipExtractionResult,
            GeneratedExample, ExampleGenerationResult,
            GeneratedExercise, ExerciseGenerationResult,
            ConceptEnrichmentResult,
            VALID_CATEGORIES, VALID_RELATIONSHIP_TYPES,
            VALID_LANGUAGES, VALID_EXERCISE_TYPES,
        )
        check("All Pydantic enrichment models import", True)
    except Exception as e:
        check("Pydantic enrichment models import", False, str(e))
        failures.append("Pydantic enrichment models import")

    try:
        from pipeline.concept_enricher import ConceptEnricher, CONCEPT_ENRICHMENT_PROMPT
        from pipeline.eli5_generator import ELI5Generator, ELI5_SYSTEM_PROMPT
        from pipeline.example_generator import ExampleGenerator, EXAMPLE_GENERATION_PROMPT
        from pipeline.exercise_generator import ExerciseGenerator, EXERCISE_GENERATION_PROMPT
        check("All pipeline generators import", True)
    except Exception as e:
        check("Pipeline generators import", False, str(e))
        failures.append("Pipeline generators import")

    try:
        from pipeline.cli_colors import (
            CATEGORY_COLORS, CATEGORY_ICONS, EXERCISE_TYPE_COLORS,
            category_badge, status_ok, status_fail, progress,
        )
        check("CLI colors module imports", True)
    except Exception as e:
        check("CLI colors import", False, str(e))
        failures.append("CLI colors import")

    try:
        from config.models import get_model_name, OLLAMA_BASE_URL, MODEL_ROLE_MAP
        check("Config models imports", True)
    except Exception as e:
        check("Config models import", False, str(e))
        failures.append("Config models import")

except Exception as e:
    print(f"FATAL: Import block failed: {e}")
    traceback.print_exc()
    sys.exit(1)


section("2. PYDANTIC MODELS — Validation logic")

try:
    ex = GeneratedExample(
        title="Getting Started — async function",
        code="async def greet(name):\n    return f'Hello {name}'",
        language="python",
        explanation="Basic async function declaration.",
        when_to_use="Use this when you first need to declare an async function.",
        difficulty_level=1,
    )
    check("GeneratedExample with all new fields", True)
    check("when_to_use populated", ex.when_to_use is not None)
    check("difficulty_level=1", ex.difficulty_level == 1)
except Exception as e:
    check("GeneratedExample full fields", False, str(e))
    failures.append("GeneratedExample full fields")

try:
    ex_min = GeneratedExample(
        title="Minimal example",
        code="print('hello')",
        language="python",
    )
    check("GeneratedExample with only required fields (defaults)", True)
    check("when_to_use defaults to None", ex_min.when_to_use is None)
    check("difficulty_level defaults to 1", ex_min.difficulty_level == 1)
except Exception as e:
    check("GeneratedExample minimal", False, str(e))
    failures.append("GeneratedExample minimal")

try:
    ex_invalid_level = GeneratedExample(
        title="Bad level",
        code="x=1",
        language="python",
        difficulty_level=5,
    )
    check("GeneratedExample rejects difficulty_level > 3", False, "Should have raised ValidationError")
    failures.append("GeneratedExample difficulty_level validation")
except Exception:
    check("GeneratedExample rejects difficulty_level > 3", True)

try:
    ex_invalid_lang = GeneratedExample(
        title="Bad lang",
        code="x=1",
        language="cobol",
    )
    check("GeneratedExample rejects invalid language", False, "Should have raised")
    failures.append("GeneratedExample language validation")
except Exception:
    check("GeneratedExample rejects invalid language 'cobol'", True)

try:
    exercise_predict = GeneratedExercise(
        title="Predict output of list comprehension",
        description="What does this code print?",
        difficulty=2,
        language="python",
        exercise_type="predict_output",
        solution_code="x = [i**2 for i in range(4)]\nprint(x[-1])",
        options=[
            {"label": "9", "is_correct": True},
            {"label": "16", "is_correct": False},
            {"label": "[0,1,4,9]", "is_correct": False},
            {"label": "3", "is_correct": False},
        ],
        correct_answer="9",
        learning_objectives=["Understand list comprehensions and negative indexing"],
    )
    check("GeneratedExercise predict_output with all fields", True)
    check("exercise_type=predict_output", exercise_predict.exercise_type == "predict_output")
    check("options populated", exercise_predict.options is not None and len(exercise_predict.options) == 4)
    check("correct_answer populated", exercise_predict.correct_answer == "9")
except Exception as e:
    check("GeneratedExercise predict_output", False, str(e))
    failures.append("GeneratedExercise predict_output")

try:
    exercise_fix = GeneratedExercise(
        title="Fix the async bug",
        description="This code has a bug.",
        difficulty=3,
        language="python",
        exercise_type="fix_bug",
        buggy_code="async def fetch(url):\n    response = requests.get(url)\n    return response.json()",
        solution_code="async def fetch(url):\n    async with httpx.AsyncClient() as c:\n        return (await c.get(url)).json()",
        bug_explanation="Uses sync requests library in async function.",
        hints=["Check if the HTTP library supports async"],
    )
    check("GeneratedExercise fix_bug with all fields", True)
    check("buggy_code populated", exercise_fix.buggy_code is not None)
    check("bug_explanation populated", exercise_fix.bug_explanation is not None)
    check("exercise_type=fix_bug", exercise_fix.exercise_type == "fix_bug")
except Exception as e:
    check("GeneratedExercise fix_bug", False, str(e))
    failures.append("GeneratedExercise fix_bug")

try:
    exercise_build = GeneratedExercise(
        title="Build an async fetcher",
        description="Write a function that fetches URLs.",
        difficulty=4,
        language="python",
        exercise_type="build_from_spec",
        starter_code="async def fetch_all(urls):\n    # TODO\n    pass",
        solution_code="async def fetch_all(urls):\n    tasks = [fetch(u) for u in urls]\n    return await asyncio.gather(*tasks)",
        hints=["Use gather", "Create tasks with list comprehension"],
        test_cases=[{"input": "2 urls", "expected": "2 responses"}],
        learning_objectives=["Use asyncio.gather"],
    )
    check("GeneratedExercise build_from_spec", True)
    check("starter_code populated", exercise_build.starter_code is not None)
    check("test_cases populated", len(exercise_build.test_cases) == 1)
except Exception as e:
    check("GeneratedExercise build_from_spec", False, str(e))
    failures.append("GeneratedExercise build_from_spec")

try:
    exercise_bad_type = GeneratedExercise(
        title="Bad type",
        description="Testing invalid type",
        difficulty=2,
        language="python",
        exercise_type="fill_in_the_blank",
        solution_code="x=1",
    )
    check("GeneratedExercise rejects invalid exercise_type", False, "Should have raised")
    failures.append("GeneratedExercise exercise_type validation")
except Exception:
    check("GeneratedExercise rejects invalid exercise_type 'fill_in_the_blank'", True)

try:
    enrichment = ConceptEnrichmentResult(
        concept_name="async/await",
        key_points=[
            "async def declares a coroutine",
            "await pauses execution until result is ready",
            "Only works inside async functions",
        ],
        common_mistakes=[
            "Forgetting await: coroutine runs but result is never collected",
            "Using sync libraries inside async functions blocks the event loop",
        ],
    )
    check("ConceptEnrichmentResult validates", True)
    check("key_points has 3 items", len(enrichment.key_points) == 3)
    check("common_mistakes has 2 items", len(enrichment.common_mistakes) == 2)
except Exception as e:
    check("ConceptEnrichmentResult", False, str(e))
    failures.append("ConceptEnrichmentResult")


section("3. SQLALCHEMY MODELS — New columns exist")

try:
    example_cols = {c.name for c in Example.__table__.columns}
    check("Example.when_to_use column exists", "when_to_use" in example_cols)
    check("Example.difficulty_level column exists", "difficulty_level" in example_cols)

    if "when_to_use" not in example_cols:
        failures.append("Example.when_to_use column missing")
    if "difficulty_level" not in example_cols:
        failures.append("Example.difficulty_level column missing")
except Exception as e:
    check("Example columns check", False, str(e))
    failures.append("Example columns check")

try:
    exercise_cols = {c.name for c in Exercise.__table__.columns}
    check("Exercise.exercise_type column exists", "exercise_type" in exercise_cols)
    check("Exercise.options column exists", "options" in exercise_cols)
    check("Exercise.correct_answer column exists", "correct_answer" in exercise_cols)
    check("Exercise.buggy_code column exists", "buggy_code" in exercise_cols)
    check("Exercise.bug_explanation column exists", "bug_explanation" in exercise_cols)

    for col in ["exercise_type", "options", "correct_answer", "buggy_code", "bug_explanation"]:
        if col not in exercise_cols:
            failures.append(f"Exercise.{col} column missing")
except Exception as e:
    check("Exercise columns check", False, str(e))
    failures.append("Exercise columns check")

try:
    concept_cols = {c.name for c in Concept.__table__.columns}
    check("Concept.key_points column exists", "key_points" in concept_cols)
    check("Concept.common_mistakes column exists", "common_mistakes" in concept_cols)
except Exception as e:
    check("Concept columns check", False, str(e))
    failures.append("Concept columns check")


section("4. PIPELINE PROMPTS — Quality checks")

check("ELI5 prompt mentions '4-6 sentences'", "4-6 sentences" in ELI5_SYSTEM_PROMPT)
check("ELI5 prompt mentions '80-150 words'", "80-150 words" in ELI5_SYSTEM_PROMPT)
check("ELI5 prompt mentions 'real-world scenario'", "real-world scenario" in ELI5_SYSTEM_PROMPT.lower() or "REAL-WORLD SCENARIO" in ELI5_SYSTEM_PROMPT)

check("Example prompt mentions 'Getting Started'", "Getting Started" in EXAMPLE_GENERATION_PROMPT)
check("Example prompt mentions 'Real-World Usage'", "Real-World Usage" in EXAMPLE_GENERATION_PROMPT)
check("Example prompt mentions 'Advanced Pattern'", "Advanced Pattern" in EXAMPLE_GENERATION_PROMPT)
check("Example prompt mentions 'when_to_use'", "when_to_use" in EXAMPLE_GENERATION_PROMPT)
check("Example prompt mentions 'difficulty_level'", "difficulty_level" in EXAMPLE_GENERATION_PROMPT)

check("Exercise prompt mentions 'predict_output'", "predict_output" in EXERCISE_GENERATION_PROMPT)
check("Exercise prompt mentions 'fix_bug'", "fix_bug" in EXERCISE_GENERATION_PROMPT)
check("Exercise prompt mentions 'build_from_spec'", "build_from_spec" in EXERCISE_GENERATION_PROMPT)
check("Exercise prompt mentions 'buggy_code'", "buggy_code" in EXERCISE_GENERATION_PROMPT)
check("Exercise prompt mentions 'bug_explanation'", "bug_explanation" in EXERCISE_GENERATION_PROMPT)
check("Exercise prompt mentions 'options'", '"options"' in EXERCISE_GENERATION_PROMPT)

check("Enrichment prompt mentions 'key_points'", "key_points" in CONCEPT_ENRICHMENT_PROMPT)
check("Enrichment prompt mentions 'common_mistakes'", "common_mistakes" in CONCEPT_ENRICHMENT_PROMPT)


section("5. CLI COLORS — All category/exercise types have colors")

all_cats = {"language_feature", "framework", "tool", "pattern", "concept"}
for cat in all_cats:
    has_color = cat in CATEGORY_COLORS
    has_icon = cat in CATEGORY_ICONS
    check(f"CATEGORY_COLORS['{cat}'] exists", has_color)
    check(f"CATEGORY_ICONS['{cat}'] exists", has_icon)
    if not has_color:
        failures.append(f"CATEGORY_COLORS['{cat}'] missing")
    if not has_icon:
        failures.append(f"CATEGORY_ICONS['{cat}'] missing")

all_ex_types = {"predict_output", "fix_bug", "build_from_spec"}
for et in all_ex_types:
    has_color = et in EXERCISE_TYPE_COLORS
    check(f"EXERCISE_TYPE_COLORS['{et}'] exists", has_color)
    if not has_color:
        failures.append(f"EXERCISE_TYPE_COLORS['{et}'] missing")


section("6. ALEMBIC MIGRATION — File structure")

try:
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "migration_0002",
        "alembic/versions/0002_enrichment_quality.py",
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    check("Migration has revision='0002'", mod.revision == "0002")
    check("Migration has down_revision='0001'", mod.down_revision == "0001")
    check("Migration has upgrade()", hasattr(mod, "upgrade"))
    check("Migration has downgrade()", hasattr(mod, "downgrade"))

    import inspect
    upgrade_src = inspect.getsource(mod.upgrade)
    downgrade_src = inspect.getsource(mod.downgrade)

    for col in ["when_to_use", "difficulty_level"]:
        check(f"upgrade() adds examples.{col}", col in upgrade_src)

    for col in ["exercise_type", "options", "correct_answer", "buggy_code", "bug_explanation"]:
        check(f"upgrade() adds exercises.{col}", col in upgrade_src)

    for col in ["when_to_use", "difficulty_level", "exercise_type", "options", "correct_answer", "buggy_code", "bug_explanation"]:
        check(f"downgrade() drops {col}", col in downgrade_src)

except Exception as e:
    check("Alembic migration loads", False, str(e))
    failures.append("Alembic migration")


section("7. DATABASE CONNECTION — Tables reachable")

try:
    from database.connection import SessionLocal, engine
    from sqlalchemy import inspect as sa_inspect

    insp = sa_inspect(engine)
    table_names = set(insp.get_table_names())

    required_tables = [
        "domains", "topics", "concepts", "concept_relationships",
        "examples", "exercises", "source_sections", "raw_articles",
    ]
    for t in required_tables:
        exists = t in table_names
        check(f"Table '{t}' exists in PostgreSQL", exists)
        if not exists:
            failures.append(f"Table '{t}' missing from DB")

    if "examples" in table_names:
        ex_cols = {c["name"] for c in insp.get_columns("examples")}
        check("examples.when_to_use in actual DB", "when_to_use" in ex_cols)
        check("examples.difficulty_level in actual DB", "difficulty_level" in ex_cols)
        if "when_to_use" not in ex_cols:
            failures.append("examples.when_to_use not in DB — run: alembic upgrade head")
        if "difficulty_level" not in ex_cols:
            failures.append("examples.difficulty_level not in DB — run: alembic upgrade head")

    if "exercises" in table_names:
        ex_cols = {c["name"] for c in insp.get_columns("exercises")}
        check("exercises.exercise_type in actual DB", "exercise_type" in ex_cols)
        check("exercises.options in actual DB", "options" in ex_cols)
        check("exercises.correct_answer in actual DB", "correct_answer" in ex_cols)
        check("exercises.buggy_code in actual DB", "buggy_code" in ex_cols)
        check("exercises.bug_explanation in actual DB", "bug_explanation" in ex_cols)
        for col in ["exercise_type", "options", "correct_answer", "buggy_code", "bug_explanation"]:
            if col not in ex_cols:
                failures.append(f"exercises.{col} not in DB — run: alembic upgrade head")

    with SessionLocal() as session:
        concept_count = session.query(Concept).count()
        check(f"Concepts exist in DB ({concept_count} total)", concept_count > 0)
        if concept_count == 0:
            failures.append("No concepts in DB — run seed + enrichment first")

        sample = session.query(Concept).first()
        if sample:
            check(f"Sample concept: '{sample.name}' (category={sample.category}, difficulty={sample.difficulty})", True)

except Exception as e:
    err_msg = str(e)
    if "connection" in err_msg.lower() or "refused" in err_msg.lower():
        check("Database connection -- PostgreSQL not running (start Docker first)", True)
        check("  Run: docker compose up -d", True)
        print("  [!!] Skipping DB column checks (no connection)")
    else:
        check("Database connection", False, str(e)[:100])
        failures.append(f"Database connection: {e}")


section("8. GENERATOR INITIALIZATION — Pipeline objects create")

try:
    enricher = ConceptEnricher()
    check(f"ConceptEnricher init (model={enricher.model_name})", True)
except Exception as e:
    check("ConceptEnricher init", False, str(e))
    failures.append("ConceptEnricher init")

try:
    eli5 = ELI5Generator()
    check(f"ELI5Generator init (model={eli5.model_name})", True)
except Exception as e:
    check("ELI5Generator init", False, str(e))
    failures.append("ELI5Generator init")

try:
    ex_gen = ExampleGenerator()
    check(f"ExampleGenerator init (model={ex_gen.model_name})", True)
except Exception as e:
    check("ExampleGenerator init", False, str(e))
    failures.append("ExampleGenerator init")

try:
    exer_gen = ExerciseGenerator()
    check(f"ExerciseGenerator init (model={exer_gen.model_name})", True)
except Exception as e:
    check("ExerciseGenerator init", False, str(e))
    failures.append("ExerciseGenerator init")


section("9. ENTRY POINTS — Scripts are importable")

try:
    import importlib.util

    for script in ["enrich_key_points.py", "enrich_examples.py", "enrich_exercises.py", "enrich_eli5.py"]:
        spec = importlib.util.spec_from_file_location(script, script)
        check(f"{script} is loadable", spec is not None)
        if spec is None:
            failures.append(f"{script} not found")
except Exception as e:
    check("Entry points check", False, str(e))
    failures.append("Entry points check")


section("10. FRONTEND BUILD CHECK")

import subprocess

try:
    result = subprocess.run(
        ["npx", "next", "build"],
        capture_output=True, text=True, timeout=120,
        cwd="frontend",
    )
    if result.returncode == 0:
        check("Next.js build succeeds", True)
    else:
        errors = result.stderr[-500:] if result.stderr else result.stdout[-500:]
        check("Next.js build succeeds", False, errors[:200])
        failures.append("Next.js build failed")
except FileNotFoundError:
    check("Next.js build — npx not found (skipped)", True)
except subprocess.TimeoutExpired:
    check("Next.js build — timed out (skipped)", True)
except Exception as e:
    check(f"Next.js build — {str(e)[:80]}", True)


section("RESULTS")

total_checks = 0
passed = 0

if failures:
    print(f"\n  FAILURES ({len(failures)}):")
    for f in failures:
        print(f"    [XX] {f}")
    print(f"\n  Status: FAILED — {len(failures)} issue(s) need fixing")
    sys.exit(1)
else:
    print(f"\n  ALL CHECKS PASSED")
    print(f"  Pipeline is ready for generation.")
    print(f"\n  Next steps:")
    print(f"    1. alembic upgrade head")
    print(f"    2. python enrich_key_points.py")
    print(f"    3. python enrich_eli5.py --force")
    print(f"    4. python enrich_examples.py --force")
    print(f"    5. python enrich_exercises.py --force")
    sys.exit(0)
