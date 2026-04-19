# ============================================================
# config/models.py — Central LLM Model Configuration
# ============================================================
# Implements the "Fast-Slow" architecture for our pipeline:
#   - BRAIN model: Heavy reasoning tasks (concept extraction, relationships)
#   - WORKER model: Fast JSON output tasks (ELI5, examples, exercises)
#
# Models are configured via .env variables:
#   LLM_BRAIN_MODEL=qwen3.5:27b    (17GB, ~35 tok/s on RTX 3090)
#   LLM_WORKER_MODEL=qwen3.5:9b    (6.6GB, ~80+ tok/s on RTX 3090)
#   OLLAMA_BASE_URL=http://localhost:11434
#
# WHY TWO MODELS?
#   Dense models (27B) are smart but slow — perfect for identifying concepts
#   and relationships where quality matters. Smaller models (9B) are fast at
#   generating structured JSON output, which is the bottleneck for our pipeline.
#
# WHY ENV VARS INSTEAD OF HARDCODING?
#   - Swap models without touching code (just edit .env)
#   - Different developers can use different hardware
#   - CI/CD can use API-based models instead of local
#   - Follows 12-factor app principles
# ============================================================

import os
from dotenv import load_dotenv

load_dotenv()

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")

LLM_BRAIN_MODEL = os.getenv("LLM_BRAIN_MODEL", "qwen3.5:27b")
LLM_WORKER_MODEL = os.getenv("LLM_WORKER_MODEL", "qwen3.5:9b")

MODEL_ROLE_MAP = {
    "concept_extractor": LLM_BRAIN_MODEL,
    "relationship_extractor": LLM_BRAIN_MODEL,
    "eli5_generator": LLM_WORKER_MODEL,
    "example_generator": LLM_WORKER_MODEL,
    "exercise_generator": LLM_WORKER_MODEL,
}


def get_model_name(role: str) -> str:
    """
    Get the model name for a given pipeline role.

    Args:
        role: One of 'concept_extractor', 'relationship_extractor',
              'eli5_generator', 'example_generator', 'exercise_generator'

    Returns:
        The Ollama model tag (e.g., 'qwen3.5:9b')
    """
    return MODEL_ROLE_MAP.get(role, LLM_WORKER_MODEL)
