from backend.services.path_handlers._shared import (
    _slow_executor,
    _fast_executor,
    _get_ollama_semaphore,
    _ollama_last_inference_time,
    _INFERENCE_COOLDOWN_SECONDS,
    _MAX_RESPONSE_CHARS,
    _RESOURCE_AWARE,
    _INPUT_PROCESSOR_AVAILABLE,
    SPIRIT_CORE_AVAILABLE,
    _VECTOR_AVAILABLE,
    _check_vector_available,
    _run_sync,
    _run_slow,
    _save_to_experience_pool,
)

from backend.services.path_handlers.experience_path import (
    fetch_experience,
    get_experience_context,
    get_last_response,
)

from backend.services.path_handlers.knowledge_path import fetch_knowledge
from backend.services.path_handlers.ollama_path import (
    get_available_ollama_models_async,
    get_available_ollama_model_async,
    ollama_background_save,
    fetch_ollama,
    fetch_ollama_all,
    fetch_ollama_response,
    diagnose_ollama_status,
)
from backend.services.path_handlers.external_api_path import (
    fetch_external_api,
    fetch_external_learning,
)
from backend.services.path_handlers.rule_path import fetch_rule, generate_smart_reply
from backend.services.path_handlers.fact_path import fetch_fact_assertions
from backend.services.path_handlers.tool_path import (
    fetch_tool_results,
    query_needs_tools,
    extract_tool_params,
)